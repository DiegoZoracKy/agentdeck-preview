#!/usr/bin/env python3
"""Backward-compatible wrapper for the package-owned research export surface."""

try:
    from scripts._bootstrap import ensure_repo_src_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _bootstrap import ensure_repo_src_on_path

ensure_repo_src_on_path()

from agentdeck.research.export import (
    _behavioral_config_from_manifest,
    _canonical_recordings_dirs_from_artifact,
    _export_matrix_cells,
    _export_matrix_package,
    _iter_selected_cells,
    _list_matrix_cells,
    _recordings_dirs_for_cell,
    _resolve_matrix_path,
    _session_recordings_dirs_for_cell,
    export_results,
    main,
)

__all__ = [
    "export_results",
    "main",
    "_behavioral_config_from_manifest",
    "_resolve_matrix_path",
    "_iter_selected_cells",
    "_canonical_recordings_dirs_from_artifact",
    "_session_recordings_dirs_for_cell",
    "_recordings_dirs_for_cell",
    "_export_matrix_cells",
    "_export_matrix_package",
    "_list_matrix_cells",
]


if __name__ == "__main__":
    raise SystemExit(main())
