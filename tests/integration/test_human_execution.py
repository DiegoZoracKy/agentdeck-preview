"""End-to-end human-controlled execution and Record/replay coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentdeck import (
    ActionOnlyController,
    AgentDeck,
    AgentDeckConfig,
    ConclusionPolicy,
    FixedDamageGame,
    HangmanGame,
    HumanPlayer,
    MockPlayer,
    Spectator,
)
from agentdeck.core.console import ParallelExecutionError
from agentdeck.core.types import Event, EventType


class GameplayCapture(Spectator):
    def __init__(self) -> None:
        self.events: list[Event] = []

    def on_gameplay(self, event: Event) -> None:
        self.events.append(event)


def _config(run_dir: Path, *, max_turns: int = 10, concurrency: int = 1) -> AgentDeckConfig:
    return AgentDeckConfig(
        seed=7,
        run_dir=str(run_dir),
        max_turns=max_turns,
        concurrency=concurrency,
        first_player_policy="fixed",
        fixed_first_player_index=0,
        log_level=None,
        log_file_levels=[],
        conclusion=ConclusionPolicy(enabled=False),
    )


def _record(directory: str) -> tuple[Path, dict[str, Any]]:
    path = next(Path(directory).glob("match_*.json"))
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_human_can_play_hangman_and_replay_the_exact_record(tmp_path: Path) -> None:
    responses = iter(["OK", "ACTION: A"])
    prompts: list[str] = []

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return next(responses)

    capture = GameplayCapture()
    player = HumanPlayer(
        "Human",
        controller=ActionOnlyController(),
        response_reader=read,
    )
    with AgentDeck(
        game=HangmanGame(word_list=["A"]),
        session=_config(tmp_path / "hangman"),
    ) as deck:
        results = deck.play(players=[player], matches=1)
        record_path, record = _record(deck.session.record_directory)
        deck.replay(path=record_path, spectators=[capture], speed=0.0)

    assert results.matches[0].winner == "Human"
    assert len(prompts) == 2
    assert record["metadata"]["player_configs"]["Human"]["interaction"] == {
        "authority": "human",
        "mode": "callable",
    }
    assert "model" not in record["metadata"]["player_configs"]["Human"]
    assert "total_cost" not in record["metadata"]["player_summaries"][0]
    assert record["metadata"]["match"]["player_costs"] == {}

    live_gameplay = next(event for event in record["events"] if event["type"] == "gameplay")
    assert live_gameplay["data"]["player"] == "Human"
    assert live_gameplay["data"]["action"]["value"] == "A"
    assert live_gameplay["data"]["interaction"]["response_text"] == "ACTION: A"
    assert live_gameplay["data"]["interaction"]["usage_info"] is None

    assert len(capture.events) == 1
    assert capture.events[0].type == EventType.GAMEPLAY.value
    assert capture.events[0].data["interaction"]["response_text"] == "ACTION: A"


def test_human_can_play_fixed_damage_against_an_existing_player(tmp_path: Path) -> None:
    responses = iter(["OK", "ACTION: ATTACK"])
    human = HumanPlayer(
        "Human",
        controller=ActionOnlyController(),
        response_reader=lambda _prompt: next(responses),
    )
    mock = MockPlayer("Mock", actions=["ATTACK"], controller=ActionOnlyController())
    game = FixedDamageGame(max_health=20, attack_damage=20)

    with AgentDeck(game=game, session=_config(tmp_path / "fixed")) as deck:
        results = deck.play(players=[human, mock], matches=1)
        _, record = _record(deck.session.record_directory)

    assert results.matches[0].winner == "Human"
    gameplay = [event for event in record["events"] if event["type"] == "gameplay"]
    assert len(gameplay) == 1
    assert gameplay[0]["data"]["player"] == "Human"
    assert gameplay[0]["data"]["action"]["value"] == "ATTACK"
    assert record["metadata"]["match"]["player_costs"] == {}


def test_parallel_human_execution_fails_before_requesting_input(tmp_path: Path) -> None:
    prompts: list[str] = []

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return "OK"

    human = HumanPlayer(
        "Human",
        controller=ActionOnlyController(),
        response_reader=read,
    )
    mock = MockPlayer("Mock", actions=["ATTACK"], controller=ActionOnlyController())

    with AgentDeck(
        game=FixedDamageGame(max_health=20, attack_damage=20),
        session=_config(tmp_path / "parallel", concurrency=2),
    ) as deck:
        with pytest.raises(ParallelExecutionError, match="concurrency=1"):
            deck.play(players=[human, mock], matches=2)

    assert prompts == []
