"""Tests for Match Surface projection spectator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentdeck.core.types import Event, MatchResult
from agentdeck.spectators.match_surface import (
    InMemorySink,
    JsonArtifactSink,
    MatchSurfaceProjector,
)


class MockGame:
    pass


class MockPlayer:
    def __init__(self, name: str):
        self.name = name

    def get_summary(self):
        return {"name": self.name, "type": "MockPlayer"}


def _gameplay_event() -> Event:
    return Event(
        type="gameplay",
        data={
            "match_id": "match-1",
            "mechanic": "turn_based",
            "phase_index": 0,
            "player": "Alice",
            "action": {
                "value": "ATTACK",
                "reasoning": "Finish the match.",
                "metadata": {"parser_success": True},
            },
            "interaction": {
                "prompt_text": "Take your turn.",
                "prompt_blocks": [{"role": "system", "content": "Take your turn."}],
                "response_text": "REASONING: Finish\nACTION: ATTACK",
                "usage_info": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "tokens": 15,
                    "cost": 0.0002,
                    "latency_ms": 123,
                },
                "renderer_output": {"template_id": "default"},
                "controller_format": "ACTION: <MOVE>",
                "controller_metadata": {"allowed": ["ATTACK", "POTION"]},
            },
            "state_before": {"health": {"Alice": 40, "Bob": 20}},
            "state_after": {"health": {"Alice": 40, "Bob": 0}},
            "turn_context": {"turn_number": 1, "phase_index": 0},
        },
        context={"match_id": "match-1", "phase_index": 0},
        timestamp=1000.0,
    )


def test_match_surface_projector_builds_decision_frame():
    sink = InMemorySink()
    projector = MatchSurfaceProjector(sink=sink)

    projector.on_match_start(MockGame(), [MockPlayer("Alice"), MockPlayer("Bob")], "match-1")
    projector.on_gameplay(_gameplay_event())
    projector.on_match_end(
        MatchResult(
            winner="Alice",
            final_state={"health": {"Alice": 40, "Bob": 0}},
            events=[],
            seed=42,
            metadata={"turns": 1},
        )
    )

    assert sink.document is not None
    document = sink.document
    assert document["schema_type"] == "match_surface"
    assert document["source"]["record_schema_version"] == "2.0"
    assert document["match"]["winner"] == "Alice"
    assert document["players"] == [
        {"name": "Alice", "type": "MockPlayer"},
        {"name": "Bob", "type": "MockPlayer"},
    ]

    frame = document["frames"][0]
    assert frame["phase_index"] == 0
    assert frame["action"]["value"] == "ATTACK"
    assert frame["interaction"]["response_text"] == "REASONING: Finish\nACTION: ATTACK"
    assert frame["state_delta"] == {"health.Bob": {"before": 20, "after": 0}}
    assert frame["economics"]["cost"] == 0.0002
    assert document["economics"]["total_calls"] == 1
    assert document["economics"]["total_tokens"] == 15


def test_match_surface_projector_rejects_old_gameplay_shape():
    sink = InMemorySink()
    projector = MatchSurfaceProjector(sink=sink)
    event = _gameplay_event()
    event.data["action"] = "ATTACK"

    with pytest.raises(ValueError, match="canonical action.value"):
        projector.on_gameplay(event)


def test_match_surface_redactor_runs_before_json_write(tmp_path: Path):
    sink = JsonArtifactSink(tmp_path)

    def redactor(document):
        redacted = dict(document)
        redacted["players"] = [{"name": "REDACTED"}]
        return redacted

    projector = MatchSurfaceProjector(sink=sink, redactor=redactor)
    projector.on_match_start(MockGame(), [MockPlayer("Alice")], "match-1")
    projector.on_gameplay(_gameplay_event())
    projector.on_match_end(
        MatchResult(winner="Alice", final_state={}, events=[], seed=1, metadata={"turns": 1})
    )

    artifact = tmp_path / "match-1.json"
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["players"] == [{"name": "REDACTED"}]
    assert sink.last_path == artifact


def test_match_surface_marker_provider_isolated():
    class BrokenProvider:
        def markers_for_frame(self, frame):
            raise RuntimeError("boom")

    sink = InMemorySink()
    projector = MatchSurfaceProjector(sink=sink, marker_providers=[BrokenProvider()])
    projector.on_match_start(MockGame(), [MockPlayer("Alice")], "match-1")
    projector.on_gameplay(_gameplay_event())

    assert projector.diagnostics[0]["kind"] == "marker_provider_error"
    assert sink.frames[0]["markers"] == []
