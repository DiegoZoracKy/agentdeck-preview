#!/usr/bin/env python3
"""Export results.json and results.csv from match recordings."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple, Union

try:
    from agentdeck.research.provider_utils import provider_from_module as _provider_from_module
except ImportError:
    def _provider_from_module(module: str) -> str:
        module_lower = (module or "").lower()
        if "openai" in module_lower:
            return "openai"
        if "anthropic" in module_lower:
            return "anthropic"
        if "google" in module_lower:
            return "google"
        if "mock" in module_lower:
            return "mock"
        return "unknown"

try:
    from agentdeck.research.recording_metrics import (
        compute_format_strictness,
        compute_inferential_statistics,
        compute_position_effect,
    )
except ImportError:
    compute_format_strictness = None
    compute_inferential_statistics = None
    compute_position_effect = None


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _load_match(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    match_meta = metadata.get("match", {})

    players = data.get("players") or match_meta.get("players") or []
    winner = data.get("winner")
    outcome = match_meta.get("outcome")
    if not outcome:
        outcome = "draw" if winner is None else "win"

    match_entry = {
        "match_id": data.get("match_id"),
        "players": players,
        "winner": winner,
        "turns": match_meta.get("turns"),
        "outcome": outcome,
        "seed": data.get("seed") or match_meta.get("seed"),
        "duration": match_meta.get("duration"),
        "cost": match_meta.get("cost"),
        "player_costs": match_meta.get("player_costs", {}),
        "player_order_source": match_meta.get("player_order_source"),
        "first_player": match_meta.get("first_player", {}),
    }

    return match_entry, metadata, data


def _collect_players(metadata_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    player_meta: Dict[str, Dict[str, Any]] = {}
    player_order: List[str] = []

    for metadata in metadata_list:
        configs = metadata.get("player_configs") or {}
        for name, cfg in configs.items():
            entry = player_meta.setdefault(name, {"name": name})
            entry.setdefault("provider", _provider_from_module(cfg.get("module", "")))
            if cfg.get("model"):
                entry.setdefault("model", cfg.get("model"))
            if cfg.get("type"):
                entry.setdefault("type", cfg.get("type"))

        summaries = metadata.get("player_summaries") or []
        for summary in summaries:
            name = summary.get("name")
            if not name:
                continue
            entry = player_meta.setdefault(name, {"name": name})
            for key in ("model", "controller", "renderer", "temperature", "max_tokens"):
                if summary.get(key) is not None:
                    entry.setdefault(key, summary.get(key))

        match_meta = metadata.get("match", {})
        players = match_meta.get("players") or []
        if players and not player_order:
            player_order = players

    if player_order:
        ordered = [player_meta[name] for name in player_order if name in player_meta]
        for name in player_meta:
            if name not in player_order:
                ordered.append(player_meta[name])
        return ordered

    return [player_meta[name] for name in sorted(player_meta.keys())]


def _fallback_statistics(
    players: List[Dict[str, Any]], matches: List[Dict[str, Any]]
) -> Dict[str, Any]:
    player_names = [player.get("name") for player in players if player.get("name")]
    wins = {name: 0 for name in player_names}
    decisive = 0
    for match in matches:
        winner = match.get("winner")
        if winner in wins:
            wins[winner] += 1
            decisive += 1

    per_player = {}
    for name in player_names:
        win_rate = float(wins[name]) / float(decisive) if decisive else 0.0
        per_player[name] = {
            "wins": wins[name],
            "win_rate": win_rate,
            "ci": [max(0.0, win_rate - 0.1), min(1.0, win_rate + 0.1)],
            "p_value": 1.0,
            "effect_size": 0.0,
            "effect_label": "negligible",
            "is_significant": False,
        }

    return {
        "method": "fallback",
        "confidence_level": 0.95,
        "alpha": 0.05,
        "null_win_rate": 0.5,
        "n_total": len(matches),
        "n_decisive": decisive,
        "players": per_player,
        "pairwise_comparisons": {},
        "quality": {
            "insufficient_sample": decisive < 10,
            "n_decisive": decisive,
            "min_recommended": 10,
            "is_actionable": decisive >= 10,
            "quality_note": "Statistical backend unavailable; fallback values applied",
        },
    }


def _fallback_format_strictness() -> Dict[str, Any]:
    return {
        "overall": {
            "turn_attempts": 0,
            "parse_failures": 0,
            "parse_failure_rate": 0.0,
            "contract_evaluable_attempts": 0,
            "strict_contract_passes": 0,
            "strict_contract_rate": 0.0,
            "recoverable_non_strict": 0,
            "recoverable_non_strict_rate": 0.0,
            "action_line_rate": 0.0,
            "reasoning_line_rate": 0.0,
        },
        "by_player": {},
    }


def _fallback_position_effect(
    players: List[Dict[str, Any]], matches: List[Dict[str, Any]]
) -> Dict[str, Any]:
    player_names = [player.get("name") for player in players if player.get("name")]
    return {
        "total_matches": len(matches),
        "first_player_wins": 0,
        "first_player_win_rate": 0.0,
        "second_player_wins": 0,
        "upset_rate": 0.0,
        "by_player": {
            str(name): {
                "first_count": 0,
                "second_count": 0,
                "wins_as_first": 0,
                "wins_as_second": 0,
                "win_rate_as_first": 0.0,
                "win_rate_as_second": 0.0,
            }
            for name in player_names
        },
    }


def export_results(
    recordings_dir: Union[Path, Sequence[Path]],
    output_dir: Path,
    experiment_id: str,
    *,
    include_generated_at: bool = True,
) -> None:
    if isinstance(recordings_dir, Path):
        recordings_dirs: List[Path] = [recordings_dir]
    else:
        recordings_dirs = [Path(path) for path in recordings_dir]

    if not recordings_dirs:
        raise ValueError("At least one recordings directory is required.")

    normalized_dirs: List[Path] = []
    seen_dirs = set()
    for directory in recordings_dirs:
        resolved = directory.resolve()
        key = str(resolved)
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        normalized_dirs.append(resolved)

    match_files: List[Path] = []
    for directory in normalized_dirs:
        files = sorted(directory.glob("match_*.json"))
        if not files:
            raise FileNotFoundError(f"No match_*.json files found in {directory}")
        match_files.extend(files)

    matches: List[Dict[str, Any]] = []
    match_payloads: List[Dict[str, Any]] = []
    metadata_list: List[Dict[str, Any]] = []
    seen_match_ids: Dict[str, Path] = {}

    for match_path in match_files:
        match_entry, metadata, payload = _load_match(match_path)
        match_id = str(match_entry.get("match_id") or "")
        if not match_id:
            raise ValueError(f"Missing match_id in {match_path}")
        if match_id in seen_match_ids:
            raise ValueError(
                f"Duplicate match_id '{match_id}' found in {match_path} "
                f"and {seen_match_ids[match_id]}"
            )
        seen_match_ids[match_id] = match_path
        matches.append(match_entry)
        match_payloads.append(payload)
        metadata_list.append(metadata)

    players = _collect_players(metadata_list)

    wins = {player["name"]: 0 for player in players}
    draws = 0
    turns = []
    durations = []
    costs = []

    for match in matches:
        winner = match.get("winner")
        if winner is None:
            draws += 1
        elif winner in wins:
            wins[winner] += 1

        if match.get("turns") is not None:
            turns.append(float(match["turns"]))
        if match.get("duration") is not None:
            durations.append(float(match["duration"]))
        if match.get("cost") is not None:
            costs.append(float(match["cost"]))

    decisive = sum(wins.values())
    win_rates = {
        player: (wins[player] / decisive if decisive else 0.0) for player in wins
    }

    summary = {
        "total_matches": len(matches),
        "decisive_matches": decisive,
        "draws": draws,
        "win_rates": win_rates,
        "total_cost": sum(costs) if costs else 0.0,
        "avg_turns": _safe_mean(turns),
        "avg_duration": _safe_mean(durations),
        "avg_cost": _safe_mean(costs),
    }

    if compute_inferential_statistics is not None:
        statistics = compute_inferential_statistics(players=players, matches=matches)
    else:
        statistics = _fallback_statistics(players, matches)

    if compute_format_strictness is not None:
        format_strictness = compute_format_strictness(match_payloads)
    else:
        format_strictness = _fallback_format_strictness()

    if compute_position_effect is not None:
        position_effect = compute_position_effect(players=players, matches=matches)
    else:
        position_effect = _fallback_position_effect(players, matches)

    source: Dict[str, Any] = {"recordings_dir": str(normalized_dirs[0])}
    if len(normalized_dirs) > 1:
        source["recordings_dirs"] = [str(path) for path in normalized_dirs]

    results: Dict[str, Any] = {
        "schema_version": 2,
        "experiment_id": experiment_id,
        "source": source,
        "summary": summary,
        "statistics": statistics,
        "format_strictness": format_strictness,
        "position_effect": position_effect,
        "players": players,
        "matches": matches,
    }
    if include_generated_at:
        results["generated_at"] = _iso_timestamp()

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "results.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    csv_path = output_dir / "results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "match_id",
                "winner",
                "turns",
                "outcome",
                "seed",
                "duration",
                "cost",
                "player_order_source",
                "first_player",
                "players",
                "player_costs",
            ]
        )
        for match in matches:
            writer.writerow(
                [
                    match.get("match_id"),
                    match.get("winner"),
                    match.get("turns"),
                    match.get("outcome"),
                    match.get("seed"),
                    match.get("duration"),
                    match.get("cost"),
                    match.get("player_order_source"),
                    (match.get("first_player") or {}).get("name"),
                    ",".join(match.get("players") or []),
                    json.dumps(match.get("player_costs") or {}),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export results from match recordings.")
    parser.add_argument(
        "--recordings-dir",
        required=True,
        action="append",
        type=Path,
        help="Recordings directory containing match_*.json. Repeat to aggregate checkpoints.",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument(
        "--no-generated-at",
        action="store_true",
        help="Omit generated_at timestamp for deterministic exports.",
    )
    args = parser.parse_args()

    experiment_id = args.experiment_id or args.output_dir.name
    recordings_arg: Union[Path, Sequence[Path]]
    if len(args.recordings_dir) == 1:
        recordings_arg = args.recordings_dir[0]
    else:
        recordings_arg = args.recordings_dir
    export_results(
        recordings_arg,
        args.output_dir,
        experiment_id,
        include_generated_at=not args.no_generated_at,
    )


if __name__ == "__main__":
    main()
