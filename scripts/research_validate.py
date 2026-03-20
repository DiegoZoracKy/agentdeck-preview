#!/usr/bin/env python3
"""Validate research manifests and research/INDEX.md consistency."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
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
RESULTS_CSV_HEADER = (
    "match_id",
    "winner",
    "turns",
    "outcome",
    "seed",
    "duration",
    "cost",
    "player_order_source",
    "first_player",
    "players",
    "player_costs",
)
AUTO_FACTS_BEGIN = "<!-- AUTO_FACTS:BEGIN -->"
AUTO_FACTS_END = "<!-- AUTO_FACTS:END -->"
AUTO_FACTS_PLACEHOLDER_PATTERNS = (
    r"\bTBD\b",
    r"YYYY-MM-DD-slug",
    r"Matches:\s*0/0",
    r"Sample size \(`n`\):\s*0\b",
    r"Win rates:\s*\{\s*\}",
    r"Topline Winner:\s*TBD",
    r"Topline winner:\s*TBD",
)


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


def _validate_results(experiment_dir: Path, manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    experiment_name = experiment_dir.name
    status = manifest.get("status")
    results_json = experiment_dir / "results.json"
    results_csv = experiment_dir / "results.csv"

    results_present = results_json.exists() or results_csv.exists()
    should_validate = results_present or status == "complete"

    if not should_validate:
        return errors

    if not results_json.exists():
        errors.append(f"{experiment_name}: results.json missing (run research_export.py)")
    if not results_csv.exists():
        errors.append(f"{experiment_name}: results.csv missing (run research_export.py)")

    if results_json.exists():
        try:
            data = json.loads(results_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{experiment_name}: results.json invalid JSON ({exc})")
            data = None
        if isinstance(data, dict):
            if data.get("experiment_id") != experiment_name:
                errors.append(
                    f"{experiment_name}: results.json experiment_id mismatch"
                )
            source = data.get("source", {})
            if not isinstance(source, dict):
                errors.append(f"{experiment_name}: results.json missing source object")
            else:
                recordings_dir = source.get("recordings_dir")
                recordings_dirs = source.get("recordings_dirs")
                has_single = isinstance(recordings_dir, str) and bool(recordings_dir.strip())
                has_multi = isinstance(recordings_dirs, list) and len(recordings_dirs) > 0
                if not has_single and not has_multi:
                    errors.append(
                        f"{experiment_name}: results.json missing source.recordings_dir(s)"
                    )
            if "summary" not in data or not isinstance(data.get("summary"), dict):
                errors.append(f"{experiment_name}: results.json missing summary")
            if "players" not in data or not isinstance(data.get("players"), list):
                errors.append(f"{experiment_name}: results.json missing players list")
            if "matches" not in data or not isinstance(data.get("matches"), list):
                errors.append(f"{experiment_name}: results.json missing matches list")

            matches = data.get("matches") if isinstance(data.get("matches"), list) else []
            has_matches = len(matches) > 0
            results_schema_version = data.get("schema_version", 1)
            enforce_extended_research_metrics = (
                _is_int(results_schema_version) and results_schema_version >= 2
            )

            statistics = data.get("statistics")
            if has_matches and enforce_extended_research_metrics:
                if not isinstance(statistics, dict):
                    errors.append(f"{experiment_name}: results.json missing statistics object")
                else:
                    required_stats_keys = {
                        "method",
                        "confidence_level",
                        "alpha",
                        "null_win_rate",
                        "n_total",
                        "n_decisive",
                        "players",
                    }
                    missing_stats = sorted(required_stats_keys - set(statistics.keys()))
                    if missing_stats:
                        errors.append(
                            f"{experiment_name}: results.json.statistics missing keys {missing_stats}"
                        )
                    if not isinstance(statistics.get("players"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.statistics.players must be mapping"
                        )
                    if statistics.get("n_total") != len(matches):
                        errors.append(
                            f"{experiment_name}: results.json.statistics.n_total must equal matches length"
                        )

            strictness = data.get("format_strictness")
            if has_matches and enforce_extended_research_metrics:
                if not isinstance(strictness, dict):
                    errors.append(
                        f"{experiment_name}: results.json missing format_strictness object"
                    )
                else:
                    if not isinstance(strictness.get("overall"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.format_strictness.overall must be mapping"
                        )
                    if not isinstance(strictness.get("by_player"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.format_strictness.by_player must be mapping"
                        )

            position_effect = data.get("position_effect")
            if has_matches and enforce_extended_research_metrics:
                if not isinstance(position_effect, dict):
                    errors.append(
                        f"{experiment_name}: results.json missing position_effect object"
                    )
                else:
                    required_position_keys = {
                        "total_matches",
                        "first_player_wins",
                        "first_player_win_rate",
                        "second_player_wins",
                        "upset_rate",
                        "by_player",
                    }
                    missing_position = sorted(required_position_keys - set(position_effect.keys()))
                    if missing_position:
                        errors.append(
                            f"{experiment_name}: results.json.position_effect missing keys {missing_position}"
                        )
                    if not isinstance(position_effect.get("by_player"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.position_effect.by_player must be mapping"
                        )
                    if position_effect.get("total_matches") != len(matches):
                        errors.append(
                            f"{experiment_name}: results.json.position_effect.total_matches must equal matches length"
                        )

            summary = data.get("summary")
            if isinstance(summary, dict) and summary.get("total_matches") != len(matches):
                errors.append(
                    f"{experiment_name}: results.json.summary.total_matches must equal matches length"
                )

            artifact_validation = data.get("artifact_validation")
            if has_matches and _is_int(results_schema_version) and results_schema_version >= 3:
                if not isinstance(artifact_validation, dict):
                    errors.append(
                        f"{experiment_name}: results.json missing artifact_validation object"
                    )
                else:
                    required_validation_keys = {
                        "matches_checked",
                        "all_passed",
                        "checks",
                        "failures",
                    }
                    missing_validation = sorted(
                        required_validation_keys - set(artifact_validation.keys())
                    )
                    if missing_validation:
                        errors.append(
                            f"{experiment_name}: results.json.artifact_validation missing keys {missing_validation}"
                        )
                    if artifact_validation.get("matches_checked") != len(matches):
                        errors.append(
                            f"{experiment_name}: results.json.artifact_validation.matches_checked must equal matches length"
                        )
                    if not isinstance(artifact_validation.get("all_passed"), bool):
                        errors.append(
                            f"{experiment_name}: results.json.artifact_validation.all_passed must be bool"
                        )
                    if not isinstance(artifact_validation.get("checks"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.artifact_validation.checks must be mapping"
                        )
                    else:
                        required_check_names = {
                            "monotonic_gameplay_timeline",
                            "top_level_timing_consistency",
                            "prompt_turn_number_coherence",
                            "winner_final_state_consistency",
                        }
                        missing_checks = sorted(
                            required_check_names - set(artifact_validation["checks"].keys())
                        )
                        if missing_checks:
                            errors.append(
                                f"{experiment_name}: results.json.artifact_validation.checks missing keys {missing_checks}"
                            )
                        for check_name, check_payload in artifact_validation["checks"].items():
                            if not isinstance(check_payload, dict):
                                errors.append(
                                    f"{experiment_name}: results.json.artifact_validation.checks.{check_name} must be mapping"
                                )
                                continue
                            if not _is_int(check_payload.get("passed")):
                                errors.append(
                                    f"{experiment_name}: results.json.artifact_validation.checks.{check_name}.passed must be int"
                                )
                            if not _is_int(check_payload.get("failed")):
                                errors.append(
                                    f"{experiment_name}: results.json.artifact_validation.checks.{check_name}.failed must be int"
                                )
                    failures = artifact_validation.get("failures")
                    if not isinstance(failures, list):
                        errors.append(
                            f"{experiment_name}: results.json.artifact_validation.failures must be list"
                        )
                    if artifact_validation.get("all_passed") is False:
                        errors.append(
                            f"{experiment_name}: results.json.artifact_validation.all_passed must be true for committed results"
                        )
                    if isinstance(failures, list) and failures:
                        errors.append(
                            f"{experiment_name}: results.json.artifact_validation.failures must be empty for committed results"
                        )

            behavioral_profile = data.get("behavioral_profile")
            if behavioral_profile is not None:
                if not isinstance(behavioral_profile, dict):
                    errors.append(
                        f"{experiment_name}: results.json.behavioral_profile must be mapping"
                    )
                else:
                    required_behavioral_keys = {
                        "schema_version",
                        "game_id",
                        "profile_id",
                        "profile_version",
                        "coverage",
                        "aggregate_metrics",
                        "per_player",
                        "state_metrics",
                        "evidence",
                        "quality_flags",
                    }
                    missing_behavioral = sorted(
                        required_behavioral_keys - set(behavioral_profile.keys())
                    )
                    if missing_behavioral:
                        errors.append(
                            f"{experiment_name}: results.json.behavioral_profile missing keys {missing_behavioral}"
                        )
                    coverage = behavioral_profile.get("coverage")
                    if not isinstance(coverage, dict):
                        errors.append(
                            f"{experiment_name}: results.json.behavioral_profile.coverage must be mapping"
                        )
                    else:
                        for key in (
                            "matches_total",
                            "matches_evaluable",
                            "turns_total",
                            "turns_evaluable",
                        ):
                            if not _is_int(coverage.get(key)):
                                errors.append(
                                    f"{experiment_name}: results.json.behavioral_profile.coverage.{key} must be int"
                                )
                    if not isinstance(behavioral_profile.get("aggregate_metrics"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.behavioral_profile.aggregate_metrics must be mapping"
                        )
                    if not isinstance(behavioral_profile.get("per_player"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.behavioral_profile.per_player must be mapping"
                        )
                    if not isinstance(behavioral_profile.get("state_metrics"), dict):
                        errors.append(
                            f"{experiment_name}: results.json.behavioral_profile.state_metrics must be mapping"
                        )
                    evidence = behavioral_profile.get("evidence")
                    if not isinstance(evidence, dict):
                        errors.append(
                            f"{experiment_name}: results.json.behavioral_profile.evidence must be mapping"
                        )
                    else:
                        for key in (
                            "aggregate_metrics",
                            "per_player",
                            "state_metrics",
                        ):
                            if not isinstance(evidence.get(key), dict):
                                errors.append(
                                    f"{experiment_name}: results.json.behavioral_profile.evidence.{key} must be mapping"
                                )
                    quality_flags = behavioral_profile.get("quality_flags")
                    if not isinstance(quality_flags, dict):
                        errors.append(
                            f"{experiment_name}: results.json.behavioral_profile.quality_flags must be mapping"
                        )
                    else:
                        if not isinstance(quality_flags.get("complete"), bool):
                            errors.append(
                                f"{experiment_name}: results.json.behavioral_profile.quality_flags.complete must be bool"
                            )
                        unsupported_metrics = quality_flags.get("unsupported_metrics")
                        if not isinstance(unsupported_metrics, list) or not all(
                            isinstance(item, str) for item in unsupported_metrics
                        ):
                            errors.append(
                                f"{experiment_name}: results.json.behavioral_profile.quality_flags.unsupported_metrics must be list[str]"
                            )

            schema_version = data.get("schema_version")
            if schema_version is not None:
                if not _is_int(schema_version):
                    errors.append(
                        f"{experiment_name}: results.json schema_version must be int"
                    )
                elif schema_version < 1:
                    errors.append(
                        f"{experiment_name}: results.json schema_version must be >= 1"
                    )
        elif data is not None:
            errors.append(f"{experiment_name}: results.json must be mapping")

    if results_csv.exists():
        try:
            with results_csv.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, [])
        except Exception as exc:
            errors.append(f"{experiment_name}: results.csv unreadable ({exc})")
            header = []
        if not header:
            errors.append(f"{experiment_name}: results.csv missing header row")
        elif tuple(header) != RESULTS_CSV_HEADER:
            errors.append(
                f"{experiment_name}: results.csv header mismatch "
                f"(expected {list(RESULTS_CSV_HEADER)})"
            )

    return errors


def _extract_auto_facts_block(markdown: str) -> Tuple[bool, str]:
    begin_idx = markdown.find(AUTO_FACTS_BEGIN)
    end_idx = markdown.find(AUTO_FACTS_END)
    if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
        return False, ""
    block_start = begin_idx + len(AUTO_FACTS_BEGIN)
    return True, markdown[block_start:end_idx].strip()


def _has_auto_facts_placeholder(block: str) -> bool:
    for pattern in AUTO_FACTS_PLACEHOLDER_PATTERNS:
        if re.search(pattern, block):
            return True
    return False


def _validate_markdown_facts(experiment_dir: Path, manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    experiment_name = experiment_dir.name
    status = manifest.get("status")
    run = manifest.get("run") if isinstance(manifest.get("run"), dict) else {}
    matches_completed = run.get("matches_completed")

    must_enforce = (
        status in {"complete", "archived"}
        and _is_int(matches_completed)
        and matches_completed > 0
    )
    if not must_enforce:
        return errors

    for doc_name in ("README.md", "analysis.md"):
        path = experiment_dir / doc_name
        if not path.exists():
            errors.append(f"{experiment_name}: {doc_name} missing")
            continue

        content = path.read_text(encoding="utf-8")
        has_block, block = _extract_auto_facts_block(content)
        if not has_block:
            errors.append(
                f"{experiment_name}: {doc_name} missing AUTO_FACTS block markers"
            )
            continue

        if _has_auto_facts_placeholder(block):
            errors.append(
                f"{experiment_name}: {doc_name} AUTO_FACTS block still contains placeholders"
            )

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

    for manifest_path in manifest_paths:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            errors.append(f"{manifest_path.parent.name}: manifest must be mapping")
            continue
        errors.extend(_validate_manifest(manifest_path, manifest))
        errors.extend(_validate_results(manifest_path.parent, manifest))
        errors.extend(_validate_markdown_facts(manifest_path.parent, manifest))

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
