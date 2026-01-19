#!/usr/bin/env python3
"""Export results.json and results.csv from match recordings."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _load_match(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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

    return match_entry, metadata


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


def export_results(recordings_dir: Path, output_dir: Path, experiment_id: str) -> None:
    match_files = sorted(recordings_dir.glob("match_*.json"))
    if not match_files:
        raise FileNotFoundError(f"No match_*.json files found in {recordings_dir}")

    matches: List[Dict[str, Any]] = []
    metadata_list: List[Dict[str, Any]] = []

    for match_path in match_files:
        match_entry, metadata = _load_match(match_path)
        matches.append(match_entry)
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

    results = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "generated_at": _iso_timestamp(),
        "source": {"recordings_dir": str(recordings_dir)},
        "summary": summary,
        "players": players,
        "matches": matches,
    }

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
    parser.add_argument("--recordings-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--experiment-id", default=None)
    args = parser.parse_args()

    experiment_id = args.experiment_id or args.output_dir.name
    export_results(args.recordings_dir, args.output_dir, experiment_id)


if __name__ == "__main__":
    main()
