#!/usr/bin/env python3
"""Validate research manifests and research/INDEX.md consistency."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


REQUIRED_FIELDS: Tuple[Tuple[str, ...], ...] = (
    ("schema_version",),
    ("experiment_id",),
    ("status",),
    ("question",),
    ("game", "name"),
    ("players",),
    ("run", "matches_planned"),
    ("run", "seed_base"),
)

ALLOWED_STATUS = {"planned", "running", "complete", "archived"}


def _load_generate_index() -> Any:
    script_path = Path(__file__).with_name("research_index.py")
    spec = importlib.util.spec_from_file_location("research_index", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate_index


def _get_nested(data: Dict[str, Any], path: Tuple[str, ...]) -> Tuple[Any, bool]:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None, False
        current = current[key]
    return current, True


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_manifest(manifest_path: Path, manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    experiment_dir = manifest_path.parent
    experiment_name = experiment_dir.name

    for field in REQUIRED_FIELDS:
        value, ok = _get_nested(manifest, field)
        if not ok:
            errors.append(f"{experiment_name}: missing {'.'.join(field)}")
            continue
        if value is None or value == "":
            errors.append(f"{experiment_name}: empty {'.'.join(field)}")

    schema_version = manifest.get("schema_version")
    if schema_version is not None and not _is_int(schema_version):
        errors.append(f"{experiment_name}: schema_version must be int")
    if _is_int(schema_version) and schema_version < 1:
        errors.append(f"{experiment_name}: schema_version must be >= 1")

    status = manifest.get("status")
    if status is not None and status not in ALLOWED_STATUS:
        errors.append(f"{experiment_name}: status '{status}' not in {sorted(ALLOWED_STATUS)}")

    experiment_id = manifest.get("experiment_id")
    if experiment_id and experiment_id != experiment_name:
        errors.append(
            f"{experiment_name}: experiment_id '{experiment_id}' != folder name"
        )

    players = manifest.get("players")
    if isinstance(players, list):
        if not players:
            errors.append(f"{experiment_name}: players must be non-empty")
        for idx, player in enumerate(players):
            if not isinstance(player, dict):
                errors.append(f"{experiment_name}: players[{idx}] must be mapping")
                continue
            if not player.get("provider"):
                errors.append(f"{experiment_name}: players[{idx}].provider missing")
            if not player.get("model"):
                errors.append(f"{experiment_name}: players[{idx}].model missing")

    run = manifest.get("run", {})
    matches_planned = run.get("matches_planned")
    seed_base = run.get("seed_base")
    if matches_planned is not None and not _is_int(matches_planned):
        errors.append(f"{experiment_name}: run.matches_planned must be int")
    if _is_int(matches_planned) and matches_planned < 0:
        errors.append(f"{experiment_name}: run.matches_planned must be >= 0")
    if seed_base is not None and not _is_int(seed_base):
        errors.append(f"{experiment_name}: run.seed_base must be int")

    return errors


def _normalize_index(content: str, timestamp_line: str) -> str:
    lines = content.splitlines()
    normalized = []
    replaced = False
    for line in lines:
        if line.startswith("Last updated:"):
            normalized.append(timestamp_line)
            replaced = True
        else:
            normalized.append(line)
    if not replaced:
        normalized = lines
    return "\n".join(normalized) + ("\n" if content.endswith("\n") else "")


def _validate_index(
    research_dir: Path, index_path: Path, write_index: bool
) -> List[str]:
    generate_index = _load_generate_index()
    generated = generate_index(research_dir)

    if write_index:
        index_path.write_text(generated, encoding="utf-8")
        return []

    if not index_path.exists():
        return [f"INDEX.md missing at {index_path}"]

    current = index_path.read_text(encoding="utf-8")
    timestamp_line = next(
        (line for line in current.splitlines() if line.startswith("Last updated:")),
        None,
    )
    if timestamp_line:
        generated = _normalize_index(generated, timestamp_line)

    if current != generated:
        return ["INDEX.md out of date (regenerate with scripts/research_index.py)"]

    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate research manifests and INDEX.md consistency."
    )
    parser.add_argument("--research-dir", default=Path("research"), type=Path)
    parser.add_argument("--index", default=Path("research/INDEX.md"), type=Path)
    parser.add_argument(
        "--write-index",
        action="store_true",
        help="Regenerate INDEX.md when out of date.",
    )
    args = parser.parse_args()

    research_dir = args.research_dir
    if not research_dir.exists():
        print(f"Research dir not found: {research_dir}", file=sys.stderr)
        return 1

    errors: List[str] = []
    manifest_paths = sorted(
        path
        for path in research_dir.glob("*/manifest.yaml")
        if "_templates" not in str(path)
    )

    if not manifest_paths:
        errors.append("No manifest.yaml files found under research/")

    for manifest_path in manifest_paths:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            errors.append(f"{manifest_path.parent.name}: manifest must be mapping")
            continue
        errors.extend(_validate_manifest(manifest_path, manifest))

    errors.extend(_validate_index(research_dir, args.index, args.write_index))

    if errors:
        print("Research validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Research validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
