#!/usr/bin/env python3
"""Backward-compatible wrapper for the package-owned research validation surface."""

try:
    from scripts._bootstrap import ensure_repo_src_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _bootstrap import ensure_repo_src_on_path

ensure_repo_src_on_path()

from agentdeck.research.validate import (
    _validate_manifest,
    _validate_markdown_facts,
    _validate_results,
    main,
    validate_research_tree,
)

__all__ = [
    "validate_research_tree",
    "main",
    "_validate_manifest",
    "_validate_results",
    "_validate_markdown_facts",
]


if __name__ == "__main__":
    raise SystemExit(main())
