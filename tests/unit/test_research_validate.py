"""Unit tests for research markdown completeness validation."""

from __future__ import annotations

import importlib.util
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
