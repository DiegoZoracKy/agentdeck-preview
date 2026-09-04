"""Deterministic Measures for the Agentic Edge Study.

These functions emit flat, individually addressable results. They do not author
Evidence or interpret what the results mean.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import median
from typing import Any, Mapping


def outcome_measure(measure_input):
    """Derive outcome, cost, seat, and declared binomial statistics per Cell."""

    results = []
    for cell_id, records in _by_cell(measure_input.records).items():
        payloads = [record.payload for record in records]
        players = sorted({str(player) for payload in payloads for player in payload["players"]})
        winners = Counter(payload.get("winner") for payload in payloads)
        decisive = sum(count for player, count in winners.items() if player is not None)
        costs = [_match_cost(payload) for payload in payloads]
        turns = [_match_turns(payload) for payload in payloads]
        durations = [_match_duration(payload) for payload in payloads]
        first_player_wins = sum(
            payload.get("winner") == _first_player(payload) for payload in payloads
        )
        dimensions = {"cell": cell_id}
        results.extend(
            [
                _result("match-count", dimensions, len(payloads), "records", len(payloads)),
                _result("decisive-match-count", dimensions, decisive, "records", len(payloads)),
                _result(
                    "draw-count", dimensions, len(payloads) - decisive, "records", len(payloads)
                ),
                _result("average-turns", dimensions, sum(turns) / len(turns), "turns", len(turns)),
                _result(
                    "first-player-win-rate",
                    dimensions,
                    first_player_wins / len(payloads),
                    "proportion",
                    len(payloads),
                ),
            ]
        )
        results.extend(_cost_results(dimensions, costs))
        results.append(
            _average_or_unavailable("average-duration", dimensions, durations, "seconds")
        )
        for player in players:
            player_dimensions = {"cell": cell_id, "player": player}
            wins = winners[player]
            as_first = [payload for payload in payloads if _first_player(payload) == player]
            as_second = [payload for payload in payloads if _first_player(payload) != player]
            first_wins = sum(payload.get("winner") == player for payload in as_first)
            second_wins = sum(payload.get("winner") == player for payload in as_second)
            results.append(_result("wins", player_dimensions, wins, "records", decisive))
            results.extend(_decisive_results(player_dimensions, wins, decisive))
            results.extend(
                (
                    _result(
                        "wins-as-first", player_dimensions, first_wins, "records", len(as_first)
                    ),
                    _rate_or_unavailable(
                        "win-rate-as-first",
                        player_dimensions,
                        first_wins,
                        len(as_first),
                        "records",
                    ),
                    _result(
                        "wins-as-second",
                        player_dimensions,
                        second_wins,
                        "records",
                        len(as_second),
                    ),
                    _rate_or_unavailable(
                        "win-rate-as-second",
                        player_dimensions,
                        second_wins,
                        len(as_second),
                        "records",
                    ),
                )
            )
    return results


def combat_behavior_measure(measure_input):
    """Derive promoted resource-policy and risk-band observations per Cell/Player."""

    parameters = dict(measure_input.parameters)
    fixed_threshold = int(parameters.get("fixed_critical_hp", 40))
    max_attack = int(parameters.get("variable_max_attack_damage", 25))
    potion_heal = int(parameters.get("potion_heal", 30))
    results = []
    for cell_id, records in _by_cell(measure_input.records).items():
        game_names = {str(record.payload.get("game")) for record in records}
        if len(game_names) != 1:
            raise ValueError(f"Cell {cell_id!r} contains multiple Games")
        game_name = next(iter(game_names))
        players = sorted(
            {str(player) for record in records for player in record.payload["players"]}
        )
        for player in players:
            match_turns = []
            losses = 0
            losses_with_unused = 0
            first_potion_hp = []
            all_attack = 0
            turns = []
            for record in records:
                payload = record.payload
                player_turns = [
                    turn for turn in _gameplay_turns(payload) if turn["player"] == player
                ]
                match_turns.append(player_turns)
                turns.extend(player_turns)
                if player_turns and all(turn["action"] == "ATTACK" for turn in player_turns):
                    all_attack += 1
                first_potion = next(
                    (turn["own_hp"] for turn in player_turns if turn["action"] == "POTION"),
                    None,
                )
                if first_potion is not None:
                    first_potion_hp.append(first_potion)
                if payload.get("winner") is not None and payload.get("winner") != player:
                    losses += 1
                    if (
                        int((payload.get("final_state") or {}).get("potions", {}).get(player, 0))
                        > 0
                    ):
                        losses_with_unused += 1
            dimensions = {"cell": cell_id, "player": player}
            support_matches = len(records)
            results.extend(
                [
                    _result(
                        "all-attack-match-rate",
                        dimensions,
                        all_attack / support_matches,
                        "proportion",
                        support_matches,
                    ),
                    _result(
                        "never-used-potion-rate",
                        dimensions,
                        (support_matches - len(first_potion_hp)) / support_matches,
                        "proportion",
                        support_matches,
                    ),
                    _available_or_unavailable_median(
                        "median-first-potion-hp", dimensions, first_potion_hp
                    ),
                    _rate_or_unavailable(
                        "unused-potions-on-loss-rate",
                        dimensions,
                        losses_with_unused,
                        losses,
                        "losses",
                    ),
                    _state_action_consistency(dimensions, turns),
                ]
            )
            if game_name == "FixedDamageGame":
                critical = [
                    turn
                    for turn in turns
                    if turn["own_potions"] > 0 and turn["own_hp"] <= fixed_threshold
                ]
                results.append(
                    _rate_or_unavailable(
                        "critical-potion-response-rate",
                        dimensions,
                        sum(turn["action"] == "POTION" for turn in critical),
                        len(critical),
                        "turns",
                    )
                )
            elif game_name == "VariableDamageGame":
                for band in ("lethal", "danger", "safe"):
                    band_turns = [
                        turn
                        for turn in turns
                        if turn["own_potions"] > 0
                        and _risk_band(turn["own_hp"], max_attack, potion_heal) == band
                    ]
                    results.append(
                        _rate_or_unavailable(
                            "potion-rate-by-risk-band",
                            {**dimensions, "risk-band": band},
                            sum(turn["action"] == "POTION" for turn in band_turns),
                            len(band_turns),
                            "turns",
                        )
                    )
            else:
                raise ValueError(f"Unsupported combat Game: {game_name}")
    return results


def _by_cell(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[record.cell_id].append(record)
    return {cell: grouped[cell] for cell in sorted(grouped)}


def _gameplay_turns(payload: Mapping[str, Any]):
    players = [str(player) for player in payload["players"]]
    first = _first_player(payload)
    positions = {player: ("first" if player == first else "second") for player in players}
    result = []
    for event in payload.get("events") or []:
        if event.get("type") != "gameplay":
            continue
        data = event.get("data") or {}
        player = str(data.get("player"))
        state = data.get("state_before") or {}
        action = data.get("action") or {}
        action_value = action.get("value") if isinstance(action, Mapping) else action
        opponent = next(candidate for candidate in players if candidate != player)
        result.append(
            {
                "player": player,
                "position": positions[player],
                "action": str(action_value).upper(),
                "own_hp": int((state.get("health") or {})[player]),
                "own_potions": int((state.get("potions") or {})[player]),
                "last_self": (state.get("last_action") or {}).get(player),
                "last_opponent": (state.get("last_action") or {}).get(opponent),
            }
        )
    return result


def _state_action_consistency(dimensions, turns):
    counts = defaultdict(Counter)
    for turn in turns:
        key = (
            turn["position"],
            turn["own_hp"],
            turn["own_potions"],
            turn["last_self"],
            turn["last_opponent"],
        )
        counts[key][turn["action"]] += 1
    supported = [counter for counter in counts.values() if sum(counter.values()) >= 2]
    support = sum(sum(counter.values()) for counter in supported)
    if not support:
        return _unavailable(
            "state-action-consistency",
            dimensions,
            "measure.insufficient-support",
            "No repeated decision state has support >= 2.",
        )
    return _result(
        "state-action-consistency",
        dimensions,
        sum(max(counter.values()) for counter in supported) / support,
        "proportion",
        support,
        support_unit="turns",
    )


def _first_player(payload):
    return str(
        (((payload.get("metadata") or {}).get("match") or {}).get("first_player") or {})["name"]
    )


def _match_cost(payload):
    match = (payload.get("metadata") or {}).get("match") or {}
    value = match.get("cost")
    return None if value is None else float(value)


def _match_duration(payload):
    value = payload.get("duration_seconds")
    return None if value is None else float(value)


def _match_turns(payload):
    match = (payload.get("metadata") or {}).get("match") or {}
    return int(
        match.get("turns")
        or sum(event.get("type") == "gameplay" for event in payload.get("events") or [])
    )


def _risk_band(hp, max_attack, potion_heal):
    if hp <= max_attack:
        return "lethal"
    if hp <= max_attack + potion_heal:
        return "danger"
    return "safe"


def _two_sided_binomial_p(successes, trials):
    if trials <= 0:
        raise ValueError("Exact binomial probability requires at least one trial")
    observed = math.comb(trials, successes) / (2.0**trials)
    return min(
        1.0,
        sum(
            math.comb(trials, count) / (2.0**trials)
            for count in range(trials + 1)
            if math.comb(trials, count) / (2.0**trials) <= observed + 1e-15
        ),
    )


def _wilson_interval(successes, trials):
    if trials <= 0:
        raise ValueError("Wilson interval requires at least one trial")
    z = 1.959963984540054
    rate = successes / trials
    denominator = 1.0 + z * z / trials
    center = (rate + z * z / (2.0 * trials)) / denominator
    margin = (
        z * math.sqrt(rate * (1.0 - rate) / trials + z * z / (4.0 * trials * trials)) / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def _available_or_unavailable_median(metric, dimensions, values):
    if not values:
        return _unavailable(
            metric,
            dimensions,
            "measure.no-observations",
            "No Player match contains the required POTION observation.",
        )
    return _result(
        metric, dimensions, float(median(values)), "hp", len(values), support_unit="observations"
    )


def _cost_results(dimensions, costs):
    if any(value is None for value in costs):
        diagnostic = (
            "measure.missing-cost",
            "At least one Record does not contain an observed Match cost.",
        )
        return [
            _unavailable("total-cost", dimensions, *diagnostic),
            _unavailable("average-cost", dimensions, *diagnostic),
        ]
    total = sum(costs)
    return [
        _result("total-cost", dimensions, total, "usd", len(costs)),
        _result("average-cost", dimensions, total / len(costs), "usd", len(costs)),
    ]


def _average_or_unavailable(metric, dimensions, values, unit):
    if not values or any(value is None for value in values):
        return _unavailable(
            metric,
            dimensions,
            "measure.missing-observation",
            f"At least one Record does not contain the required {metric} observation.",
        )
    return _result(metric, dimensions, sum(values) / len(values), unit, len(values))


def _decisive_results(dimensions, wins, decisive):
    metrics = (
        "win-rate",
        "win-rate-ci-lower",
        "win-rate-ci-upper",
        "exact-binomial-p-value",
        "cohens-h-versus-half",
    )
    if not decisive:
        return [
            _unavailable(
                metric,
                dimensions,
                "measure.no-decisive-matches",
                "No decisive Matches satisfy the Measure denominator.",
            )
            for metric in metrics
        ]
    rate = wins / decisive
    lower, upper = _wilson_interval(wins, decisive)
    return [
        _result("win-rate", dimensions, rate, "proportion", decisive),
        _result("win-rate-ci-lower", dimensions, lower, "proportion", decisive),
        _result("win-rate-ci-upper", dimensions, upper, "proportion", decisive),
        _result(
            "exact-binomial-p-value",
            dimensions,
            _two_sided_binomial_p(wins, decisive),
            "probability",
            decisive,
        ),
        _result(
            "cohens-h-versus-half",
            dimensions,
            2.0 * math.asin(math.sqrt(rate)) - math.pi / 2.0,
            "effect-size",
            decisive,
        ),
    ]


def _rate_or_unavailable(metric, dimensions, hits, support, support_unit):
    if not support:
        return _unavailable(
            metric,
            dimensions,
            "measure.no-support",
            f"No {support_unit} satisfy the Measure denominator.",
        )
    return _result(
        metric, dimensions, hits / support, "proportion", support, support_unit=support_unit
    )


def _result(metric, dimensions, value, unit, support, support_unit="records"):
    return {
        "metric": metric,
        "dimensions": dimensions,
        "status": "available",
        "value": value,
        "unit": unit,
        "support": {"count": support, "unit": support_unit},
    }


def _unavailable(metric, dimensions, code, message):
    return {
        "metric": metric,
        "dimensions": dimensions,
        "status": "unavailable",
        "diagnostic": {"code": code, "message": message},
    }
