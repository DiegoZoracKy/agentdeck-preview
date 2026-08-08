"""Behavioral profile declarations and strict JSON Pointer resolution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

from agentdeck.core.artifact_safety import require_json_value

from .manifest import InstrumentManifestError

PROFILE_KEYS = {"schema_version", "profile_id", "profile_version", "metrics", "calibration"}
METRIC_KEYS = {"id", "output_pointer", "record_pointers", "allow_unsupported"}
CALIBRATION_KEYS = {"expected"}
METRIC_ID = re.compile(r"^[a-z][a-z0-9_]*$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 JSON Pointer or raise an actionable error."""
    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise InstrumentManifestError(f"invalid JSON Pointer: {pointer!r}")
    current = document
    for encoded in pointer[1:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise InstrumentManifestError(f"JSON Pointer does not resolve: {pointer}")
            current = current[int(token)]
        elif isinstance(current, Mapping):
            if token not in current:
                raise InstrumentManifestError(f"JSON Pointer does not resolve: {pointer}")
            current = current[token]
        else:
            raise InstrumentManifestError(f"JSON Pointer does not resolve: {pointer}")
    return current


def _exact_keys(value: Any, allowed: set[str], field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise InstrumentManifestError(f"{field} must be a mapping")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise InstrumentManifestError(f"{field} contains unknown fields: {unknown}")
    return value


def load_behavioral_profile(path: Path) -> Dict[str, Any]:
    """Read and validate a non-executable behavioral profile declaration."""
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise InstrumentManifestError(f"invalid behavioral profile YAML: {exc}") from exc
    profile = _exact_keys(value, PROFILE_KEYS, "behavioral profile")
    require_json_value(profile, field="behavioral profile")
    if profile.get("schema_version") != "1.0":
        raise InstrumentManifestError("behavioral profile schema_version must be '1.0'")
    profile_id = profile.get("profile_id")
    if not isinstance(profile_id, str) or not METRIC_ID.fullmatch(profile_id):
        raise InstrumentManifestError("behavioral profile_id is invalid")
    version = profile.get("profile_version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise InstrumentManifestError("behavioral profile_version must use MAJOR.MINOR.PATCH")
    metrics = profile.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise InstrumentManifestError("behavioral profile metrics must be non-empty")
    metric_ids: set[str] = set()
    for index, raw_metric in enumerate(metrics):
        metric = _exact_keys(raw_metric, METRIC_KEYS, f"metrics[{index}]")
        metric_id = metric.get("id")
        if not isinstance(metric_id, str) or not METRIC_ID.fullmatch(metric_id):
            raise InstrumentManifestError(f"metrics[{index}].id is invalid")
        if metric_id in metric_ids:
            raise InstrumentManifestError(f"duplicate metric id: {metric_id}")
        metric_ids.add(metric_id)
        output_pointer = metric.get("output_pointer")
        if not isinstance(output_pointer, str) or not output_pointer.startswith("/"):
            raise InstrumentManifestError(f"metrics[{index}].output_pointer is invalid")
        pointers = metric.get("record_pointers")
        if (
            not isinstance(pointers, list)
            or not pointers
            or any(
                not isinstance(pointer, str) or not pointer.startswith("/") for pointer in pointers
            )
        ):
            raise InstrumentManifestError(
                f"metrics[{index}].record_pointers must be non-empty JSON Pointers"
            )
        if not isinstance(metric.get("allow_unsupported"), bool):
            raise InstrumentManifestError(f"metrics[{index}].allow_unsupported must be boolean")
    calibration = _exact_keys(profile.get("calibration"), CALIBRATION_KEYS, "calibration")
    expected = calibration.get("expected")
    if not isinstance(expected, dict) or not expected:
        raise InstrumentManifestError("calibration.expected must be a non-empty mapping")
    if any(not isinstance(pointer, str) or not pointer.startswith("/") for pointer in expected):
        raise InstrumentManifestError("calibration.expected keys must be JSON Pointers")
    return profile


__all__ = ["load_behavioral_profile", "resolve_json_pointer"]
