#!/usr/bin/env python3
"""Generate research/INDEX.md from experiment manifests."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _format_status(status: str) -> str:
    if status in {"planned", "running"}:
        return f"*{status}*"
    return status


def _format_players(players: List[Dict[str, Any]]) -> str:
    if not players:
        return "TBD"
    parts = []
    for player in players:
        provider = player.get("provider", "unknown")
        model = player.get("model", "unknown")
        parts.append(f"{provider}:{model}")
    return ", ".join(parts)


def _format_matches(run: Dict[str, Any]) -> str:
    planned = run.get("matches_planned")
    completed = run.get("matches_completed")
    if planned is None and completed is None:
        return "TBD"
    if completed is None:
        return str(planned)
    if planned is None:
        return str(completed)
    return f"{completed}/{planned}"


def _format_results(results_path: Path) -> str:
    if not results_path.exists():
        return "TBD"
    data = json.loads(results_path.read_text(encoding="utf-8"))
    players = data.get("players") or []
    if len(players) > 2:
        return "See README"
    summary = data.get("summary", {})
    win_rates = summary.get("win_rates", {})
    if not win_rates:
        return "TBD"
    top_player = max(win_rates.items(), key=lambda item: item[1])
    return f"{top_player[0]} {top_player[1]:.1%}"


def generate_index(research_dir: Path) -> str:
    manifest_paths = sorted(
        path
        for path in research_dir.glob("*/manifest.yaml")
        if "_templates" not in str(path)
    )

    rows = []
    for manifest_path in manifest_paths:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        experiment_id = manifest.get("experiment_id", manifest_path.parent.name)
        title = manifest.get("title", experiment_id)
        status = _format_status(manifest.get("status", "unknown"))
        game = (manifest.get("game") or {}).get("name", "TBD")
        players = _format_players(manifest.get("players") or [])
        matches = _format_matches(manifest.get("run") or {})
        results = _format_results(manifest_path.parent / "results.json")
        link = f"[{title}]({experiment_id}/README.md)"

        rows.append([link, status, game, players, matches, results])

    lines = [
        "# Research Index",
        "",
        f"Last updated: {_iso_timestamp()}",
        "",
        "| Experiment | Status | Game | Players | Matches | Results |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    if not rows:
        lines.append("| (none) | - | - | - | - | - |")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate research/INDEX.md from manifests.")
    parser.add_argument("--research-dir", default=Path("research"), type=Path)
    parser.add_argument("--output", default=Path("research/INDEX.md"), type=Path)
    args = parser.parse_args()

    content = generate_index(args.research_dir)
    args.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
