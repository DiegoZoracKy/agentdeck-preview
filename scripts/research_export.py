#!/usr/bin/env python3
"""Backward-compatible wrapper for the package-owned research export surface."""

try:
    from scripts._bootstrap import ensure_repo_src_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _bootstrap import ensure_repo_src_on_path

ensure_repo_src_on_path()

from agentdeck.research.export import (
    behavioral_config_from_manifest,
    canonical_recordings_dirs_from_artifact,
    collect_players,
    export_matrix_cells,
    export_matrix_package,
    export_results,
    iter_selected_cells,
    list_matrix_cells,
    load_match,
    main,
    recordings_dirs_for_cell,
    resolve_matrix_path,
    session_recordings_dirs_for_cell,
)

__all__ = [
    "export_results",
    "main",
    "behavioral_config_from_manifest",
    "resolve_matrix_path",
    "iter_selected_cells",
    "canonical_recordings_dirs_from_artifact",
    "session_recordings_dirs_for_cell",
    "recordings_dirs_for_cell",
    "export_matrix_cells",
    "export_matrix_package",
    "list_matrix_cells",
    "load_match",
    "collect_players",
]


if __name__ == "__main__":
    raise SystemExit(main())
