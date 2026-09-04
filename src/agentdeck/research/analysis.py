"""Immutable Study analysis bundles over explicit corpora and Measures."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Sequence

from ._canonical import sha256_json, write_json_once
from .evidence import Evidence, RecordCorpus, build_record_corpus, derive_evidence
from .execution import StudyExecution
from .measure import PreparedMeasure, load_measure, prepare_measure
from .study import PreparedStudy, prepare_study


@dataclass(frozen=True)
class StudyAnalysis:
    schema_version: int
    study_id: str
    plan_sha256: str
    cell_ids: tuple[str, ...]
    corpus_sha256: str
    corpus_origin_kind: str
    measures: tuple[PreparedMeasure, ...]
    evidence: tuple[Evidence, ...]
    assumptions: tuple[str, ...]
    analysis_sha256: str
    analysis_root: Path = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cell_ids", tuple(self.cell_ids))
        object.__setattr__(self, "measures", tuple(self.measures))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "study_id": self.study_id,
            "plan_sha256": self.plan_sha256,
            "cell_ids": list(self.cell_ids),
            "corpus_sha256": self.corpus_sha256,
            "corpus_origin_kind": self.corpus_origin_kind,
            "assumptions": list(self.assumptions),
            "derivations": [
                {
                    "measure_id": measure.id,
                    "measure_sha256": measure.measure_sha256,
                    "prepared_measure_path": f"measures/{measure.id}.json",
                    "evidence_sha256": evidence.evidence_sha256,
                    "evidence_path": f"evidence/{measure.id}.json",
                }
                for measure, evidence in zip(self.measures, self.evidence)
            ],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "analysis_sha256": self.analysis_sha256}

    @property
    def receipt_path(self) -> Path:
        return self.analysis_root / "analysis.json"


def analyze_study(
    path: str | Path,
    *,
    cell_ids: Sequence[str],
    measure_ids: Sequence[str],
    output_root: str | Path,
    study_executions: Sequence[StudyExecution] = (),
    imported_manifest: str | Path | None = None,
    assumptions: Sequence[str] = (),
) -> StudyAnalysis:
    """Derive and persist Evidence from one explicit Study/corpus/Measure selection."""

    if not measure_ids or len(set(measure_ids)) != len(measure_ids):
        raise ValueError("Study analysis requires non-empty unique Measure ids")
    prepared_study = prepare_study(path)
    corpus = build_record_corpus(
        prepared_study,
        cell_ids=cell_ids,
        study_executions=study_executions,
        imported_manifest=imported_manifest,
    )
    prepared_measures = tuple(
        prepare_measure(load_measure(prepared_study.definition.package_root, measure_id))
        for measure_id in measure_ids
    )
    evidence = tuple(
        derive_evidence(prepared_study, measure, corpus, assumptions=assumptions)
        for measure in prepared_measures
    )
    provisional = StudyAnalysis(
        schema_version=1,
        study_id=prepared_study.definition.id,
        plan_sha256=prepared_study.plan_sha256,
        cell_ids=corpus.cell_ids,
        corpus_sha256=corpus.corpus_sha256,
        corpus_origin_kind=corpus.origin_kind,
        measures=prepared_measures,
        evidence=evidence,
        assumptions=tuple(assumptions),
        analysis_sha256="",
        analysis_root=Path(),
    )
    analysis_hash = sha256_json(provisional.identity_payload())
    root = (
        Path(output_root).expanduser().resolve()
        / prepared_study.definition.id
        / f"analysis_{analysis_hash[:16]}"
    )
    if root.is_relative_to(prepared_study.definition.package_root.resolve()):
        raise ValueError("Study analysis output must be outside the authored package")
    root.mkdir(parents=True, exist_ok=False)
    analysis = replace(provisional, analysis_sha256=analysis_hash, analysis_root=root)
    write_json_once(root / "prepared-study.json", prepared_study.as_dict())
    write_json_once(root / "corpus.json", corpus.as_dict())
    for measure in prepared_measures:
        write_json_once(root / "measures" / f"{measure.id}.json", measure.as_dict())
    for artifact in evidence:
        write_json_once(root / "evidence" / f"{artifact.measure_id}.json", artifact.as_dict())
    write_json_once(root / "analysis.json", analysis.as_dict())
    return analysis


__all__ = ["StudyAnalysis", "analyze_study"]
