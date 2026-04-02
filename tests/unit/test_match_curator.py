"""Unit tests for MatchCurator sidecar generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentdeck.core.types import Event, MatchResult
from agentdeck.spectators.curator import MatchCurator, MatchCuratorPayload, MatchHighlight, curate_match_file


class MockGame:
    """Mock game for curator tests."""


class MockPlayer:
    """Mock player carrying only a name."""

    def __init__(self, name: str):
        self.name = name


def _gameplay_event(
    *,
    turn: int,
    player: str,
    action: str,
    before: dict,
    after: dict,
) -> Event:
    return Event(
        type="gameplay",
        data={
            "mechanic": "turn_based",
            "player": player,
            "action": action,
            "state_before": before,
            "state_after": after,
            "turn_context": {"turn_number": turn},
        },
        context={"turn_index": turn - 1, "match_id": "match-test"},
    )


def _match_result(*, winner: str | None = "Alice", turns: int = 3) -> MatchResult:
    return MatchResult(
        winner=winner,
        final_state={"health": {"Alice": 40, "Bob": 0}, "turn": turns},
        events=[],
        seed=42,
        metadata={"turns": turns},
    )


def test_match_curator_writes_sidecar_from_source_path(tmp_path: Path):
    source = tmp_path / "match_demo.json"
    source.write_text("{}", encoding="utf-8")

    def generator(_snapshot):
        return MatchCuratorPayload(
            version=1,
            subtitle="Test subtitle",
            synopsis="Test synopsis naming the key moment.",
            highlights=[MatchHighlight(turn=2, label="Key moment", kind="turning_point")],
        )

    curator = MatchCurator(source_path=source, generator=generator)
    curator.on_match_start(
        game=MockGame(),
        players=[MockPlayer("Alice"), MockPlayer("Bob")],
        match_id="match-test",
    )
    curator.on_gameplay(
        _gameplay_event(
            turn=1,
            player="Alice",
            action="ATTACK",
            before={"health": {"Alice": 60, "Bob": 60}, "turn": 1},
            after={"health": {"Alice": 60, "Bob": 45}, "turn": 2},
        )
    )
    curator.on_match_end(_match_result())

    sidecar = source.with_suffix(".meta.json")
    assert sidecar.exists()

    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["subtitle"] == "Test subtitle"
    assert payload["synopsis"] == "Test synopsis naming the key moment."
    assert payload["highlights"] == [{"turn": 2, "label": "Key moment", "kind": "turning_point"}]
    assert curator.last_output_path == sidecar


def test_match_curator_keeps_metadata_in_memory_without_output_target():
    curator = MatchCurator()
    curator.on_match_start(
        game=MockGame(),
        players=[MockPlayer("Alice"), MockPlayer("Bob")],
        match_id="match-test",
    )
    curator.on_gameplay(
        _gameplay_event(
            turn=1,
            player="Alice",
            action="ATTACK",
            before={"health": {"Alice": 60, "Bob": 60}, "turn": 1},
            after={"health": {"Alice": 60, "Bob": 45}, "turn": 2},
        )
    )
    curator.on_match_end(_match_result(turns=1))

    assert curator.last_metadata is not None
    assert curator.last_output_path is None
    assert curator.last_metadata.subtitle
    assert curator.last_metadata.synopsis
    assert curator.last_metadata.highlights


def test_match_curator_default_generator_produces_valid_payload():
    curator = MatchCurator(include_transcript=True)
    curator.on_match_start(
        game=MockGame(),
        players=[MockPlayer("Alice"), MockPlayer("Bob")],
        match_id="match-test",
    )
    curator.on_gameplay(
        _gameplay_event(
            turn=1,
            player="Alice",
            action="ATTACK",
            before={"health": {"Alice": 60, "Bob": 60}, "turn": 1},
            after={"health": {"Alice": 60, "Bob": 45}, "turn": 2},
        )
    )
    curator.on_gameplay(
        _gameplay_event(
            turn=2,
            player="Bob",
            action="POTION",
            before={"health": {"Alice": 60, "Bob": 45}, "potions": {"Bob": 1}, "turn": 2},
            after={"health": {"Alice": 60, "Bob": 60}, "potions": {"Bob": 0}, "turn": 3},
        )
    )
    curator.on_gameplay(
        _gameplay_event(
            turn=3,
            player="Alice",
            action="ATTACK",
            before={"health": {"Alice": 60, "Bob": 15}, "turn": 3},
            after={"health": {"Alice": 60, "Bob": 0}, "turn": 4},
        )
    )
    curator.on_match_end(_match_result(turns=3))

    payload = curator.last_metadata
    assert payload is not None
    assert payload.version == 1
    assert payload.subtitle
    assert payload.synopsis
    assert payload.transcript is not None
    assert [highlight.turn for highlight in payload.highlights] == sorted(
        highlight.turn for highlight in payload.highlights
    )
    assert all(len(highlight.label) <= 50 for highlight in payload.highlights)
    assert all(highlight.kind in {None, "mistake", "smart_move", "surprise", "turning_point"} for highlight in payload.highlights)


def test_match_curator_rejects_overlong_highlight_labels():
    def generator(_snapshot):
        return {
            "subtitle": "Test subtitle",
            "synopsis": "Test synopsis.",
            "highlights": [{"turn": 1, "label": "x" * 51}],
        }

    curator = MatchCurator(generator=generator)
    curator.on_match_start(
        game=MockGame(),
        players=[MockPlayer("Alice"), MockPlayer("Bob")],
        match_id="match-test",
    )

    with pytest.raises(ValueError, match="<= 50 characters"):
        curator.on_match_end(_match_result(turns=1))


def test_match_curator_rejects_invalid_highlight_kind():
    def generator(_snapshot):
        return {
            "subtitle": "Test subtitle",
            "synopsis": "Test synopsis.",
            "highlights": [{"turn": 1, "kind": "wild", "label": "Bad kind"}],
        }

    curator = MatchCurator(generator=generator)
    curator.on_match_start(
        game=MockGame(),
        players=[MockPlayer("Alice"), MockPlayer("Bob")],
        match_id="match-test",
    )

    with pytest.raises(ValueError, match="highlight kind must be one of"):
        curator.on_match_end(_match_result(turns=1))


def test_curate_match_file_replays_and_writes_sidecar(tmp_path: Path):
    match_path = tmp_path / "match_demo.json"
    match_payload = {
        "schema_version": "1.3",
        "match_id": "match-demo",
        "game": "FixedDamageGame",
        "players": ["Alice", "Bob"],
        "winner": "Alice",
        "seed": 42,
        "final_state": {"health": {"Alice": 40, "Bob": 0}, "turn": 2},
        "metadata": {"match": {"turns": 2}},
        "events": [
            {
                "type": "gameplay",
                "timestamp": 1,
                "context": {"turn_index": 0, "match_id": "match-demo"},
                "data": {
                    "player": "Alice",
                    "action": "ATTACK",
                    "state_before": {"health": {"Alice": 60, "Bob": 60}, "turn": 1},
                    "state_after": {"health": {"Alice": 60, "Bob": 20}, "turn": 2},
                    "turn_context": {"turn_number": 1},
                },
            },
            {
                "type": "gameplay",
                "timestamp": 2,
                "context": {"turn_index": 1, "match_id": "match-demo"},
                "data": {
                    "player": "Alice",
                    "action": "ATTACK",
                    "state_before": {"health": {"Alice": 60, "Bob": 20}, "turn": 2},
                    "state_after": {"health": {"Alice": 60, "Bob": 0}, "turn": 3},
                    "turn_context": {"turn_number": 2},
                },
            },
        ],
    }
    match_path.write_text(json.dumps(match_payload), encoding="utf-8")

    curator = curate_match_file(match_path)

    assert curator.last_metadata is not None
    assert match_path.with_suffix(".meta.json").exists()
