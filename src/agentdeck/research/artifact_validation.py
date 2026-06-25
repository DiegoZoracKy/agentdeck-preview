"""Game-agnostic artifact invariant checks for recorded match payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

_CHECK_ORDER: Tuple[str, ...] = (
    "monotonic_gameplay_timeline",
    "top_level_timing_consistency",
    "prompt_turn_number_coherence",
    "winner_final_state_consistency",
)


def _as_match_id(payload: Dict[str, Any], index: int) -> str:
    match_id = payload.get("match_id")
    if isinstance(match_id, str) and match_id.strip():
        return match_id
    return f"<match-{index}>"


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _get_top_level_timing(payload: Dict[str, Any]) -> Tuple[Any, Any, Any]:
    metadata = payload.get("metadata")
    match_meta = metadata.get("match") if isinstance(metadata, dict) else None

    started_at = payload.get("started_at")
    ended_at = payload.get("ended_at")
    duration_seconds = payload.get("duration_seconds")

    if started_at is None and isinstance(match_meta, dict):
        started_at = match_meta.get("started_at")
    if ended_at is None and isinstance(match_meta, dict):
        ended_at = match_meta.get("ended_at")
    if duration_seconds is None and isinstance(match_meta, dict):
        duration_seconds = match_meta.get("duration_seconds")
    if duration_seconds is None and isinstance(match_meta, dict):
        duration_seconds = match_meta.get("duration")

    return started_at, ended_at, duration_seconds


def _source_turn_numbers(event_data: Dict[str, Any]) -> List[Tuple[str, int]]:
    values: List[Tuple[str, int]] = []

    turn_context = event_data.get("turn_context")
    if isinstance(turn_context, dict):
        turn_number = _as_int(turn_context.get("turn_number"))
        if turn_number is not None:
            values.append(("data.turn_context.turn_number", turn_number))

    return values


def _resolve_consistent_turn_number(
    event_data: Dict[str, Any],
) -> Tuple[Optional[int], Optional[str]]:
    values = _source_turn_numbers(event_data)

    if not values:
        return None, None

    unique_turn_numbers = sorted({turn for _, turn in values})
    if len(unique_turn_numbers) > 1:
        details = ", ".join(f"{source}={turn}" for source, turn in values)
        return None, f"conflicting turn numbers ({details})"

    return unique_turn_numbers[0], None


def _check_monotonic_gameplay_timeline(payload: Dict[str, Any], match_id: str) -> List[str]:
    failures: List[str] = []
    events = payload.get("events")
    if not isinstance(events, list):
        return [f"{match_id}: events must be a list"]

    previous_timestamp: Optional[float] = None
    previous_turn_number: Optional[int] = None

    for event_index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("type") != "gameplay":
            continue

        timestamp = _as_float(event.get("timestamp"))
        if event.get("timestamp") is not None and timestamp is None:
            failures.append(f"{match_id}: gameplay event {event_index} has non-numeric timestamp")
        if (
            previous_timestamp is not None
            and timestamp is not None
            and timestamp < previous_timestamp
        ):
            failures.append(f"{match_id}: gameplay timestamp decreased at event {event_index}")
        if timestamp is not None:
            previous_timestamp = timestamp

        data = event.get("data")
        if not isinstance(data, dict):
            failures.append(f"{match_id}: gameplay event {event_index} has non-mapping data")
            continue

        prompt_turn_number, error = _resolve_consistent_turn_number(data)
        if error is not None:
            failures.append(f"{match_id}: gameplay event {event_index} has {error}")
            continue

        if previous_turn_number is not None and prompt_turn_number is not None:
            if prompt_turn_number <= previous_turn_number:
                failures.append(
                    f"{match_id}: gameplay turn number did not increase at event {event_index}"
                )
        if prompt_turn_number is not None:
            previous_turn_number = prompt_turn_number

    return failures


def _check_top_level_timing_consistency(payload: Dict[str, Any], match_id: str) -> List[str]:
    failures: List[str] = []
    started_at, ended_at, duration_seconds = _get_top_level_timing(payload)

    start_dt = _parse_iso(started_at)
    end_dt = _parse_iso(ended_at)
    duration = _as_float(duration_seconds)

    if started_at is None:
        failures.append(f"{match_id}: missing started_at")
    elif start_dt is None:
        failures.append(f"{match_id}: started_at is not valid ISO-8601")

    if ended_at is None:
        failures.append(f"{match_id}: missing ended_at")
    elif end_dt is None:
        failures.append(f"{match_id}: ended_at is not valid ISO-8601")

    if duration_seconds is None:
        failures.append(f"{match_id}: missing duration_seconds")
    elif duration is None:
        failures.append(f"{match_id}: duration_seconds must be numeric")
    elif duration < 0:
        failures.append(f"{match_id}: duration_seconds must be >= 0")

    if start_dt is not None and end_dt is not None:
        observed_duration = (end_dt - start_dt).total_seconds()
        if observed_duration < 0:
            failures.append(f"{match_id}: ended_at precedes started_at")
        elif duration is not None and abs(observed_duration - duration) > 1e-6:
            failures.append(
                f"{match_id}: duration_seconds does not match started_at/ended_at delta"
            )

    return failures


def _check_prompt_turn_number_coherence(payload: Dict[str, Any], match_id: str) -> List[str]:
    failures: List[str] = []
    events = payload.get("events")
    if not isinstance(events, list):
        return [f"{match_id}: events must be a list"]

    for event_index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("type") != "gameplay":
            continue

        data = event.get("data")
        if not isinstance(data, dict):
            failures.append(
                f"{match_id}: {event.get('type')} event {event_index} has non-mapping data"
            )
            continue

        source_turns = _source_turn_numbers(data)
        unique_turn_numbers = sorted({turn for _, turn in source_turns})

        if not unique_turn_numbers:
            failures.append(
                f"{match_id}: gameplay event {event_index} missing turn_context.turn_number"
            )
            continue

    return failures


def _check_winner_final_state_consistency(payload: Dict[str, Any], match_id: str) -> List[str]:
    failures: List[str] = []
    players = payload.get("players")
    winner = payload.get("winner")
    final_state = payload.get("final_state")
    metadata = payload.get("metadata")

    if not isinstance(players, list) or not all(isinstance(player, str) for player in players):
        failures.append(f"{match_id}: players must be a list of strings")
        return failures

    if winner is not None and winner not in players:
        failures.append(f"{match_id}: winner must be one of players")

    if final_state is None:
        failures.append(f"{match_id}: final_state missing")
    elif not isinstance(final_state, dict):
        failures.append(f"{match_id}: final_state must be a mapping")

    metadata_winner = None
    if isinstance(metadata, dict):
        if isinstance(metadata.get("winner"), str):
            metadata_winner = metadata["winner"]
        match_meta = metadata.get("match")
        if isinstance(match_meta, dict) and isinstance(match_meta.get("winner"), str):
            metadata_winner = match_meta["winner"]

    if metadata_winner is not None and metadata_winner != winner:
        failures.append(f"{match_id}: metadata winner does not match top-level winner")

    return failures


def validate_artifact_invariants(match_payloads: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate game-agnostic recording invariants across exported match payloads."""

    checkers = {
        "monotonic_gameplay_timeline": _check_monotonic_gameplay_timeline,
        "top_level_timing_consistency": _check_top_level_timing_consistency,
        "prompt_turn_number_coherence": _check_prompt_turn_number_coherence,
        "winner_final_state_consistency": _check_winner_final_state_consistency,
    }
    failed_matches: Dict[str, set[str]] = {name: set() for name in _CHECK_ORDER}
    failures: List[Dict[str, str]] = []

    for index, payload in enumerate(match_payloads):
        match_id = _as_match_id(payload, index)
        for check_name in _CHECK_ORDER:
            messages = checkers[check_name](payload, match_id)
            if not messages:
                continue
            failed_matches[check_name].add(match_id)
            for message in messages:
                failures.append(
                    {
                        "match_id": match_id,
                        "check": check_name,
                        "message": message,
                    }
                )

    total_matches = len(match_payloads)
    checks: Dict[str, Dict[str, int]] = {}
    for check_name in _CHECK_ORDER:
        failed = len(failed_matches[check_name])
        checks[check_name] = {
            "passed": total_matches - failed,
            "failed": failed,
        }

    return {
        "matches_checked": total_matches,
        "all_passed": len(failures) == 0,
        "checks": checks,
        "failures": failures,
    }


def format_artifact_validation_errors(validation: Dict[str, Any]) -> str:
    """Render invariant failures into a stable human-readable message."""

    failures = validation.get("failures")
    if not isinstance(failures, list) or not failures:
        return ""

    lines: List[str] = []
    for item in failures:
        if not isinstance(item, dict):
            continue
        message = item.get("message")
        if isinstance(message, str) and message:
            lines.append(f"- {message}")
    return "\n".join(lines)
