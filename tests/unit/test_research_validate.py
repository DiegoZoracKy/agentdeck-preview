"""Unit tests for research markdown completeness validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

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
) -> None:
    results_payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "experiment_id": experiment_dir.name,
        "source": {"recordings_dir": "agentdeck_runs/session_x/records"},
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
        "m1,Alice,1,win,42,1.0,0.0,console,Alice,\"Alice,Bob\",{}\n",
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
        [sys.executable, str(index_script), "--research-dir", str(research_dir), "--output", str(index_path)],
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

    result = research_validate.main(
        ["--research-dir", str(research_dir), "--write-index"]
    )

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
