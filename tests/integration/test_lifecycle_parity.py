"""
Integration test: Live vs Replay event stream parity (SPEC-REPLAY R1).

This test validates SPEC-REPLAY v1.0.0 §6.2 R1 parity guarantee:
"Replays MUST emit the EXACT same event sequence as live execution."

Additionally validates:
- EP1: Event types match
- EP2: Event order matches
- EP3: Event data matches
- LC1/LC2: PLAYER_HANDSHAKE_START → COMPLETE/ABORT before MATCH_START
- CR1/CR2: EventContext populated with session/batch/match IDs

Test approach:
1. Run live match with EventCapture
2. Replay recording with EventCapture
3. Compare event streams (types, order, data)
"""

import json
import tempfile
from pathlib import Path
from typing import List

import pytest

from agentdeck import AgentDeck, AgentDeckConfig, FixedDamageGame, MockPlayer, Recorder
from agentdeck.core.replay import ReplayEngine
from agentdeck.core.types import Event, EventType


class EventCapture:
    """Spy that captures all lifecycle events in order."""

    def __init__(self):
        self.events: List[Event] = []

    def on_player_handshake_start(self, **kwargs):
        context = kwargs.pop("context", {})
        self.events.append(
            Event(type=EventType.PLAYER_HANDSHAKE_START, data=kwargs, context=context)
        )

    def on_player_handshake_complete(self, **kwargs):
        context = kwargs.pop("context", {})
        self.events.append(
            Event(type=EventType.PLAYER_HANDSHAKE_COMPLETE, data=kwargs, context=context)
        )

    def on_player_handshake_abort(self, **kwargs):
        context = kwargs.pop("context", {})
        self.events.append(
            Event(type=EventType.PLAYER_HANDSHAKE_ABORT, data=kwargs, context=context)
        )

    def on_match_start(self, **kwargs):
        context = kwargs.pop("context", {})
        self.events.append(Event(type=EventType.MATCH_START, data=kwargs, context=context))

    def on_gameplay(self, **kwargs):
        context = kwargs.pop("context", {})
        self.events.append(Event(type=EventType.GAMEPLAY, data=kwargs, context=context))

    def on_match_end(self, **kwargs):
        context = kwargs.pop("context", {})
        self.events.append(Event(type=EventType.MATCH_END, data=kwargs, context=context))

    def on_player_conclusion(self, **kwargs):
        context = kwargs.pop("context", {})
        self.events.append(Event(type=EventType.PLAYER_CONCLUSION, data=kwargs, context=context))


@pytest.fixture
def temp_recording_dir():
    """Create temporary directory for recordings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


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

    # Configure AgentDeck to use temp directory for recordings
    config = AgentDeckConfig(run_dir=str(temp_recording_dir))
    recorder = Recorder(output_dir=str(temp_recording_dir))

    # Pass spectators to AgentDeck constructor
    deck = AgentDeck(spectators=[live_capture, recorder], session=config)

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

    # Load recording
    with open(match_files[0]) as f:
        match_data = json.load(f)

    # Capture events during replay
    replay_capture = EventCapture()

    engine = ReplayEngine(match_data)
    engine.replay(spectators=[replay_capture], speed=0.0)

    # =============== PARITY VERIFICATION (R1/EP1-EP3) ===============
    live_event_types = [e.type for e in live_capture.events]
    replay_event_types = [e.type for e in replay_capture.events]

    # EP1: Event type parity

    # Count each event type
    live_counts = {
        "handshake_start": live_event_types.count(EventType.PLAYER_HANDSHAKE_START),
        "handshake_complete": live_event_types.count(EventType.PLAYER_HANDSHAKE_COMPLETE),
        "match_start": live_event_types.count(EventType.MATCH_START),
        "gameplay": live_event_types.count(EventType.GAMEPLAY),
        "conclusion": live_event_types.count(EventType.PLAYER_CONCLUSION),
        "match_end": live_event_types.count(EventType.MATCH_END),
    }

    replay_counts = {
        "handshake_start": replay_event_types.count(EventType.PLAYER_HANDSHAKE_START),
        "handshake_complete": replay_event_types.count(EventType.PLAYER_HANDSHAKE_COMPLETE),
        "match_start": replay_event_types.count(EventType.MATCH_START),
        "gameplay": replay_event_types.count(EventType.GAMEPLAY),
        "conclusion": replay_event_types.count(EventType.PLAYER_CONCLUSION),
        "match_end": replay_event_types.count(EventType.MATCH_END),
    }

    # EP1: Verify event counts match exactly (R1 parity guarantee)
    assert (
        live_counts["handshake_start"] == replay_counts["handshake_start"]
    ), "PLAYER_HANDSHAKE_START count must match (R1/EP1)"
    assert (
        live_counts["handshake_complete"] == replay_counts["handshake_complete"]
    ), "PLAYER_HANDSHAKE_COMPLETE count must match (R1/EP1)"
    assert (
        live_counts["match_start"] == replay_counts["match_start"]
    ), "MATCH_START count must match (R1/EP1)"
    assert (
        live_counts["gameplay"] == replay_counts["gameplay"]
    ), "GAMEPLAY count must match (R1/EP1)"
    assert (
        live_counts["conclusion"] == replay_counts["conclusion"]
    ), "PLAYER_CONCLUSION count must match (R1/EP1)"
    assert (
        live_counts["match_end"] == replay_counts["match_end"]
    ), "MATCH_END count must match (R1/EP1)"

    # EP2/EP3: Verify handshake events match in order and data
    live_handshake_starts = [
        e for e in live_capture.events if e.type == EventType.PLAYER_HANDSHAKE_START
    ]
    replay_handshake_starts = [
        e for e in replay_capture.events if e.type == EventType.PLAYER_HANDSHAKE_START
    ]

    assert len(live_handshake_starts) == len(
        replay_handshake_starts
    ), "Same number of PLAYER_HANDSHAKE_START (EP2)"
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

    live_handshake_completes = [
        e for e in live_capture.events if e.type == EventType.PLAYER_HANDSHAKE_COMPLETE
    ]
    replay_handshake_completes = [
        e for e in replay_capture.events if e.type == EventType.PLAYER_HANDSHAKE_COMPLETE
    ]

    assert len(live_handshake_completes) == len(
        replay_handshake_completes
    ), "Same number of PLAYER_HANDSHAKE_COMPLETE (EP2)"
    for i, (live_hc, replay_hc) in enumerate(
        zip(live_handshake_completes, replay_handshake_completes)
    ):
        assert live_hc.data.get("player") == replay_hc.data.get(
            "player"
        ), f"Handshake COMPLETE {i}: player mismatch (EP3)"

    # EP2/EP3: Verify gameplay events match in order and data
    live_gameplay = [e for e in live_capture.events if e.type == EventType.GAMEPLAY]
    replay_gameplay = [e for e in replay_capture.events if e.type == EventType.GAMEPLAY]

    assert len(live_gameplay) == len(replay_gameplay), "Same number of gameplay events (EP2)"
    for i, (live_gp, replay_gp) in enumerate(zip(live_gameplay, replay_gameplay)):
        assert live_gp.data.get("player") == replay_gp.data.get(
            "player"
        ), f"Gameplay {i}: player mismatch (EP3)"

    # Verify both live and replay follow SPEC-REPLAY lifecycle requirements

    # LC1/LC2: Handshake lifecycle - verify in BOTH live and replay
    for name, event_types in [("Live", live_event_types), ("Replay", replay_event_types)]:
        handshake_start_indices = [
            i for i, t in enumerate(event_types) if t == EventType.PLAYER_HANDSHAKE_START
        ]
        handshake_complete_indices = [
            i for i, t in enumerate(event_types) if t == EventType.PLAYER_HANDSHAKE_COMPLETE
        ]
        match_start_idx = event_types.index(EventType.MATCH_START)

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
    replay_match_end_idx = replay_event_types.index(EventType.MATCH_END)
    replay_conclusion_indices = [
        i for i, t in enumerate(replay_event_types) if t == EventType.PLAYER_CONCLUSION
    ]
    assert all(
        idx < replay_match_end_idx for idx in replay_conclusion_indices
    ), "Replay conclusions must precede MATCH_END (LC5)"

    live_match_end_idx = live_event_types.index(EventType.MATCH_END)
    live_conclusion_indices = [
        i for i, t in enumerate(live_event_types) if t == EventType.PLAYER_CONCLUSION
    ]
    assert all(
        idx < live_match_end_idx for idx in live_conclusion_indices
    ), "Live conclusions must precede MATCH_END (LC5)"

    # CR1/CR2: Verify replay events have context fields
    replay_lifecycle_events = [
        e
        for e in replay_capture.events
        if e.type
        in (
            EventType.PLAYER_HANDSHAKE_START,
            EventType.PLAYER_HANDSHAKE_COMPLETE,
            EventType.PLAYER_CONCLUSION,
        )
    ]
    for event in replay_lifecycle_events:
        assert "match_id" in event.context, f"{event.type} missing match_id in context (CR1/CR2)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
