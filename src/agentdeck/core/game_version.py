"""Portable, non-blocking Game implementation provenance."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Optional, Tuple

from .artifact_safety import require_json_value


_MODULE_NAME = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")


def _digest_sources(sources: Iterable[Tuple[str, bytes]]) -> tuple[str, list[Dict[str, str]]]:
    digest = hashlib.sha256()
    entries: list[Dict[str, str]] = []
    for name, content in sorted(sources, key=lambda item: item[0]):
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(8, "big"))
        digest.update(encoded_name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
        entries.append({"name": name, "sha256": hashlib.sha256(content).hexdigest()})
    return digest.hexdigest(), entries


def _declared_modules(game: Any) -> Optional[tuple[str, ...]]:
    value = getattr(game.__class__, "GAME_IMPLEMENTATION_MODULES", None)
    if value is None:
        return None
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError("GAME_IMPLEMENTATION_MODULES must be a non-empty list or tuple")
    modules = tuple(value)
    if any(not isinstance(name, str) or _MODULE_NAME.fullmatch(name) is None for name in modules):
        raise ValueError("GAME_IMPLEMENTATION_MODULES must contain portable qualified module names")
    if len(set(modules)) != len(modules):
        raise ValueError("GAME_IMPLEMENTATION_MODULES must not contain duplicates")
    return modules


def _module_bytes(module_name: str) -> Optional[bytes]:
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, AttributeError, ValueError):
        return None
    origin = getattr(spec, "origin", None) if spec else None
    if not isinstance(origin, str) or origin in {"built-in", "frozen"}:
        return None
    try:
        return Path(origin).read_bytes()
    except OSError:
        return None


def _explicit_text(value: Any, *, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string when declared")
    return value.strip()


def describe_game_version(game: Any) -> Dict[str, Any]:
    """Describe exactly how much of a Game implementation can be fingerprinted."""

    game_type = game.__class__
    fallback_family = f"{game_type.__module__}:{game_type.__qualname__}"
    family_id = _explicit_text(
        getattr(game_type, "GAME_FAMILY_ID", None), field="GAME_FAMILY_ID"
    ) or fallback_family
    declared_version = _explicit_text(
        getattr(game_type, "GAME_VERSION", None), field="GAME_VERSION"
    )

    modules = _declared_modules(game)
    if modules is not None:
        source_values = [(f"module:{name}", _module_bytes(name)) for name in modules]
        if all(content is not None for _, content in source_values):
            digest, sources = _digest_sources(
                (name, content) for name, content in source_values if content is not None
            )
            descriptor: Dict[str, Any] = {
                "family_id": family_id,
                "declared_version": declared_version,
                "implementation_sha256": digest,
                "fingerprint_scope": "declared_closure",
                "sources": sources,
                "assurance": "content_addressed",
            }
        else:
            descriptor = {
                "family_id": family_id,
                "declared_version": declared_version,
                "implementation_sha256": None,
                "fingerprint_scope": "unresolved",
                "sources": [
                    {
                        "name": name,
                        "sha256": hashlib.sha256(content).hexdigest() if content is not None else None,
                    }
                    for name, content in source_values
                ],
                "assurance": "unresolved",
            }
    else:
        try:
            class_source = inspect.getsource(game_type).encode("utf-8")
        except (OSError, TypeError):
            class_source = None
        if class_source is None:
            descriptor = {
                "family_id": family_id,
                "declared_version": declared_version,
                "implementation_sha256": None,
                "fingerprint_scope": "unresolved",
                "sources": [],
                "assurance": "unresolved",
            }
        else:
            digest, sources = _digest_sources(
                [(f"class:{fallback_family}", class_source)]
            )
            descriptor = {
                "family_id": family_id,
                "declared_version": declared_version,
                "implementation_sha256": digest,
                "fingerprint_scope": "class_source",
                "sources": sources,
                "assurance": "class_source_only",
            }

    require_json_value(descriptor, field="game version provenance")
    return descriptor
