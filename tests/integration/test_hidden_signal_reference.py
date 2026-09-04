"""End-to-end acceptance for the orthogonal Hidden Signal reference."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from agentdeck import prepare_game_research_profile, prepare_study

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY = REPO_ROOT / "research" / "2026-08-29-hidden-signal-information-acquisition"
REFERENCE = REPO_ROOT / "research" / "references" / "hidden-signal"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def test_hidden_signal_closes_fresh_record_to_finding_and_stage(tmp_path: Path) -> None:
    reproducer = _load_module("hidden_signal_reproducer", REFERENCE / "reproduce.py")
    output = tmp_path / "reference"

    assert reproducer.main(["--output", str(output)]) == 0

    reference = json.loads((output / "reference.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "stage" / "manifest.json").read_text(encoding="utf-8"))
    study = prepare_study(STUDY)
    profile = prepare_game_research_profile(STUDY / "research-profile.yaml")

    assert reference["reference"]["revision"] == 3
    assert len(reference["probe_sha256"]) == 64
    assert reference["probe_revision"]["execution_plan_sha256"] == study.plan_sha256
    assert reference["probe_revision"]["game_research_profile_sha256"] == profile.profile_sha256
    assert (
        reference["source_verification"]["profiles"]["hidden-signal"]["profile_sha256"]
        == profile.profile_sha256
    )
    assert reference["execution"]["record_count"] == 40
    assert reference["execution"]["origin_kind"] == "study_execution"
    assert reference["moment"]["label"] == "ONE RUN · N=1"
    assert reference["pattern"]["label"] == "40 RUNS · DERIVED PATTERN"
    assert [item["value"] for item in reference["pattern"]["results"]] == [1.0, 0.0]
    assert reference["finding"]["finding"]["author"]["kind"] == "ai_assisted"
    assert len(reference["finding"]["finding"]["citations"]) == 2

    record_path = output / "stage" / manifest["record"]
    surface_path = output / "stage" / manifest["match_surface"]
    assert hashlib.sha256(record_path.read_bytes()).hexdigest() == manifest["record_sha256"]
    assert hashlib.sha256(surface_path.read_bytes()).hexdigest() == manifest["match_surface_sha256"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    event = record["events"][manifest["moment"]["source"]["event_index"]]
    assert event["data"]["action"]["value"] == "INSPECT"
    assert record["winner"] is None


def test_hidden_signal_measure_uses_unavailable_not_a_neutral_value() -> None:
    measures = _load_module("hidden_signal_measures", STUDY / "measures.py")
    input_without_commitment = SimpleNamespace(
        records=(
            SimpleNamespace(
                cell_id="incomplete-observation",
                record_sha256="a" * 64,
                payload={"events": [], "final_state": {"correct": None}},
            ),
        ),
        parameters={},
    )

    results = measures.inspection_measure(input_without_commitment)

    assert {item["metric"] for item in results} == {
        "inspection-before-commit-rate",
        "correct-commitment-rate",
        "average-decision-turns",
    }
    assert all(item["status"] == "unavailable" for item in results)
    assert all("value" not in item for item in results)
    assert all(item["diagnostic"]["code"] == "measure.no-commitments" for item in results)


def test_bundled_hidden_signal_stage_is_pinned_to_exact_current_artifacts() -> None:
    canonical = REFERENCE / "stage" / "canonical"
    manifest = json.loads((canonical / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["label"] == "ONE RUN · N=1"
    assert (
        hashlib.sha256((canonical / manifest["record"]).read_bytes()).hexdigest()
        == manifest["record_sha256"]
    )
    assert (
        hashlib.sha256((canonical / manifest["match_surface"]).read_bytes()).hexdigest()
        == manifest["match_surface_sha256"]
    )
    surface = json.loads((canonical / manifest["match_surface"]).read_text(encoding="utf-8"))
    assert surface["schema_type"] == "match_surface"
    assert surface["schema_version"] == "0.2"
    assert surface["match"]["game"] == "HiddenSignalGame"
    assert surface["match"]["winner"] is None
