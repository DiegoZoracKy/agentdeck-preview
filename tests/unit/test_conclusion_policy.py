from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentdeck import AgentDeck, AgentDeckConfig, ConclusionPolicy, FixedDamageGame, MockPlayer
from agentdeck.controllers import ActionOnlyController
from agentdeck.core.base import Player


class ConclusionCapture:
    def __init__(self) -> None:
        self.events = []

    def on_player_conclusion(self, event) -> None:
        self.events.append(event)


class PrivateConclusionGame(FixedDamageGame):
    """Keep an oracle in canonical state while exposing only the public view."""

    def setup(self, players, seed):
        state = super().setup(players, seed)
        state["private_oracle"] = "CONCLUSION_PRIVATE_ORACLE_7B3F"
        return state

    def get_view(self, game_state, player):
        view = super().get_view(game_state, player)
        view.pop("private_oracle", None)
        return view


class TemplateConclusionPlayer(Player):
    def __init__(self, name: str):
        super().__init__(name=name, controller=ActionOnlyController())

    def get_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "ready to begin" in prompt_lower or "respond 'ok'" in prompt_lower:
            return "OK"
        return "ATTACK"


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
    _, capture = _run_match(ConclusionPolicy(enabled=True, mode="specific", player="Bob"), tmp_path)
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
    with AgentDeck(game=FixedDamageGame(), session=config, spectators=[capture]) as deck:
        deck.play(players=[BaseConcludePlayer("Alice"), BaseConcludePlayer("Bob")], matches=1)

    assert len(capture.events) == 2
    for event in capture.events:
        assert event.data["prompt_text"]
        assert isinstance(event.data["prompt_blocks"], list)


@pytest.mark.parametrize(("concurrency", "matches"), [(1, 1), (2, 2)])
def test_cv1_default_conclusion_uses_player_visible_terminal_state(
    tmp_path: Path, concurrency: int, matches: int
):
    capture = ConclusionCapture()
    config = AgentDeckConfig(
        seed=42,
        run_dir=str(tmp_path / "runs"),
        concurrency=concurrency,
        conclusion=ConclusionPolicy(enabled=True, mode="all"),
    )

    with AgentDeck(game=PrivateConclusionGame(), session=config, spectators=[capture]) as deck:
        results = deck.play(
            players=[TemplateConclusionPlayer("Alice"), TemplateConclusionPlayer("Bob")],
            matches=matches,
        )

    assert len(capture.events) == matches * 2
    assert all(
        "CONCLUSION_PRIVATE_ORACLE_7B3F" not in event.data["prompt_text"]
        for event in capture.events
    )
    assert all(
        result.final_state["private_oracle"] == "CONCLUSION_PRIVATE_ORACLE_7B3F"
        for result in results
    )

    record_paths = sorted((tmp_path / "runs").glob("session_*/records/match_*.json"))
    assert len(record_paths) == matches
    assert all(
        json.loads(path.read_text())["final_state"]["private_oracle"]
        == "CONCLUSION_PRIVATE_ORACLE_7B3F"
        for path in record_paths
    )
