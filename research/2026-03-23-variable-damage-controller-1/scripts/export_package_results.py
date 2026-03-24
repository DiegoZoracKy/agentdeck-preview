#!/usr/bin/env python3
"""Export top-level results for the VariableDamage Controller 1 package."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_export import export_results


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = EXPERIMENT_DIR / "manifest.yaml"
MATRIX_PATH = EXPERIMENT_DIR / "matrix.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _canonical_recordings_dirs(cell_id: str) -> List[Path]:
    artifact_results = EXPERIMENT_DIR / "artifacts" / cell_id / "results.json"
    if not artifact_results.exists():
        raise FileNotFoundError(
            f"Missing canonical cell artifact for {cell_id}: {artifact_results}"
        )
    payload = json.loads(artifact_results.read_text(encoding="utf-8"))
    source = payload.get("source") or {}
    recordings_dirs = source.get("recordings_dirs") or []
    if recordings_dirs:
        return [Path(path) for path in recordings_dirs]
    recordings_dir = source.get("recordings_dir")
    if not recordings_dir:
        raise ValueError(f"Artifact for {cell_id} missing source.recordings_dir(s)")
    return [Path(recordings_dir)]


def main() -> None:
    manifest = _load_yaml(MANIFEST_PATH)
    matrix = _load_yaml(MATRIX_PATH)
    behavioral_config = dict((manifest.get("game") or {}).get("config") or {})

    recordings_dirs: List[Path] = []
    for cell in matrix.get("cells", []):
        recordings_dirs.extend(_canonical_recordings_dirs(cell["id"]))

    export_results(
        recordings_dirs,
        EXPERIMENT_DIR,
        experiment_id=manifest["experiment_id"],
        include_generated_at=False,
        behavioral_profile_id="auto",
        behavioral_config=behavioral_config,
    )
    print(f"Exported package results -> {EXPERIMENT_DIR}")


if __name__ == "__main__":
    main()
