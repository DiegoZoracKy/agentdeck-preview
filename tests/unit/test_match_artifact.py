"""
Unit tests for MatchArtifact type (SPEC-PARALLEL v1.0.0 §4).

Tests verify:
- MatchArtifact structure and field types
- Integration with MatchResult and Event types
- Sorting by match_index (for ordered replay)
"""

import pytest
from agentdeck.core.types import MatchArtifact, MatchResult, Event


def test_match_artifact_structure():
    """Verify MatchArtifact has correct structure."""
    result = MatchResult(
        winner="Player A",
        final_state={"score": {"Player A": 10, "Player B": 5}},
        events=[],
        seed=42,
        metadata={"match_id": "test-match-1"},
    )

    events = [
        Event(
            type="match_start",
            data={"match_id": "test-match-1"},
            context={"session_id": "session-123", "batch_id": "batch-1"},
            timestamp=1.0,
            duration=0.0,
        ),
        Event(
            type="gameplay",
            data={"player": "Player A", "action": "attack"},
            context={
                "session_id": "session-123",
                "batch_id": "batch-1",
                "match_id": "test-match-1",
            },
            timestamp=2.0,
            duration=0.1,
        ),
        Event(
            type="match_end",
            data={"winner": "Player A"},
            context={
                "session_id": "session-123",
                "batch_id": "batch-1",
                "match_id": "test-match-1",
            },
            timestamp=3.0,
            duration=2.0,
        ),
    ]

    artifact = MatchArtifact(match_index=0, result=result, events=events)

    assert artifact.match_index == 0
    assert artifact.result == result
    assert artifact.events == events
    assert len(artifact.events) == 3


def test_match_artifact_fields_are_typed_correctly():
    """Verify field types match spec."""
    result = MatchResult(
        winner="Player A",
        final_state={},
        events=[],
        seed=42,
        metadata={},
    )

    artifact = MatchArtifact(match_index=5, result=result, events=[])

    assert isinstance(artifact.match_index, int)
    assert isinstance(artifact.result, MatchResult)
    assert isinstance(artifact.events, list)


def test_match_artifact_sorting_by_index():
    """Verify artifacts can be sorted by match_index for replay ordering."""
    # Create artifacts out of order
    artifact_2 = MatchArtifact(
        match_index=2,
        result=MatchResult(winner="B", final_state={}, events=[], seed=44, metadata={}),
        events=[],
    )
    artifact_0 = MatchArtifact(
        match_index=0,
        result=MatchResult(winner="A", final_state={}, events=[], seed=42, metadata={}),
        events=[],
    )
    artifact_1 = MatchArtifact(
        match_index=1,
        result=MatchResult(winner="C", final_state={}, events=[], seed=43, metadata={}),
        events=[],
    )

    artifacts = [artifact_2, artifact_0, artifact_1]

    # Sort by match_index (as Console will do for replay)
    sorted_artifacts = sorted(artifacts, key=lambda a: a.match_index)

    assert sorted_artifacts[0].match_index == 0
    assert sorted_artifacts[1].match_index == 1
    assert sorted_artifacts[2].match_index == 2

    # Verify results are in correct order
    assert sorted_artifacts[0].result.winner == "A"
    assert sorted_artifacts[1].result.winner == "C"
    assert sorted_artifacts[2].result.winner == "B"


def test_match_artifact_with_captured_events():
    """Verify artifact can hold events captured from worker's EventBus."""
    # Simulate events captured during worker execution
    captured_events = [
        Event(type="match_start", data={}, context={}, timestamp=1.0, duration=0.0),
        Event(type="player_handshake_start", data={}, context={}, timestamp=1.5, duration=0.0),
        Event(type="player_handshake_complete", data={}, context={}, timestamp=2.0, duration=0.5),
        Event(type="gameplay", data={}, context={}, timestamp=3.0, duration=0.0),
        Event(type="gameplay", data={}, context={}, timestamp=4.0, duration=0.0),
        Event(type="match_end", data={}, context={}, timestamp=5.0, duration=0.0),
    ]

    result = MatchResult(
        winner="Player A",
        final_state={},
        events=captured_events,  # MatchResult also stores events
        seed=42,
        metadata={},
    )

    artifact = MatchArtifact(match_index=0, result=result, events=captured_events)

    # Verify all events captured
    assert len(artifact.events) == 6
    assert artifact.events[0].type == "match_start"
    assert artifact.events[-1].type == "match_end"


def test_match_artifact_empty_events_valid():
    """Verify artifact can have empty events list (edge case)."""
    result = MatchResult(
        winner="Player A",
        final_state={},
        events=[],
        seed=42,
        metadata={},
    )

    artifact = MatchArtifact(match_index=0, result=result, events=[])

    assert artifact.events == []
    assert len(artifact.events) == 0
