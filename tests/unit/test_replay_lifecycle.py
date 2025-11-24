"""
Tests for ReplayEngine lifecycle event emission (handshake/conclusion parity).

These tests validate SPEC-REPLAY §6.5 (LC1-LC5) and §6.6 (PM1-PM3) requirements
for replaying handshake and conclusion events with full prompt metadata.
"""

from typing import List

import pytest

from agentdeck.core.replay import ReplayEngine
from agentdeck.core.types import Event, EventType


class EventCapture:
    """Test spy to capture emitted events in order."""

    def __init__(self):
        self.events: List[Event] = []

    def on_player_handshake_start(self, **kwargs):
        """Capture handshake start events."""
        context = kwargs.pop("context", {})
        self.events.append(
            Event(type=EventType.PLAYER_HANDSHAKE_START, data=kwargs, context=context)
        )

    def on_player_handshake_complete(self, **kwargs):
        """Capture handshake complete events."""
        context = kwargs.pop("context", {})
        self.events.append(
            Event(type=EventType.PLAYER_HANDSHAKE_COMPLETE, data=kwargs, context=context)
        )

    def on_player_handshake_abort(self, **kwargs):
        """Capture handshake abort events."""
        context = kwargs.pop("context", {})
        self.events.append(
            Event(type=EventType.PLAYER_HANDSHAKE_ABORT, data=kwargs, context=context)
        )

    def on_match_start(self, **kwargs):
        """Capture match start events."""
        context = kwargs.pop("context", {})
        self.events.append(Event(type=EventType.MATCH_START, data=kwargs, context=context))

    def on_match_end(self, **kwargs):
        """Capture match end events."""
        context = kwargs.pop("context", {})
        self.events.append(Event(type=EventType.MATCH_END, data=kwargs, context=context))

    def on_player_conclusion(self, **kwargs):
        """Capture conclusion events."""
        context = kwargs.pop("context", {})
        self.events.append(Event(type=EventType.PLAYER_CONCLUSION, data=kwargs, context=context))


@pytest.fixture
def sample_recording_with_handshakes():
    """Create a sample recording with handshake events aligned to SPEC-RECORDER v1.3.0."""
    return {
        "schema_version": "1.3",
        "schema_type": "match",
        "match_id": "match_test",
        "game": "TestGame",
        "players": ["Player-1", "Player-2"],
        "winner": "Player-1",
        "final_state": {"health": {"Player-1": 100, "Player-2": 0}},
        "seed": 42,
        "events": [
            {
                "type": "player_handshake_complete",
                "data": {
                    "player": "Player-1",
                    "response": "OK",
                    "metadata": {
                        "allowed": ["READY", "OK", "YES"],
                        "player": "Player-1",
                        "match_id": "match_test",
                    },
                },
                "context": {"match_id": "match_test"},
                "timestamp": 950,
            },
            {
                "type": "player_handshake_complete",
                "data": {
                    "player": "Player-2",
                    "response": "READY",
                    "metadata": {
                        "allowed": ["READY", "OK", "YES"],
                        "player": "Player-2",
                        "match_id": "match_test",
                    },
                },
                "context": {"match_id": "match_test"},
                "timestamp": 980,
            },
            {
                "type": "gameplay",
                "data": {
                    "player": "Player-1",
                    "action": {
                        "action": "ATTACK",
                        "reasoning": "Attack first",
                        "metadata": {
                            "prompt_text": "Turn prompt",
                        },
                        "raw_response": "ACTION: ATTACK",
                    },
                    "state_before": {"_turn_count": 1},
                    "state_after": {"_turn_count": 2},
                    "phase_index": 0,
                },
                "context": {"match_id": "match_test", "phase_index": 0},
                "timestamp": 1000,
            },
            {
                "type": "player_conclusion",
                "data": {
                    "player": "Player-1",
                    "reflection": "Great game.",
                    "prompt_text": "How did you play?",
                    "prompt_blocks": [{"key": "outcome", "content": "You won!"}],
                },
                "context": {"match_id": "match_test"},
                "timestamp": 1500,
            },
        ],
        "metadata": {
            "match_id": "match_test",
            "players": ["Player-1", "Player-2"],
        },
    }


@pytest.fixture
def sample_recording_with_conclusions():
    """Create a sample recording with conclusion events."""
    return {
        "schema_version": "1.3",
        "schema_type": "match",
        "match_id": "match_conclusion",
        "game": "TestGame",
        "players": ["Player-1"],
        "winner": "Player-1",
        "final_state": {},
        "seed": 42,
        "events": [
            {
                "type": "gameplay",
                "data": {
                    "player": "Player-1",
                    "action": {
                        "action": "ATTACK",
                        "raw_response": "ACTION: ATTACK",
                    },
                    "state_before": {"_turn_count": 1},
                    "state_after": {"_turn_count": 2},
                    "phase_index": 0,
                },
                "context": {"match_id": "match_conclusion", "phase_index": 0},
                "timestamp": 1200,
            },
            {
                "type": "player_conclusion",
                "data": {
                    "player": "Player-1",
                    "reflection": "I played well and won.",
                    "prompt_text": "Match concluded. You won!",
                    "prompt_blocks": [{"key": "outcome", "content": "You won!"}],
                },
                "context": {"match_id": "match_conclusion"},
                "timestamp": 1600,
            },
        ],
        "metadata": {
            "match_id": "match_conclusion",
            "players": ["Player-1"],
        },
    }


class TestHandshakeReplay:
    """
    Test 2B.1: Validate PLAYER_HANDSHAKE_COMPLETE events emitted before MATCH_START.

    Per SPEC-REPLAY LC2: MUST emit handshake events from dialogue array before MATCH_START.
    """

    def test_emits_handshake_before_match_start(self, sample_recording_with_handshakes):
        """
        Verify handshake events emitted in correct order.

        Event order must be (per SPEC-REPLAY LC1/LC2):
        1. PLAYER_HANDSHAKE_START (Player-1)
        2. PLAYER_HANDSHAKE_COMPLETE (Player-1)
        3. PLAYER_HANDSHAKE_START (Player-2)
        4. PLAYER_HANDSHAKE_COMPLETE (Player-2)
        5. MATCH_START
        6. ... gameplay events ...
        7. MATCH_END
        """
        engine = ReplayEngine(sample_recording_with_handshakes)
        spy = EventCapture()

        engine.replay(spectators=[spy], speed=0.0)

        # Extract event types in order
        event_types = [e.type for e in spy.events]

        # Find indices for START and COMPLETE events
        handshake_start_indices = [
            i for i, t in enumerate(event_types) if t == EventType.PLAYER_HANDSHAKE_START
        ]
        handshake_complete_indices = [
            i for i, t in enumerate(event_types) if t == EventType.PLAYER_HANDSHAKE_COMPLETE
        ]
        match_start_idx = event_types.index(EventType.MATCH_START)

        # Verify both START and COMPLETE events present
        assert len(handshake_start_indices) == 2, "Should have 2 handshake START events"
        assert len(handshake_complete_indices) == 2, "Should have 2 handshake COMPLETE events"

        # Verify all handshake events before MATCH_START
        all_handshake_indices = handshake_start_indices + handshake_complete_indices
        assert all(
            idx < match_start_idx for idx in all_handshake_indices
        ), "All handshake events must precede MATCH_START"

        # Verify START precedes COMPLETE for each player
        for start_idx, complete_idx in zip(handshake_start_indices, handshake_complete_indices):
            assert (
                start_idx < complete_idx
            ), "PLAYER_HANDSHAKE_START must precede PLAYER_HANDSHAKE_COMPLETE"

    def test_handshake_event_includes_metadata(self, sample_recording_with_handshakes):
        """
        Verify handshake events include response and controller metadata.

        Per SPEC-REPLAY EP3: payload must match live execution data (player, response, metadata)
        """
        engine = ReplayEngine(sample_recording_with_handshakes)
        spy = EventCapture()

        engine.replay(spectators=[spy], speed=0.0)

        # Find first handshake COMPLETE event
        handshake_events = [e for e in spy.events if e.type == EventType.PLAYER_HANDSHAKE_COMPLETE]
        first_handshake = handshake_events[0]

        # Verify payload matches live structure
        assert first_handshake.data["player"] == "Player-1"
        assert first_handshake.data["response"] == "OK"
        assert first_handshake.data["metadata"] == {
            "allowed": ["READY", "OK", "YES"],
            "player": "Player-1",
            "match_id": "match_test",
        }

    def test_handles_recordings_with_explicit_handshake_start_events(self):
        """
        ReplayEngine must not duplicate PLAYER_HANDSHAKE_START when recordings already contain them.

        Scenario mirrors MatchResult snapshots captured in-memory (runtime.events includes START).
        """
        recording = {
            "schema_version": "1.3",
            "schema_type": "match",
            "match_id": "match_start_prefixed",
            "game": "TestGame",
            "players": ["Player-1"],
            "winner": "Player-1",
            "final_state": {},
            "seed": 1,
            "events": [
                {
                    "type": "player_handshake_start",
                    "data": {"player": "Player-1"},
                    "context": {"match_id": "match_start_prefixed"},
                    "timestamp": 900,
                },
                {
                    "type": "player_handshake_complete",
                    "data": {
                        "player": "Player-1",
                        "response": "OK",
                        "metadata": {
                            "player": "Player-1",
                            "match_id": "match_start_prefixed",
                            "allowed": ["OK"],
                        },
                    },
                    "context": {"match_id": "match_start_prefixed"},
                    "timestamp": 950,
                },
                {
                    "type": "gameplay",
                    "data": {
                        "player": "Player-1",
                        "action": {"action": "ATTACK"},
                        "state_before": {"_turn_count": 1},
                        "state_after": {"_turn_count": 2},
                        "phase_index": 0,
                    },
                    "context": {"match_id": "match_start_prefixed", "phase_index": 0},
                    "timestamp": 960,
                },
            ],
            "metadata": {
                "match_id": "match_start_prefixed",
                "players": ["Player-1"],
            },
        }

        engine = ReplayEngine(recording)
        spy = EventCapture()

        engine.replay(spectators=[spy], speed=0.0)

        event_types = [e.type for e in spy.events]
        handshake_start_count = event_types.count(EventType.PLAYER_HANDSHAKE_START)

        assert handshake_start_count == 1, "Recorded START events must not be duplicated"
        match_start_index = event_types.index(EventType.MATCH_START)
        start_index = event_types.index(EventType.PLAYER_HANDSHAKE_START)
        assert start_index < match_start_index, "MATCH_START must follow all handshake events"


class TestConclusionReplay:
    """
    Test 2B.2: Validate PLAYER_CONCLUSION events emitted after MATCH_END.

    Per SPEC-REPLAY LC5: conclusions must be emitted AFTER MATCH_END.
    """

    def test_emits_conclusions_after_match_end(self, sample_recording_with_conclusions):
        """
        Verify conclusion events emitted after MATCH_END.

        Event order must be (per SPEC-REPLAY LC5):
        1. MATCH_START
        2. ... gameplay events ...
        3. MATCH_END
        4. PLAYER_CONCLUSION (Player-1)
        """
        engine = ReplayEngine(sample_recording_with_conclusions)
        spy = EventCapture()

        engine.replay(spectators=[spy], speed=0.0)

        event_types = [e.type for e in spy.events]

        match_end_idx = event_types.index(EventType.MATCH_END)
        conclusion_indices = [
            i for i, t in enumerate(event_types) if t == EventType.PLAYER_CONCLUSION
        ]

        assert len(conclusion_indices) == 1, "Should have 1 conclusion event"
        assert (
            conclusion_indices[0] > match_end_idx
        ), "Conclusion must follow MATCH_END (SPEC-REPLAY LC5)"

    def test_conclusion_event_includes_reflection(self, sample_recording_with_conclusions):
        """
        Verify conclusion events include reflection text.

        Per SPEC-REPLAY PM1-PM3: MUST include response_text as reflection.
        """
        engine = ReplayEngine(sample_recording_with_conclusions)
        spy = EventCapture()

        engine.replay(spectators=[spy], speed=0.0)

        conclusion_events = [e for e in spy.events if e.type == EventType.PLAYER_CONCLUSION]
        assert len(conclusion_events) == 1

        conclusion = conclusion_events[0]
        assert conclusion.data["player"] == "Player-1"
        assert conclusion.data["reflection"] == "I played well and won."
        assert "prompt_text" in conclusion.data


class TestSpectatorCleanup:
    """
    Test 2B.3: Validate spectator unsubscribe after replay (SI2).

    Per SPEC-REPLAY SI2: MUST unsubscribe spectators after replay completes.
    """

    def test_unsubscribes_spectators_after_replay(self, sample_recording_with_handshakes):
        """
        Verify EventBus is clean after replay completes.
        """
        engine = ReplayEngine(sample_recording_with_handshakes)
        spy1 = EventCapture()
        spy2 = EventCapture()

        # Subscribe spectators
        engine.replay(spectators=[spy1, spy2], speed=0.0)

        # Verify EventBus has no subscribers (clean state)
        assert len(engine.event_bus._spectators) == 0, "All spectators should be unsubscribed"


class TestContextHydration:
    """
    Test 2B.3: Validate SPEC-REPLAY CR1/CR2 - EventContext hydration.

    Per SPEC-REPLAY CR1/CR2: ReplayEngine MUST populate EventContext with
    session_id, batch_id, match_id from recording metadata so spectators
    can access them via event.context (modern) or context kwarg (legacy).
    """

    def test_lifecycle_events_include_context_fields(self):
        """
        Verify handshake and conclusion events carry session/batch/match IDs.

        Per CR1: Modern spectators access via event.context
        Per CR2: Legacy handlers receive as context kwarg
        """
        # Create recording with full context metadata (v1.3.0 format)
        recording = {
            "schema_version": "1.3",
            "schema_type": "match",
            "match_id": "match_ctx_test",
            "game": "TestGame",
            "players": ["Player-1"],
            "winner": "Player-1",
            "final_state": {},
            "seed": 42,
            "events": [
                {
                    "type": "player_handshake_complete",
                    "data": {
                        "player": "Player-1",
                        "response": "OK",
                        "metadata": {
                            "allowed": ["READY", "OK", "YES"],
                            "player": "Player-1",
                            "match_id": "match_ctx_test",
                        },
                    },
                    "context": {
                        "session_id": "session_abc123",
                        "batch_id": "batch_xyz789",
                        "match_id": "match_ctx_test",
                    },
                    "timestamp": 950,
                },
                {
                    "type": "player_conclusion",
                    "data": {
                        "player": "Player-1",
                        "reflection": "I won",
                        "prompt_text": "Reflect",
                    },
                    "context": {
                        "session_id": "session_abc123",
                        "batch_id": "batch_xyz789",
                        "match_id": "match_ctx_test",
                    },
                    "timestamp": 1500,
                },
            ],
            "metadata": {
                "session_id": "session_abc123",
                "batch_id": "batch_xyz789",
                "match_id": "match_ctx_test",
                "players": ["Player-1"],
            },
        }

        engine = ReplayEngine(recording)
        spy = EventCapture()

        engine.replay(spectators=[spy], speed=0.0)

        # Find lifecycle events
        handshake_starts = [e for e in spy.events if e.type == EventType.PLAYER_HANDSHAKE_START]
        handshake_completes = [
            e for e in spy.events if e.type == EventType.PLAYER_HANDSHAKE_COMPLETE
        ]
        conclusions = [e for e in spy.events if e.type == EventType.PLAYER_CONCLUSION]

        assert len(handshake_starts) == 1, "Should have handshake START"
        assert len(handshake_completes) == 1, "Should have handshake COMPLETE"
        assert len(conclusions) == 1, "Should have conclusion"

        # Verify context fields present (CR1/CR2)
        for event in handshake_starts + handshake_completes + conclusions:
            assert (
                "session_id" in event.context
            ), f"{event.type} missing session_id in context (CR1)"
            assert event.context["session_id"] == "session_abc123", "session_id mismatch"

            assert "batch_id" in event.context, f"{event.type} missing batch_id in context (CR1)"
            assert event.context["batch_id"] == "batch_xyz789", "batch_id mismatch"

            assert "match_id" in event.context, f"{event.type} missing match_id in context (CR1)"
            assert event.context["match_id"] == "match_ctx_test", "match_id mismatch"


class TestSchemaValidation:
    """Ensure ReplayEngine enforces Recorder schema contracts."""

    def test_raises_error_for_missing_schema_version(self):
        recording = {
            # schema_version intentionally omitted
            "schema_type": "match",
            "match_id": "missing_schema",
            "game": "TestGame",
            "players": ["Player-1"],
            "events": [],
            "metadata": {"match_id": "missing_schema"},
        }

        with pytest.raises(ValueError, match="schema_version"):
            ReplayEngine(recording)

    def test_raises_error_for_unsupported_schema_version(self):
        recording = {
            "schema_version": "0.9",
            "schema_type": "match",
            "match_id": "old_schema",
            "game": "TestGame",
            "players": ["Player-1"],
            "events": [],
            "metadata": {"match_id": "old_schema"},
        }

        with pytest.raises(ValueError, match="Unsupported recording schema_version"):
            ReplayEngine(recording)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
