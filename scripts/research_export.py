#!/usr/bin/env python3
"""Export results.json and results.csv from match recordings."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

import yaml

try:
    from agentdeck.research.behavioral import compute_behavioral_profile
except ImportError:
    compute_behavioral_profile = None

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

from agentdeck.research.artifact_validation import (
    format_artifact_validation_errors,
    validate_artifact_invariants,
)


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _behavioral_config_from_manifest(experiment_dir: Path) -> Dict[str, Any]:
    manifest_path = experiment_dir / "manifest.yaml"
    if not manifest_path.exists():
        return {}
    manifest = _load_yaml(manifest_path)
    return dict((manifest.get("game") or {}).get("config") or {})


def _resolve_matrix_path(experiment_dir: Path, matrix_path: Path | None) -> Path:
    resolved = matrix_path or (experiment_dir / "matrix.yaml")
    if not resolved.exists():
        raise FileNotFoundError(f"Matrix file not found: {resolved}")
    return resolved


def _iter_selected_cells(
    matrix: Dict[str, Any], *, phase: str | None, cell_ids: set[str] | None
) -> Iterable[Dict[str, Any]]:
    phase_to_cells: Dict[str, set[str]] = {}
    for phase_entry in matrix.get("execution_plan", {}).get("phases", []):
        phase_to_cells[phase_entry["phase_id"]] = set(phase_entry.get("cell_ids", []))

    for cell in matrix.get("cells", []):
        if phase and cell["id"] not in phase_to_cells.get(phase, set()):
            continue
        if cell_ids and cell["id"] not in cell_ids:
            continue
        yield cell


def _canonical_recordings_dirs_from_artifact(experiment_dir: Path, cell_id: str) -> List[Path]:
    artifact_results = experiment_dir / "artifacts" / cell_id / "results.json"
    if not artifact_results.exists():
        return []
    payload = json.loads(artifact_results.read_text(encoding="utf-8"))
    source = payload.get("source") or {}
    recordings_dirs = source.get("recordings_dirs") or []
    if recordings_dirs:
        return [Path(path) for path in recordings_dirs]
    recordings_dir = source.get("recordings_dir")
    if recordings_dir:
        return [Path(recordings_dir)]
    return []


def _session_recordings_dirs_for_cell(experiment_dir: Path, cell_id: str) -> List[Path]:
    cell_run_dir = experiment_dir / "agentdeck_runs" / cell_id
    usable_dirs: List[Path] = []
    if not cell_run_dir.exists():
        return usable_dirs
    for path in sorted(cell_run_dir.glob("session_*/records")):
        if not path.is_dir():
            continue
        if not any(path.glob("match_*.json")):
            continue
        usable_dirs.append(path)
    return usable_dirs


def _recordings_dirs_for_cell(experiment_dir: Path, cell_id: str) -> List[Path]:
    merged: List[Path] = []
    seen = set()
    for path in _canonical_recordings_dirs_from_artifact(
        experiment_dir, cell_id
    ) + _session_recordings_dirs_for_cell(experiment_dir, cell_id):
        resolved = path.resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        merged.append(resolved)
    return merged


def _export_matrix_cells(
    experiment_dir: Path,
    *,
    matrix_path: Path | None,
    phase: str | None,
    cell_ids: set[str] | None,
    include_generated_at: bool,
) -> int:
    matrix = _load_yaml(_resolve_matrix_path(experiment_dir, matrix_path))
    selected = list(_iter_selected_cells(matrix, phase=phase, cell_ids=cell_ids))
    if not selected:
        raise SystemExit("No cells selected. Use --list-cells, --phase, or --cell.")

    behavioral_config = _behavioral_config_from_manifest(experiment_dir)
    exported = 0

    for cell in selected:
        cell_id = cell["id"]
        recordings_dirs = _recordings_dirs_for_cell(experiment_dir, cell_id)
        if not recordings_dirs:
            print(f"Skipping {cell_id}: no session recordings found.")
            continue

        output_dir = experiment_dir / "artifacts" / cell_id
        export_results(
            recordings_dirs,
            output_dir,
            experiment_id=f"{matrix['experiment_id']}::{cell_id}",
            include_generated_at=include_generated_at,
            behavioral_profile_id="auto",
            behavioral_config=behavioral_config,
        )
        print(f"Exported {cell_id} -> {output_dir}")
        exported += 1

    return exported


def _export_matrix_package(
    experiment_dir: Path,
    *,
    matrix_path: Path | None,
    include_generated_at: bool,
) -> None:
    matrix = _load_yaml(_resolve_matrix_path(experiment_dir, matrix_path))
    manifest_path = experiment_dir / "manifest.yaml"
    manifest = _load_yaml(manifest_path) if manifest_path.exists() else {}
    behavioral_config = dict((manifest.get("game") or {}).get("config") or {})

    recordings_dirs: List[Path] = []
    for cell in matrix.get("cells", []):
        recordings_dirs.extend(_recordings_dirs_for_cell(experiment_dir, cell["id"]))

    if not recordings_dirs:
        raise SystemExit(
            "No recordings discovered for package export. Export cells first or ensure "
            "agentdeck_runs/<cell_id>/session_*/records exists."
        )

    experiment_id = manifest.get("experiment_id") or matrix.get("experiment_id") or experiment_dir.name
    export_results(
        recordings_dirs,
        experiment_dir,
        experiment_id=experiment_id,
        include_generated_at=include_generated_at,
        behavioral_profile_id="auto",
        behavioral_config=behavioral_config,
    )
    print(f"Exported package results -> {experiment_dir}")


def _list_matrix_cells(experiment_dir: Path, *, matrix_path: Path | None) -> None:
    matrix = _load_yaml(_resolve_matrix_path(experiment_dir, matrix_path))
    for cell in matrix.get("cells", []):
        print(f"{cell['id']} [{cell.get('phase', '?')}]")


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
        "duration": (
            match_meta.get("duration")
            if match_meta.get("duration") is not None
            else match_meta.get("duration_seconds", data.get("duration_seconds"))
        ),
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
            # Placeholder band only. When the statistical backend is unavailable we keep
            # schema compatibility, but this is not a real inferential confidence interval.
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
            "quality_note": (
                "Statistical backend unavailable; placeholder +/-10pp CI bands applied "
                "for schema compatibility"
            ),
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
    behavioral_profile_id: str | None = "auto",
    behavioral_config: Dict[str, Any] | None = None,
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

    artifact_validation = validate_artifact_invariants(match_payloads)
    if not artifact_validation["all_passed"]:
        formatted_failures = format_artifact_validation_errors(artifact_validation)
        detail = f"\n{formatted_failures}" if formatted_failures else ""
        raise ValueError(f"Artifact invariant validation failed.{detail}")

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

    behavioral_profile = None
    if compute_behavioral_profile is not None and behavioral_profile_id != "none":
        behavioral_profile = compute_behavioral_profile(
            players=players,
            match_payloads=match_payloads,
            profile_id=behavioral_profile_id,
            config=behavioral_config,
        )

    source: Dict[str, Any] = {"recordings_dir": str(normalized_dirs[0])}
    if len(normalized_dirs) > 1:
        source["recordings_dirs"] = [str(path) for path in normalized_dirs]

    results: Dict[str, Any] = {
        "schema_version": 3,
        "experiment_id": experiment_id,
        "source": source,
        "summary": summary,
        "statistics": statistics,
        "format_strictness": format_strictness,
        "position_effect": position_effect,
        "artifact_validation": artifact_validation,
        "players": players,
        "matches": matches,
    }
    if behavioral_profile is not None:
        results["behavioral_profile"] = behavioral_profile
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
        action="append",
        type=Path,
        help="Recordings directory containing match_*.json. Repeat to aggregate checkpoints.",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument(
        "--experiment-dir",
        type=Path,
        help="Experiment package root for matrix-based export workflows.",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        help="Override matrix path for matrix-based workflows (defaults to <experiment-dir>/matrix.yaml).",
    )
    parser.add_argument("--phase", help="Export all cells in one phase (matrix mode only).")
    parser.add_argument(
        "--cell",
        action="append",
        dest="cells",
        help="Export one or more specific cell IDs (matrix mode only).",
    )
    parser.add_argument(
        "--list-cells",
        action="store_true",
        help="List available matrix cells and exit.",
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="Export top-level package results from discovered matrix cell sources.",
    )
    parser.add_argument(
        "--no-generated-at",
        action="store_true",
        help="Omit generated_at timestamp for deterministic exports.",
    )
    args = parser.parse_args()

    matrix_mode = any(
        [
            args.experiment_dir is not None,
            args.matrix is not None,
            args.phase is not None,
            bool(args.cells),
            args.list_cells,
            args.package,
        ]
    )

    if args.recordings_dir and matrix_mode:
        parser.error(
            "Direct mode (--recordings-dir/--output-dir) cannot be combined with matrix mode "
            "(--experiment-dir/--matrix/--cell/--phase/--package)."
        )

    if args.recordings_dir:
        if args.output_dir is None:
            parser.error("--output-dir is required in direct export mode.")
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
        return

    if not matrix_mode:
        parser.error(
            "Specify either direct export (--recordings-dir --output-dir) or matrix mode "
            "(--experiment-dir/--matrix with --cell/--phase/--package/--list-cells)."
        )

    if args.output_dir is not None or args.experiment_id is not None:
        parser.error("--output-dir and --experiment-id are only valid in direct export mode.")

    if args.package and (args.phase is not None or args.cells):
        parser.error("--package cannot be combined with --phase or --cell.")

    experiment_dir = args.experiment_dir or (args.matrix.parent if args.matrix else None)
    if experiment_dir is None:
        parser.error("--experiment-dir is required for matrix mode unless --matrix is supplied.")

    if args.list_cells:
        _list_matrix_cells(experiment_dir, matrix_path=args.matrix)
        return

    if args.package:
        _export_matrix_package(
            experiment_dir,
            matrix_path=args.matrix,
            include_generated_at=not args.no_generated_at,
        )
        return

    _export_matrix_cells(
        experiment_dir,
        matrix_path=args.matrix,
        phase=args.phase,
        cell_ids=set(args.cells or []) or None,
        include_generated_at=not args.no_generated_at,
    )


if __name__ == "__main__":
    main()
