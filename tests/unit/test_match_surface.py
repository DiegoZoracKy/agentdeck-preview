"""Tests for Match Surface projection spectator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentdeck.core.replay import ReplayEngine
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
                "provider_call": {
                    "schema_version": "0.1",
                    "call_id": "call-audit-1",
                    "context_selection": {
                        "policy": {"id": "full_history", "version": "1", "parameters": {}},
                        "selected_history_messages": 2,
                        "available_history_messages": 2,
                        "selected_message_ids": ["handshake-user", "handshake-assistant"],
                        "omitted_message_ids": [],
                    },
                    "composed_input": {
                        "messages": [
                            {"role": "user", "content": "Handshake"},
                            {"role": "assistant", "content": "READY"},
                            {"role": "user", "content": "Take your turn."},
                        ],
                        "current_message_index": 2,
                        "ordered_messages_sha256": "abc123",
                    },
                    "sdk_request": {
                        "sdk": "openai",
                        "method": "openai.responses.create",
                        "arguments": {"model": "gpt-test", "input": []},
                        "arguments_sha256": "def456",
                        "assurance": "sent_to_official_sdk",
                    },
                    "sdk_response": {"response_text": "ACTION: ATTACK"},
                    "attempts": [{"attempt": 1, "outcome": "completed"}],
                },
            },
            "state_before": {"health": {"Alice": 40, "Bob": 20}},
            "state_after": {"health": {"Alice": 40, "Bob": 0}},
            "turn_context": {"turn_number": 1, "phase_index": 0},
        },
        context={"match_id": "match-1", "phase_index": 0},
        timestamp=1000.0,
    )


def test_MSP21_MSP22_match_surface_projector_builds_auditable_decision_frame():
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
    assert frame["turn_context"]["turn_number"] == 1
    assert frame["turn_context"].get("rng_seed") is None
    assert frame["interaction"]["response_text"] == "REASONING: Finish\nACTION: ATTACK"
    assert frame["interaction"]["provider_call"]["sdk_request"]["method"] == "openai.responses.create"
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


def test_msp20_json_sink_rejects_path_escape_before_write(tmp_path: Path):
    """MSP20: record-provided match IDs cannot escape the artifact root."""
    sink = JsonArtifactSink(tmp_path / "surfaces")
    document = {"match": {"match_id": "../escaped"}, "frames": []}

    with pytest.raises(ValueError, match="match_id"):
        sink.finish(document)

    assert not (tmp_path / "escaped.json").exists()


def test_msp20_json_sink_rejects_non_json_without_replacing(tmp_path: Path):
    """MSP20/AS5: strict JSON failure leaves the previous artifact unchanged."""
    sink = JsonArtifactSink(tmp_path)
    artifact = tmp_path / "match-1.json"
    artifact.write_text('{"preserved": true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="strict JSON"):
        sink.finish({"match": {"match_id": "match-1"}, "bad": {"set"}})

    assert artifact.read_text(encoding="utf-8") == '{"preserved": true}\n'


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


def test_CTA4_MSP23_match_surface_keeps_historical_lifecycle_without_provider_call():
    sink = InMemorySink()
    projector = MatchSurfaceProjector(sink=sink)
    projector.on_match_start(MockGame(), [MockPlayer("Alice")], "match-1")
    projector.on_player_handshake_start(
        Event(
            type="player_handshake_start",
            data={"player": "Alice", "prompt_text": "Acknowledge the rules."},
            context={"match_id": "match-1"},
            timestamp=10.0,
        )
    )
    projector.on_player_handshake_complete(
        Event(
            type="player_handshake_complete",
            data={"player": "Alice", "response_text": "OK"},
            context={"match_id": "match-1"},
            timestamp=11.0,
        )
    )
    projector.on_player_conclusion(
        Event(
            type="player_conclusion",
            data={"player": "Alice", "response_text": "I used a potion at low health."},
            context={"match_id": "match-1"},
            timestamp=12.0,
        )
    )
    projector.on_match_end(
        MatchResult(winner="Alice", final_state={}, events=[], seed=1, metadata={"turns": 0})
    )

    assert sink.document is not None
    assert sink.document["schema_version"] == "0.2"
    assert [entry["state"] for entry in sink.document["handshakes"]] == ["started", "accepted"]
    assert all("provider_call" not in entry for entry in sink.document["handshakes"])
    assert sink.document["conclusions"] == [
        {
            "player": "Alice",
            "state": "agent_self_report",
            "phase": "conclusion",
            "prompt_text": None,
            "prompt_blocks": None,
            "response_text": "I used a potion at low health.",
            "controller_metadata": None,
            "usage_info": None,
            "timestamp": 12.0,
        }
    ]
    assert "provider_call" not in sink.document["conclusions"][0]


def test_match_surface_preserves_handshakes_emitted_before_match_start():
    """Replay lifecycle emits Handshake before MATCH_START (SPEC-REPLAY LC2)."""
    sink = InMemorySink()
    projector = MatchSurfaceProjector(sink=sink)
    projector.on_player_handshake_start(
        Event(
            type="player_handshake_start",
            data={"player": "Alice", "prompt_text": "Acknowledge the rules."},
            context={"match_id": "match-1"},
            timestamp=10.0,
        )
    )
    projector.on_player_handshake_complete(
        Event(
            type="player_handshake_complete",
            data={"player": "Alice", "response_text": "OK"},
            context={"match_id": "match-1"},
            timestamp=11.0,
        )
    )

    projector.on_match_start(MockGame(), [MockPlayer("Alice")], "match-1")
    projector.on_match_end(
        MatchResult(winner="Alice", final_state={}, events=[], seed=1, metadata={"turns": 0})
    )

    assert sink.document is not None
    assert sink.document["players"] == [{"name": "Alice", "type": "MockPlayer"}]
    assert [entry["state"] for entry in sink.document["handshakes"]] == ["started", "accepted"]


def test_match_surface_replay_preserves_recorded_player_models():
    """SPEC-MATCH-SURFACE MSP19: replay keeps recorded Player identity."""
    recording = {
        "schema_version": "2.0",
        "schema_type": "match",
        "match_id": "match-identity",
        "game": "MockGame",
        "players": ["Alice", "Bob"],
        "winner": None,
        "final_state": {},
        "seed": 1,
        "events": [],
        "metadata": {
            "match_id": "match-identity",
            "players": ["Alice", "Bob"],
            "player_summaries": [
                {
                    "name": "Alice",
                    "type": "GPTPlayer",
                    "model": "gpt-4o-mini",
                    "total_cost": 0.001,
                },
                {
                    "name": "Bob",
                    "type": "ClaudePlayer",
                    "model": "claude-haiku",
                    "total_cost": 0.002,
                },
            ],
        },
    }
    sink = InMemorySink()

    ReplayEngine(recording).replay(spectators=[MatchSurfaceProjector(sink=sink)], speed=0.0)

    assert sink.document is not None
    assert sink.document["players"] == [
        {"name": "Alice", "type": "GPTPlayer", "model": "gpt-4o-mini"},
        {"name": "Bob", "type": "ClaudePlayer", "model": "claude-haiku"},
    ]


def test_match_surface_redacts_start_and_frame_emissions():
    sink = InMemorySink()

    def redactor(payload):
        payload.pop("interaction", None)
        if "players" in payload:
            payload["players"] = [{"name": "REDACTED"}]
        return payload

    projector = MatchSurfaceProjector(sink=sink, redactor=redactor)
    projector.on_match_start(MockGame(), [MockPlayer("Alice")], "match-1")
    projector.on_gameplay(_gameplay_event())

    assert sink.started["players"] == [{"name": "REDACTED"}]
    assert "interaction" not in sink.frames[0]
