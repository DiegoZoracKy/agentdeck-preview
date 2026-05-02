import json
import os
import subprocess
import sys
from pathlib import Path

from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    ArchivistChoiceGame,
    FixedDamageGame,
    LogLevel,
    MockPlayer,
)
from agentdeck.controllers import ActionOnlyController
from agentdeck.core.logging import InMemoryLogHandler


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_first_game_walkthrough_uses_one_recording_path(tmp_path, monkeypatch):
    from examples.first_game_walkthrough import run_and_replay

    monkeypatch.chdir(tmp_path)

    run_and_replay()

    recordings = sorted((tmp_path / "agentdeck_records" / "first_game").rglob("match_*.json"))
    assert len(recordings) == 1
    assert recordings[0].parent.name == "records"


def test_schema_validator_runs_offline_without_openai_key(tmp_path):
    recording = tmp_path / "match_offline.json"
    recording.write_text(
        json.dumps(
            {
                "schema_version": "1.3",
                "schema_type": "match",
                "match_id": "match_offline",
                "game": "FixedDamageGame",
                "players": ["Alice", "Bob"],
                "winner": "Alice",
                "final_state": {},
                "events": [
                    {
                        "type": "gameplay",
                        "data": {
                            "player": "Alice",
                            "action": "ATTACK",
                            "state_before": {},
                            "state_after": {},
                        },
                        "context": {"turn_index": 0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "scripts/validate_schema_v1_3.py", str(recording)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OPENAI_API_KEY" not in result.stdout
    assert "Result: PASS" in result.stdout


def test_match_reporter_owns_visible_turn_narration(tmp_path):
    config = AgentDeckConfig(
        seed=42,
        run_dir=str(tmp_path),
        log_level=None,
        log_file_levels=[LogLevel.DEBUG],
    )
    handler = InMemoryLogHandler()
    players = [
        MockPlayer(name="Alice", actions=["ATTACK", "ATTACK", "ATTACK"]),
        MockPlayer(name="Bob", actions=["POTION", "ATTACK", "ATTACK"]),
    ]

    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        deck.logger.logger.addHandler(handler)
        deck.play(players=players, matches=1, seed=42)

    info_messages = [
        record.getMessage() for record in handler.records if record.levelname == "INFO"
    ]
    debug_messages = [
        record.getMessage() for record in handler.records if record.levelname == "DEBUG"
    ]

    assert sum(message.startswith("Turn 1:") for message in info_messages) == 1
    assert sum(message.startswith("Turn 1:") for message in debug_messages) == 1
    assert not any(message.startswith("First player selected:") for message in info_messages)
    assert any("First player selected:" in message for message in debug_messages)


def test_archivist_choice_game_runs_without_api_keys(tmp_path):
    controller = ActionOnlyController()
    players = [
        MockPlayer(
            name="Cataloger",
            actions=["CATALOG", "CATALOG", "CATALOG", "CATALOG"],
            controller=controller,
        ),
        MockPlayer(
            name="Conservator",
            actions=["RESTORE", "QUARANTINE", "CATALOG", "RESTORE"],
            controller=controller,
        ),
    ]
    config = AgentDeckConfig(
        seed=11,
        run_dir=str(tmp_path),
        log_level=None,
        log_file_levels=[],
    )

    with AgentDeck(game=ArchivistChoiceGame(), session=config, spectators=[]) as deck:
        results = deck.play(players=players, matches=1, seed=11)
        record_dir = Path(deck.session.record_directory)

    assert results.single.winner == "Conservator"
    assert results.single.final_state["scores"] == {"Cataloger": 3, "Conservator": 11}
    assert len(results.single.final_state["processed"]["Conservator"]) == 4
    assert len(list(record_dir.glob("match_*.json"))) == 1
