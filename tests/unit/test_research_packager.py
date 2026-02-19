"""Tests for session-to-research packager (SPEC-RESEARCH-PACKAGER RP1-RP11)."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from agentdeck.research.packager import build_manifest, package_session


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_session(tmp_path: Path, *, include_model: bool = True) -> Path:
    run_dir = tmp_path / "agentdeck_runs"
    session_dir = run_dir / "session_20260120_000000_abcd12"
    records_dir = session_dir / "records"
    records_dir.mkdir(parents=True)

    player_summaries = [
        {
            "name": "Alice",
            "model": "gpt-4o-mini" if include_model else None,
            "controller": "ActionOnlyController",
            "renderer": "TextRenderer",
        },
        {
            "name": "Bob",
            "model": "gpt-4o-mini",
            "controller": "ActionOnlyController",
            "renderer": "TextRenderer",
        },
    ]

    batch_data = {
        "schema_version": "1.3",
        "schema_type": "batch",
        "batch_id": "batch_test",
        "match_refs": [
            {
                "match_id": "match_001",
                "filename": "match_001.json",
                "winner": "Alice",
                "turns": 3,
                "player_summaries": player_summaries,
            }
        ],
        "metadata": {
            "session_id": session_dir.name,
            "game": "FixedDamageGame",
            "players": ["Alice", "Bob"],
            "matches_planned": 2,
            "matches_completed": 1,
            "started_at": "2026-01-20T00:00:00Z",
            "ended_at": "2026-01-20T00:01:00Z",
            "seeds_used": [123],
            "configuration": {
                "game": {"name": "FixedDamageGame"},
                "players": [
                    {"name": "Alice", "module": "agentdeck.players.openai_player"},
                    {"name": "Bob", "module": "agentdeck.players.openai_player"},
                ],
            },
        },
    }

    match_data = {
        "match_id": "match_001",
        "players": ["Alice", "Bob"],
        "winner": "Alice",
        "seed": 123,
        "metadata": {
            "match": {"turns": 3, "duration": 1.0, "cost": 0.01},
            "player_summaries": player_summaries,
        },
    }

    _write_json(records_dir / "batch_batch_test.json", batch_data)
    _write_json(records_dir / "match_001.json", match_data)

    return session_dir


def _prepare_research_dir(tmp_path: Path) -> Path:
    research_dir = tmp_path / "research"
    templates_src = _repo_root() / "research" / "_templates"
    shutil.copytree(templates_src, research_dir / "_templates")
    return research_dir


def test_build_manifest_infers_required_fields(tmp_path):
    """RP3: Build manifest with required fields inferred from batch metadata."""
    session_dir = _make_session(tmp_path)
    records_dir = session_dir / "records"
    batch_data = json.loads((records_dir / "batch_batch_test.json").read_text(encoding="utf-8"))
    match_files = [records_dir / "match_001.json"]

    manifest = build_manifest(
        template_path=_repo_root() / "research" / "_templates" / "manifest.yaml",
        experiment_id="2026-01-20-demo",
        question="Does Alice beat Bob?",
        batch_data=batch_data,
        match_files=match_files,
    )

    assert manifest["experiment_id"] == "2026-01-20-demo"
    assert manifest["question"] == "Does Alice beat Bob?"
    assert manifest["game"]["name"] == "FixedDamageGame"
    assert manifest["run"]["matches_planned"] == 2
    assert manifest["run"]["matches_completed"] == 1
    assert manifest["run"]["seed_base"] == 123
    assert manifest["players"][0]["provider"] == "openai"
    assert manifest["players"][0]["model"] == "gpt-4o-mini"
    assert manifest["variants"]["models"] == ["gpt-4o-mini"]
    assert manifest["variants"]["controllers"] == ["ActionOnlyController"]


def test_package_session_creates_outputs(tmp_path):
    """RP4/RP5: Export results and update index when packaging."""
    session_dir = _make_session(tmp_path)
    research_dir = _prepare_research_dir(tmp_path)

    result = package_session(
        session_dir=session_dir,
        session_id=None,
        run_dir=tmp_path / "agentdeck_runs",
        research_dir=research_dir,
        experiment_id="2026-01-20-demo",
        question="Does Alice beat Bob?",
        status=None,
        title="Walkthrough Demo",
        include_matrix=False,
        dry_run=False,
    )

    experiment_dir = Path(result["experiment_dir"])
    assert (experiment_dir / "manifest.yaml").exists()
    assert (experiment_dir / "results.json").exists()
    assert (experiment_dir / "results.csv").exists()
    assert (experiment_dir / "recordings" / "README.md").exists()
    assert not (experiment_dir / "matrix.yaml").exists()
    assert (research_dir / "INDEX.md").exists()

    manifest = yaml.safe_load((experiment_dir / "manifest.yaml").read_text(encoding="utf-8"))
    assert "matrix_source" not in manifest["run"]
    assert "matrix_yaml" not in manifest["artifacts"]

    readme = (experiment_dir / "README.md").read_text(encoding="utf-8")
    analysis = (experiment_dir / "analysis.md").read_text(encoding="utf-8")
    assert "Topline Winner: Alice (100.0%)" in readme
    assert "Sample size (`n`): 1" in analysis
    assert "One-paragraph motivation and intended audience." in readme


def test_package_session_include_matrix_keeps_matrix_scaffold(tmp_path):
    """RP9: matrix.yaml is optional by default and opt-in for benchmark grids."""
    session_dir = _make_session(tmp_path)
    research_dir = _prepare_research_dir(tmp_path)

    result = package_session(
        session_dir=session_dir,
        session_id=None,
        run_dir=tmp_path / "agentdeck_runs",
        research_dir=research_dir,
        experiment_id="2026-01-20-demo-matrix",
        question="Does Alice beat Bob?",
        status=None,
        title="Walkthrough Demo Matrix",
        include_matrix=True,
        dry_run=False,
    )

    experiment_dir = Path(result["experiment_dir"])
    assert (experiment_dir / "matrix.yaml").exists()

    manifest = yaml.safe_load((experiment_dir / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["run"]["matrix_source"] == "matrix.yaml"
    assert manifest["artifacts"]["matrix_yaml"] == "matrix.yaml"


def test_package_session_existing_dir_fails(tmp_path):
    """RP6: Fail fast when experiment directory already exists."""
    session_dir = _make_session(tmp_path)
    research_dir = _prepare_research_dir(tmp_path)
    (research_dir / "2026-01-20-demo").mkdir(parents=True)

    with pytest.raises(FileExistsError):
        package_session(
            session_dir=session_dir,
            session_id=None,
            run_dir=tmp_path / "agentdeck_runs",
            research_dir=research_dir,
            experiment_id="2026-01-20-demo",
            question="Does Alice beat Bob?",
            status=None,
            title=None,
            include_matrix=False,
            dry_run=False,
        )


def test_package_session_missing_model_fails(tmp_path):
    """RP7: Fail when required player fields cannot be inferred."""
    session_dir = _make_session(tmp_path, include_model=False)
    records_dir = session_dir / "records"
    batch_data = json.loads((records_dir / "batch_batch_test.json").read_text(encoding="utf-8"))
    match_files = [records_dir / "match_001.json"]

    with pytest.raises(ValueError, match="Missing required player fields"):
        build_manifest(
            template_path=_repo_root() / "research" / "_templates" / "manifest.yaml",
            experiment_id="2026-01-20-demo",
            question="Does Alice beat Bob?",
            batch_data=batch_data,
            match_files=match_files,
        )
