"""Deterministic Markdown reports generated from research results artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_usd(value: Any) -> str:
    try:
        return f"${float(value):.6f}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_num(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.3f}"


def _fmt_ratio(wins: Any, total: Any) -> str:
    try:
        wins_int = int(wins)
        total_int = int(total)
    except (TypeError, ValueError):
        return "N/A"
    if total_int <= 0:
        return f"{wins_int}/{total_int} (N/A)"
    return f"{wins_int}/{total_int} ({_fmt_pct(wins_int / total_int)})"


def _escape_cell(value: Any) -> str:
    text = str(value if value is not None else "N/A")
    return text.replace("|", "\\|").replace("\n", "<br>")


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> List[str]:
    if not rows:
        return ["_No rows._"]
    lines = [
        "| " + " | ".join(_escape_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        lines.append(
            "| " + " | ".join(_escape_cell(value) for value in padded[: len(headers)]) + " |"
        )
    return lines


def _source_scope(source: Mapping[str, Any]) -> List[str]:
    lines: List[str] = []
    if source.get("aggregation_scope"):
        lines.append(f"- Aggregation scope: `{source.get('aggregation_scope')}`")
    if source.get("phase"):
        lines.append(f"- Phase: `{source.get('phase')}`")
    if source.get("cell_id"):
        lines.append(f"- Cell: `{source.get('cell_id')}`")
    phases = source.get("phases_included")
    if isinstance(phases, list) and phases:
        lines.append("- Phases included: " + ", ".join(f"`{phase}`" for phase in phases))
    cells = source.get("cells_included")
    if isinstance(cells, list) and cells:
        lines.append("- Cells included: " + ", ".join(f"`{cell}`" for cell in cells))
    if source.get("recordings_dir"):
        lines.append(f"- Primary recordings source: `{source.get('recordings_dir')}`")
    recordings_dirs = source.get("recordings_dirs")
    if isinstance(recordings_dirs, list) and len(recordings_dirs) > 1:
        lines.append(f"- Recordings source count: {len(recordings_dirs)}")
    return lines


def _summary_rows(summary: Mapping[str, Any]) -> List[List[Any]]:
    return [
        ["Total matches", summary.get("total_matches", "N/A")],
        ["Decisive matches", summary.get("decisive_matches", "N/A")],
        ["Draws", summary.get("draws", "N/A")],
        ["Average turns", _fmt_num(summary.get("avg_turns"))],
        ["Average duration seconds", _fmt_num(summary.get("avg_duration"))],
        ["Total cost", _fmt_usd(summary.get("total_cost"))],
        ["Average cost per match", _fmt_usd(summary.get("avg_cost"))],
    ]


def _player_rows(statistics: Mapping[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    players = statistics.get("players") or {}
    if not isinstance(players, dict):
        return rows
    for name, stats in sorted(players.items()):
        stats = stats or {}
        ci = stats.get("ci") or []
        ci_text = (
            f"{_fmt_pct(ci[0])}-{_fmt_pct(ci[1])}"
            if isinstance(ci, list) and len(ci) == 2
            else "N/A"
        )
        rows.append(
            [
                name,
                stats.get("wins", "N/A"),
                _fmt_pct(stats.get("win_rate")),
                ci_text,
                _fmt_num(stats.get("p_value")),
                _fmt_num(stats.get("effect_size")),
                stats.get("effect_label", "N/A"),
            ]
        )
    return rows


def _pairwise_rows(statistics: Mapping[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    comparisons = statistics.get("pairwise_comparisons") or {}
    if not isinstance(comparisons, dict):
        return rows
    for key, entry in sorted(comparisons.items()):
        entry = entry or {}
        player_a = entry.get("player_a", "A")
        player_b = entry.get("player_b", "B")
        decisive = entry.get("head_to_head_decisive")
        rows.append(
            [
                key,
                entry.get("comparison_scope", "N/A"),
                f"{player_a}: {_fmt_ratio(entry.get('wins_a'), decisive)}",
                f"{player_b}: {_fmt_ratio(entry.get('wins_b'), decisive)}",
                entry.get("head_to_head_matches", "N/A"),
                _fmt_num(entry.get("p_value")),
                entry.get("effect_label", "N/A"),
            ]
        )
    return rows


def _position_rows(position: Mapping[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    by_player = position.get("by_player") or {}
    if not isinstance(by_player, dict):
        return rows
    for name, stats in sorted(by_player.items()):
        stats = stats or {}
        rows.append(
            [
                name,
                _fmt_ratio(stats.get("wins_as_first"), stats.get("first_count")),
                _fmt_ratio(stats.get("wins_as_second"), stats.get("second_count")),
            ]
        )
    return rows


def _strictness_rows(strictness: Mapping[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    by_player = strictness.get("by_player") or {}
    if not isinstance(by_player, dict):
        return rows
    for name, stats in sorted(by_player.items()):
        stats = stats or {}
        rows.append(
            [
                name,
                stats.get("turn_attempts", "N/A"),
                _fmt_pct(stats.get("parse_failure_rate")),
                _fmt_pct(stats.get("strict_contract_rate")),
                _fmt_pct(stats.get("action_line_rate")),
                _fmt_pct(stats.get("reasoning_line_rate")),
            ]
        )
    return rows


def _player_cost_rows(matches: Sequence[Mapping[str, Any]]) -> List[List[Any]]:
    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for match in matches:
        player_costs = match.get("player_costs") or {}
        if not isinstance(player_costs, dict):
            continue
        for player, cost in player_costs.items():
            try:
                numeric = float(cost)
            except (TypeError, ValueError):
                continue
            player = str(player)
            totals[player] = totals.get(player, 0.0) + numeric
            counts[player] = counts.get(player, 0) + 1

    rows: List[List[Any]] = []
    for player in sorted(totals):
        count = counts.get(player, 0)
        avg = totals[player] / count if count else 0.0
        rows.append([player, count, _fmt_usd(totals[player]), _fmt_usd(avg)])
    return rows


def _scalar_metric_rows(metrics: Mapping[str, Any], *, max_rows: int = 20) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for key, value in sorted(metrics.items()):
        if isinstance(value, (str, int, float, bool)) or value is None:
            rows.append([key, _fmt_num(value)])
        if len(rows) >= max_rows:
            break
    return rows


def _direct_result(results: Mapping[str, Any]) -> str:
    statistics = results.get("statistics") or {}
    comparisons = statistics.get("pairwise_comparisons") or {}
    if isinstance(comparisons, dict) and len(comparisons) == 1:
        entry = _single_pairwise_entry(results) or {}
        decisive = entry.get("head_to_head_decisive")
        return (
            f"{entry.get('player_a', 'A')} {_fmt_ratio(entry.get('wins_a'), decisive)} vs "
            f"{entry.get('player_b', 'B')} {_fmt_ratio(entry.get('wins_b'), decisive)}"
        )

    summary = results.get("summary") or {}
    win_rates = summary.get("win_rates") or {}
    if isinstance(win_rates, dict) and win_rates:
        ordered = sorted(win_rates.items(), key=lambda item: float(item[1]), reverse=True)
        return "; ".join(f"{name} {_fmt_pct(rate)}" for name, rate in ordered)
    return "N/A"


def _single_pairwise_entry(results: Mapping[str, Any]) -> Dict[str, Any] | None:
    statistics = results.get("statistics") or {}
    comparisons = statistics.get("pairwise_comparisons") or {}
    if not isinstance(comparisons, dict) or len(comparisons) != 1:
        return None
    entry = next(iter(comparisons.values()))
    return entry if isinstance(entry, dict) else None


def _direct_p_value(results: Mapping[str, Any]) -> str:
    entry = _single_pairwise_entry(results)
    if not entry:
        return "N/A"
    return _fmt_num(entry.get("p_value"))


def _direct_effect(results: Mapping[str, Any]) -> str:
    entry = _single_pairwise_entry(results)
    if not entry:
        return "N/A"
    return str(entry.get("effect_label", "N/A"))


def _winner(results: Mapping[str, Any]) -> str:
    summary = results.get("summary") or {}
    win_rates = summary.get("win_rates") or {}
    if not isinstance(win_rates, dict) or not win_rates:
        return "N/A"
    name, rate = max(win_rates.items(), key=lambda item: float(item[1]))
    return f"{name} ({_fmt_pct(rate)})"


def _load_cell_artifacts(
    output_dir: Path, source: Mapping[str, Any]
) -> List[tuple[str, Dict[str, Any]]]:
    cells = source.get("cells_included")
    if not isinstance(cells, list):
        return []
    loaded: List[tuple[str, Dict[str, Any]]] = []
    for cell in cells:
        cell_id = str(cell)
        payload = _load_json(output_dir / "artifacts" / cell_id / "results.json")
        if payload:
            loaded.append((cell_id, payload))
    return loaded


def _cell_overview_rows(cells: Iterable[tuple[str, Mapping[str, Any]]]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for cell_id, payload in cells:
        summary = payload.get("summary") or {}
        position = payload.get("position_effect") or {}
        validation = payload.get("artifact_validation") or {}
        rows.append(
            [
                f"[{cell_id}](artifacts/{cell_id}/results.json)",
                summary.get("total_matches", "N/A"),
                _winner(payload),
                _direct_result(payload),
                _direct_p_value(payload),
                _direct_effect(payload),
                _fmt_pct(position.get("first_player_win_rate")),
                _fmt_usd(summary.get("total_cost")),
                validation.get("all_passed", "N/A"),
            ]
        )
    return rows


def _cell_position_rows(cells: Iterable[tuple[str, Mapping[str, Any]]]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for cell_id, payload in cells:
        position = payload.get("position_effect") or {}
        for player, stats in sorted((position.get("by_player") or {}).items()):
            stats = stats or {}
            rows.append(
                [
                    cell_id,
                    player,
                    _fmt_ratio(stats.get("wins_as_first"), stats.get("first_count")),
                    _fmt_ratio(stats.get("wins_as_second"), stats.get("second_count")),
                ]
            )
    return rows


def _warning_lines(
    results: Mapping[str, Any], cells: Sequence[tuple[str, Mapping[str, Any]]]
) -> List[str]:
    warnings: List[str] = []
    source = results.get("source") or {}
    if isinstance(source.get("cells_included"), list) and len(source["cells_included"]) > 1:
        warnings.append(
            "Package aggregate spans multiple cells; use cell-level rows for outcome claims."
        )

    def add_position_warning(label: str, payload: Mapping[str, Any]) -> None:
        position = payload.get("position_effect") or {}
        try:
            first_rate = float(position.get("first_player_win_rate"))
        except (TypeError, ValueError):
            return
        if first_rate >= 0.75 or first_rate <= 0.25:
            warnings.append(
                f"{label} has high first-player skew ({_fmt_pct(first_rate)}); "
                "interpret aggregate win rates with seat splits."
            )

    add_position_warning("Package aggregate", results)
    for cell_id, payload in cells:
        add_position_warning(f"Cell `{cell_id}`", payload)

    def add_significance_warning(label: str, payload: Mapping[str, Any]) -> None:
        entry = _single_pairwise_entry(payload)
        if not entry:
            return
        statistics = payload.get("statistics") or {}
        try:
            p_value = float(entry.get("p_value"))
            alpha = float(statistics.get("alpha", 0.05))
        except (TypeError, ValueError):
            return
        if p_value >= alpha:
            warnings.append(
                f"{label} direct result is not statistically significant "
                f"(p={p_value:.3f}, alpha={alpha:.2f}); avoid strong dominance claims."
            )

    if cells:
        for cell_id, payload in cells:
            add_significance_warning(f"Cell `{cell_id}`", payload)
    else:
        add_significance_warning("Direct comparison", results)

    validation = results.get("artifact_validation") or {}
    if validation.get("all_passed") is False:
        warnings.append("Artifact validation did not pass.")

    return warnings


def render_results_markdown(results: Mapping[str, Any], *, output_dir: Path | None = None) -> str:
    """Render a deterministic human-readable report from a results payload."""
    source = results.get("source") or {}
    summary = results.get("summary") or {}
    statistics = results.get("statistics") or {}
    strictness = results.get("format_strictness") or {}
    position = results.get("position_effect") or {}
    validation = results.get("artifact_validation") or {}
    behavioral = results.get("behavioral_profile") or {}
    matches = results.get("matches") or []
    cell_artifacts = _load_cell_artifacts(output_dir, source) if output_dir else []
    has_cell_artifacts = bool(cell_artifacts)

    lines: List[str] = [
        "# Results Report",
        "",
        "> Generated deterministically from `results.json`. Authored interpretation belongs under `analysis/`.",
        "",
        "## Scope",
        f"- Experiment ID: `{results.get('experiment_id', 'N/A')}`",
        f"- Schema version: `{results.get('schema_version', 'N/A')}`",
    ]
    lines.extend(_source_scope(source) or ["- Scope metadata: N/A"])

    warnings = _warning_lines(results, cell_artifacts)
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    lines.extend(["", "## Summary"])
    lines.extend(_table(["Metric", "Value"], _summary_rows(summary)))

    if has_cell_artifacts:
        lines.extend(["", "## Cell Overview"])
        lines.extend(
            _table(
                [
                    "Cell",
                    "n",
                    "Winner",
                    "Direct Result",
                    "p-value",
                    "Effect",
                    "First-Player WR",
                    "Cost",
                    "Validation",
                ],
                _cell_overview_rows(cell_artifacts),
            )
        )
        lines.extend(["", "## Cell Seat Splits"])
        lines.extend(
            _table(
                ["Cell", "Player", "As First", "As Second"],
                _cell_position_rows(cell_artifacts),
            )
        )

    player_heading = (
        "## Package Aggregate Player Exposure" if has_cell_artifacts else "## Player Results"
    )
    lines.extend(["", player_heading])
    if has_cell_artifacts:
        lines.extend(
            [
                "",
                "_These rows pool all included package matches and are not cell-level toplines._",
                "",
            ]
        )
    lines.extend(
        _table(
            ["Player", "Wins", "Win Rate", "95% CI", "p-value", "Effect Size", "Effect"],
            _player_rows(statistics),
        )
    )

    h2h_heading = (
        "## Package Aggregate Direct Head-to-Head"
        if has_cell_artifacts
        else "## Direct Head-to-Head"
    )
    lines.extend(["", h2h_heading])
    if has_cell_artifacts:
        lines.extend(
            [
                "",
                "_These comparisons pool direct matches across included cells. Use Cell Overview for study claims._",
                "",
            ]
        )
    lines.extend(
        _table(
            [
                "Comparison",
                "Scope",
                "Player A Result",
                "Player B Result",
                "Matches",
                "p-value",
                "Effect",
            ],
            _pairwise_rows(statistics),
        )
    )

    lines.extend(["", "## Position Effects"])
    lines.extend(
        _table(
            ["Metric", "Value"],
            [
                ["First-player wins", position.get("first_player_wins", "N/A")],
                ["First-player win rate", _fmt_pct(position.get("first_player_win_rate"))],
                ["Second-player wins", position.get("second_player_wins", "N/A")],
                ["Second-player win rate", _fmt_pct(position.get("upset_rate"))],
            ],
        )
    )
    lines.extend(["", "### Seat Split By Player"])
    lines.extend(_table(["Player", "As First", "As Second"], _position_rows(position)))

    lines.extend(["", "## Format Strictness"])
    overall = strictness.get("overall") or {}
    lines.extend(
        _table(
            ["Metric", "Value"],
            [
                ["Turn attempts", overall.get("turn_attempts", "N/A")],
                ["Parse failure rate", _fmt_pct(overall.get("parse_failure_rate"))],
                ["Strict contract rate", _fmt_pct(overall.get("strict_contract_rate"))],
                ["Action-line rate", _fmt_pct(overall.get("action_line_rate"))],
                ["Reasoning-line rate", _fmt_pct(overall.get("reasoning_line_rate"))],
            ],
        )
    )
    lines.extend(["", "### Strictness By Player"])
    lines.extend(
        _table(
            [
                "Player",
                "Attempts",
                "Parse Failure Rate",
                "Strict Contract Rate",
                "Action-Line Rate",
                "Reasoning-Line Rate",
            ],
            _strictness_rows(strictness),
        )
    )

    cost_rows = _player_cost_rows(matches if isinstance(matches, list) else [])
    if cost_rows:
        lines.extend(["", "## Player Costs"])
        lines.extend(_table(["Player", "Player-Matches", "Total Cost", "Avg Cost"], cost_rows))

    if behavioral:
        lines.extend(["", "## Behavioral Profile"])
        lines.extend(
            _table(
                ["Field", "Value"],
                [
                    ["Profile", behavioral.get("profile_id", "N/A")],
                    ["Game", behavioral.get("game_id", "N/A")],
                    ["Version", behavioral.get("profile_version", "N/A")],
                ],
            )
        )
        aggregate_metrics = behavioral.get("aggregate_metrics") or {}
        if isinstance(aggregate_metrics, dict) and aggregate_metrics:
            lines.extend(["", "### Aggregate Behavioral Metrics"])
            lines.extend(_table(["Metric", "Value"], _scalar_metric_rows(aggregate_metrics)))

    lines.extend(["", "## Artifact Validation"])
    lines.extend(
        _table(
            ["Metric", "Value"],
            [
                ["Matches checked", validation.get("matches_checked", "N/A")],
                ["All passed", validation.get("all_passed", "N/A")],
                ["Failure count", len(validation.get("failures") or [])],
            ],
        )
    )

    return "\n".join(lines).rstrip() + "\n"


def write_results_markdown_report(output_dir: Path) -> None:
    """Write `results.md` next to `results.json`."""
    results = _load_json(output_dir / "results.json")
    if not results:
        return
    (output_dir / "results.md").write_text(
        render_results_markdown(results, output_dir=output_dir),
        encoding="utf-8",
    )
