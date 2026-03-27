"""Helpers for running repo-local wrapper scripts without an editable install."""

from __future__ import annotations

from pathlib import Path
import sys


def ensure_repo_src_on_path() -> None:
    """Add the repository's ``src/`` directory to ``sys.path`` if needed."""
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
