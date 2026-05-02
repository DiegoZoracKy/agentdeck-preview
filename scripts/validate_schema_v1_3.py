#!/usr/bin/env python3
"""
Offline schema v1.3 recording validator.

This script validates existing AgentDeck match recordings without provider
credentials or network calls. Use live_schema_check_v1_3.py for the live
OpenAI-backed regression flow.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

# Add src to path for development checkout execution.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def validate_pm_metadata(event_data: Dict[str, Any], event_type: str) -> List[str]:
    """
    Validate PM1-PM6 metadata fields in event data.

    Schema v1.3 stores prompt metadata under event["data"]["prompt"].
    """
    issues: List[str] = []

    if event_type in {
        "player_handshake_complete",
        "player_action_parse_failed",
        "player_conclusion",
    }:
        prompt_data = event_data.get("prompt", {})

        if not prompt_data:
            issues.append(f"Missing 'prompt' metadata dict in {event_type}")
            return issues

        if not isinstance(prompt_data, dict):
            issues.append(f"'prompt' field is not a dict in {event_type}")

    return issues


def _is_match_record(payload: Dict[str, Any]) -> bool:
    return bool(
        payload.get("schema_type") == "match"
        or (
            payload.get("match_id")
            and payload.get("game")
            and isinstance(payload.get("events"), list)
        )
    )


def discover_recordings(paths: Iterable[Path]) -> List[Path]:
    """Return candidate match recording JSON files from files and directories."""
    recordings: List[Path] = []
    for path in paths:
        if path.is_file():
            recordings.append(path)
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*.json")):
                if candidate.name.endswith(".meta.json") or candidate.name == "manifest.json":
                    continue
                try:
                    with candidate.open("r", encoding="utf-8") as handle:
                        payload = json.load(handle)
                except (json.JSONDecodeError, OSError):
                    continue
                if isinstance(payload, dict) and _is_match_record(payload):
                    recordings.append(candidate)
            continue
        raise FileNotFoundError(f"No such path: {path}")
    return sorted(set(recordings))


def validate_recording(recording_path: Path) -> Dict[str, Any]:
    """Validate a single match recording and return a result dictionary."""
    print(f"\n  Validating: {recording_path}")

    with recording_path.open("r", encoding="utf-8") as handle:
        match_data = json.load(handle)

    results: Dict[str, Any] = {
        "path": str(recording_path),
        "schema_version": match_data.get("schema_version"),
        "has_dialogue_array": "dialogue" in match_data,
        "event_count": len(match_data.get("events", [])),
        "pm_issues": [],
        "success": True,
    }

    if results["schema_version"] != "1.3":
        results["pm_issues"].append(f"Wrong schema version: {results['schema_version']}")
        results["success"] = False

    if results["has_dialogue_array"]:
        results["pm_issues"].append(
            "Dialogue array still present; schema v1.3 stores prompts in events"
        )
        results["success"] = False

    events = match_data.get("events", [])
    if not isinstance(events, list):
        results["pm_issues"].append("'events' must be a list")
        results["success"] = False
        events = []

    for event in events:
        if not isinstance(event, dict):
            results["pm_issues"].append("Event entry is not an object")
            results["success"] = False
            continue

        event_type = event.get("type")
        event_data = event.get("data", {})
        if not isinstance(event_data, dict):
            results["pm_issues"].append(f"Event data is not an object in {event_type}")
            results["success"] = False
            continue

        issues = validate_pm_metadata(event_data, str(event_type))
        results["pm_issues"].extend(issues)
        if issues:
            results["success"] = False

    if results["success"]:
        print(f"    OK - {results['event_count']} events, schema v{results['schema_version']}")
    else:
        print("    Issues found:")
        for issue in results["pm_issues"]:
            print(f"       - {issue}")

    return results


def test_replay_recording(recording_path: Path) -> bool:
    """Replay a recording through the public AgentDeck replay API."""
    try:
        from agentdeck import AgentDeck

        deck = AgentDeck()
        deck.replay(path=str(recording_path))
        print(f"    Replay OK: {recording_path}")
        return True
    except Exception as exc:  # pragma: no cover - CLI diagnostic path
        print(f"    Replay failed for {recording_path}: {exc}")
        return False


def validate_paths(paths: Iterable[Path], *, replay: bool = False) -> bool:
    """Validate all recordings found under paths."""
    recordings = discover_recordings(paths)
    if not recordings:
        print("No match recordings found.")
        return False

    all_valid = True
    for recording in recordings:
        validation = validate_recording(recording)
        if not validation["success"]:
            all_valid = False
        if replay and not test_replay_recording(recording):
            all_valid = False

    print("\nValidation Summary")
    print("=" * 70)
    print(f"Recordings checked: {len(recordings)}")
    print(f"Result: {'PASS' if all_valid else 'FAIL'}")
    return all_valid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate AgentDeck schema v1.3 match recordings.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("viewer/matches")],
        help="Recording JSON files or directories. Defaults to viewer/matches.",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Also replay each valid recording through AgentDeck.replay().",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print("=" * 70)
    print("Schema v1.3 Offline Recording Validation")
    print("=" * 70)

    try:
        return 0 if validate_paths(args.paths, replay=args.replay) else 1
    except FileNotFoundError as exc:
        print(exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
