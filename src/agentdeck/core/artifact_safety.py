"""Shared artifact identity, containment, and strict JSON helpers."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from os import PathLike
from pathlib import Path
from typing import Any

_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", re.ASCII)


def validate_artifact_id(value: str, *, field: str = "artifact_id") -> str:
    """Return a portable artifact identifier or raise ``ValueError``."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if not _ARTIFACT_ID.fullmatch(value) or value in {".", ".."}:
        raise ValueError(
            f"{field} must be 1-128 ASCII characters matching " "[A-Za-z0-9][A-Za-z0-9._-]*"
        )
    return value


def contained_path(root: str | PathLike[str], *segments: str) -> Path:
    """Resolve validated path segments beneath ``root``."""
    resolved_root = Path(root).resolve()
    candidate = resolved_root
    for index, segment in enumerate(segments):
        candidate /= validate_artifact_id(segment, field=f"path segment {index}")
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Resolved artifact path leaves declared root: {resolved_root}") from exc
    return resolved_candidate


def ensure_contained_path(root: str | PathLike[str], candidate: str | PathLike[str]) -> Path:
    """Return ``candidate`` only when its resolved path remains under ``root``."""
    resolved_root = Path(root).resolve()
    resolved_candidate = Path(candidate).resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Resolved artifact path leaves declared root: {resolved_root}") from exc
    return resolved_candidate


def _require_json_node(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError(f"{path} contains a non-finite float")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_json_node(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} contains non-string object key {key!r}")
            _require_json_node(item, f"{path}.{key}")
        return
    raise TypeError(f"{path} contains unsupported JSON type {type(value).__name__}")


def require_json_value(value: object, *, field: str) -> None:
    """Require a lossless strict JSON value without encoder fallbacks."""
    try:
        _require_json_node(value, field)
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a strict JSON value: {exc}") from exc


def atomic_write_text(path: str | PathLike[str], text: str, *, encoding: str = "utf-8") -> None:
    """Commit text with one same-directory atomic replacement."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_json(path: str | PathLike[str], value: object, *, field: str) -> None:
    """Validate and atomically commit one strict JSON document."""
    require_json_value(value, field=field)
    payload = json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)
    atomic_write_text(path, payload)


__all__ = [
    "atomic_write_json",
    "atomic_write_text",
    "contained_path",
    "ensure_contained_path",
    "require_json_value",
    "validate_artifact_id",
]
