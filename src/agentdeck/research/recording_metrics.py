"""Reusable metrics computed from recorder match payloads.

This module is game-agnostic by design. It computes:
- Inferential statistics from match winners
- Format strictness/compliance from recorder events
"""

from __future__ import annotations

import re
from itertools import combinations
from typing import Any, Dict, Iterable, List, Tuple

from .statistical import (
    calculate_confidence_interval,
    calculate_effect_size,
    statistical_significance,
)

ACTION_LINE = re.compile(r"(?im)^\s*ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)\b")
REASONING_LINE = re.compile(r"(?im)^\s*REASONING:\s*(?P<reasoning>.+)$")


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _effect_label(effect_size: float) -> str:
    magnitude = abs(float(effect_size))
    if magnitude < 0.2:
        return "negligible"
    if magnitude < 0.5:
        return "small"
    if magnitude < 0.8:
        return "medium"
    return "large"


def _player_names(players: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> List[str]:
    names = [str(player.get("name")) for player in players if player.get("name")]
    if names:
        return names

    inferred = set()
    for match in matches:
        for name in match.get("players") or []:
            inferred.add(str(name))
        winner = match.get("winner")
        if winner:
            inferred.add(str(winner))
    return sorted(inferred)


def compute_inferential_statistics(
    *,
    players: List[Dict[str, Any]],
    matches: List[Dict[str, Any]],
    confidence_level: float = 0.95,
    alpha: float = 0.05,
    null_win_rate: float = 0.5,
) -> Dict[str, Any]:
    """
    Compute inferential statistics from match-level outcomes.

    Args:
        players: Results player payload (`results.players`)
        matches: Results match payload (`results.matches`)
        confidence_level: Confidence level for interval computation
        alpha: Significance threshold
        null_win_rate: Null hypothesis win probability

    Returns:
        Dict ready to be embedded under `results.json.statistics`.
    """
    player_names = _player_names(players, matches)
    wins = {name: 0 for name in player_names}
    decisive = 0

    for match in matches:
        winner = match.get("winner")
        if winner in wins:
            wins[winner] += 1
            decisive += 1

    per_player: Dict[str, Dict[str, Any]] = {}
    for name in player_names:
        successes = wins[name]
        win_rate = _safe_rate(successes, decisive)

        if decisive > 0:
            try:
                ci_lower, ci_upper = calculate_confidence_interval(
                    successes, decisive, confidence_level
                )
            except ImportError:
                ci_lower, ci_upper = (max(0.0, win_rate - 0.1), min(1.0, win_rate + 0.1))

            try:
                p_value = statistical_significance(successes, decisive, null_win_rate)
            except ImportError:
                p_value = 1.0

            effect_size = calculate_effect_size(win_rate, null_win_rate, decisive)
        else:
            ci_lower, ci_upper = (0.0, 0.0)
            p_value = 1.0
            effect_size = 0.0

        per_player[name] = {
            "wins": successes,
            "win_rate": win_rate,
            "ci": [float(ci_lower), float(ci_upper)],
            "p_value": float(p_value),
            "effect_size": float(effect_size),
            "effect_label": _effect_label(effect_size),
            "is_significant": bool(p_value < alpha),
        }

    pairwise: Dict[str, Dict[str, Any]] = {}
    for left, right in combinations(player_names, 2):
        left_wins = wins[left]
        right_wins = wins[right]
        head_to_head = left_wins + right_wins

        if head_to_head > 0:
            left_rate = _safe_rate(left_wins, head_to_head)
            try:
                ci_lower, ci_upper = calculate_confidence_interval(
                    left_wins, head_to_head, confidence_level
                )
            except ImportError:
                ci_lower, ci_upper = (max(0.0, left_rate - 0.1), min(1.0, left_rate + 0.1))

            try:
                p_value = statistical_significance(left_wins, head_to_head, 0.5)
            except ImportError:
                p_value = 1.0

            effect_size = calculate_effect_size(left_rate, 0.5, head_to_head)
        else:
            left_rate = 0.0
            ci_lower, ci_upper = (0.0, 0.0)
            p_value = 1.0
            effect_size = 0.0

        key = f"{left}_vs_{right}"
        pairwise[key] = {
            "player_a": left,
            "player_b": right,
            "wins_a": left_wins,
            "wins_b": right_wins,
            "head_to_head_decisive": head_to_head,
            "win_rate_a": left_rate,
            "ci_a": [float(ci_lower), float(ci_upper)],
            "p_value": float(p_value),
            "effect_size": float(effect_size),
            "effect_label": _effect_label(effect_size),
            "is_significant": bool(p_value < alpha),
        }

    minimum_recommended = 10
    insufficient_sample = decisive < minimum_recommended

    return {
        "method": "exact_binomial",
        "confidence_level": float(confidence_level),
        "alpha": float(alpha),
        "null_win_rate": float(null_win_rate),
        "n_total": len(matches),
        "n_decisive": decisive,
        "players": per_player,
        "pairwise_comparisons": pairwise,
        "quality": {
            "insufficient_sample": insufficient_sample,
            "n_decisive": decisive,
            "min_recommended": minimum_recommended,
            "is_actionable": not insufficient_sample,
            "quality_note": (
                "Sample too small for reliable inference"
                if insufficient_sample
                else "Sample size sufficient for baseline inferential readout"
            ),
        },
    }


def _initial_strictness_row() -> Dict[str, Any]:
    return {
        "turn_attempts": 0,
        "parse_failures": 0,
        "contract_evaluable_attempts": 0,
        "strict_contract_passes": 0,
        "recoverable_non_strict": 0,
        "action_line_hits": 0,
        "reasoning_line_hits": 0,
    }


def _controller_contract_kind(controller_name: str | None) -> str | None:
    if not controller_name:
        return None
    lowered = controller_name.lower()
    if "reasoningcontroller" in lowered:
        return "reasoning"
    if "actiononlycontroller" in lowered:
        return "action_only"
    return None


def _raw_response_from_event(event_data: Dict[str, Any]) -> str:
    metadata = event_data.get("metadata") or {}
    prompt = event_data.get("prompt") or {}

    value = (
        metadata.get("raw_response")
        or event_data.get("raw_response")
        or prompt.get("response_text")
        or event_data.get("response_text")
        or ""
    )
    return str(value).strip()


def _finalize_strictness_row(row: Dict[str, Any]) -> Dict[str, Any]:
    attempts = int(row.get("turn_attempts", 0))
    contract_attempts = int(row.get("contract_evaluable_attempts", 0))
    parse_failures = int(row.get("parse_failures", 0))
    strict_passes = int(row.get("strict_contract_passes", 0))
    recoverable_non_strict = int(row.get("recoverable_non_strict", 0))
    action_hits = int(row.get("action_line_hits", 0))
    reasoning_hits = int(row.get("reasoning_line_hits", 0))

    return {
        "turn_attempts": attempts,
        "parse_failures": parse_failures,
        "parse_failure_rate": _safe_rate(parse_failures, attempts),
        "contract_evaluable_attempts": contract_attempts,
        "strict_contract_passes": strict_passes,
        "strict_contract_rate": _safe_rate(strict_passes, contract_attempts),
        "recoverable_non_strict": recoverable_non_strict,
        "recoverable_non_strict_rate": _safe_rate(recoverable_non_strict, contract_attempts),
        "action_line_rate": _safe_rate(action_hits, attempts),
        "reasoning_line_rate": _safe_rate(reasoning_hits, attempts),
    }


def compute_format_strictness(match_payloads: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute game-agnostic response format strictness from recorder events.

    Evaluated event types:
    - `gameplay`
    - `player_action_parse_failed`

    Strict contract per controller:
    - ActionOnlyController: requires `ACTION:` line
    - ReasoningController: requires both `REASONING:` and `ACTION:` lines
    """
    controller_by_player: Dict[str, str] = {}
    for payload in match_payloads:
        summaries = (payload.get("metadata") or {}).get("player_summaries") or []
        for summary in summaries:
            name = summary.get("name")
            controller = summary.get("controller")
            if name and controller:
                controller_by_player[str(name)] = str(controller)

    rows: Dict[str, Dict[str, Any]] = {
        player: _initial_strictness_row() for player in sorted(controller_by_player.keys())
    }

    for payload in match_payloads:
        for event in payload.get("events") or []:
            event_type = event.get("type")
            if event_type not in {"gameplay", "player_action_parse_failed"}:
                continue

            event_data = event.get("data") or {}
            player = event_data.get("player")
            if not player:
                continue
            player = str(player)
            row = rows.setdefault(player, _initial_strictness_row())
            row["turn_attempts"] += 1

            metadata = event_data.get("metadata") or {}
            parse_success = bool(metadata.get("parser_success", True))
            parse_failed = event_type == "player_action_parse_failed" or not parse_success
            if parse_failed:
                row["parse_failures"] += 1

            raw_response = _raw_response_from_event(event_data)
            has_action_line = bool(ACTION_LINE.search(raw_response))
            has_reasoning_line = bool(REASONING_LINE.search(raw_response))

            if has_action_line:
                row["action_line_hits"] += 1
            if has_reasoning_line:
                row["reasoning_line_hits"] += 1

            contract_kind = _controller_contract_kind(controller_by_player.get(player))
            if contract_kind is None:
                continue

            row["contract_evaluable_attempts"] += 1

            if contract_kind == "reasoning":
                strict_pass = has_action_line and has_reasoning_line
            else:
                strict_pass = has_action_line

            if strict_pass:
                row["strict_contract_passes"] += 1
            elif not parse_failed:
                row["recoverable_non_strict"] += 1

    finalized = {player: _finalize_strictness_row(row) for player, row in rows.items()}

    aggregate = _initial_strictness_row()
    for row in rows.values():
        for key in aggregate:
            aggregate[key] += int(row.get(key, 0))

    return {"overall": _finalize_strictness_row(aggregate), "by_player": finalized}


def compute_position_effect(
    *,
    players: List[Dict[str, Any]],
    matches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute first-player advantage and upset metrics from match-level metadata.

    This metric is intentionally game-agnostic and uses only:
    - `match.first_player.name`
    - `match.winner`
    """
    player_names = _player_names(players, matches)
    by_player: Dict[str, Dict[str, Any]] = {
        name: {
            "first_count": 0,
            "second_count": 0,
            "wins_as_first": 0,
            "wins_as_second": 0,
        }
        for name in player_names
    }

    first_player_wins = 0
    second_player_wins = 0

    for match in matches:
        participants = [str(p) for p in (match.get("players") or [])]
        winner = match.get("winner")
        first = ((match.get("first_player") or {}).get("name")) or None

        if not participants:
            continue

        second = None
        if first in participants:
            for participant in participants:
                if participant != first:
                    second = participant
                    break

        if first in by_player:
            by_player[first]["first_count"] += 1
        if second in by_player:
            by_player[second]["second_count"] += 1

        if winner and first and winner == first:
            first_player_wins += 1
            if first in by_player:
                by_player[first]["wins_as_first"] += 1
        elif winner and first:
            second_player_wins += 1
            if winner in by_player:
                by_player[winner]["wins_as_second"] += 1

    total_matches = len(matches)
    finalized_by_player: Dict[str, Dict[str, Any]] = {}
    for name, row in by_player.items():
        first_count = int(row["first_count"])
        second_count = int(row["second_count"])
        wins_as_first = int(row["wins_as_first"])
        wins_as_second = int(row["wins_as_second"])
        finalized_by_player[name] = {
            "first_count": first_count,
            "second_count": second_count,
            "wins_as_first": wins_as_first,
            "wins_as_second": wins_as_second,
            "win_rate_as_first": _safe_rate(wins_as_first, first_count),
            "win_rate_as_second": _safe_rate(wins_as_second, second_count),
        }

    return {
        "total_matches": total_matches,
        "first_player_wins": first_player_wins,
        "first_player_win_rate": _safe_rate(first_player_wins, total_matches),
        "second_player_wins": second_player_wins,
        "upset_rate": _safe_rate(second_player_wins, total_matches),
        "by_player": finalized_by_player,
    }
