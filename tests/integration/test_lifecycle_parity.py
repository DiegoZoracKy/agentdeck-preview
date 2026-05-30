"""Integration tests for live/replay event stream parity."""

import tempfile
from pathlib import Path
from typing import List

import pytest

from agentdeck import AgentDeck, AgentDeckConfig, FixedDamageGame, MockPlayer, Recorder
from agentdeck.core.replay import ReplayEngine
from agentdeck.core.types import Event, EventType
from agentdeck.spectators.match_surface import InMemorySink, MatchSurfaceProjector


class EventCapture:
    """Spy that captures all lifecycle events in order."""

    def __init__(self):
        self.events: List[Event] = []

    def on_player_handshake_start(self, event: Event):
        self.events.append(event)

    def on_player_handshake_complete(self, event: Event):
        self.events.append(event)

    def on_player_handshake_abort(self, event: Event):
        self.events.append(event)

    def on_match_start(self, event: Event):
        self.events.append(event)

    def on_gameplay(self, event: Event):
        self.events.append(event)

    def on_match_end(self, event: Event):
        self.events.append(event)

    def on_player_conclusion(self, event: Event):
        self.events.append(event)


@pytest.fixture
def temp_recording_dir():
    """Create temporary directory for recordings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _event_type(event: Event) -> str:
    return event.type.value if isinstance(event.type, EventType) else event.type


def _events_of_type(events: List[Event], event_type: EventType) -> List[Event]:
    return [event for event in events if _event_type(event) == event_type.value]


def _gameplay_payloads(events: List[Event]) -> List[dict]:
    return [event.data for event in _events_of_type(events, EventType.GAMEPLAY)]


def _assert_canonical_gameplay(event: Event) -> None:
    data = event.data
    context = event.context

    assert data["mechanic"] == "turn_based"
    assert isinstance(data["phase_index"], int)
    assert context["phase_index"] == data["phase_index"]
    assert "turn_index" not in data
    assert "turn_index" not in context
    assert "prompt" not in data
    assert "prompt_text" not in data
    assert "response_text" not in data
    assert "usage_info" not in data

    action = data["action"]
    assert set(action) == {"value", "reasoning", "metadata"}
    assert "action" not in action
    assert "raw_response" not in action

    interaction = data["interaction"]
    for key in (
        "prompt_text",
        "prompt_blocks",
        "response_text",
        "usage_info",
        "renderer_output",
        "controller_format",
        "controller_metadata",
    ):
        assert key in interaction


def _surface_frames_without_timestamps(document: dict) -> list[dict]:
    frames = []
    for frame in document["frames"]:
        clone = {**frame, "source_event": dict(frame["source_event"])}
        clone["source_event"].pop("timestamp", None)
        context = dict(clone["source_event"].get("context") or {})
        context.pop("timestamp", None)
        context.pop("monotonic_time", None)
        clone["source_event"]["context"] = context
        frames.append(clone)
    return frames


def test_live_vs_replay_event_parity(temp_recording_dir):
    """
    Verify live and replay emit matching event streams (SPEC-REPLAY R1/EP1-EP3).

    This test enforces the R1 parity guarantee by comparing live execution
    against replay. It validates:
    - EP1: Event types match between live and replay
    - EP2: Event order matches between live and replay
    - EP3: Event data (player names, metadata) matches
    - LC1/LC2: Handshake lifecycle (START → COMPLETE) in both
    - CR1/CR2: Context fields present in replay events

    """
    # =============== LIVE EXECUTION ===============
    # Capture events during live match
    live_capture = EventCapture()
    live_surface_sink = InMemorySink()
    live_surface_projector = MatchSurfaceProjector(sink=live_surface_sink)

    # Configure AgentDeck to use temp directory for recordings
    config = AgentDeckConfig(run_dir=str(temp_recording_dir))
    recorder = Recorder(output_dir=str(temp_recording_dir))

    # Pass spectators to AgentDeck constructor
    deck = AgentDeck(spectators=[live_capture, recorder, live_surface_projector], session=config)

    game = FixedDamageGame()
    player1 = MockPlayer("Player-1")
    player2 = MockPlayer("Player-2")

    # Run single match
    results = deck.play(
        game=game,
        players=[player1, player2],
        matches=1,
    )

    # Verify match completed
    assert results.matches[0].winner is not None, "Match should have a winner"

    # =============== REPLAY EXECUTION ===============
    # Find recorded match file (should be directly in temp_recording_dir)
    match_files = list(temp_recording_dir.glob("*.json"))
    # Filter to only match files (exclude batch files)
    match_files = [f for f in match_files if not f.name.startswith("batch_")]
    assert (
        len(match_files) == 1
    ), f"Should have exactly 1 match recording, found {len(match_files)}: {[f.name for f in match_files]}"

    # Capture events during replay from the in-memory MatchResult and from disk.
    in_memory_replay_capture = EventCapture()
    path_replay_capture = EventCapture()
    in_memory_surface_sink = InMemorySink()
    path_surface_sink = InMemorySink()

    ReplayEngine(results.matches[0]).replay(
        spectators=[
            in_memory_replay_capture,
            MatchSurfaceProjector(sink=in_memory_surface_sink),
        ],
        speed=0.0,
    )
    deck.replay(
        path=match_files[0],
        spectators=[
            path_replay_capture,
            MatchSurfaceProjector(sink=path_surface_sink),
        ],
        speed=0.0,
    )

    # =============== PARITY VERIFICATION (R1/EP1-EP3) ===============
    in_memory_replay_event_types = [_event_type(e) for e in in_memory_replay_capture.events]
    path_replay_event_types = [_event_type(e) for e in path_replay_capture.events]
    live_event_types = [_event_type(e) for e in live_capture.events]

    # EP1: Event type parity

    # Count each event type
    live_counts = {
        "handshake_start": live_event_types.count(EventType.PLAYER_HANDSHAKE_START.value),
        "handshake_complete": live_event_types.count(EventType.PLAYER_HANDSHAKE_COMPLETE.value),
        "match_start": live_event_types.count(EventType.MATCH_START.value),
        "gameplay": live_event_types.count(EventType.GAMEPLAY.value),
        "conclusion": live_event_types.count(EventType.PLAYER_CONCLUSION.value),
        "match_end": live_event_types.count(EventType.MATCH_END.value),
    }

    for label, event_types in (
        ("in-memory replay", in_memory_replay_event_types),
        ("path replay", path_replay_event_types),
    ):
        replay_counts = {
            "handshake_start": event_types.count(EventType.PLAYER_HANDSHAKE_START.value),
            "handshake_complete": event_types.count(EventType.PLAYER_HANDSHAKE_COMPLETE.value),
            "match_start": event_types.count(EventType.MATCH_START.value),
            "gameplay": event_types.count(EventType.GAMEPLAY.value),
            "conclusion": event_types.count(EventType.PLAYER_CONCLUSION.value),
            "match_end": event_types.count(EventType.MATCH_END.value),
        }
        assert live_counts == replay_counts, f"event counts must match for {label}"

    # EP2/EP3: Verify handshake events match in order and data
    live_handshake_starts = _events_of_type(live_capture.events, EventType.PLAYER_HANDSHAKE_START)
    replay_handshake_starts = _events_of_type(
        path_replay_capture.events, EventType.PLAYER_HANDSHAKE_START
    )

    for i, (live_hs, replay_hs) in enumerate(zip(live_handshake_starts, replay_handshake_starts)):
        assert live_hs.data.get("player") == replay_hs.data.get(
            "player"
        ), f"Handshake START {i}: player mismatch (EP3)"
        assert live_hs.data.get(
            "prompt_text"
        ), f"Handshake START {i}: missing prompt_text (HS spec)"
        assert isinstance(
            live_hs.data.get("prompt_blocks"), list
        ), f"Handshake START {i}: prompt_blocks must be list (HS spec)"
        assert live_hs.data.get("prompt_text") == replay_hs.data.get(
            "prompt_text"
        ), f"Handshake START {i}: prompt_text mismatch (EP3)"

    live_handshake_completes = _events_of_type(
        live_capture.events, EventType.PLAYER_HANDSHAKE_COMPLETE
    )
    replay_handshake_completes = _events_of_type(
        path_replay_capture.events, EventType.PLAYER_HANDSHAKE_COMPLETE
    )
    for i, (live_hc, replay_hc) in enumerate(
        zip(live_handshake_completes, replay_handshake_completes)
    ):
        assert live_hc.data.get("player") == replay_hc.data.get(
            "player"
        ), f"Handshake COMPLETE {i}: player mismatch (EP3)"

    # EP2/EP3: Verify gameplay events match in order and data
    live_gameplay = _events_of_type(live_capture.events, EventType.GAMEPLAY)
    in_memory_gameplay = _events_of_type(in_memory_replay_capture.events, EventType.GAMEPLAY)
    path_gameplay = _events_of_type(path_replay_capture.events, EventType.GAMEPLAY)

    assert len(live_gameplay) == len(in_memory_gameplay) == len(path_gameplay)
    for event in live_gameplay + in_memory_gameplay + path_gameplay:
        _assert_canonical_gameplay(event)

    assert _gameplay_payloads(live_capture.events) == _gameplay_payloads(
        in_memory_replay_capture.events
    ), "live and in-memory replay gameplay payloads must match exactly"
    assert _gameplay_payloads(live_capture.events) == _gameplay_payloads(
        path_replay_capture.events
    ), "live and path replay gameplay payloads must match exactly"
    assert live_surface_sink.document is not None
    assert in_memory_surface_sink.document is not None
    assert path_surface_sink.document is not None
    assert _surface_frames_without_timestamps(live_surface_sink.document) == (
        _surface_frames_without_timestamps(in_memory_surface_sink.document)
    )
    assert _surface_frames_without_timestamps(live_surface_sink.document) == (
        _surface_frames_without_timestamps(path_surface_sink.document)
    )

    # Verify both live and replay follow SPEC-REPLAY lifecycle requirements

    # LC1/LC2: Handshake lifecycle - verify in BOTH live and replay
    for name, event_types in [
        ("Live", live_event_types),
        ("In-memory replay", in_memory_replay_event_types),
        ("Path replay", path_replay_event_types),
    ]:
        handshake_start_indices = [
            i for i, t in enumerate(event_types) if t == EventType.PLAYER_HANDSHAKE_START.value
        ]
        handshake_complete_indices = [
            i for i, t in enumerate(event_types) if t == EventType.PLAYER_HANDSHAKE_COMPLETE.value
        ]
        match_start_idx = event_types.index(EventType.MATCH_START.value)

        # LC1: START precedes COMPLETE
        for start_idx, complete_idx in zip(handshake_start_indices, handshake_complete_indices):
            assert (
                start_idx < complete_idx
            ), f"{name}: PLAYER_HANDSHAKE_START must precede COMPLETE (LC1)"

        # LC2: All handshake events before MATCH_START
        all_handshake_indices = handshake_start_indices + handshake_complete_indices
        assert all(
            idx < match_start_idx for idx in all_handshake_indices
        ), f"{name}: All handshake events must precede MATCH_START (LC2)"

    # LC5: Verify conclusions are emitted BEFORE MATCH_END
    replay_event_types = path_replay_event_types
    replay_match_end_idx = replay_event_types.index(EventType.MATCH_END.value)
    replay_conclusion_indices = [
        i for i, t in enumerate(replay_event_types) if t == EventType.PLAYER_CONCLUSION.value
    ]
    assert all(
        idx < replay_match_end_idx for idx in replay_conclusion_indices
    ), "Replay conclusions must precede MATCH_END (LC5)"

    live_match_end_idx = live_event_types.index(EventType.MATCH_END.value)
    live_conclusion_indices = [
        i for i, t in enumerate(live_event_types) if t == EventType.PLAYER_CONCLUSION.value
    ]
    assert all(
        idx < live_match_end_idx for idx in live_conclusion_indices
    ), "Live conclusions must precede MATCH_END (LC5)"

    # CR1/CR2: Verify replay events have context fields
    replay_lifecycle_events = [
        e
        for e in path_replay_capture.events
        if _event_type(e)
        in {
            EventType.PLAYER_HANDSHAKE_START.value,
            EventType.PLAYER_HANDSHAKE_COMPLETE.value,
            EventType.PLAYER_CONCLUSION.value,
        }
    ]
    for event in replay_lifecycle_events:
        assert "match_id" in event.context, f"{event.type} missing match_id in context (CR1/CR2)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
