"""Tests for static Match Surface artifact export."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.match_surface_export import export_record  # noqa: E402


def _record_payload() -> dict:
    return {
        "schema_version": "2.0",
        "schema_type": "match",
        "match_id": "match_export",
        "game": "TestGame",
        "players": ["Alice", "Bob"],
        "winner": "Alice",
        "final_state": {"health": {"Alice": 40, "Bob": 0}},
        "seed": 42,
        "migration_provenance": {
            "source_schema_version": "1.3",
            "source_match_id": "match_export",
            "source_artifact": "/source/match_export.json",
            "migration_script": "scripts/migrate_agentic_edge_records_v2.py",
            "migration_target_schema": "2.0",
            "migrated_at": "2026-06-26T00:00:00Z",
        },
        "events": [
            {
                "type": "gameplay",
                "data": {
                    "match_id": "match_export",
                    "mechanic": "turn_based",
                    "phase_index": 0,
                    "player": "Alice",
                    "action": {
                        "value": "ATTACK",
                        "reasoning": "Finish the match.",
                        "metadata": {},
                    },
                    "interaction": {
                        "prompt_text": "Take your turn.",
                        "prompt_blocks": [],
                        "response_text": "ACTION: ATTACK",
                        "usage_info": {
                            "prompt_tokens": 10,
                            "completion_tokens": 5,
                            "tokens": 15,
                        },
                    },
                    "state_before": {"health": {"Alice": 40, "Bob": 20}},
                    "state_after": {"health": {"Alice": 40, "Bob": 0}},
                    "turn_context": {"turn_number": 1, "phase_index": 0},
                },
                "context": {"match_id": "match_export", "phase_index": 0},
                "timestamp": 1000.0,
            }
        ],
        "metadata": {
            "match_id": "match_export",
            "game": "TestGame",
            "players": ["Alice", "Bob"],
            "turns": 1,
        },
    }


def _write_record(tmp_path: Path, payload: dict | None = None) -> Path:
    record_path = tmp_path / "match_export.json"
    record_path.write_text(json.dumps(payload or _record_payload()), encoding="utf-8")
    return record_path


def _write_sidecar(tmp_path: Path, payload: dict) -> Path:
    sidecar_dir = tmp_path / "sidecars"
    sidecar_dir.mkdir()
    (sidecar_dir / "match_export.meta.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return sidecar_dir


def test_export_record_propagates_migration_provenance(tmp_path: Path) -> None:
    record_path = _write_record(tmp_path)
    output_path = export_record(record_path, tmp_path / "surface")

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["schema_type"] == "match_surface"
    assert payload["source"]["provenance"]["source_schema_version"] == "1.3"
    assert payload["source"]["provenance"]["migration_target_schema"] == "2.0"
    assert payload["source"]["match_id"] == "match_export"
    assert payload["frames"][0]["interaction"]["prompt_text"] == "Take your turn."


def test_export_record_imports_sidecar_curation_and_markers(tmp_path: Path) -> None:
    record_path = _write_record(tmp_path)
    sidecar_dir = tmp_path / "sidecars"
    sidecar_dir.mkdir()
    (sidecar_dir / "match_export.meta.json").write_text(
        json.dumps(
            {
                "version": 1,
                "subtitle": "One decisive turn",
                "synopsis": "Alice attacks and ends the match.",
                "highlights": [{"turn": 1, "kind": "turning_point", "label": "Decisive attack"}],
                "transcript": [{"turn": 1, "text": "Do not embed this."}],
            }
        ),
        encoding="utf-8",
    )

    output_path = export_record(record_path, tmp_path / "surface", sidecar_dir=sidecar_dir)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["curation"] == {
        "version": 1,
        "subtitle": "One decisive turn",
        "synopsis": "Alice attacks and ends the match.",
        "source": {
            "type": "curation_sidecar",
            "artifact": "match_export.meta.json",
        },
    }
    assert "transcript" not in payload["curation"]

    marker = payload["markers"][0]
    assert marker["id"] == "curation-highlight-1-1"
    assert marker["phase_index"] == 0
    assert marker["turn"] == 1
    assert marker["source"] == "upstream"
    assert marker["rule"] == "curation_sidecar.highlight"
    assert marker["label"] == "Decisive attack"
    assert marker["data"]["kind"] == "turning_point"
    assert payload["frames"][0]["markers"] == [marker]


def test_export_record_requires_sidecar_when_directory_is_explicit(tmp_path: Path) -> None:
    record_path = _write_record(tmp_path)
    sidecar_dir = tmp_path / "sidecars"
    sidecar_dir.mkdir()

    with pytest.raises(ValueError, match="Missing curation sidecar"):
        export_record(record_path, tmp_path / "surface", sidecar_dir=sidecar_dir)


def test_export_record_rejects_legacy_schema(tmp_path: Path) -> None:
    payload = _record_payload()
    payload["schema_version"] = "1.3"
    record_path = _write_record(tmp_path, payload)

    with pytest.raises(ValueError, match="Recorder 2.0 record"):
        export_record(record_path, tmp_path / "surface")


def test_export_record_rejects_highlight_without_matching_frame(tmp_path: Path) -> None:
    record_path = _write_record(tmp_path)
    sidecar_dir = _write_sidecar(
        tmp_path,
        {
            "version": 1,
            "subtitle": "One decisive turn",
            "synopsis": "Alice attacks and ends the match.",
            "highlights": [{"turn": 2, "label": "Impossible second turn"}],
        },
    )

    with pytest.raises(ValueError, match="does not map to a Match Surface frame"):
        export_record(record_path, tmp_path / "surface", sidecar_dir=sidecar_dir)


def test_export_record_rejects_sidecar_missing_required_field(tmp_path: Path) -> None:
    record_path = _write_record(tmp_path)
    sidecar_dir = _write_sidecar(
        tmp_path,
        {
            "version": 1,
            "subtitle": "One decisive turn",
            "highlights": [{"turn": 1, "label": "Decisive attack"}],
        },
    )

    with pytest.raises(ValueError, match="synopsis"):
        export_record(record_path, tmp_path / "surface", sidecar_dir=sidecar_dir)
