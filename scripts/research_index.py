#!/usr/bin/env python3
"""Backward-compatible wrapper for the package-owned research index surface."""

try:
    from scripts._bootstrap import ensure_repo_src_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _bootstrap import ensure_repo_src_on_path

ensure_repo_src_on_path()

from agentdeck.research.index import generate_index, main

__all__ = ["generate_index", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
