import json
from pathlib import Path

import pytest
import yaml

from agentdeck import (
    EvidenceCitation,
    FindingAuthor,
    FindingDeclaration,
    analyze_study,
    build_record_corpus,
    derive_evidence,
    execute_prepared_study,
    load_finding,
    load_evidence,
    load_game_research_profile,
    load_measure,
    prepare_finding,
    prepare_game_research_profile,
    prepare_measure,
    prepare_study,
    render_finding_markdown,
    select_study,
    load_study_execution,
    write_finding_report,
)
from test_study import write_study

CUSTOM_MEASURE = """
def observe_rate(measure_input):
    results = []
    for cell in sorted({record.cell_id for record in measure_input.records}):
        records = [record for record in measure_input.records if record.cell_id == cell]
        observed = [record for record in records if record.payload["final_state"]["action"] == "OBSERVE"]
        results.append({
            "metric": "observe-rate",
            "dimensions": {"cell": cell},
            "status": "available",
            "value": len(observed) / len(records),
            "unit": "proportion",
            "support": {"count": len(records), "unit": "records"},
            "sources": [{
                "record_sha256": record.record_sha256,
                "pointer": "/final_state/action",
            } for record in observed],
        })
    return results
"""


def _write_research_files(root: Path) -> None:
    (root / "measures.py").write_text(CUSTOM_MEASURE, encoding="utf-8")
    (root / "measures.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "measures": [
                    {
                        "id": "observe-rate",
                        "implementation": {
                            "entrypoint": "measures.py:observe_rate",
                            "artifacts": [],
                        },
                        "parameters": {},
                        "material_distributions": [],
                    },
                    {
                        "id": "record-count",
                        "implementation": {"builtin": "record-count"},
                        "parameters": {},
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "research-profile.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "profile": {
                    "id": "observation-game",
                    "version": 1,
                    "game": {"name": "ObservationGame"},
                    "summary": "One decision under an explicit information condition.",
                },
                "opportunities": [
                    {
                        "id": "information-sensitivity",
                        "question": "Does visible information change the chosen action?",
                        "mechanism": "The same role acts under two information surfaces.",
                        "observables": ["final_state.action"],
                        "boundaries": ["Does not establish behavior outside this Game."],
                    }
                ],
                "operationalizations": [
                    {
                        "id": "observe-rate",
                        "opportunity": "information-sensitivity",
                        "measure": {"source": "measures.yaml", "id": "observe-rate"},
                        "required_observables": ["final_state.action"],
                        "limitations": ["The fixture policy always chooses OBSERVE."],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _execute_study(tmp_path: Path):
    root = tmp_path / "study"
    manifest = write_study(root)
    _write_research_files(root)
    prepared = prepare_study(manifest)
    selection = select_study(prepared, all_groups=True)
    execution = execute_prepared_study(
        manifest,
        prepared,
        selection,
        output_root=tmp_path / "runs",
    )
    return root, prepared, execution


def test_game_research_profile_prepares_measure_without_execution_authority(tmp_path):
    root = write_study(tmp_path / "study").parent
    _write_research_files(root)

    loaded = load_game_research_profile(root)
    prepared = prepare_game_research_profile(root)

    assert loaded.game_name == "ObservationGame"
    assert prepared.profile_sha256
    assert prepared.as_dict()["operationalizations"] == [
        {
            "id": "observe-rate",
            "assurance": "prepared",
            "measure_sha256": prepared.prepared_measures["observe-rate"].measure_sha256,
        }
    ]
    assert "calibrated" not in json.dumps(prepared.as_dict())


def test_complete_no_winner_study_reaches_evidence_and_authored_finding(tmp_path):
    root, study, execution = _execute_study(tmp_path)
    source_hashes = {
        path: path.read_bytes()
        for path in execution.records[0].path.parents[2].rglob("match_*.json")
    }
    corpus = build_record_corpus(
        study,
        cell_ids=["partial", "full"],
        study_executions=[execution],
    )
    prepared_measure = prepare_measure(load_measure(root, "observe-rate"))
    evidence = derive_evidence(
        study,
        prepared_measure,
        corpus,
        assumptions=["The fixture's OBSERVE action is the declared observation."],
    )

    assert corpus.complete is True
    assert len(corpus.records) == 4
    assert evidence.derivation_status == "complete"
    assert len(evidence.results) == 2
    assert {result.value for result in evidence.results} == {1.0}
    assert all(result.metric == "observe-rate" for result in evidence.results)
    first = evidence.results[0]
    declaration = FindingDeclaration(
        id="observe-policy-executed",
        claim="The declared fixture policy selected OBSERVE in both information conditions.",
        author=FindingAuthor("AgentDeck acceptance fixture", "human"),
        citations=(EvidenceCitation("supports", evidence.evidence_sha256, first.result_sha256),),
        limitations=("This validates the Research chain, not model information sensitivity.",),
    )
    finding = prepare_finding(declaration, [evidence])
    report = render_finding_markdown(finding, [evidence])

    assert finding.finding_sha256 in report
    assert evidence.evidence_sha256 in report
    assert 'dimensions `{"cell":"full"}`' in report
    assert "origin `study_execution`" in report
    assert "authored interpretation" in report
    assert all(path.read_bytes() == content for path, content in source_hashes.items())


def test_same_corpus_supports_two_measures_without_changing_identity(tmp_path):
    root, study, execution = _execute_study(tmp_path)
    corpus = build_record_corpus(
        study,
        cell_ids=["partial", "full"],
        study_executions=[execution],
    )
    first = derive_evidence(study, prepare_measure(load_measure(root, "observe-rate")), corpus)
    second = derive_evidence(study, prepare_measure(load_measure(root, "record-count")), corpus)

    assert first.corpus_sha256 == second.corpus_sha256 == corpus.corpus_sha256
    assert first.measure_sha256 != second.measure_sha256
    assert {result.value for result in second.results} == {2}


def test_finding_yaml_requires_exact_result_citation(tmp_path):
    root, study, execution = _execute_study(tmp_path)
    corpus = build_record_corpus(
        study,
        cell_ids=["partial", "full"],
        study_executions=[execution],
    )
    evidence = derive_evidence(study, prepare_measure(load_measure(root, "record-count")), corpus)
    result = evidence.results[0]
    (root / "findings.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "findings": [
                    {
                        "id": "complete-fixture",
                        "claim": "The selected Cell contains the planned number of Records.",
                        "author": {"name": "Fixture author", "kind": "human"},
                        "citations": [
                            {
                                "relation": "supports",
                                "evidence": f"sha256:{evidence.evidence_sha256}",
                                "result": f"sha256:{result.result_sha256}",
                            }
                        ],
                        "limitations": ["This is artifact completeness, not behavioral evidence."],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    finding = prepare_finding(load_finding(root, "complete-fixture"), [evidence])
    assert finding.declaration.citations[0].result_sha256 == result.result_sha256


def test_analysis_bundle_and_receipt_loaders_preserve_exact_identities(tmp_path):
    root, study, execution = _execute_study(tmp_path)
    loaded_execution = load_study_execution(execution.receipt_path)

    assert loaded_execution.as_dict() == execution.as_dict()

    analysis = analyze_study(
        root,
        cell_ids=["partial", "full"],
        measure_ids=["observe-rate", "record-count"],
        study_executions=[loaded_execution],
        assumptions=["OBSERVE is the declared fixture observation."],
        output_root=tmp_path / "analysis",
    )

    assert analysis.receipt_path.is_file()
    assert (analysis.analysis_root / "corpus.json").is_file()
    assert [item.measure_id for item in analysis.evidence] == [
        "observe-rate",
        "record-count",
    ]
    for artifact in analysis.evidence:
        loaded = load_evidence(analysis.analysis_root / "evidence" / f"{artifact.measure_id}.json")
        assert loaded.as_dict() == artifact.as_dict()

    with pytest.raises(FileExistsError):
        analyze_study(
            root,
            cell_ids=["partial", "full"],
            measure_ids=["observe-rate", "record-count"],
            study_executions=[loaded_execution],
            assumptions=["OBSERVE is the declared fixture observation."],
            output_root=tmp_path / "analysis",
        )


def test_finding_report_is_authored_resolved_and_write_once(tmp_path):
    root, study, execution = _execute_study(tmp_path)
    corpus = build_record_corpus(
        study,
        cell_ids=["partial", "full"],
        study_executions=[execution],
    )
    evidence = derive_evidence(
        study,
        prepare_measure(load_measure(root, "record-count")),
        corpus,
    )
    result = evidence.results[0]
    declaration = FindingDeclaration(
        id="complete-fixture",
        claim="The selected Cell contains the planned number of Records.",
        author=FindingAuthor("Fixture author", "human"),
        citations=(
            EvidenceCitation(
                "supports",
                evidence.evidence_sha256,
                result.result_sha256,
            ),
        ),
        limitations=("This is artifact completeness, not behavioral evidence.",),
    )
    output = tmp_path / "report"
    finding, finding_path, report_path = write_finding_report(
        declaration,
        [evidence],
        output=output,
    )

    assert json.loads(finding_path.read_text(encoding="utf-8"))["finding_sha256"] == (
        finding.finding_sha256
    )
    assert evidence.evidence_sha256 in report_path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_finding_report(declaration, [evidence], output=output)
