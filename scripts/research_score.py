#!/usr/bin/env python3
"""Backward-compatible wrapper for the package-owned behavioral rescore surface."""

try:
    from scripts._bootstrap import ensure_repo_src_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _bootstrap import ensure_repo_src_on_path

ensure_repo_src_on_path()

from agentdeck.research.score import main, rescore_experiment

__all__ = ["rescore_experiment", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
