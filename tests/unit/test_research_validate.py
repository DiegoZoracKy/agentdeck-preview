"""Unit tests for research markdown completeness validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentdeck.research import validate as research_validate
from scripts import research_index as research_index_wrapper
from scripts import research_validate as research_validate_wrapper


def _load_validator_module():
    return research_validate


def _manifest(status: str, matches_completed: int) -> Dict[str, Any]:
    return {
        "status": status,
        "run": {"matches_completed": matches_completed},
    }


def _write_results_files(
    experiment_dir: Path,
    *,
    include_statistics: bool,
    include_position_effect: bool = True,
    include_artifact_validation: bool = True,
    artifact_validation_all_passed: bool = True,
    schema_version: int = 3,
    include_generated_at: bool = True,
    behavioral_profile: Dict[str, Any] | None = None,
    source: Dict[str, Any] | None = None,
) -> None:
    results_payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "experiment_id": experiment_dir.name,
        "source": source or {"recordings_dir": "agentdeck_runs/session_x/records"},
        "summary": {"total_matches": 1},
        "players": [{"name": "Alice"}],
        "matches": [{"match_id": "m1", "winner": "Alice"}],
        "format_strictness": {"overall": {}, "by_player": {}},
        "position_effect": {
            "total_matches": 1,
            "first_player_wins": 1,
            "first_player_win_rate": 1.0,
            "second_player_wins": 0,
            "upset_rate": 0.0,
            "by_player": {"Alice": {}},
        },
    }
    if include_generated_at:
        results_payload["generated_at"] = "2026-03-17T00:00:00Z"
    if include_statistics:
        results_payload["statistics"] = {
            "method": "exact_binomial",
            "confidence_level": 0.95,
            "alpha": 0.05,
            "null_win_rate": 0.5,
            "n_total": 1,
            "n_decisive": 1,
            "players": {"Alice": {"wins": 1}},
        }

    if not include_position_effect:
        results_payload.pop("position_effect", None)

    if include_artifact_validation:
        results_payload["artifact_validation"] = {
            "matches_checked": 1,
            "all_passed": artifact_validation_all_passed,
            "checks": {
                "monotonic_gameplay_timeline": {"passed": 1, "failed": 0},
                "top_level_timing_consistency": {"passed": 1, "failed": 0},
                "prompt_turn_number_coherence": {"passed": 1, "failed": 0},
                "winner_final_state_consistency": {"passed": 1, "failed": 0},
            },
            "failures": [] if artifact_validation_all_passed else [{"message": "bad"}],
        }

    if behavioral_profile is not None:
        results_payload["behavioral_profile"] = behavioral_profile

    (experiment_dir / "results.json").write_text(json.dumps(results_payload), encoding="utf-8")
    (experiment_dir / "results.csv").write_text(
        "match_id,winner,turns,outcome,seed,duration,cost,player_order_source,first_player,players,player_costs\n"
        'm1,Alice,1,win,42,1.0,0.0,console,Alice,"Alice,Bob",{}\n',
        encoding="utf-8",
    )


def _write_phase_matrix(experiment_dir: Path) -> None:
    (experiment_dir / "matrix.yaml").write_text(
        yaml.safe_dump(
            {
                "experiment_id": experiment_dir.name,
                "phase_model": {
                    "preflight_phases": ["P0"],
                    "study_phases": ["P1"],
                },
                "execution_plan": {
                    "preflight": {"phase_id": "P0", "cell_ids": ["p0_smoke"]},
                    "phases": [{"phase_id": "P1", "cell_ids": ["p1_study"]}],
                },
                "cells": [
                    {"id": "p0_smoke", "phase": "P0"},
                    {"id": "p1_study", "phase": "P1"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_docs(experiment_dir: Path, *, placeholder: bool) -> None:
    if placeholder:
        readme_block = "- Topline Winner: TBD"
        analysis_block = "- Sample size (`n`): 0"
    else:
        readme_block = "- Topline Winner: Alice (100.0%)"
        analysis_block = "- Sample size (`n`): 1"

    readme = (
        "# Experiment\n\n"
        "## Factual Snapshot\n"
        "<!-- AUTO_FACTS:BEGIN -->\n"
        f"{readme_block}\n"
        "<!-- AUTO_FACTS:END -->\n"
    )
    analysis = (
        "# Analysis\n\n"
        "## Factual Snapshot\n"
        "<!-- AUTO_FACTS:BEGIN -->\n"
        f"{analysis_block}\n"
        "<!-- AUTO_FACTS:END -->\n"
    )
    (experiment_dir / "README.md").write_text(readme, encoding="utf-8")
    (experiment_dir / "analysis.md").write_text(analysis, encoding="utf-8")


def test_complete_with_placeholders_fails(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_docs(experiment_dir, placeholder=True)

    errors = validator._validate_markdown_facts(experiment_dir, _manifest("complete", 1))
    assert any("README.md AUTO_FACTS block still contains placeholders" in e for e in errors)
    assert any("analysis.md AUTO_FACTS block still contains placeholders" in e for e in errors)


def test_complete_with_factual_blocks_passes(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_docs(experiment_dir, placeholder=False)

    errors = validator._validate_markdown_facts(experiment_dir, _manifest("complete", 1))
    assert errors == []


def test_complete_without_legacy_analysis_md_passes_markdown_facts(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    readme = (
        "# Experiment\n\n"
        "## Factual Snapshot\n"
        "<!-- AUTO_FACTS:BEGIN -->\n"
        "- Topline Winner: Alice (100.0%)\n"
        "<!-- AUTO_FACTS:END -->\n"
    )
    (experiment_dir / "README.md").write_text(readme, encoding="utf-8")

    errors = validator._validate_markdown_facts(experiment_dir, _manifest("complete", 1))
    assert errors == []


def test_planned_allows_placeholders(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_docs(experiment_dir, placeholder=True)

    errors = validator._validate_markdown_facts(experiment_dir, _manifest("planned", 0))
    assert errors == []


def test_complete_results_require_statistics_block(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(experiment_dir, include_statistics=False, schema_version=2)

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert any("missing statistics object" in e for e in errors)


def test_complete_results_with_statistics_block_pass(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(experiment_dir, include_statistics=True, schema_version=3)

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert errors == []


def test_results_pairwise_must_match_direct_matches(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    results_payload: Dict[str, Any] = {
        "schema_version": 3,
        "experiment_id": experiment_dir.name,
        "source": {"recordings_dir": "agentdeck_runs/session_x/records"},
        "summary": {"total_matches": 2},
        "players": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}],
        "matches": [
            {"match_id": "m1", "winner": "Alice", "players": ["Alice", "Bob"]},
            {"match_id": "m2", "winner": "Carol", "players": ["Alice", "Carol"]},
        ],
        "statistics": {
            "method": "exact_binomial",
            "confidence_level": 0.95,
            "alpha": 0.05,
            "null_win_rate": 0.5,
            "n_total": 2,
            "n_decisive": 2,
            "players": {
                "Alice": {"wins": 1},
                "Bob": {"wins": 0},
                "Carol": {"wins": 1},
            },
            "pairwise_comparisons": {
                "Alice_vs_Bob": {
                    "player_a": "Alice",
                    "player_b": "Bob",
                    "comparison_scope": "direct_head_to_head",
                    "wins_a": 2,
                    "wins_b": 0,
                    "head_to_head_matches": 2,
                    "head_to_head_decisive": 2,
                }
            },
        },
        "format_strictness": {"overall": {}, "by_player": {}},
        "position_effect": {
            "total_matches": 2,
            "first_player_wins": 0,
            "first_player_win_rate": 0.0,
            "second_player_wins": 0,
            "upset_rate": 0.0,
            "by_player": {},
        },
        "artifact_validation": {
            "matches_checked": 2,
            "all_passed": True,
            "checks": {
                "monotonic_gameplay_timeline": {"passed": 2, "failed": 0},
                "top_level_timing_consistency": {"passed": 2, "failed": 0},
                "prompt_turn_number_coherence": {"passed": 2, "failed": 0},
                "winner_final_state_consistency": {"passed": 2, "failed": 0},
            },
            "failures": [],
        },
    }
    (experiment_dir / "results.json").write_text(json.dumps(results_payload), encoding="utf-8")
    (experiment_dir / "results.csv").write_text(
        "match_id,winner,turns,outcome,seed,duration,cost,player_order_source,first_player,players,player_costs\n",
        encoding="utf-8",
    )

    errors = validator._validate_results(experiment_dir, {"status": "complete"})

    assert any(".Alice_vs_Bob.wins_a must equal direct wins for player_a (1)" in e for e in errors)
    assert any(".Alice_vs_Bob.head_to_head_matches must equal direct match count (1)" in e for e in errors)


def test_phase_aware_package_results_pass_validation(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "2026-03-26-matrix-demo"
    experiment_dir.mkdir()
    _write_phase_matrix(experiment_dir)
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        schema_version=3,
        source={
            "recordings_dir": "agentdeck_runs/p1_study/session_001/records",
            "aggregation_scope": "study_phases",
            "phases_included": ["P1"],
            "cells_included": ["p1_study"],
        },
    )

    manifest = {"status": "complete", "run": {"matches_completed": 1}}
    errors = validator._validate_results(experiment_dir, manifest)
    assert errors == []


def test_phase_contaminated_package_results_fail_validation(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "2026-03-26-matrix-demo"
    experiment_dir.mkdir()
    _write_phase_matrix(experiment_dir)
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        schema_version=3,
        source={
            "recordings_dir": "agentdeck_runs/p0_smoke/session_001/records",
            "aggregation_scope": "study_phases",
            "phases_included": ["P0", "P1"],
            "cells_included": ["p0_smoke", "p1_study"],
        },
    )

    manifest = {"status": "complete", "run": {"matches_completed": 1}}
    errors = validator._validate_results(experiment_dir, manifest)
    assert any("includes non-study phases" in e for e in errors)
    assert any("includes excluded phases" in e for e in errors)


def test_phase_model_requires_source_scope_metadata(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "2026-03-26-matrix-demo"
    experiment_dir.mkdir()
    _write_phase_matrix(experiment_dir)
    _write_results_files(experiment_dir, include_statistics=True, schema_version=3)

    manifest = {"status": "complete", "run": {"matches_completed": 1}}
    errors = validator._validate_results(experiment_dir, manifest)
    assert any("source.aggregation_scope missing" in e for e in errors)
    assert any("source.phases_included must be list[str]" in e for e in errors)
    assert any("source.cells_included must be list[str]" in e for e in errors)


def test_complete_results_require_position_effect_block(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        include_position_effect=False,
        schema_version=3,
    )

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert any("missing position_effect object" in e for e in errors)


def test_schema_v1_results_do_not_require_extended_metrics(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(experiment_dir, include_statistics=False, schema_version=1)

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert errors == []


def test_schema_v3_results_require_artifact_validation_block(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        include_artifact_validation=False,
        schema_version=3,
    )

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert any("missing artifact_validation object" in e for e in errors)


def test_schema_v3_results_reject_failed_artifact_validation(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        include_artifact_validation=True,
        artifact_validation_all_passed=False,
        schema_version=3,
    )

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert any("all_passed must be true" in e for e in errors)


def test_results_without_generated_at_are_valid_for_deterministic_exports(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        schema_version=3,
        include_generated_at=False,
    )

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert errors == []


def test_declared_results_markdown_required_for_complete_package(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
        "artifacts": {"results_md": "results.md"},
    }
    errors = validator._validate_results_markdown_report(experiment_dir, manifest)
    assert any("results.md missing" in e for e in errors)


def test_declared_results_markdown_passes_with_generated_provenance(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    (experiment_dir / "results.md").write_text(
        "# Results Report\n\n"
        "> Generated deterministically from `results.json`. Authored interpretation belongs under `analysis/`.\n",
        encoding="utf-8",
    )

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
        "artifacts": {"results_md": "results.md"},
    }
    errors = validator._validate_results_markdown_report(experiment_dir, manifest)
    assert errors == []


def test_analysis_namespace_requires_readme_when_declared(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    (experiment_dir / "analysis").mkdir()

    errors = validator._validate_analysis_namespace(
        experiment_dir,
        {"artifacts": {"analysis_dir": "analysis/"}},
    )
    assert any("analysis/README.md missing" in e for e in errors)


def test_analysis_namespace_requires_prefixed_report_dirs(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    analysis_dir = experiment_dir / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "README.md").write_text("# Analysis\n", encoding="utf-8")
    (analysis_dir / "20260428_143001_codex_results_review").mkdir()

    errors = validator._validate_analysis_namespace(
        experiment_dir,
        {"artifacts": {"analysis_dir": "analysis/"}},
    )
    assert any("analysis_YYYYMMDD_HHMMSS" in e for e in errors)

    (analysis_dir / "20260428_143001_codex_results_review").rename(
        analysis_dir / "analysis_20260428_143001_codex_results_review"
    )
    assert (
        validator._validate_analysis_namespace(
            experiment_dir,
            {"artifacts": {"analysis_dir": "analysis/"}},
        )
        == []
    )


def test_behavioral_profile_shape_is_valid_when_present(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        schema_version=3,
        behavioral_profile={
            "schema_version": 2,
            "game_id": "fixed_damage",
            "profile_id": "fixed_damage_behavioral",
            "profile_version": "0.2.0",
            "coverage": {
                "matches_total": 1,
                "matches_evaluable": 1,
                "turns_total": 1,
                "turns_evaluable": 1,
            },
            "aggregate_metrics": {},
            "per_player": {},
            "state_metrics": {},
            "evidence": {
                "aggregate_metrics": {},
                "per_player": {},
                "state_metrics": {},
            },
            "quality_flags": {
                "complete": True,
                "unsupported_metrics": [],
            },
        },
    )

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert errors == []


def test_behavioral_profile_requires_minimum_keys_when_present(tmp_path):
    validator = _load_validator_module()
    experiment_dir = tmp_path / "exp"
    experiment_dir.mkdir()
    _write_results_files(
        experiment_dir,
        include_statistics=True,
        schema_version=3,
        behavioral_profile={
            "schema_version": 2,
            "game_id": "fixed_damage",
        },
    )

    manifest = {
        "status": "complete",
        "run": {"matches_completed": 1},
    }
    errors = validator._validate_results(experiment_dir, manifest)
    assert any("behavioral_profile missing keys" in e for e in errors)


def test_empty_research_tree_is_valid(tmp_path):
    validator_script = Path(__file__).resolve().parents[2] / "scripts" / "research_validate.py"
    index_script = Path(__file__).resolve().parents[2] / "scripts" / "research_index.py"

    research_dir = tmp_path / "research"
    research_dir.mkdir()
    index_path = research_dir / "INDEX.md"

    result = subprocess.run(
        [
            sys.executable,
            str(index_script),
            "--research-dir",
            str(research_dir),
            "--output",
            str(index_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    result = subprocess.run(
        [
            sys.executable,
            str(validator_script),
            "--research-dir",
            str(research_dir),
            "--index",
            str(index_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_validate_main_write_index_defaults_to_research_dir(tmp_path, monkeypatch):
    research_dir = tmp_path / "external-research"
    research_dir.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    result = research_validate.main(["--research-dir", str(research_dir), "--write-index"])

    assert result == 0
    assert (research_dir / "INDEX.md").exists()
    assert not (cwd / "research" / "INDEX.md").exists()


def test_research_index_main_defaults_output_to_research_dir(tmp_path, monkeypatch):
    research_dir = tmp_path / "external-research"
    research_dir.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    result = research_index_wrapper.main(["--research-dir", str(research_dir)])

    assert result == 0
    assert (research_dir / "INDEX.md").exists()
    assert not (cwd / "research" / "INDEX.md").exists()


def test_validate_script_wrapper_reexports_package_surface() -> None:
    assert research_validate_wrapper.main is research_validate.main
    assert research_validate_wrapper._validate_results is research_validate._validate_results
