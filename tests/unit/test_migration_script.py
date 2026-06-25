"""Tests for scripts/migrate_agentic_edge_records_v2.py safe-mode flags."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.migrate_agentic_edge_records_v2 import (  # noqa: E402
    assert_canonical_v2,
    migrate_match_payload,
)

MINIMAL_V1_RECORD = {
    "schema_version": "1.3",
    "match_id": "match_test_001",
    "game": "FixedDamageGame",
    "players": ["Alice", "Bob"],
    "winner": "Alice",
    "seed": 42,
    "final_state": {},
    "metadata": {},
    "events": [
        {
            "type": "gameplay",
            "data": {
                "player": "Alice",
                "action": "ATTACK",
                "reasoning": "Go aggressive",
                "mechanic": "turn_based",
                "phase_index": 0,
                "state_before": {"health": {"Alice": 100, "Bob": 100}},
                "state_after": {"health": {"Alice": 100, "Bob": 80}},
                "turn_context": {"turn_number": 1},
                "metadata": {
                    "raw_prompt": "Your turn.",
                    "raw_response": "ACTION: ATTACK",
                    "usage_info": {"prompt_tokens": 10, "completion_tokens": 2},
                },
            },
            "context": {"phase_index": 0},
            "timestamp": 1.0,
        }
    ],
}


def _write_record(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _read_record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# migrate_match_payload unit tests
# ---------------------------------------------------------------------------


def test_provenance_fields_present(tmp_path):
    source = tmp_path / "match_001.json"
    result = migrate_match_payload(MINIMAL_V1_RECORD, source_path=source)

    prov = result.get("migration_provenance")
    assert prov is not None, "migration_provenance must be present"
    assert prov["source_schema_version"] == "1.3"
    assert prov["source_match_id"] == "match_test_001"
    assert prov["source_artifact"] == str(source)
    assert prov["migration_script"] == "scripts/migrate_agentic_edge_records_v2.py"
    assert prov["migration_target_schema"] == "2.0"
    assert "migrated_at" in prov


def test_provenance_without_source_path():
    result = migrate_match_payload(MINIMAL_V1_RECORD)
    assert result["migration_provenance"]["source_artifact"] is None


def test_derived_payload_is_canonical_v2(tmp_path):
    source = tmp_path / "match_001.json"
    result = migrate_match_payload(MINIMAL_V1_RECORD, source_path=source)
    assert result["schema_version"] == "2.0"
    assert_canonical_v2(result, source)


def test_gameplay_action_value(tmp_path):
    source = tmp_path / "match_001.json"
    result = migrate_match_payload(MINIMAL_V1_RECORD, source_path=source)
    event = next(e for e in result["events"] if e["type"] == "gameplay")
    action = event["data"]["action"]
    assert isinstance(action, dict), "action must be a dict in v2"
    assert action["value"] == "ATTACK"


def test_gameplay_interaction_present(tmp_path):
    source = tmp_path / "match_001.json"
    result = migrate_match_payload(MINIMAL_V1_RECORD, source_path=source)
    event = next(e for e in result["events"] if e["type"] == "gameplay")
    assert "interaction" in event["data"], "interaction must be present in v2 gameplay"
    assert event["data"]["interaction"]["prompt_text"] == "Your turn."


def test_no_turn_index_in_derived(tmp_path):
    source = tmp_path / "match_001.json"
    result = migrate_match_payload(MINIMAL_V1_RECORD, source_path=source)
    for event in result["events"]:
        data = event.get("data") or {}
        context = event.get("context") or {}
        assert "turn_index" not in data, "turn_index must not appear in v2 data"
        assert "turn_index" not in context, "turn_index must not appear in v2 context"


def test_original_unchanged(tmp_path):
    import copy

    original_copy = copy.deepcopy(MINIMAL_V1_RECORD)
    migrate_match_payload(MINIMAL_V1_RECORD, source_path=tmp_path / "x.json")
    assert MINIMAL_V1_RECORD == original_copy, "migrate_match_payload must not mutate input"


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def _run_script(args: list[str]) -> tuple[int, str, str]:
    import subprocess

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/migrate_agentic_edge_records_v2.py")] + args,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def test_output_dir_writes_derived_record(tmp_path):
    source = tmp_path / "source" / "match_001.json"
    source.parent.mkdir()
    _write_record(source, MINIMAL_V1_RECORD)

    out_dir = tmp_path / "derived"

    rc, stdout, _ = _run_script([str(source), "--output-dir", str(out_dir)])
    assert rc == 0, stdout

    out_file = out_dir / "match_001.json"
    assert out_file.exists(), "derived record must exist in output-dir"

    derived = _read_record(out_file)
    assert derived["schema_version"] == "2.0"
    assert "migration_provenance" in derived


def test_original_unchanged_after_output_dir(tmp_path):
    source = tmp_path / "match_001.json"
    _write_record(source, MINIMAL_V1_RECORD)
    out_dir = tmp_path / "derived"

    _run_script([str(source), "--output-dir", str(out_dir)])

    original_after = _read_record(source)
    assert original_after["schema_version"] == "1.3", "original must not be modified"


def test_write_refused_for_viewer_matches_without_force(tmp_path):
    # Absolute path to viewer/matches/ — must be refused regardless of cwd
    protected = REPO_ROOT / "viewer" / "matches" / "match_fake.json"
    rc, stdout, stderr = _run_script([str(protected), "--write"])
    assert rc != 0
    combined = stdout + stderr
    assert "viewer/matches" in combined or "protected" in combined


def test_write_refused_for_viewer_matches_from_foreign_cwd(tmp_path):
    # P1: guard must hold even when script is invoked from outside the repo root
    protected = REPO_ROOT / "viewer" / "matches" / "match_fake.json"
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/migrate_agentic_edge_records_v2.py"),
            str(protected),
            "--write",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),  # foreign cwd — not the repo root
    )
    assert result.returncode != 0, "guard must refuse from foreign cwd"
    combined = result.stdout + result.stderr
    assert "viewer/matches" in combined or "protected" in combined


def test_source_artifact_is_absolute_for_relative_input(tmp_path):
    # P2: provenance source_artifact must be absolute even when source path is relative
    source = tmp_path / "match_001.json"
    _write_record(source, MINIMAL_V1_RECORD)

    # Pass a path relative to cwd — the script runs from REPO_ROOT
    import os

    rel_path = os.path.relpath(str(source), str(REPO_ROOT))
    out_dir = tmp_path / "derived"

    rc, stdout, _ = _run_script([rel_path, "--output-dir", str(out_dir)])
    assert rc == 0, stdout

    derived = _read_record(out_dir / "match_001.json")
    artifact = derived["migration_provenance"]["source_artifact"]
    assert Path(artifact).is_absolute(), f"source_artifact must be absolute, got: {artifact!r}"


def test_output_dir_collision_is_refused(tmp_path):
    # P3: two records with the same basename must be detected before any write
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    _write_record(dir_a / "match_001.json", MINIMAL_V1_RECORD)
    _write_record(dir_b / "match_001.json", MINIMAL_V1_RECORD)

    out_dir = tmp_path / "derived"
    rc, stdout, stderr = _run_script(
        [str(dir_a / "match_001.json"), str(dir_b / "match_001.json"), "--output-dir", str(out_dir)]
    )
    assert rc != 0
    combined = stdout + stderr
    assert "collision" in combined


def test_output_dir_and_write_are_mutually_exclusive(tmp_path):
    rc, stdout, stderr = _run_script(["--output-dir", str(tmp_path), "--write"])
    assert rc != 0


def test_dry_run_does_not_write(tmp_path):
    source = tmp_path / "match_001.json"
    _write_record(source, MINIMAL_V1_RECORD)

    rc, stdout, _ = _run_script([str(source)])
    assert rc == 0
    assert "dry run" in stdout

    original_after = _read_record(source)
    assert original_after["schema_version"] == "1.3", "dry run must not modify source"
