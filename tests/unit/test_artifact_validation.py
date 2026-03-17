"""Unit tests for exported recording artifact invariants."""

from __future__ import annotations

from agentdeck.research.artifact_validation import validate_artifact_invariants


def _match_payload() -> dict:
    return {
        "match_id": "match_001",
        "players": ["Alice", "Bob"],
        "winner": "Alice",
        "final_state": {"health": {"Alice": 40, "Bob": 0}},
        "started_at": "2026-03-17T12:00:00Z",
        "ended_at": "2026-03-17T12:00:01Z",
        "duration_seconds": 1.0,
        "metadata": {
            "winner": "Alice",
            "match": {
                "winner": "Alice",
                "started_at": "2026-03-17T12:00:00Z",
                "ended_at": "2026-03-17T12:00:01Z",
                "duration_seconds": 1.0,
            },
        },
        "events": [
            {
                "type": "gameplay",
                "timestamp": 10.0,
                "data": {
                    "turn_context": {"turn_number": 1},
                    "prompt": {"phase": "turn", "turn_number": 1},
                },
            },
            {
                "type": "gameplay",
                "timestamp": 11.0,
                "data": {
                    "turn_context": {"turn_number": 2},
                    "prompt": {"phase": "turn", "turn_number": 2},
                },
            },
        ],
    }


def test_validate_artifact_invariants_passes_for_consistent_payload() -> None:
    validation = validate_artifact_invariants([_match_payload()])

    assert validation["all_passed"] is True
    assert validation["matches_checked"] == 1
    assert validation["failures"] == []
    assert validation["checks"]["monotonic_gameplay_timeline"]["failed"] == 0


def test_detects_monotonic_gameplay_timestamp_regression() -> None:
    payload = _match_payload()
    payload["events"][1]["timestamp"] = 9.0

    validation = validate_artifact_invariants([payload])

    assert validation["all_passed"] is False
    messages = [failure["message"] for failure in validation["failures"]]
    assert any("gameplay timestamp decreased" in message for message in messages)


def test_detects_top_level_timing_mismatch() -> None:
    payload = _match_payload()
    payload["ended_at"] = "2026-03-17T11:59:59Z"
    payload["duration_seconds"] = 5.0

    validation = validate_artifact_invariants([payload])

    assert validation["all_passed"] is False
    messages = [failure["message"] for failure in validation["failures"]]
    assert any(
        "duration_seconds" in message or "ended_at precedes started_at" in message
        for message in messages
    )


def test_detects_prompt_turn_number_mismatch() -> None:
    payload = _match_payload()
    payload["events"][1]["data"]["prompt"]["turn_number"] = 3

    validation = validate_artifact_invariants([payload])

    assert validation["all_passed"] is False
    messages = [failure["message"] for failure in validation["failures"]]
    assert any("prompt.turn_number mismatch" in message for message in messages)


def test_detects_conflicting_turn_number_sources() -> None:
    payload = _match_payload()
    payload["events"][1]["data"]["metadata"] = {"turn_number": 5}

    validation = validate_artifact_invariants([payload])

    assert validation["all_passed"] is False
    messages = [failure["message"] for failure in validation["failures"]]
    assert any("conflicting turn numbers" in message for message in messages)


def test_detects_winner_final_state_inconsistency() -> None:
    payload = _match_payload()
    payload["metadata"]["match"]["winner"] = "Bob"

    validation = validate_artifact_invariants([payload])

    assert validation["all_passed"] is False
    messages = [failure["message"] for failure in validation["failures"]]
    assert any("metadata winner does not match top-level winner" in message for message in messages)
