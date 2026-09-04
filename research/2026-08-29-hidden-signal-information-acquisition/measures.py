"""Deterministic behavioral Measure for Hidden Signal Records."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping


def inspection_measure(measure_input):
    """Derive inspection and commitment observations per exact Study Cell."""

    results = []
    for cell_id, records in _by_cell(measure_input.records).items():
        committed = []
        for record in records:
            actions = _actions(record.payload)
            choice_index = next(
                (index for index, action in enumerate(actions) if action.startswith("CHOOSE_")),
                None,
            )
            if choice_index is not None:
                committed.append((record, actions, choice_index))

        dimensions = {"cell": cell_id}
        if not committed:
            results.extend(
                (
                    _unavailable(
                        "inspection-before-commit-rate",
                        dimensions,
                        "measure.no-commitments",
                        "No Record contains a commitment action.",
                    ),
                    _unavailable(
                        "correct-commitment-rate",
                        dimensions,
                        "measure.no-commitments",
                        "No Record contains a commitment action.",
                    ),
                    _unavailable(
                        "average-decision-turns",
                        dimensions,
                        "measure.no-commitments",
                        "No Record contains a commitment action.",
                    ),
                )
            )
            continue

        inspected = sum(
            "INSPECT" in actions[:choice_index] for _, actions, choice_index in committed
        )
        turns = [choice_index + 1 for _, _, choice_index in committed]
        commitment_sources = [
            {
                "record_sha256": record.record_sha256,
                "pointer": _action_pointer(record.payload, choice_index),
            }
            for record, _, choice_index in committed
        ]
        results.extend(
            (
                _available(
                    "inspection-before-commit-rate",
                    dimensions,
                    inspected / len(committed),
                    "proportion",
                    len(committed),
                    "committed-runs",
                    commitment_sources,
                ),
                _available(
                    "average-decision-turns",
                    dimensions,
                    sum(turns) / len(turns),
                    "turns",
                    len(committed),
                    "committed-runs",
                    commitment_sources,
                ),
            )
        )
        correctness = [
            record.payload.get("final_state", {}).get("correct") for record, _, _ in committed
        ]
        if all(isinstance(value, bool) for value in correctness):
            results.append(
                _available(
                    "correct-commitment-rate",
                    dimensions,
                    sum(correctness) / len(correctness),
                    "proportion",
                    len(committed),
                    "committed-runs",
                    [
                        {
                            "record_sha256": record.record_sha256,
                            "pointer": "/final_state/correct",
                        }
                        for record, _, _ in committed
                    ],
                )
            )
        else:
            results.append(
                _unavailable(
                    "correct-commitment-rate",
                    dimensions,
                    "measure.missing-correctness",
                    "At least one committed Record has no boolean final correctness.",
                )
            )
    return results


def _by_cell(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[record.cell_id].append(record)
    return {cell: grouped[cell] for cell in sorted(grouped)}


def _actions(payload: Mapping[str, Any]) -> list[str]:
    return [
        _action_value(event)
        for event in payload.get("events") or []
        if event.get("type") == "gameplay"
    ]


def _action_value(event: Mapping[str, Any]) -> str:
    action = (event.get("data") or {}).get("action")
    value = action.get("value") if isinstance(action, Mapping) else action
    return str(value).upper()


def _action_pointer(payload: Mapping[str, Any], gameplay_index: int) -> str:
    current = -1
    for event_index, event in enumerate(payload.get("events") or []):
        if event.get("type") != "gameplay":
            continue
        current += 1
        if current == gameplay_index:
            action = (event.get("data") or {}).get("action")
            suffix = "/value" if isinstance(action, Mapping) else ""
            return f"/events/{event_index}/data/action{suffix}"
    raise ValueError("Commitment action does not resolve to a gameplay event")


def _available(metric, dimensions, value, unit, support, support_unit, sources):
    return {
        "metric": metric,
        "dimensions": dimensions,
        "status": "available",
        "value": value,
        "unit": unit,
        "support": {"count": support, "unit": support_unit},
        "sources": sources,
    }


def _unavailable(metric, dimensions, code, message):
    return {
        "metric": metric,
        "dimensions": dimensions,
        "status": "unavailable",
        "diagnostic": {"code": code, "message": message},
    }
