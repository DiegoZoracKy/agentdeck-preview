from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentdeck.research import export as research_export
from scripts import research_export as research_export_wrapper


def _match_payload(match_id: str) -> dict:
    return {
        "schema_version": 1,
        "schema_type": "match_recording",
        "match_id": match_id,
        "game": "FixedDamageGame",
        "players": ["Alpha", "Beta"],
        "winner": "Alpha",
        "final_state": {
            "health": {"Alpha": 80, "Beta": 0},
            "potions": {"Alpha": 3, "Beta": 3},
            "last_action": {"Alpha": "ATTACK", "Beta": "ATTACK"},
            "turn": 3,
        },
        "seed": 42,
        "events": [
            {
                "type": "gameplay",
                "data": {
                    "player": "Alpha",
                    "action": "ATTACK",
                    "state_before": {
                        "health": {"Alpha": 80, "Beta": 80},
                        "potions": {"Alpha": 3, "Beta": 3},
                        "last_action": {"Alpha": None, "Beta": None},
                        "turn": 1,
                    },
                    "state_after": {
                        "health": {"Alpha": 80, "Beta": 60},
                        "potions": {"Alpha": 3, "Beta": 3},
                        "last_action": {"Alpha": "ATTACK", "Beta": None},
                        "turn": 2,
                    },
                    "metadata": {
                        "parser_success": True,
                        "raw_response": "ACTION: ATTACK",
                        "turn_number": 1,
                    },
                    "turn_context": {"turn_number": 1, "player": "Alpha"},
                    "prompt": {"turn_number": 1},
                },
                "timestamp": 1.0,
                "duration": 0.1,
                "context": {
                    "session_id": "session_x",
                    "batch_id": "batch_x",
                    "match_id": match_id,
                    "phase_index": 0,
                    "turn_index": 0,
                    "timestamp": 1.0,
                    "monotonic_time": 1.0,
                },
            }
        ],
        "metadata": {
            "player_summaries": [
                {"name": "Alpha", "controller": "ActionOnlyController"},
                {"name": "Beta", "controller": "ActionOnlyController"},
            ],
            "match": {
                "seed": 42,
                "players": ["Alpha", "Beta"],
                "player_order": [0, 1],
                "player_order_source": "configured",
                "first_player": {"name": "Alpha", "index": 0, "ordered_index": 0},
                "turns": 1,
                "duration": 0.1,
                "duration_seconds": 0.1,
                "cost": 0.0,
                "player_costs": {"Alpha": 0.0, "Beta": 0.0},
                "schema_version": 1,
                "fairness_policy": {
                    "pairing_policy": "paired_side_swap",
                    "first_player_policy": "random",
                },
                "game": {"name": "FixedDamageGame"},
                "started_at": "2026-03-19T00:00:00Z",
                "ended_at": "2026-03-19T00:00:01Z",
                "handshake_completed": True,
                "batch_id": "batch_x",
                "truncated_by_max_turns": False,
            },
            "player_configs": {
                "Alpha": {"module": "agentdeck.players.mock_player", "type": "MockPlayer"},
                "Beta": {"module": "agentdeck.players.mock_player", "type": "MockPlayer"},
            },
        },
        "batch_id": "batch_x",
        "started_at": "2026-03-19T00:00:00Z",
        "ended_at": "2026-03-19T00:00:01Z",
        "duration_seconds": 0.1,
    }


def _write_match(records_dir: Path, match_id: str) -> None:
    records_dir.mkdir(parents=True, exist_ok=True)
    (records_dir / f"{match_id}.json").write_text(
        json.dumps(_match_payload(match_id)),
        encoding="utf-8",
    )


def _write_matrix_experiment(tmp_path: Path, *, cell_ids: list[str]) -> Path:
    experiment_dir = tmp_path / "research" / "2026-03-26-matrix-demo"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "experiment_id": "2026-03-26-matrix-demo",
                "status": "running",
                "question": "demo",
                "game": {
                    "name": "FixedDamageGame",
                    "config": {"attack_damage": 20, "max_health": 100},
                },
                "players": [
                    {"id": "A", "provider": "mock", "model": "MockPlayer"},
                    {"id": "B", "provider": "mock", "model": "MockPlayer"},
                ],
                "run": {"seed_base": 42, "matches_planned": len(cell_ids), "matches_completed": 0},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (experiment_dir / "matrix.yaml").write_text(
        yaml.safe_dump(
            {
                "experiment_id": "2026-03-26-matrix-demo",
                "execution_plan": {
                    "phases": [{"phase_id": "P1", "cell_ids": cell_ids}],
                },
                "cells": [{"id": cell_id, "phase": "P1"} for cell_id in cell_ids],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return experiment_dir


def _pass_artifact_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        research_export,
        "validate_artifact_invariants",
        lambda payloads: {
            "matches_checked": len(payloads),
            "all_passed": True,
            "checks": {
                "monotonic_gameplay_timeline": {"passed": len(payloads), "failed": 0},
                "top_level_timing_consistency": {"passed": len(payloads), "failed": 0},
                "prompt_turn_number_coherence": {"passed": len(payloads), "failed": 0},
                "winner_final_state_consistency": {"passed": len(payloads), "failed": 0},
            },
            "failures": [],
        },
    )


def test_export_results_includes_behavioral_profile(tmp_path, monkeypatch) -> None:
    recordings_dir = tmp_path / "records"
    recordings_dir.mkdir()
    (recordings_dir / "match_001.json").write_text(
        json.dumps(_match_payload("match_001")),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        research_export,
        "validate_artifact_invariants",
        lambda payloads: {
            "matches_checked": len(payloads),
            "all_passed": True,
            "checks": {
                "monotonic_gameplay_timeline": {"passed": len(payloads), "failed": 0},
                "top_level_timing_consistency": {"passed": len(payloads), "failed": 0},
                "prompt_turn_number_coherence": {"passed": len(payloads), "failed": 0},
                "winner_final_state_consistency": {"passed": len(payloads), "failed": 0},
            },
            "failures": [],
        },
    )

    output_dir = tmp_path / "out"
    research_export.export_results(
        recordings_dir,
        output_dir,
        experiment_id="behavioral-export-test",
        include_generated_at=False,
        behavioral_profile_id="auto",
        behavioral_config={"attack_damage": 20, "max_health": 100},
    )

    payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    assert "behavioral_profile" in payload
    assert payload["behavioral_profile"]["profile_id"] == "fixed_damage_behavioral"
    assert payload["behavioral_profile"]["quality_flags"]["complete"] is True
    assert payload["behavioral_profile"]["evidence"]["aggregate_metrics"] == {}
    alpha_evidence = payload["behavioral_profile"]["evidence"]["per_player"]["Alpha"]
    assert "position_policy_delta" in alpha_evidence
    assert "state_action_consistency" in alpha_evidence
    assert "examples" in alpha_evidence["position_policy_delta"]
    assert "examples" in alpha_evidence["state_action_consistency"]
    assert payload["behavioral_profile"]["evidence"]["state_metrics"] == {}


def test_export_matrix_cells_uses_discovered_session_recordings(tmp_path, monkeypatch) -> None:
    _pass_artifact_validation(monkeypatch)
    experiment_dir = _write_matrix_experiment(tmp_path, cell_ids=["p1_c01_demo"])
    records_dir = (
        experiment_dir
        / "agentdeck_runs"
        / "p1_c01_demo"
        / "session_001"
        / "records"
    )
    _write_match(records_dir, "match_001")

    exported = research_export.export_matrix_cells(
        experiment_dir,
        matrix_path=None,
        phase="P1",
        cell_ids=None,
        include_generated_at=False,
    )

    assert exported == 1
    payload = json.loads(
        (experiment_dir / "artifacts" / "p1_c01_demo" / "results.json").read_text(encoding="utf-8")
    )
    assert payload["experiment_id"] == "2026-03-26-matrix-demo::p1_c01_demo"
    assert payload["source"]["recordings_dir"] == str(records_dir.resolve())


def test_export_matrix_package_prefers_canonical_cell_artifacts(tmp_path, monkeypatch) -> None:
    _pass_artifact_validation(monkeypatch)
    experiment_dir = _write_matrix_experiment(tmp_path, cell_ids=["p1_c01_demo"])
    canonical_dir = (
        experiment_dir
        / "agentdeck_runs"
        / "p1_c01_demo"
        / "session_001"
        / "records"
    )
    extra_dir = (
        experiment_dir
        / "agentdeck_runs"
        / "p1_c01_demo"
        / "session_002"
        / "records"
    )
    _write_match(canonical_dir, "match_001")
    _write_match(extra_dir, "match_002")

    artifact_dir = experiment_dir / "artifacts" / "p1_c01_demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "results.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "experiment_id": "2026-03-26-matrix-demo::p1_c01_demo",
                "source": {"recordings_dir": str(canonical_dir.resolve())},
            }
        ),
        encoding="utf-8",
    )

    research_export.export_matrix_package(
        experiment_dir,
        matrix_path=None,
        include_generated_at=False,
    )

    payload = json.loads((experiment_dir / "results.json").read_text(encoding="utf-8"))
    assert payload["source"]["recordings_dir"] == str(canonical_dir.resolve())
    assert payload["summary"]["total_matches"] == 2
    assert payload["source"]["recordings_dirs"] == [
        str(canonical_dir.resolve()),
        str(extra_dir.resolve()),
    ]


def test_export_matrix_package_falls_back_to_session_discovery(tmp_path, monkeypatch) -> None:
    _pass_artifact_validation(monkeypatch)
    experiment_dir = _write_matrix_experiment(tmp_path, cell_ids=["p1_c01_demo"])
    records_dir = (
        experiment_dir
        / "agentdeck_runs"
        / "p1_c01_demo"
        / "session_001"
        / "records"
    )
    _write_match(records_dir, "match_001")

    research_export.export_matrix_package(
        experiment_dir,
        matrix_path=None,
        include_generated_at=False,
    )

    payload = json.loads((experiment_dir / "results.json").read_text(encoding="utf-8"))
    assert payload["source"]["recordings_dir"] == str(records_dir.resolve())
    assert payload["summary"]["total_matches"] == 1


@pytest.mark.parametrize("dead_kind", ["missing", "empty"])
def test_export_matrix_package_ignores_unusable_canonical_sources(
    tmp_path, monkeypatch, dead_kind: str
) -> None:
    _pass_artifact_validation(monkeypatch)
    experiment_dir = _write_matrix_experiment(tmp_path, cell_ids=["p1_c01_demo"])
    discovered_dir = (
        experiment_dir
        / "agentdeck_runs"
        / "p1_c01_demo"
        / "session_001"
        / "records"
    )
    _write_match(discovered_dir, "match_001")

    dead_canonical_dir = tmp_path / "stale_records"
    if dead_kind == "empty":
        dead_canonical_dir.mkdir(parents=True, exist_ok=True)

    artifact_dir = experiment_dir / "artifacts" / "p1_c01_demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "results.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "experiment_id": "2026-03-26-matrix-demo::p1_c01_demo",
                "source": {"recordings_dir": str(dead_canonical_dir.resolve())},
            }
        ),
        encoding="utf-8",
    )

    research_export.export_matrix_package(
        experiment_dir,
        matrix_path=None,
        include_generated_at=False,
    )

    payload = json.loads((experiment_dir / "results.json").read_text(encoding="utf-8"))
    assert payload["source"]["recordings_dir"] == str(discovered_dir.resolve())
    assert payload["source"].get("recordings_dirs") in (None, [str(discovered_dir.resolve())])
    assert payload["summary"]["total_matches"] == 1


def test_recordings_dirs_for_cell_deduplicates_canonical_and_discovered_paths(
    tmp_path, monkeypatch
) -> None:
    _pass_artifact_validation(monkeypatch)
    experiment_dir = _write_matrix_experiment(tmp_path, cell_ids=["p1_c01_demo"])
    records_dir = (
        experiment_dir
        / "agentdeck_runs"
        / "p1_c01_demo"
        / "session_001"
        / "records"
    )
    _write_match(records_dir, "match_001")

    artifact_dir = experiment_dir / "artifacts" / "p1_c01_demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "results.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "experiment_id": "2026-03-26-matrix-demo::p1_c01_demo",
                "source": {"recordings_dir": str(records_dir.resolve())},
            }
        ),
        encoding="utf-8",
    )

    merged = research_export.recordings_dirs_for_cell(experiment_dir, "p1_c01_demo")
    assert merged == [records_dir.resolve()]


def test_export_matrix_cells_fails_fast_for_unknown_cell(tmp_path, monkeypatch) -> None:
    _pass_artifact_validation(monkeypatch)
    experiment_dir = _write_matrix_experiment(tmp_path, cell_ids=["p1_c01_demo"])

    with pytest.raises(SystemExit, match="No cells selected"):
        research_export.export_matrix_cells(
            experiment_dir,
            matrix_path=None,
            phase=None,
            cell_ids={"missing_cell"},
            include_generated_at=False,
        )


def test_export_matrix_cells_skips_cells_without_recordings(tmp_path, monkeypatch) -> None:
    _pass_artifact_validation(monkeypatch)
    experiment_dir = _write_matrix_experiment(tmp_path, cell_ids=["p1_c01_demo"])

    exported = research_export.export_matrix_cells(
        experiment_dir,
        matrix_path=None,
        phase="P1",
        cell_ids=None,
        include_generated_at=False,
    )

    assert exported == 0
    assert not (experiment_dir / "artifacts" / "p1_c01_demo").exists()


def test_export_results_no_generated_at_is_deterministic(tmp_path, monkeypatch) -> None:
    recordings_dir = tmp_path / "records"
    _write_match(recordings_dir, "match_001")
    _pass_artifact_validation(monkeypatch)

    output_a = tmp_path / "out_a"
    output_b = tmp_path / "out_b"

    research_export.export_results(
        recordings_dir,
        output_a,
        experiment_id="deterministic-export-test",
        include_generated_at=False,
        behavioral_profile_id="auto",
        behavioral_config={"attack_damage": 20, "max_health": 100},
    )
    research_export.export_results(
        recordings_dir,
        output_b,
        experiment_id="deterministic-export-test",
        include_generated_at=False,
        behavioral_profile_id="auto",
        behavioral_config={"attack_damage": 20, "max_health": 100},
    )

    assert (output_a / "results.json").read_text(encoding="utf-8") == (
        output_b / "results.json"
    ).read_text(encoding="utf-8")


def test_script_wrapper_reexports_package_surface() -> None:
    assert research_export_wrapper.export_results is research_export.export_results
    assert research_export_wrapper.main is research_export.main
