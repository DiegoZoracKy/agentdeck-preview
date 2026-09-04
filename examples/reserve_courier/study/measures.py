"""Deterministic observations from immutable canonical Records, never provider calls."""

from collections import defaultdict


def behavior_measure(measure_input):
    cells = defaultdict(list)
    for record in measure_input.records:
        cells[record.cell_id].append(record)
    results = []
    for cell, records in sorted(cells.items()):
        completed = [
            r
            for r in records
            if r.payload.get("final_state", {}).get("done") is True
            and r.payload.get("metadata", {}).get("match", {}).get("outcome")
            not in {"aborted", "execution_error"}
        ]
        sources = [{"record_sha256": r.record_sha256, "pointer": "/final_state"} for r in records]

        def emit(metric, value, unit, count, support_unit="records", source=sources):
            results.append(
                {
                    "metric": metric,
                    "dimensions": {"cell": cell},
                    "status": "available",
                    "value": value,
                    "unit": unit,
                    "support": {"count": count, "unit": support_unit},
                    "sources": source,
                }
            )

        emit("terminal-observation-rate", len(completed) / len(records), "proportion", len(records))
        if completed:
            terminal_sources = [
                {"record_sha256": r.record_sha256, "pointer": "/final_state"} for r in completed
            ]
            states = [r.payload["final_state"] for r in completed]
            emit(
                "viable-rate",
                sum(s["viable"] for s in states) / len(states),
                "proportion",
                len(states),
                source=terminal_sources,
            )
            emit(
                "optimal-rate",
                sum(s["score"] == 15 for s in states) / len(states),
                "proportion",
                len(states),
                source=terminal_sources,
            )
            emit(
                "mean-score",
                sum(s["score"] for s in states) / len(states),
                "points",
                len(states),
                source=terminal_sources,
            )
            emit(
                "mean-regret",
                sum(15 - s["score"] for s in states) / len(states),
                "points",
                len(states),
                source=terminal_sources,
            )
        else:
            for metric in ("viable-rate", "optimal-rate", "mean-score", "mean-regret"):
                results.append(
                    {
                        "metric": metric,
                        "dimensions": {"cell": cell},
                        "status": "unavailable",
                        "diagnostic": {
                            "code": "courier.no-terminal-observation",
                            "message": "No completed Game state; no behavioral score inferred.",
                        },
                    }
                )
        turns = [
            (r, i, e["data"])
            for r in records
            for i, e in enumerate(r.payload.get("events", ()))
            if e["type"] == "gameplay"
        ]
        failed = sum(
            any(e["type"] == "player_action_parse_failed" for e in r.payload.get("events", ()))
            for r in records
        )
        emit(
            "parse-failure-record-rate",
            failed / len(records),
            "proportion",
            len(records),
            source=[{"record_sha256": r.record_sha256, "pointer": "/events"} for r in records],
        )
        if turns:
            turn_sources = [
                {"record_sha256": r.record_sha256, "pointer": f"/events/{i}/data"}
                for r, i, _ in turns
            ]
            compliant = 0
            for _, _, data in turns:
                metadata = data["action"].get("metadata") or {}
                compliant += metadata.get("contract_satisfied") is True
            emit(
                "response-contract-rate",
                compliant / len(turns),
                "proportion",
                len(turns),
                "turns",
                turn_sources,
            )
            emit(
                "express-action-rate",
                sum(d["action"]["value"] == "EXPRESS" for _, _, d in turns) / len(turns),
                "proportion",
                len(turns),
                "turns",
                turn_sources,
            )
        costs = [(r.payload.get("metadata", {}).get("match") or {}).get("cost") for r in records]
        if all(isinstance(cost, (int, float)) for cost in costs):
            emit(
                "known-total-cost",
                sum(costs),
                "usd",
                len(records),
                source=[
                    {"record_sha256": r.record_sha256, "pointer": "/metadata/match/cost"}
                    for r in records
                ],
            )
    return results
