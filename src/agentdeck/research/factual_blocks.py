"""Helpers for hydrating README/analysis factual blocks from results.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..core.artifact_safety import atomic_write_text

AUTO_FACTS_BEGIN = "<!-- AUTO_FACTS:BEGIN -->"
AUTO_FACTS_END = "<!-- AUTO_FACTS:END -->"


def _format_pct(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{numeric * 100:.1f}%"


def _format_usd(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"${numeric:.6f}"


def _replace_auto_facts_block(path: Path, lines: List[str]) -> None:
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    begin_idx = content.find(AUTO_FACTS_BEGIN)
    end_idx = content.find(AUTO_FACTS_END)

    if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
        return

    insert_start = begin_idx + len(AUTO_FACTS_BEGIN)
    replacement = "\n" + "\n".join(lines).rstrip() + "\n"
    updated = content[:insert_start] + replacement + content[end_idx:]
    atomic_write_text(path, updated)


def _player_label(player: Dict[str, Any]) -> str:
    player_id = player.get("id", "?")
    provider = player.get("provider", "unknown")
    model = player.get("model", "unknown")
    return f"{player_id}={provider}:{model}"


def _winner_topline(results: Dict[str, Any]) -> str:
    source = results.get("source") or {}
    cells_included = source.get("cells_included")
    if isinstance(cells_included, list) and len(cells_included) > 1:
        return "See per-cell results (matrix aggregate)"

    summary = results.get("summary") or {}
    win_rates = summary.get("win_rates") or {}
    if not isinstance(win_rates, dict) or not win_rates:
        return "No decisive winner (empty win_rates)"

    winner, rate = max(win_rates.items(), key=lambda item: float(item[1]))
    return f"{winner} ({_format_pct(rate)})"


def _first_player(results: Dict[str, Any]) -> str:
    matches = results.get("matches") or []
    if not matches:
        return "N/A"

    first = (matches[0].get("first_player") or {}).get("name")
    return first or "N/A"


def _load_results_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _source_scope_lines(source: Dict[str, Any]) -> List[str]:
    scope = source.get("aggregation_scope")
    if not scope:
        return []

    lines = [f"- Aggregation Scope: {scope}"]
    phases = source.get("phases_included")
    cells = source.get("cells_included")
    if isinstance(phases, list) and phases:
        lines.append(f"- Phases Included: {', '.join(str(item) for item in phases)}")
    if isinstance(cells, list):
        lines.append(f"- Cells Included: {len(cells)}")
    elif source.get("cell_id"):
        lines.append(f"- Cell: {source.get('cell_id')}")
    return lines


def write_factual_markdown_blocks(dest_dir: Path, manifest: Dict[str, Any]) -> None:
    """Refresh AUTO_FACTS blocks from results.json while preserving narrative text."""
    results = _load_results_json(dest_dir / "results.json")
    source = results.get("source") or {}
    summary = results.get("summary") or {}
    statistics = results.get("statistics") or {}
    strictness = results.get("format_strictness") or {}
    position = results.get("position_effect") or {}
    strictness_overall = strictness.get("overall") or {}
    quality = statistics.get("quality") or {}
    run = manifest.get("run") or {}
    players = manifest.get("players") or []

    player_line = ", ".join(_player_label(player) for player in players) or "N/A"
    matches_planned = run.get("matches_planned", "N/A")
    matches_completed = summary.get("total_matches", run.get("matches_completed", "N/A"))

    readme_lines = [
        f"- Status: {manifest.get('status', 'N/A')}",
        f"- Matches: {matches_completed}/{matches_planned}",
        f"- Game: {((manifest.get('game') or {}).get('name') or 'N/A')}",
        f"- Players: {player_line}",
        f"- Seed Base: {run.get('seed_base', 'N/A')}",
        f"- Topline Winner: {_winner_topline(results)}",
        f"- Avg Turns: {summary.get('avg_turns', 'N/A')}",
        f"- Avg Duration (s): {summary.get('avg_duration', 'N/A')}",
        f"- Total Cost: {_format_usd(summary.get('total_cost'))}",
    ]
    readme_lines.extend(_source_scope_lines(source))
    _replace_auto_facts_block(dest_dir / "README.md", readme_lines)

    analysis_lines = [
        f"- Sample size (`n`): {summary.get('total_matches', 'N/A')}",
        f"- Decisive matches: {summary.get('decisive_matches', 'N/A')}",
        f"- Draws: {summary.get('draws', 'N/A')}",
        f"- Win rates: {summary.get('win_rates', {})}",
        f"- Statistical method: {statistics.get('method', 'N/A')}",
        f"- Confidence level: {statistics.get('confidence_level', 'N/A')}",
        f"- Alpha: {statistics.get('alpha', 'N/A')}",
        f"- Topline winner: {_winner_topline(results)}",
        f"- First player in first recorded match: {_first_player(results)}",
        f"- Average turns: {summary.get('avg_turns', 'N/A')}",
        f"- Average duration (s): {summary.get('avg_duration', 'N/A')}",
        f"- Total cost: {_format_usd(summary.get('total_cost'))}",
        f"- First-player win rate: {_format_pct(position.get('first_player_win_rate'))}",
        f"- Upset rate (second-player wins): {_format_pct(position.get('upset_rate'))}",
        f"- Parse failure rate: {_format_pct(strictness_overall.get('parse_failure_rate'))}",
        f"- Strict contract rate: {_format_pct(strictness_overall.get('strict_contract_rate'))}",
        f"- Quality actionable: {quality.get('is_actionable', 'N/A')}",
        f"- Quality note: {quality.get('quality_note', 'N/A')}",
    ]
    analysis_lines.extend(_source_scope_lines(source))
    _replace_auto_facts_block(dest_dir / "analysis.md", analysis_lines)
