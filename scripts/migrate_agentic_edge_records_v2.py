#!/usr/bin/env python3
"""One-shot migration for Agentic Edge match records to Recorder v2.0.

This is intentionally not runtime compatibility. It rewrites the irreplaceable
Agentic Edge research records once so current Core code can stay cleanly v2-only.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

DEFAULT_ROOT = Path("research/2026-04-27-agentic-edge-strategy-stack")

INTERACTION_METADATA_KEYS = {
    "raw_prompt",
    "prompt_text",
    "prompt_blocks",
    "raw_response",
    "response_text",
    "usage_info",
    "renderer_output",
    "controller_format",
    "controller_metadata",
    "prompt_length",
    "template_id",
    "call_id",
    "duration",
    "turn_number",
    "turn_context",
}


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _clean_context(context: Any) -> Dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    cleaned = dict(context)
    if "phase_index" not in cleaned and "turn_index" in cleaned:
        cleaned["phase_index"] = cleaned["turn_index"]
    cleaned.pop("turn_index", None)
    return cleaned


def _clean_turn_context(turn_context: Any, *, phase_index: int | None) -> Dict[str, Any]:
    if not isinstance(turn_context, dict):
        turn_context = {}
    cleaned = dict(turn_context)
    if "phase_index" not in cleaned:
        if phase_index is not None:
            cleaned["phase_index"] = phase_index
        elif "turn_index" in cleaned:
            cleaned["phase_index"] = cleaned["turn_index"]
    cleaned.pop("turn_index", None)
    return cleaned


def _metadata_without_interaction(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: _copy(value) for key, value in metadata.items() if key not in INTERACTION_METADATA_KEYS
    }


def _extract_action(data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    raw_action = data.get("action")
    action_metadata: Dict[str, Any] = {}

    if isinstance(raw_action, dict):
        value = raw_action.get("value", raw_action.get("action"))
        reasoning = raw_action.get("reasoning", data.get("reasoning"))
        raw_action_metadata = raw_action.get("metadata")
        if isinstance(raw_action_metadata, dict):
            action_metadata.update(raw_action_metadata)
    else:
        value = raw_action
        reasoning = data.get("reasoning")

    action_metadata.update(_metadata_without_interaction(metadata))
    return {
        "value": value,
        "reasoning": reasoning,
        "metadata": action_metadata,
    }


def _extract_interaction(data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    prompt = data.get("prompt") if isinstance(data.get("prompt"), dict) else {}
    interaction = {
        "prompt_text": prompt.get("prompt_text")
        or metadata.get("prompt_text")
        or metadata.get("raw_prompt"),
        "prompt_blocks": _copy(
            prompt.get("prompt_blocks")
            if prompt.get("prompt_blocks") is not None
            else metadata.get("prompt_blocks", [])
        ),
        "response_text": prompt.get("response_text")
        or metadata.get("response_text")
        or metadata.get("raw_response")
        or data.get("response_text")
        or data.get("raw_response"),
        "usage_info": _copy(prompt.get("usage_info") or metadata.get("usage_info")),
        "renderer_output": _copy(prompt.get("renderer_output") or metadata.get("renderer_output")),
        "controller_format": prompt.get("controller_format") or metadata.get("controller_format"),
        "controller_metadata": _copy(
            prompt.get("controller_metadata") or metadata.get("controller_metadata")
        ),
    }
    for key in ("call_id", "duration"):
        if prompt.get(key) is not None:
            interaction[key] = _copy(prompt[key])
        elif metadata.get(key) is not None:
            interaction[key] = _copy(metadata[key])
    return interaction


def _migrate_gameplay_event(event: Dict[str, Any]) -> Dict[str, Any]:
    migrated = _copy(event)
    data = migrated.get("data") or {}
    if not isinstance(data, dict):
        return migrated

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    phase_index = data.get("phase_index", data.get("turn_index"))
    if phase_index is None:
        context = event.get("context") if isinstance(event.get("context"), dict) else {}
        phase_index = context.get("phase_index", context.get("turn_index"))

    migrated_data = {
        "match_id": data.get("match_id") or event.get("match_id"),
        "mechanic": data.get("mechanic", "turn_based"),
        "phase_index": phase_index,
        "player": data.get("player"),
        "action": _extract_action(data, metadata),
        "interaction": _extract_interaction(data, metadata),
        "state_before": _copy(data.get("state_before", {})),
        "state_after": _copy(data.get("state_after", {})),
        "turn_context": _clean_turn_context(data.get("turn_context"), phase_index=phase_index),
    }
    migrated["data"] = migrated_data
    migrated["context"] = _clean_context(migrated.get("context"))
    return migrated


def _migrate_lifecycle_event(event: Dict[str, Any]) -> Dict[str, Any]:
    migrated = _copy(event)
    data = migrated.get("data")
    if not isinstance(data, dict):
        return migrated

    prompt = data.get("prompt") if isinstance(data.get("prompt"), dict) else {}
    for key in (
        "prompt_text",
        "prompt_blocks",
        "response_text",
        "usage_info",
        "renderer_output",
        "controller_format",
        "controller_metadata",
    ):
        if key not in data and key in prompt:
            data[key] = _copy(prompt[key])
    for key in ("call_id", "duration"):
        if key not in data and key in prompt:
            data[key] = _copy(prompt[key])
    data.pop("prompt", None)
    migrated["context"] = _clean_context(migrated.get("context"))
    return migrated


def migrate_match_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    migrated = _copy(payload)
    migrated["schema_version"] = "2.0"
    migrated["schema_type"] = "match"

    events = []
    for event in migrated.get("events") or []:
        if not isinstance(event, dict):
            events.append(event)
            continue
        if event.get("type") == "gameplay":
            events.append(_migrate_gameplay_event(event))
        else:
            events.append(_migrate_lifecycle_event(event))
    migrated["events"] = events
    return migrated


def _event_semantics(event: Dict[str, Any]) -> Tuple[Any, ...]:
    data = event.get("data") or {}
    if event.get("type") == "gameplay":
        action = data.get("action")
        if isinstance(action, dict):
            action_value = action.get("value", action.get("action"))
            reasoning = action.get("reasoning", data.get("reasoning"))
        else:
            action_value = action
            reasoning = data.get("reasoning")
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        prompt = data.get("prompt") if isinstance(data.get("prompt"), dict) else {}
        return (
            event.get("type"),
            data.get("player"),
            action_value,
            reasoning,
            data.get("state_before"),
            data.get("state_after"),
            prompt.get("prompt_text") or metadata.get("raw_prompt"),
            prompt.get("response_text") or metadata.get("raw_response"),
            prompt.get("usage_info") or metadata.get("usage_info"),
        )
    return (
        event.get("type"),
        data.get("player"),
        data.get("prompt_text"),
        data.get("response_text"),
        data.get("usage_info"),
    )


def _migrated_event_semantics(event: Dict[str, Any]) -> Tuple[Any, ...]:
    data = event.get("data") or {}
    if event.get("type") == "gameplay":
        action = data.get("action") or {}
        interaction = data.get("interaction") or {}
        return (
            event.get("type"),
            data.get("player"),
            action.get("value"),
            action.get("reasoning"),
            data.get("state_before"),
            data.get("state_after"),
            interaction.get("prompt_text"),
            interaction.get("response_text"),
            interaction.get("usage_info"),
        )
    return (
        event.get("type"),
        data.get("player"),
        data.get("prompt_text"),
        data.get("response_text"),
        data.get("usage_info"),
    )


def assert_lossless(original: Dict[str, Any], migrated: Dict[str, Any], path: Path) -> None:
    original_events = original.get("events") or []
    migrated_events = migrated.get("events") or []
    if len(original_events) != len(migrated_events):
        raise AssertionError(f"{path}: event count changed")
    for index, (before, after) in enumerate(zip(original_events, migrated_events)):
        if _event_semantics(before) != _migrated_event_semantics(after):
            raise AssertionError(f"{path}: semantic mismatch at event {index}")
        data = after.get("data") if isinstance(after, dict) else None
        context = after.get("context") if isinstance(after, dict) else None
        if isinstance(data, dict) and ("prompt" in data or "turn_index" in data):
            raise AssertionError(f"{path}: retired field remains in event {index}")
        if isinstance(context, dict) and "turn_index" in context:
            raise AssertionError(f"{path}: retired context field remains in event {index}")


def assert_canonical_v2(payload: Dict[str, Any], path: Path) -> None:
    if str(payload.get("schema_version")) != "2.0":
        raise AssertionError(f"{path}: expected schema_version 2.0")
    for index, event in enumerate(payload.get("events") or []):
        if not isinstance(event, dict):
            continue
        data = event.get("data")
        context = event.get("context")
        if isinstance(context, dict) and "turn_index" in context:
            raise AssertionError(f"{path}: retired context field remains in event {index}")
        if not isinstance(data, dict):
            continue
        if "prompt" in data or "turn_index" in data:
            raise AssertionError(f"{path}: retired field remains in event {index}")
        if event.get("type") == "gameplay":
            required = {
                "mechanic",
                "phase_index",
                "player",
                "action",
                "interaction",
                "state_before",
                "state_after",
                "turn_context",
            }
            missing = required - set(data)
            if missing:
                raise AssertionError(f"{path}: gameplay event {index} missing {sorted(missing)}")
            action = data.get("action")
            if not isinstance(action, dict) or "value" not in action:
                raise AssertionError(f"{path}: gameplay event {index} has noncanonical action")
            action_metadata = action.get("metadata")
            if isinstance(action_metadata, dict):
                duplicated = INTERACTION_METADATA_KEYS & set(action_metadata)
                if duplicated:
                    raise AssertionError(
                        f"{path}: gameplay event {index} action metadata duplicates {sorted(duplicated)}"
                    )


def iter_match_records(root: Path) -> Iterable[Path]:
    return sorted(root.glob("agentdeck_runs/**/records/match_*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--write", action="store_true", help="rewrite records in place")
    args = parser.parse_args()

    paths = list(iter_match_records(args.root))
    migrated_count = 0
    already_current = 0

    for path in paths:
        original = json.loads(path.read_text(encoding="utf-8"))
        if str(original.get("schema_version")) == "2.0":
            assert_canonical_v2(original, path)
            already_current += 1
            continue
        migrated = migrate_match_payload(original)
        assert_lossless(original, migrated, path)
        assert_canonical_v2(migrated, path)
        migrated_count += 1
        if args.write:
            path.write_text(
                json.dumps(migrated, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    action = "migrated" if args.write else "validated"
    print(f"{action} {migrated_count} records; {already_current} already v2.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
