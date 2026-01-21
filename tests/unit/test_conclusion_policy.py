from __future__ import annotations

from pathlib import Path

from agentdeck import AgentDeck, AgentDeckConfig, ConclusionPolicy, FixedDamageGame, MockPlayer
from agentdeck.controllers import ActionOnlyController
from agentdeck.core.base import Player


class ConclusionCapture:
    def __init__(self) -> None:
        self.events = []

    def on_player_conclusion(self, event) -> None:
        self.events.append(event)


def _run_match(policy: ConclusionPolicy, tmp_path: Path):
    capture = ConclusionCapture()
    run_dir = tmp_path / "runs"
    config = AgentDeckConfig(seed=42, run_dir=str(run_dir), conclusion=policy)
    with AgentDeck(game=FixedDamageGame(), session=config, spectators=[capture]) as deck:
        results = deck.play(players=[MockPlayer("Alice"), MockPlayer("Bob")], matches=1)
    return results.single, capture


def test_conclusion_policy_disabled_skips_events(tmp_path: Path):
    result, capture = _run_match(ConclusionPolicy(enabled=False), tmp_path)
    assert result.winner is not None
    assert capture.events == []


def test_conclusion_policy_winner_only(tmp_path: Path):
    result, capture = _run_match(ConclusionPolicy(enabled=True, mode="winner"), tmp_path)
    assert result.winner is not None
    assert len(capture.events) == 1
    assert capture.events[0].data["player"] == result.winner


def test_conclusion_policy_loser_only(tmp_path: Path):
    result, capture = _run_match(ConclusionPolicy(enabled=True, mode="loser"), tmp_path)
    assert result.winner is not None
    assert len(capture.events) == 1
    assert capture.events[0].data["player"] != result.winner


def test_conclusion_policy_specific_player(tmp_path: Path):
    _, capture = _run_match(
        ConclusionPolicy(enabled=True, mode="specific", player="Bob"), tmp_path
    )
    assert len(capture.events) == 1
    assert capture.events[0].data["player"] == "Bob"


def test_conclusion_event_payload_fields(tmp_path: Path):
    _, capture = _run_match(ConclusionPolicy(enabled=True, mode="all"), tmp_path)
    assert len(capture.events) == 2

    event = capture.events[0]
    data = event.data

    assert "reflection_text" in data
    assert "outcome" in data
    assert "prompt_text" in data
    assert "prompt_blocks" in data
    assert "response_text" in data
    assert isinstance(data["prompt_blocks"], list)


def test_conclusion_policy_default_conclude_records_prompt(tmp_path: Path):
    class BaseConcludePlayer(Player):
        def __init__(self, name: str):
            super().__init__(name=name, controller=ActionOnlyController())

        def get_response(self, prompt: str) -> str:
            prompt_lower = prompt.lower()
            if "ready to begin" in prompt_lower or "respond 'ok'" in prompt_lower:
                return "OK"
            return "ATTACK"

    run_dir = tmp_path / "runs"
    config = AgentDeckConfig(
        seed=42,
        run_dir=str(run_dir),
        conclusion=ConclusionPolicy(enabled=True, mode="all"),
    )

    capture = ConclusionCapture()
    with AgentDeck(
        game=FixedDamageGame(), session=config, spectators=[capture]
    ) as deck:
        deck.play(players=[BaseConcludePlayer("Alice"), BaseConcludePlayer("Bob")], matches=1)

    assert len(capture.events) == 2
    for event in capture.events:
        assert event.data["prompt_text"]
        assert isinstance(event.data["prompt_blocks"], list)
