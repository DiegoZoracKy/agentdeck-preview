#!/usr/bin/env python3
"""Export cell-level results for the FixedDamage OpenAI Parity 2 package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_export import export_results


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
MATRIX_PATH = EXPERIMENT_DIR / "matrix.yaml"
MANIFEST_PATH = EXPERIMENT_DIR / "manifest.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _iter_selected_cells(matrix: Dict[str, Any], *, phase: str | None, cell_ids: set[str] | None):
    phase_to_cells: Dict[str, set[str]] = {}
    for phase_entry in matrix.get("execution_plan", {}).get("phases", []):
        phase_to_cells[phase_entry["phase_id"]] = set(phase_entry.get("cell_ids", []))

    for cell in matrix.get("cells", []):
        if phase and cell["id"] not in phase_to_cells.get(phase, set()):
            continue
        if cell_ids and cell["id"] not in cell_ids:
            continue
        yield cell


def _canonical_recordings_dirs_from_artifact(cell_id: str) -> List[Path]:
    artifact_results = EXPERIMENT_DIR / "artifacts" / cell_id / "results.json"
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


def _session_recordings_dirs_for_cell(cell_id: str) -> List[Path]:
    cell_run_dir = EXPERIMENT_DIR / "agentdeck_runs" / cell_id
    usable_dirs: List[Path] = []
    for path in sorted(cell_run_dir.glob("session_*/records")):
        if not path.is_dir():
            continue
        if not any(path.glob("match_*.json")):
            continue
        usable_dirs.append(path)
    return usable_dirs


def _recordings_dirs_for_cell(cell_id: str) -> List[Path]:
    merged: List[Path] = []
    seen = set()
    for path in _canonical_recordings_dirs_from_artifact(cell_id) + _session_recordings_dirs_for_cell(
        cell_id
    ):
        resolved = path.resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        merged.append(resolved)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", help="Export all cells in one phase (e.g. P0, P1)")
    parser.add_argument("--cell", action="append", dest="cells", help="Export one or more specific cell IDs")
    parser.add_argument("--list-cells", action="store_true", help="List available cells and exit")
    args = parser.parse_args()

    matrix = _load_yaml(MATRIX_PATH)
    manifest = _load_yaml(MANIFEST_PATH)
    behavioral_config = dict((manifest.get("game") or {}).get("config") or {})

    if args.list_cells:
        for cell in matrix.get("cells", []):
            print(f"{cell['id']} [{cell['phase']}]")
        return

    selected = list(
        _iter_selected_cells(
            matrix,
            phase=args.phase,
            cell_ids=set(args.cells or []) or None,
        )
    )
    if not selected:
        raise SystemExit("No cells selected. Use --list-cells, --phase, or --cell.")

    for cell in selected:
        cell_id = cell["id"]
        recordings_dirs = _recordings_dirs_for_cell(cell_id)
        if not recordings_dirs:
            print(f"Skipping {cell_id}: no session recordings found.")
            continue

        output_dir = EXPERIMENT_DIR / "artifacts" / cell_id
        output_dir.mkdir(parents=True, exist_ok=True)

        export_results(
            recordings_dirs,
            output_dir,
            experiment_id=f"{matrix['experiment_id']}::{cell_id}",
            include_generated_at=False,
            behavioral_profile_id="auto",
            behavioral_config=behavioral_config,
        )
        print(f"Exported {cell_id} -> {output_dir}")


if __name__ == "__main__":
    main()
