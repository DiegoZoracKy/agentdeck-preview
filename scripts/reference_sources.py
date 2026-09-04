"""Reference-local source locks; never substitute for a Research artifact identity.

Only Python's version is excluded from this acceptance projection. Full Measure,
Profile and Evidence identities still include the actual material environment.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from agentdeck.research._canonical import sha256_json


def measure_sources(measure: Any) -> str:
    payload = measure.as_dict()
    del payload["measure_sha256"]
    del payload["material_environment_sha256"]
    del payload["material_environment"]["python"]
    return sha256_json(payload)


def profile_sources(profile: Any) -> str:
    payload = profile.as_dict()
    del payload["profile_sha256"]
    for item in payload["operationalizations"]:
        item["measure_sha256"] = measure_sources(profile.prepared_measures[item["id"]])
    return sha256_json(payload)


def verify_sources(
    probe_path: Path,
    profiles: Mapping[str, Any],
    measures: Mapping[str, Any],
) -> dict[str, Any]:
    """Check reviewed sources and return current, environment-specific provenance."""

    lock_path = probe_path.parent / "source-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema_version") != 1:
        raise ValueError("Reference source lock schema_version must equal 1")
    if lock["probe_sha256"] != hashlib.sha256(probe_path.read_bytes()).hexdigest():
        raise ValueError("Reference source lock belongs to a different frozen probe")
    resolved: dict[str, Any] = {"source_lock_sha256": sha256_json(lock)}
    for kind, current, project, identity_key in (
        ("profiles", profiles, profile_sources, "profile_sha256"),
        ("measures", measures, measure_sources, "measure_sha256"),
    ):
        if set(current) != set(lock[kind]):
            raise ValueError(f"Reference {kind} selection changed")
        resolved[kind] = {}
        for name, prepared in current.items():
            if project(prepared) != lock[kind][name]["sources_sha256"]:
                raise ValueError(f"Reference {kind} sources changed: {name}")
            resolved[kind][name] = {identity_key: getattr(prepared, identity_key)}
            if kind == "measures":
                resolved[kind][name]["material_environment"] = dict(prepared.material_environment)
                resolved[kind][name][
                    "material_environment_sha256"
                ] = prepared.material_environment_sha256
    return resolved
