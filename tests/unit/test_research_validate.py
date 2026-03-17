"""Unit tests for research markdown completeness validation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def _load_validator_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "research_validate.py"
    spec = importlib.util.spec_from_file_location("research_validate", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load research_validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    schema_version: int = 2,
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
    _write_results_files(experiment_dir, include_statistics=True, schema_version=2)

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
        schema_version=2,
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
