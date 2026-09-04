import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest

from agentdeck import Evidence, MeasureResult, load_measure, prepare_measure
from agentdeck.research._canonical import sha256_json

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_ROOT = REPO_ROOT / "research" / "references" / "last-potion"
SCRIPT = REFERENCE_ROOT / "scripts" / "build_reference.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("last_potion_reference", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evidence_fixture(probe, result):
    measure = prepare_measure(
        load_measure(REFERENCE_ROOT / probe["study"]["path"], probe["pattern"]["measure_id"])
    )
    provisional = Evidence(
        schema_version=1,
        research_contract_version="0.1",
        study_id=probe["study"]["id"],
        plan_sha256=probe["study"]["plan_sha256"],
        study_intent="confirmatory",
        cell_ids=(probe["pattern"]["dimensions"]["cell"],),
        phases=({"id": "p2", "kind": "study"},),
        corpus_origin_kind="imported",
        corpus_origin_identity_sha256="1" * 64,
        corpus_sha256="2" * 64,
        record_count=432,
        expected_record_count=432,
        corpus_complete=True,
        measure_id="combat-behavior",
        measure_sha256=measure.measure_sha256,
        measure_parameters=measure.declaration.parameters,
        material_environment_sha256=measure.material_environment_sha256,
        assumptions=("synthetic offline builder fixture",),
        derivation_status="complete",
        results=(result,),
        diagnostics=(),
        evidence_sha256="",
    )
    return Evidence(
        **{
            **provisional.__dict__,
            "evidence_sha256": sha256_json(provisional.identity_payload()),
        }
    )


def test_last_potion_probe_resolves_current_sources_and_exact_moment():
    builder = load_builder()
    probe = builder.load_probe(REFERENCE_ROOT / "probe.yaml")

    builder.verify_pinned_sources(probe)

    snapshot = (REFERENCE_ROOT / "snapshot.md").read_text(encoding="utf-8")
    assert "ONE RUN · N=1" in snapshot
    assert "DERIVED PATTERN" in snapshot
    assert "authored interpretation" in snapshot


def test_last_potion_builder_closes_moment_pattern_finding_offline(tmp_path):
    builder = load_builder()
    probe = builder.load_probe(REFERENCE_ROOT / "probe.yaml")
    expected = probe["pattern"]["expected"]
    provisional_result = MeasureResult(
        metric=probe["pattern"]["metric"],
        dimensions=probe["pattern"]["dimensions"],
        status="available",
        value=expected["value"],
        unit=expected["unit"],
        support_count=expected["support"]["count"],
        support_unit=expected["support"]["unit"],
        sources=(),
        diagnostic=None,
    )
    result = replace(
        provisional_result,
        result_sha256=sha256_json(provisional_result.identity_payload()),
    )
    evidence = evidence_fixture(probe, result)
    analysis_root = tmp_path / "analysis"
    evidence_root = analysis_root / "evidence"
    evidence_root.mkdir(parents=True)
    (evidence_root / "combat-behavior.json").write_text(
        json.dumps(evidence.as_dict(), sort_keys=True), encoding="utf-8"
    )

    output = tmp_path / "reference"
    assert builder.main(["--analysis-root", str(analysis_root), "--output", str(output)]) == 0

    payload = json.loads((output / "reference.json").read_text(encoding="utf-8"))
    report = (output / "reference.md").read_text(encoding="utf-8")
    assert payload["moment"]["observation"]["health_before"] == 20
    assert payload["pattern"]["result_sha256"] == result.result_sha256
    assert payload["finding"]["finding"]["citations"][0]["result_sha256"] == result.result_sha256
    assert "ONE RUN · N=1" in report
    assert "DERIVED PATTERN" in report
    assert "Finding remains authored interpretation" in report

    verification = payload["source_verification"]
    assert verification["measures"]["combat-behavior"]["measure_sha256"] == evidence.measure_sha256
    with pytest.raises(ValueError, match="Evidence Measure identity"):
        builder.verify_evidence_binding(
            replace(evidence, measure_sha256="f" * 64), probe, verification
        )
    with pytest.raises(ValueError, match="Evidence material environment"):
        builder.verify_evidence_binding(
            replace(evidence, material_environment_sha256="f" * 64), probe, verification
        )
