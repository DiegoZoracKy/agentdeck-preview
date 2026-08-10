"""
Tests for Recorder lifecycle event handling (schema v2.0).

These tests validate SPEC-RECORDER v2.0 requirements for preserving canonical
event payloads verbatim, including pre-match event buffering for handshakes that
arrive before MATCH_START.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from agentdeck.core.recorder import Recorder
from agentdeck.core.types import Event, EventType, MatchResult
from agentdeck.games.examples.fixed_damage.game import FixedDamageGame
from agentdeck.players.mock import MockPlayer as CoreMockPlayer


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


def test_GVP1_GVP2_recorder_keeps_game_version_separate_from_effective_config(
    recorder, temp_recorder_dir
):
    """GVP1 GVP2: every new record separates implementation identity from config."""

    class MockGame:
        def describe(self):
            return {"name": "MockGame", "module": __name__, "allowed_actions": [], "config": {"limit": 3}}

    class MockPlayer:
        def __init__(self, name):
            self.name = name

    game = MockGame()
    players = [MockPlayer("Alpha"), MockPlayer("Beta")]
    recorder.on_batch_start(
        batch_id="batch_gvp",
        game=game,
        players=players,
        matches=1,
        context={"session_id": "test_session"},
    )
    recorder.on_match_start(
        game=game,
        players=players,
        match_id="match_gvp",
        context={"session_id": "test_session", "batch_id": "batch_gvp"},
    )

    payload = json.loads((temp_recorder_dir / "match_gvp.json").read_text())
    assert payload["metadata"]["game_config"]["config"] == {"limit": 3}
    assert payload["metadata"]["game_version"]["family_id"].endswith("MockGame")
    assert "config" not in payload["metadata"]["game_version"]


def test_GVP8_loading_a_legacy_record_does_not_rewrite_or_backfill_it(temp_recorder_dir):
    """GVP8: reading historical bytes never fabricates modern Game provenance."""
    path = temp_recorder_dir / "legacy-match.json"
    payload = {
        "schema_version": "2.0",
        "events": [],
        "winner": None,
        "final_state": {},
        "seed": 1,
        "metadata": {"game_config": {"name": "LegacyGame"}},
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    before = path.read_bytes()

    loaded = Recorder.load_match(path)

    assert path.read_bytes() == before
    assert "game_version" not in loaded["metadata"]


class TestHandshakeEventBuffering:
    """
    Test 2A.1: Validate pre-match event buffering (schema v2.0).

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
                    "controller_format": "Reply with exactly 'OK' and nothing else if you understand and are ready to begin.",
                    "controller_metadata": {"allowed": ["OK"]},
                    "renderer_output": None,
                    "usage_info": {"tokens": 10, "cost": 0.0001},
                    "metadata": {"turn_number": 0},
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
        assert buffered_event["data"]["prompt_text"] == (
            "You are playing TestGame. Reply OK to start."
        )

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

        # Verify lifecycle interaction metadata is preserved verbatim.
        data = handshake_event["data"]
        assert data["prompt_text"] == "You are playing TestGame. Reply OK to start."
        assert data["response_text"] == "OK"
        assert "prompt_blocks" in data
        assert (
            data["controller_format"]
            == "Reply with exactly 'OK' and nothing else if you understand and are ready to begin."
        )
        assert "usage_info" in data

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


def test_aw4_rejects_match_path_escape_before_artifact_write(recorder, temp_recorder_dir):
    """AW4: a record-provided match ID cannot escape Recorder.output_dir."""
    recorder.on_batch_start(
        batch_id="batch_001",
        game=FixedDamageGame(),
        players=[CoreMockPlayer("Alice"), CoreMockPlayer("Bob")],
        matches=1,
        context={"session_id": "test_session"},
    )

    with pytest.raises(ValueError, match="match_id"):
        recorder.on_match_start(
            game=FixedDamageGame(),
            players=[CoreMockPlayer("Alice"), CoreMockPlayer("Bob")],
            match_id="../escaped",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

    assert not (temp_recorder_dir.parent / "escaped.json").exists()


def test_aw5_strict_json_failure_preserves_existing_artifact(recorder, temp_recorder_dir):
    """AW5: Recorder never uses default=str and never replaces valid prior evidence."""
    target = temp_recorder_dir / "match_existing.json"
    target.write_text('{"preserved": true}', encoding="utf-8")

    with pytest.raises(ValueError, match="strict JSON"):
        recorder._atomic_write(str(target), {"bad": {"set"}})

    assert target.read_text(encoding="utf-8") == '{"preserved": true}'


def test_mc3_mc4_capture_complete_effective_method(recorder, temp_recorder_dir):
    """MC3/MC4: match metadata preserves exact Game and Player configurations."""
    game = FixedDamageGame(
        max_health=120,
        attack_damage=17,
        potion_heal=29,
        starting_potions=2,
        information_level="partial",
    )
    players = [
        CoreMockPlayer("Alice", actions=["POTION", "ATTACK"], turn_template="A:{game_view}"),
        CoreMockPlayer("Bob", actions=["ATTACK"], turn_template="B:{game_view}"),
    ]
    recorder.on_batch_start(
        batch_id="batch_001",
        game=game,
        players=players,
        matches=1,
        context={"session_id": "test_session"},
    )
    recorder.on_match_start(
        game=game,
        players=players,
        match_id="match_001",
        context={"session_id": "test_session", "batch_id": "batch_001"},
    )

    payload = json.loads((temp_recorder_dir / "match_001.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["game_config"]["config"] == {
        "max_health": 120,
        "attack_damage": 17,
        "potion_heal": 29,
        "starting_potions": 2,
        "information_level": "partial",
    }
    alice = payload["metadata"]["player_configs"]["Alice"]
    assert alice["config"]["actions"] == ["POTION", "ATTACK"]
    assert alice["controller"]["type"] == "ActionOnlyController"
    assert alice["renderer"]["name"] == "TextRenderer"
    assert alice["templates"]["turn"] == "A:{game_view}"
    assert (
        recorder.current_batch.metadata["configuration"]["game"]
        == payload["metadata"]["game_config"]
    )


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
                    "controller_format": "Reply with exactly 'OK' and nothing else if you understand and are ready to begin.",  # PM5
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

        data = handshake_events[0]["data"]

        # Verify lifecycle metadata is preserved verbatim.
        assert data["prompt_text"] == "Full handshake prompt"
        assert len(data["prompt_blocks"]) == 2
        assert data["response_text"] == "OK"
        assert data["usage_info"]["tokens"] == 50
        assert data["usage_info"]["model"] == "gpt-4o-mini"
        assert (
            data["controller_format"]
            == "Reply with exactly 'OK' and nothing else if you understand and are ready to begin."
        )
        assert data["controller_metadata"]["accepted"] is True

        # Verify accepted flag
        assert handshake_events[0]["data"]["accepted"] is True

    def test_handshake_start_is_recorded(self, recorder, temp_recorder_dir):
        """PLAYER_HANDSHAKE_START should be persisted in match events."""

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
            context={"session_id": "test_session", "timestamp": 1705499400.0},
        )

        recorder.on_player_handshake_start(
            Event(
                type=EventType.PLAYER_HANDSHAKE_START,
                data={
                    "player": "Player-1",
                    "prompt_text": "You are playing TestGame",
                    "prompt_blocks": [],
                    "controller_format": "Reply with OK",
                },
                context={"session_id": "test_session", "timestamp": 1705499401.0},
            )
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={
                "session_id": "test_session",
                "batch_id": "batch_001",
                "timestamp": 1705499402.0,
            },
        )

        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        start_events = [e for e in match_data["events"] if e["type"] == "player_handshake_start"]
        assert len(start_events) == 1
        assert start_events[0]["data"]["player"] == "Player-1"
        assert start_events[0]["data"]["prompt_text"] == "You are playing TestGame"

    def test_match_timestamps_use_event_context(self, recorder, temp_recorder_dir):
        """Match started/ended timestamps should come from lifecycle event context."""

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

            def get_summary(self):
                return {"name": self.name, "type": "MockPlayer"}

        started_ts = 1705499402.0
        ended_ts = 1705499462.0

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session", "timestamp": started_ts - 1},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={
                "session_id": "test_session",
                "batch_id": "batch_001",
                "timestamp": started_ts,
            },
        )

        recorder.on_match_end(
            result=MatchResult(
                winner="Player-1",
                final_state={"hp": {"Player-1": 10, "Player-2": 0}},
                events=[],
                seed=42,
                metadata={"duration_seconds": 60.0, "turns": 3},
            ),
            context={
                "session_id": "test_session",
                "batch_id": "batch_001",
                "timestamp": ended_ts,
            },
        )

        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        assert match_data["started_at"] is not None
        assert match_data["ended_at"] is not None
        assert match_data["duration_seconds"] == 60.0

        # Stored timestamps should be consistent with the injected event context.
        assert match_data["started_at"].startswith("2024-01-")
        assert match_data["ended_at"].startswith("2024-01-")

    def test_gameplay_events_preserve_emission_timestamps_and_turn_durations(
        self, recorder, temp_recorder_dir
    ):
        """
        Gameplay events must keep emission-time timestamps and real turn durations.

        Regression guard:
        avoid collapsed timelines caused by recorder flush-time stamping.
        """

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

            def get_summary(self):
                return {"name": self.name, "type": "MockPlayer"}

        started_ts = 1705499402.0
        turn1_ts = started_ts + 10.0
        turn2_ts = started_ts + 25.0
        ended_ts = started_ts + 60.0

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            matches=1,
            context={"session_id": "test_session", "timestamp": started_ts - 1},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=[MockPlayer("Player-1"), MockPlayer("Player-2")],
            match_id="match_001",
            context={
                "session_id": "test_session",
                "batch_id": "batch_001",
                "timestamp": started_ts,
            },
        )

        recorder.on_gameplay(
            Event(
                type=EventType.GAMEPLAY,
                data={
                    "player": "Player-1",
                    "action": {
                        "value": "ATTACK",
                        "reasoning": "Aggressive opening",
                        "metadata": {},
                    },
                    "state_before": {
                        "health": {"Player-1": 100, "Player-2": 100},
                        "_turn_count": 1,
                        "_first_player_idx": 0,
                    },
                    "state_after": {
                        "health": {"Player-1": 100, "Player-2": 80},
                        "_turn_count": 2,
                        "_first_player_idx": 0,
                    },
                    "turn_context": {"turn_number": 1, "duration": 1.25},
                    "interaction": {
                        "prompt_text": "Turn 1",
                        "response_text": "ACTION: ATTACK",
                        "usage_info": {"call_id": "c111aaaa", "tokens": 10, "cost": 0.0001},
                    },
                },
                context={
                    "session_id": "test_session",
                    "batch_id": "batch_001",
                    "timestamp": turn1_ts,
                },
                timestamp=turn1_ts,
                duration=0.1,
            )
        )

        recorder.on_gameplay(
            Event(
                type=EventType.GAMEPLAY,
                data={
                    "player": "Player-2",
                    "action": {"value": "POTION", "reasoning": "Recover", "metadata": {}},
                    "state_before": {
                        "health": {"Player-1": 100, "Player-2": 80},
                        "_turn_count": 2,
                        "_first_player_idx": 0,
                    },
                    "state_after": {
                        "health": {"Player-1": 100, "Player-2": 100},
                        "_turn_count": 3,
                        "_first_player_idx": 0,
                    },
                    "turn_context": {"turn_number": 2, "duration": 2.5},
                    "interaction": {
                        "prompt_text": "Turn 2",
                        "response_text": "ACTION: POTION",
                        "call_id": "c222bbbb",
                        "usage_info": {"call_id": "c222bbbb", "tokens": 12, "cost": 0.0002},
                    },
                },
                context={
                    "session_id": "test_session",
                    "batch_id": "batch_001",
                    "timestamp": turn2_ts,
                },
                timestamp=turn2_ts,
                duration=0.1,
            )
        )

        recorder.on_match_end(
            result=MatchResult(
                winner="Player-1",
                final_state={"health": {"Player-1": 40, "Player-2": 0}},
                events=[],
                seed=42,
                metadata={"duration_seconds": 60.0, "turns": 2},
            ),
            context={
                "session_id": "test_session",
                "batch_id": "batch_001",
                "timestamp": ended_ts,
            },
        )

        match_file = temp_recorder_dir / "match_001.json"
        with open(match_file) as f:
            match_data = json.load(f)

        gameplay_events = [e for e in match_data["events"] if e["type"] == "gameplay"]
        assert len(gameplay_events) == 2

        # Keep event emission timestamps (not flush-time values).
        assert gameplay_events[0]["timestamp"] == turn1_ts
        assert gameplay_events[1]["timestamp"] == turn2_ts
        assert (gameplay_events[1]["timestamp"] - gameplay_events[0]["timestamp"]) == 15.0

        # Keep real per-turn durations from turn_context.
        assert gameplay_events[0]["duration"] == 1.25
        assert gameplay_events[1]["duration"] == 2.5

        # Turn context carries concrete turn numbers.
        assert gameplay_events[0]["data"]["turn_context"]["turn_number"] == 1
        assert gameplay_events[1]["data"]["turn_context"]["turn_number"] == 2

        # Engine-internal keys should be sanitized from recorded gameplay snapshots.
        assert "_turn_count" not in gameplay_events[0]["data"]["state_before"]
        assert "_first_player_idx" not in gameplay_events[0]["data"]["state_before"]
        assert "_turn_count" not in gameplay_events[1]["data"]["state_after"]
        assert "_first_player_idx" not in gameplay_events[1]["data"]["state_after"]

        # call_id should be explicit in interaction payload for request/response correlation.
        assert gameplay_events[0]["data"]["interaction"]["usage_info"]["call_id"] == "c111aaaa"
        assert gameplay_events[1]["data"]["interaction"]["usage_info"]["call_id"] == "c222bbbb"


class TestMatchCostAndIds:
    """Validate finalized cost fields and top-level batch IDs in recordings."""

    def test_match_recording_includes_api_usage_summary_from_lifecycle_events(
        self, recorder, temp_recorder_dir
    ):
        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

            def get_summary(self):
                return {"name": self.name, "type": "MockPlayer"}

        players = [MockPlayer("Player-1"), MockPlayer("Player-2")]

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=players,
            matches=1,
            context={"session_id": "test_session"},
        )

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
                    "usage_info": {
                        "prompt_tokens": 8,
                        "completion_tokens": 2,
                        "tokens": 10,
                        "cost": 0.0001,
                        "model": "gpt-4o-mini",
                    },
                },
                context={"session_id": "test_session"},
            )
        )

        recorder.on_match_start(
            game=MockGame(),
            players=players,
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        recorder.on_gameplay(
            Event(
                type=EventType.GAMEPLAY,
                data={
                    "player": "Player-1",
                    "action": {
                        "value": "ATTACK",
                        "reasoning": None,
                        "metadata": {
                            "usage_info": {
                                "prompt_tokens": 20,
                                "completion_tokens": 10,
                                "tokens": 30,
                                "cost": 0.0002,
                                "model": "gpt-4o-mini",
                            }
                        },
                    },
                    "interaction": {
                        "usage_info": {
                            "prompt_tokens": 20,
                            "completion_tokens": 10,
                            "tokens": 30,
                            "cost": 0.0002,
                            "model": "gpt-4o-mini",
                        }
                    },
                    "state_before": {},
                    "state_after": {},
                },
                context={"match_id": "match_001"},
            )
        )

        recorder.on_player_conclusion(
            Event(
                type=EventType.PLAYER_CONCLUSION,
                data={
                    "player": "Player-1",
                    "reflection_text": "Good game!",
                    "outcome": "Player-1 won the match.",
                    "prompt_text": "Conclusion prompt",
                    "response_text": "Good game!",
                    "usage_info": {
                        "prompt_tokens": 15,
                        "completion_tokens": 10,
                        "tokens": 25,
                        "cost": 0.00015,
                        "model": "gpt-4o-mini",
                    },
                },
                context={"match_id": "match_001"},
            )
        )

        recorder.on_match_end(
            result=MatchResult(
                winner="Player-1",
                final_state={},
                events=[],
                seed=42,
                metadata={},
            ),
            context={"session_id": "test_session"},
        )

        with open(temp_recorder_dir / "match_001.json") as f:
            match_data = json.load(f)

        assert match_data["api_usage_summary"] == {
            "total_calls": 3,
            "total_tokens": 65,
            "total_prompt_tokens": 43,
            "total_completion_tokens": 22,
            "total_cost": 0.00045,
            "average_latency_ms": 0.0,
            "total_latency_ms": 0.0,
            "models_used": {"gpt-4o-mini": 3},
        }

    def test_updates_player_summaries_costs_and_exposes_batch_id(self, recorder, temp_recorder_dir):
        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

            def get_summary(self):
                # Simulate stale summary cost captured at match start.
                return {"name": self.name, "type": "MockPlayer", "total_cost": 0.00001}

        players = [MockPlayer("Player-1"), MockPlayer("Player-2")]

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=players,
            matches=1,
            context={"session_id": "test_session"},
        )

        recorder.on_match_start(
            game=MockGame(),
            players=players,
            match_id="match_001",
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        result = MatchResult(
            winner="Player-1",
            final_state={},
            events=[],
            seed=42,
            metadata={
                "turns": 5,
                "duration": 1.23,
                "cost": 0.003,
                "player_costs": {"Player-1": 0.001, "Player-2": 0.002},
            },
        )

        recorder.on_match_end(result=result, context={"session_id": "test_session"})
        recorder.on_batch_end(
            batch_id="batch_001",
            results=[result],
            context={"session_id": "test_session", "batch_id": "batch_001"},
        )

        with open(temp_recorder_dir / "match_001.json") as f:
            match_data = json.load(f)
        assert match_data["batch_id"] == "batch_001"

        match_summaries = match_data["metadata"]["player_summaries"]
        p1 = next(s for s in match_summaries if s["name"] == "Player-1")
        p2 = next(s for s in match_summaries if s["name"] == "Player-2")
        assert p1["total_cost"] == 0.001
        assert p2["total_cost"] == 0.002

        with open(temp_recorder_dir / "batch_batch_001.json") as f:
            batch_data = json.load(f)
        batch_summaries = batch_data["match_refs"][0]["player_summaries"]
        b1 = next(s for s in batch_summaries if s["name"] == "Player-1")
        b2 = next(s for s in batch_summaries if s["name"] == "Player-2")
        assert b1["total_cost"] == 0.001
        assert b2["total_cost"] == 0.002

    def test_match_start_requires_batch_id_in_context(self, recorder):
        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

        players = [MockPlayer("Player-1"), MockPlayer("Player-2")]

        recorder.on_batch_start(
            batch_id="batch_001",
            game=MockGame(),
            players=players,
            matches=1,
            context={"session_id": "test_session"},
        )

        with pytest.raises(ValueError, match="requires context\\['batch_id'\\]"):
            recorder.on_match_start(
                game=MockGame(),
                players=players,
                match_id="match_001",
                context={"session_id": "test_session"},
            )


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

        assert abort_event["data"]["prompt_text"] == "Handshake prompt"
        assert abort_event["data"]["response_text"] == "I refuse to play"


class TestConclusionDialogue:
    """Test 2A.4: Validate conclusion prompt capture."""

    def test_conclusion_dialogue_captured(self, recorder, temp_recorder_dir):
        """
        Verify PLAYER_CONCLUSION event captures post-match reflection.

        Assert:
            - Event preserves conclusion prompt fields verbatim
            - Prompt includes PM1-PM3 as top-level lifecycle data
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

        data = conclusion_events[0]["data"]
        assert data["prompt_text"] == "Reflect on your performance."
        assert data["response_text"] == "I played well and won!"
        assert data["controller_format"] == "Provide a brief reflection"


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
                    "action": {"value": "ATTACK", "reasoning": None, "metadata": {}},
                    "state_before": {},
                    "state_after": {},
                    "turn_context": {
                        "turn_number": 1,
                    },
                    "interaction": {
                        "prompt_text": "Turn 1 prompt",
                        "response_text": "ACTION: ATTACK",
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

        # Verify ordering and canonical prompt homes.
        assert lifecycle_events[0]["type"] == "player_handshake_complete"
        assert lifecycle_events[0]["data"]["prompt_text"] == "Handshake prompt"

        assert lifecycle_events[1]["type"] == "gameplay"
        assert lifecycle_events[1]["data"]["interaction"]["prompt_text"] == "Turn 1 prompt"
        assert lifecycle_events[1]["data"]["turn_context"]["turn_number"] == 1

        assert lifecycle_events[2]["type"] == "player_conclusion"
        assert lifecycle_events[2]["data"]["prompt_text"] == "Conclusion prompt"


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


class TestRecorderLowPriorityFindings:
    """Regression tests for low-priority recorder findings."""

    def test_batch_recording_uses_v1_0_schema(self, recorder, temp_recorder_dir):
        """Batch artifacts must remain on schema v1.0 per SPEC-RECORDER SV1."""

        class MockGame:
            pass

        class MockPlayer:
            def __init__(self, name):
                self.name = name

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
                seed=42,
                metadata={"players": ["Alice", "Bob"]},
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
                    seed=42,
                    metadata={"players": ["Alice", "Bob"]},
                )
            ],
            context={"session_id": "test_session"},
        )

        batch_file = temp_recorder_dir / "batch_batch_001.json"
        with open(batch_file, encoding="utf-8") as f:
            batch_data = json.load(f)

        assert batch_data["schema_type"] == "batch"
        assert batch_data["schema_version"] == "1.0"

    def test_git_dirty_uses_tracked_changes_only(self, recorder, monkeypatch):
        """git_info.dirty must ignore untracked files to avoid false positives."""

        def fake_run(cmd, capture_output, check, text):  # noqa: ANN001
            if cmd == ["git", "rev-parse", "--git-dir"]:
                return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
            if cmd == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="deadbeef\n", stderr="")
            if cmd == ["git", "branch", "--show-current"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="main\n", stderr="")
            if cmd == ["git", "status", "--porcelain", "--untracked-files=no"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            raise AssertionError(f"Unexpected git command: {cmd}")

        monkeypatch.setattr("agentdeck.core.recorder.subprocess.run", fake_run)

        git_info = recorder._get_git_info()

        assert git_info is not None
        assert git_info["commit"] == "deadbeef"
        assert git_info["branch"] == "main"
        assert git_info["dirty"] is False
