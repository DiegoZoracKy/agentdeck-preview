"""
Tests for Recorder lifecycle event handling (schema v1.3).

These tests validate SPEC-RECORDER v1.3.0 requirements for capturing
prompt metadata (PM1-PM6) in lifecycle events, including pre-match
event buffering for handshakes that arrive before MATCH_START.
"""

import json
import tempfile
from pathlib import Path

import pytest

from agentdeck.core.recorder import Recorder
from agentdeck.core.types import Event, EventType, MatchResult


@pytest.fixture
def temp_recorder_dir():
    """Create temporary directory for recorder output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def recorder(temp_recorder_dir):
    """Create recorder instance with temporary output directory."""
    return Recorder(
        output_dir=str(temp_recorder_dir),
    )


class TestHandshakeEventBuffering:
    """
    Test 2A.1: Validate pre-match event buffering (schema v1.3).

    Handshake events arrive BEFORE MATCH_START when current_match is None.
    Recorder must buffer these events and flush them when MATCH_START fires.
    """

    def test_buffers_handshake_events_before_match_start(self, recorder, temp_recorder_dir):
        """
        Verify handshake events are buffered and flushed to match recording.

        Setup:
            1. Emit BATCH_START
            2. Emit PLAYER_HANDSHAKE_COMPLETE for Player-1 (before match exists)
            3. Emit MATCH_START (flushes buffer)

        Assert:
            - Before MATCH_START: _pending_events has 1 entry
            - After MATCH_START: events array has handshake event with prompt payload
            - Prompt payload includes PM1-PM6 metadata
        """

        # Step 1: BATCH_START (initializes batch context)
        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session"},
        )

        # Step 2: Emit PLAYER_HANDSHAKE_COMPLETE BEFORE MATCH_START
        recorder.on_player_handshake_complete(
            Event(
                type=EventType.PLAYER_HANDSHAKE_COMPLETE,
                data={
                    "player": "Player-1",
                    "accepted": True,
                    "normalized_response": "OK",
                    "response_text": "OK",
                    "prompt_text": "You are playing TestGame. Reply OK to start.",
                    "prompt_blocks": [
                        {
                            "key": "game_instructions",
                            "content": "You are playing TestGame.",
                            "metadata": {},
                        }
                    ],
                    "controller_format": "Reply with OK, READY, or YES",
                    "controller_metadata": {"allowed": ["OK", "READY", "YES"]},
                    "renderer_output": None,
                    "usage_info": {"tokens": 10, "cost": 0.0001},
                },
                context={"session_id": "test_session"},
            )
        )

        # Verify event is buffered (current_match is still None)
        assert recorder.current_match is None, "Match should not exist yet"
        assert len(recorder._pending_events) == 1, "Event should be buffered"
        buffered_event = recorder._pending_events[0]
        assert buffered_event["type"] == "player_handshake_complete"
        assert buffered_event["data"]["player"] == "Player-1"
        assert "prompt" in buffered_event["data"], "Should have prompt payload"
        assert buffered_event["data"]["prompt"]["phase"] == "handshake"

        # Step 3: Emit MATCH_START (flushes buffer to match recording)
        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        # Verify buffer is flushed
        assert len(recorder._pending_events) == 0, "Buffer should be cleared after MATCH_START"
        assert recorder.current_match is not None, "Match should now exist"

        # Verify event is in match recording
        match_file = temp_recorder_dir / "match_001.json"
        assert match_file.exists(), "Match file should be created"

        with open(match_file) as f:
            match_data = json.load(f)

        assert "events" in match_data, "Match should have events array"
        handshake_events = [
            e for e in match_data["events"] if e["type"] == "player_handshake_complete"
        ]
        assert len(handshake_events) == 1, "Should have 1 handshake event"

        handshake_event = handshake_events[0]
        assert handshake_event["data"]["player"] == "Player-1"
        assert handshake_event["data"]["accepted"] is True

        # Verify prompt payload (PM1-PM6)
        prompt = handshake_event["data"]["prompt"]
        assert prompt["phase"] == "handshake"
        assert prompt["prompt_text"] == "You are playing TestGame. Reply OK to start."  # PM1
        assert prompt["response_text"] == "OK"  # PM3
        assert "prompt_blocks" in prompt  # PM2
        assert prompt["controller_format"] == "Reply with OK, READY, or YES"  # PM5
        assert "usage_info" in prompt  # PM4

    def test_clears_buffer_on_match_end(self, recorder, temp_recorder_dir):
        """
        Verify _pending_events is cleared on MATCH_END to prevent cross-match leaks.

        Setup:
            1. Buffer a handshake event
            2. Start match (flush)
            3. End match
            4. Verify buffer is still empty (defensive)
        """

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session"},
        )

        # Buffer a handshake event
        recorder.on_player_handshake_complete(
            Event(
                type=EventType.PLAYER_HANDSHAKE_COMPLETE,
                data={
                    "player": "Player-1",
                    "accepted": True,
                    "normalized_response": "OK",
                    "response_text": "OK",
                    "prompt_text": "Test prompt",
                    "prompt_blocks": [],
                    "controller_format": "Reply with OK",
                    "controller_metadata": {},
                    "renderer_output": None,
                },
                context={"session_id": "test_session"},
            )
        )

        assert len(recorder._pending_events) == 1, "Event should be buffered"

        # Start match (flushes buffer)
        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        assert len(recorder._pending_events) == 0, "Buffer should be flushed"

        # End match (defensive clear)
        recorder.on_match_end(
            result=MatchResult(
                winner="Player-1",
                final_state={},
                events=[],
                seed=None,
                metadata={},
            ),
            context={"session_id": "test_session"},
        )

        # Verify buffer is still empty (no leaks)
        assert len(recorder._pending_events) == 0, "Buffer should remain empty after match end"


class TestHandshakeMetadata:
    """Test 2A.2: Validate handshake prompt metadata capture (PM1-PM6)."""

    def test_handshake_complete_captures_full_metadata(self, recorder, temp_recorder_dir):
        """
        Verify PLAYER_HANDSHAKE_COMPLETE event captures PM1-PM6 metadata.

        Assert:
            - Prompt payload has prompt_text (PM1)
            - Prompt payload has prompt_blocks (PM2)
            - Prompt payload has response_text (PM3)
            - Prompt payload has usage_info (PM4)
            - Prompt payload has controller_format (PM5)
            - accepted=True is set
        """

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

        # Setup batch and match
        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session"},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        # Emit handshake with full PM1-PM6 metadata
        recorder.on_player_handshake_complete(
            Event(
                type=EventType.PLAYER_HANDSHAKE_COMPLETE,
                data={
                    "player": "Player-1",
                    "accepted": True,
                    "normalized_response": "OK",
                    "response_text": "OK",
                    "prompt_text": "Full handshake prompt",  # PM1
                    "prompt_blocks": [  # PM2
                        {"key": "instructions", "content": "Game rules", "metadata": {}},
                        {"key": "format", "content": "Reply OK", "metadata": {}},
                    ],
                    "usage_info": {  # PM4
                        "tokens": 50,
                        "prompt_tokens": 30,
                        "completion_tokens": 20,
                        "cost": 0.0005,
                        "model": "gpt-4o-mini",
                    },
                    "controller_format": "Reply with OK, READY, or YES",  # PM5
                    "controller_metadata": {"accepted": True},  # PM6
                    "renderer_output": None,
                },
                context={"match_id": "match_001"},
            )
        )

        # Load and verify
        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        handshake_events = [
            e for e in match_data["events"] if e["type"] == "player_handshake_complete"
        ]
        assert len(handshake_events) == 1

        prompt = handshake_events[0]["data"]["prompt"]

        # Verify PM1-PM6
        assert prompt["prompt_text"] == "Full handshake prompt"  # PM1
        assert len(prompt["prompt_blocks"]) == 2  # PM2
        assert prompt["response_text"] == "OK"  # PM3
        assert prompt["usage_info"]["tokens"] == 50  # PM4
        assert prompt["usage_info"]["model"] == "gpt-4o-mini"
        assert prompt["controller_format"] == "Reply with OK, READY, or YES"  # PM5
        assert prompt["controller_metadata"]["accepted"] is True  # PM6

        # Verify accepted flag
        assert handshake_events[0]["data"]["accepted"] is True


class TestHandshakeAbort:
    """Test 2A.3: Validate handshake abort capture."""

    def test_handshake_abort_captures_reason(self, recorder, temp_recorder_dir):
        """
        Verify PLAYER_HANDSHAKE_ABORT event captures rejection reason.

        Assert:
            - Event has accepted=False
            - Event has reason field
            - Prompt payload includes PM1-PM3
        """

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

        # Setup
        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session"},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        # Emit handshake abort
        recorder.on_player_handshake_abort(
            Event(
                type=EventType.PLAYER_HANDSHAKE_ABORT,
                data={
                    "player": "Player-1",
                    "accepted": False,
                    "normalized_response": None,
                    "response_text": "I refuse to play",
                    "controller_metadata": {},
                    "reason": "Player declined participation",
                    "prompt_text": "Handshake prompt",
                    "prompt_blocks": [],
                    "controller_format": "Reply with OK",
                    "renderer_output": None,
                    "usage_info": {"tokens": 15},
                },
                context={"match_id": "match_001"},
            )
        )

        # Verify
        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        abort_events = [e for e in match_data["events"] if e["type"] == "player_handshake_abort"]
        assert len(abort_events) == 1

        abort_event = abort_events[0]
        assert abort_event["data"]["accepted"] is False
        assert abort_event["data"]["reason"] == "Player declined participation"

        prompt = abort_event["data"]["prompt"]
        assert prompt["phase"] == "handshake"
        assert prompt["prompt_text"] == "Handshake prompt"
        assert prompt["response_text"] == "I refuse to play"


class TestConclusionDialogue:
    """Test 2A.4: Validate conclusion prompt capture."""

    def test_conclusion_dialogue_captured(self, recorder, temp_recorder_dir):
        """
        Verify PLAYER_CONCLUSION event captures post-match reflection.

        Assert:
            - Event has prompt payload with phase="conclusion"
            - Prompt includes PM1-PM3
        """

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

        # Setup
        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session"},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        # Emit conclusion
        recorder.on_player_conclusion(
            Event(
                type=EventType.PLAYER_CONCLUSION,
                data={
                    "player": "Player-1",
                    "reflection_text": "I played well and won!",
                    "outcome": "Player-1 won the match.",
                    "prompt_text": "Reflect on your performance.",
                    "response_text": "I played well and won!",
                    "controller_format": "Provide a brief reflection",
                    "metadata": {
                        "usage_info": {"tokens": 25},
                    },
                },
                context={"match_id": "match_001"},
            )
        )

        # Verify
        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        conclusion_events = [e for e in match_data["events"] if e["type"] == "player_conclusion"]
        assert len(conclusion_events) == 1

        prompt = conclusion_events[0]["data"]["prompt"]
        assert prompt["phase"] == "conclusion"
        assert prompt["prompt_text"] == "Reflect on your performance."
        assert prompt["response_text"] == "I played well and won!"
        assert prompt["controller_format"] == "Provide a brief reflection"


class TestDialogueOrdering:
    """Test 2A.5: Validate lifecycle event ordering."""

    def test_dialogue_ordering_handshake_turn_conclusion(self, recorder, temp_recorder_dir):
        """
        Verify lifecycle events appear in correct order: handshake → gameplay → conclusion.

        Assert:
            - Events array has correct ordering
            - Each event has proper prompt payload with correct phase
        """

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

        # Setup
        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session"},
        )

        # Emit handshake BEFORE match starts (buffered)
        recorder.on_player_handshake_complete(
            Event(
                type=EventType.PLAYER_HANDSHAKE_COMPLETE,
                data={
                    "player": "Player-1",
                    "accepted": True,
                    "normalized_response": "OK",
                    "response_text": "OK",
                    "prompt_text": "Handshake prompt",
                    "prompt_blocks": [],
                    "controller_format": "Reply with OK",
                    "controller_metadata": {},
                    "renderer_output": None,
                },
                context={"session_id": "test_session"},
            )
        )

        # Start match (flushes handshake)
        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        # Emit gameplay (turn)
        recorder.on_gameplay(
            Event(
                type=EventType.GAMEPLAY,
                data={
                    "player": "Player-1",
                    "action": {"action": "ATTACK"},
                    "state_before": {},
                    "state_after": {},
                    "metadata": {
                        "turn_number": 1,
                        "raw_prompt": "Turn 1 prompt",
                        "raw_response": "ACTION: ATTACK",
                        "usage_info": {"tokens": 30},
                    },
                },
                context={"match_id": "match_001"},
            )
        )

        # Emit conclusion
        recorder.on_player_conclusion(
            Event(
                type=EventType.PLAYER_CONCLUSION,
                data={
                    "player": "Player-1",
                    "reflection_text": "Good game!",
                    "outcome": "Player-1 won the match.",
                    "prompt_text": "Conclusion prompt",
                    "response_text": "Good game!",
                    "metadata": {},
                },
                context={"match_id": "match_001"},
            )
        )

        # Verify ordering
        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        # Filter lifecycle events with prompts
        lifecycle_events = [
            e
            for e in match_data["events"]
            if e["type"] in ["player_handshake_complete", "gameplay", "player_conclusion"]
        ]

        assert len(lifecycle_events) == 3, "Should have 3 lifecycle events"

        # Verify ordering and phases
        assert lifecycle_events[0]["type"] == "player_handshake_complete"
        assert lifecycle_events[0]["data"]["prompt"]["phase"] == "handshake"

        assert lifecycle_events[1]["type"] == "gameplay"
        assert lifecycle_events[1]["data"]["prompt"]["phase"] == "turn"
        assert lifecycle_events[1]["data"]["prompt"]["turn_number"] == 1

        assert lifecycle_events[2]["type"] == "player_conclusion"
        assert lifecycle_events[2]["data"]["prompt"]["phase"] == "conclusion"


class TestPlayerSummariesMetadata:
    """Test 3: Validate player_summaries metadata (unchanged from v1.2)."""

    def test_match_metadata_includes_player_summaries(self, recorder, temp_recorder_dir):
        """Verify match metadata includes player_summaries list."""

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

            def get_summary(self):
                return {"name": self.name, "type": "MockPlayer"}

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Alice"), MockPlayer("Bob")],
            matches=1,
            context={"session_id": "test_session"},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Alice"), MockPlayer("Bob")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        assert "player_summaries" in match_data["metadata"]
        assert len(match_data["metadata"]["player_summaries"]) == 2
        assert match_data["metadata"]["player_summaries"][0]["name"] == "Alice"
        assert match_data["metadata"]["player_summaries"][1]["name"] == "Bob"

    def test_batch_match_refs_include_player_summaries(self, recorder, temp_recorder_dir):
        """Verify batch match_refs include player_summaries."""

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

            def get_summary(self):
                return {"name": self.name, "type": "MockPlayer"}

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Alice"), MockPlayer("Bob")],
            matches=1,
            context={"session_id": "test_session"},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Alice"), MockPlayer("Bob")],
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        recorder.on_match_end(
            result=MatchResult(
                winner="Alice",
                final_state={},
                events=[],
                seed=None,
                metadata={},
            ),
            context={"session_id": "test_session"},
        )

        recorder.on_batch_end(
            batch_id="batch_001",
            results=[
                MatchResult(
                    winner="Alice",
                    final_state={},
                    events=[],
                    seed=None,
                    metadata={},
                )
            ],
            context={"session_id": "test_session"},
        )

        batch_file = temp_recorder_dir / "batch_batch_001.json"
        with open(batch_file) as f:
            batch_data = json.load(f)

        assert len(batch_data["match_refs"]) == 1
        match_ref = batch_data["match_refs"][0]
        assert "player_summaries" in match_ref
        assert len(match_ref["player_summaries"]) == 2
