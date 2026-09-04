"""Exact Record corpora and deterministic Evidence artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence, cast

import yaml

from ._canonical import freeze_json, sha256_file, sha256_json, thaw_json
from .execution import StudyExecution, StudyRecordReceipt
from .measure import (
    MeasureDiagnostic,
    MeasureResult,
    PreparedMeasure,
    SourceLocator,
    evaluate_measure,
)
from .study import PreparedStudy, RESEARCH_CONTRACT_VERSION


@dataclass(frozen=True)
class EvidenceDiagnostic:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class CorpusRecord:
    record_sha256: str
    schema_version: str
    match_id: str
    source_identity: str
    relative_path: str
    study_id: str
    plan_sha256: str
    phase_id: str
    phase_kind: str
    execution_group_id: str
    assembly_run: str
    cell_id: str
    match_index: int
    effective_seed: int
    binding_authority: str
    payload: Mapping[str, Any] = field(compare=False, repr=False)
    path: Path = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_json(self.payload))

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_sha256": self.record_sha256,
            "schema_version": self.schema_version,
            "match_id": self.match_id,
            "source_identity": self.source_identity,
            "path": self.relative_path,
            "study_id": self.study_id,
            "plan_sha256": self.plan_sha256,
            "phase_id": self.phase_id,
            "phase_kind": self.phase_kind,
            "execution_group_id": self.execution_group_id,
            "assembly_run": self.assembly_run,
            "cell_id": self.cell_id,
            "match_index": self.match_index,
            "effective_seed": self.effective_seed,
            "binding_authority": self.binding_authority,
        }


@dataclass(frozen=True)
class RecordCorpus:
    schema_version: int
    study_id: str
    plan_sha256: str
    cell_ids: tuple[str, ...]
    origin_kind: str
    origin_identity_sha256: str
    origin: Mapping[str, Any]
    expected_records: Mapping[str, int]
    records: tuple[CorpusRecord, ...]
    complete: bool
    diagnostics: tuple[EvidenceDiagnostic, ...]
    corpus_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "cell_ids", tuple(self.cell_ids))
        object.__setattr__(self, "origin", freeze_json(self.origin))
        object.__setattr__(self, "expected_records", MappingProxyType(dict(self.expected_records)))
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "study_binding": {
                "study_id": self.study_id,
                "plan_sha256": self.plan_sha256,
                "cells": list(self.cell_ids),
            },
            "origin": thaw_json(self.origin),
            "origin_identity_sha256": self.origin_identity_sha256,
            "expected_records": dict(self.expected_records),
            "records": [record.as_dict() for record in self.records],
            "complete": self.complete,
            "diagnostics": [item.as_dict() for item in self.diagnostics],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "corpus_sha256": self.corpus_sha256}


@dataclass(frozen=True)
class Evidence:
    schema_version: int
    research_contract_version: str
    study_id: str
    plan_sha256: str
    study_intent: str
    cell_ids: tuple[str, ...]
    phases: tuple[Mapping[str, str], ...]
    corpus_origin_kind: str
    corpus_origin_identity_sha256: str
    corpus_sha256: str
    record_count: int
    expected_record_count: int
    corpus_complete: bool
    measure_id: str
    measure_sha256: str
    measure_parameters: Mapping[str, Any]
    material_environment_sha256: str
    assumptions: tuple[str, ...]
    derivation_status: str
    results: tuple[MeasureResult, ...]
    diagnostics: tuple[EvidenceDiagnostic, ...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "cell_ids", tuple(self.cell_ids))
        object.__setattr__(self, "phases", tuple(freeze_json(item) for item in self.phases))
        object.__setattr__(self, "measure_parameters", freeze_json(self.measure_parameters))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "results", tuple(self.results))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "research_contract_version": self.research_contract_version,
            "study": {
                "id": self.study_id,
                "plan_sha256": self.plan_sha256,
                "intent": self.study_intent,
                "cells": list(self.cell_ids),
                "phases": [thaw_json(item) for item in self.phases],
            },
            "corpus": {
                "origin_kind": self.corpus_origin_kind,
                "origin_identity_sha256": self.corpus_origin_identity_sha256,
                "corpus_sha256": self.corpus_sha256,
                "record_count": self.record_count,
                "expected_record_count": self.expected_record_count,
                "complete": self.corpus_complete,
            },
            "measure": {
                "id": self.measure_id,
                "measure_sha256": self.measure_sha256,
                "parameters": thaw_json(self.measure_parameters),
                "material_environment_sha256": self.material_environment_sha256,
            },
            "assumptions": list(self.assumptions),
            "derivation_status": self.derivation_status,
            "results": [result.as_dict() for result in self.results],
            "diagnostics": [item.as_dict() for item in self.diagnostics],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "evidence_sha256": self.evidence_sha256}

    def result(self, result_sha256: str) -> MeasureResult:
        matches = [item for item in self.results if item.result_sha256 == result_sha256]
        if len(matches) != 1:
            raise KeyError(f"Evidence result does not resolve exactly once: {result_sha256}")
        return matches[0]


def build_record_corpus(
    study: PreparedStudy,
    *,
    cell_ids: Sequence[str],
    study_executions: Sequence[StudyExecution] = (),
    imported_manifest: str | Path | None = None,
) -> RecordCorpus:
    """Build one explicit Measure-independent Record corpus."""

    selected_cells = _selected_cells(study, cell_ids)
    current = bool(study_executions)
    imported = imported_manifest is not None
    if current == imported:
        raise ValueError("RecordCorpus requires exactly one origin kind")
    expected = _expected_records(study, selected_cells)
    if current:
        origin, entries = _current_entries(study, selected_cells, study_executions)
        authority = "execution_receipt"
    else:
        assert imported_manifest is not None
        origin, entries = _imported_entries(study, selected_cells, imported_manifest)
        authority = "authored_import_manifest"

    records = tuple(
        _load_corpus_record(study, entry, origin["identity_sha256"], authority) for entry in entries
    )
    _validate_unique_records(records)
    cell_order = {cell_id: index for index, cell_id in enumerate(selected_cells)}
    records = tuple(
        sorted(
            records,
            key=lambda item: (cell_order[item.cell_id], item.match_index, item.record_sha256),
        )
    )
    diagnostics: list[EvidenceDiagnostic] = []
    complete = True
    for cell_id in selected_cells:
        observed = [item for item in records if item.cell_id == cell_id]
        expected_count = expected[cell_id]
        observed_slots = [item.match_index for item in observed]
        expected_slots = list(range(expected_count))
        if observed_slots != expected_slots:
            complete = False
            diagnostics.append(
                EvidenceDiagnostic(
                    "corpus.record-count-mismatch",
                    f"Cell {cell_id!r} expected slots {expected_slots}; observed {observed_slots}",
                )
            )
    identity = {
        "schema_version": 1,
        "study_binding": {
            "study_id": study.definition.id,
            "plan_sha256": study.plan_sha256,
            "cells": list(selected_cells),
        },
        "origin": origin,
        "origin_identity_sha256": origin["identity_sha256"],
        "expected_records": expected,
        "records": [record.as_dict() for record in records],
        "complete": complete,
        "diagnostics": [item.as_dict() for item in diagnostics],
    }
    return RecordCorpus(
        schema_version=1,
        study_id=study.definition.id,
        plan_sha256=study.plan_sha256,
        cell_ids=selected_cells,
        origin_kind=origin["kind"],
        origin_identity_sha256=origin["identity_sha256"],
        origin=origin,
        expected_records=expected,
        records=records,
        complete=complete,
        diagnostics=tuple(diagnostics),
        corpus_sha256=sha256_json(identity),
    )


def derive_evidence(
    study: PreparedStudy,
    measure: PreparedMeasure,
    corpus: RecordCorpus,
    *,
    assumptions: Sequence[str] = (),
) -> Evidence:
    """Bind an exact corpus and deterministic MeasureOutput into Evidence."""

    if corpus.study_id != study.definition.id or corpus.plan_sha256 != study.plan_sha256:
        raise ValueError("RecordCorpus is not bound to the supplied PreparedStudy")
    authored_assumptions = tuple(assumptions)
    if any(not isinstance(item, str) or not item.strip() for item in authored_assumptions):
        raise ValueError("Evidence assumptions must be non-empty authored strings")
    phases = tuple(
        {"id": phase.id, "kind": phase.kind}
        for phase in study.definition.phases
        if any(
            cell.id in corpus.cell_ids
            and cell.execution_group
            in {group.id for group in study.definition.execution_groups if group.phase == phase.id}
            for cell in study.definition.cells
        )
    )
    if corpus.complete:
        output = evaluate_measure(measure, corpus)
        status = "complete"
        results = output.results
        diagnostics = tuple(
            EvidenceDiagnostic(item.code, item.message) for item in output.diagnostics
        )
    else:
        status = "unavailable"
        results = ()
        diagnostics = corpus.diagnostics or (
            EvidenceDiagnostic("corpus.incomplete", "Record corpus is incomplete"),
        )
    provisional = Evidence(
        schema_version=1,
        research_contract_version=RESEARCH_CONTRACT_VERSION,
        study_id=study.definition.id,
        plan_sha256=study.plan_sha256,
        study_intent=study.definition.intent,
        cell_ids=corpus.cell_ids,
        phases=phases,
        corpus_origin_kind=corpus.origin_kind,
        corpus_origin_identity_sha256=corpus.origin_identity_sha256,
        corpus_sha256=corpus.corpus_sha256,
        record_count=len(corpus.records),
        expected_record_count=sum(corpus.expected_records.values()),
        corpus_complete=corpus.complete,
        measure_id=measure.id,
        measure_sha256=measure.measure_sha256,
        measure_parameters=measure.declaration.parameters,
        material_environment_sha256=measure.material_environment_sha256,
        assumptions=authored_assumptions,
        derivation_status=status,
        results=results,
        diagnostics=diagnostics,
        evidence_sha256="",
    )
    return replace(
        provisional,
        evidence_sha256=sha256_json(provisional.identity_payload()),
    )


def load_evidence(path: str | Path) -> Evidence:
    """Load and verify one canonical Evidence artifact."""

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"Evidence artifact is missing: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Evidence artifact could not be read: {exc}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("Evidence schema_version must equal 1")
    expected = {
        "schema_version",
        "research_contract_version",
        "study",
        "corpus",
        "measure",
        "assumptions",
        "derivation_status",
        "results",
        "diagnostics",
        "evidence_sha256",
    }
    if set(payload) != expected:
        raise ValueError("Evidence artifact has an unsupported shape")
    study_value = _load_mapping(payload.get("study"), "study")
    corpus_value = _load_mapping(payload.get("corpus"), "corpus")
    measure_value = _load_mapping(payload.get("measure"), "measure")
    phases_value = study_value.get("phases")
    if not isinstance(phases_value, list) or any(
        not isinstance(item, Mapping) for item in phases_value
    ):
        raise ValueError("Evidence study.phases must be a list of mappings")
    cells = _load_text_tuple(study_value.get("cells"), "study.cells")
    assumptions = _load_text_tuple(payload.get("assumptions"), "assumptions", allow_empty=True)
    results_value = payload.get("results")
    if not isinstance(results_value, list):
        raise ValueError("Evidence results must be a list")
    results = tuple(_load_measure_result(item, index) for index, item in enumerate(results_value))
    diagnostics_value = payload.get("diagnostics")
    if not isinstance(diagnostics_value, list):
        raise ValueError("Evidence diagnostics must be a list")
    diagnostics = tuple(
        EvidenceDiagnostic(
            _load_text(
                _load_mapping(item, f"diagnostics[{index}]").get("code"),
                f"diagnostics[{index}].code",
            ),
            _load_text(
                _load_mapping(item, f"diagnostics[{index}]").get("message"),
                f"diagnostics[{index}].message",
            ),
        )
        for index, item in enumerate(diagnostics_value)
    )
    corpus_complete = corpus_value.get("complete")
    if not isinstance(corpus_complete, bool):
        raise ValueError("Evidence corpus.complete must be boolean")
    artifact = Evidence(
        schema_version=1,
        research_contract_version=_load_text(
            payload.get("research_contract_version"), "research_contract_version"
        ),
        study_id=_load_text(study_value.get("id"), "study.id"),
        plan_sha256=_load_sha(study_value.get("plan_sha256"), "study.plan_sha256"),
        study_intent=_load_text(study_value.get("intent"), "study.intent"),
        cell_ids=cells,
        phases=tuple(dict(item) for item in phases_value),
        corpus_origin_kind=_load_text(corpus_value.get("origin_kind"), "corpus.origin_kind"),
        corpus_origin_identity_sha256=_load_sha(
            corpus_value.get("origin_identity_sha256"), "corpus.origin_identity_sha256"
        ),
        corpus_sha256=_load_sha(corpus_value.get("corpus_sha256"), "corpus.corpus_sha256"),
        record_count=_load_nonnegative_integer(
            corpus_value.get("record_count"), "corpus.record_count"
        ),
        expected_record_count=_load_nonnegative_integer(
            corpus_value.get("expected_record_count"), "corpus.expected_record_count"
        ),
        corpus_complete=corpus_complete,
        measure_id=_load_text(measure_value.get("id"), "measure.id"),
        measure_sha256=_load_sha(measure_value.get("measure_sha256"), "measure.measure_sha256"),
        measure_parameters=dict(
            _load_mapping(measure_value.get("parameters"), "measure.parameters")
        ),
        material_environment_sha256=_load_sha(
            measure_value.get("material_environment_sha256"), "measure.material_environment_sha256"
        ),
        assumptions=assumptions,
        derivation_status=_load_text(payload.get("derivation_status"), "derivation_status"),
        results=results,
        diagnostics=diagnostics,
        evidence_sha256=_load_sha(payload.get("evidence_sha256"), "evidence_sha256"),
    )
    if sha256_json(artifact.identity_payload()) != artifact.evidence_sha256:
        raise ValueError("Evidence identity does not match its payload")
    return artifact


def _load_measure_result(value: Any, index: int) -> MeasureResult:
    location = f"results[{index}]"
    data = _load_mapping(value, location)
    allowed = {
        "metric",
        "dimensions",
        "status",
        "value",
        "unit",
        "support",
        "sources",
        "diagnostic",
        "result_sha256",
    }
    if set(data) - allowed:
        raise ValueError(f"Evidence {location} contains unsupported fields")
    status = _load_text(data.get("status"), f"{location}.status")
    if status not in {"available", "unavailable"}:
        raise ValueError(f"Evidence {location}.status is unsupported")
    support_count: int | None = None
    support_unit: str | None = None
    if "support" in data:
        support = _load_mapping(data.get("support"), f"{location}.support")
        if set(support) != {"count", "unit"}:
            raise ValueError(f"Evidence {location}.support has an unsupported shape")
        support_count = _load_nonnegative_integer(support.get("count"), f"{location}.support.count")
        support_unit = _load_text(support.get("unit"), f"{location}.support.unit")
    sources_value = data.get("sources", [])
    if not isinstance(sources_value, list):
        raise ValueError(f"Evidence {location}.sources must be a list")
    sources = tuple(
        SourceLocator(
            _load_sha(
                _load_mapping(item, f"{location}.sources[{source_index}]").get("record_sha256"),
                f"{location}.sources[{source_index}].record_sha256",
            ),
            _load_text(
                _load_mapping(item, f"{location}.sources[{source_index}]").get("pointer"),
                f"{location}.sources[{source_index}].pointer",
            ),
        )
        for source_index, item in enumerate(sources_value)
    )
    diagnostic: MeasureDiagnostic | None = None
    if "diagnostic" in data:
        diagnostic_value = _load_mapping(data.get("diagnostic"), f"{location}.diagnostic")
        diagnostic = MeasureDiagnostic(
            _load_text(diagnostic_value.get("code"), f"{location}.diagnostic.code"),
            _load_text(diagnostic_value.get("message"), f"{location}.diagnostic.message"),
        )
    result = MeasureResult(
        metric=_load_text(data.get("metric"), f"{location}.metric"),
        dimensions=dict(_load_mapping(data.get("dimensions"), f"{location}.dimensions")),
        status=status,
        value=data.get("value"),
        unit=_load_optional_text(data.get("unit"), f"{location}.unit"),
        support_count=support_count,
        support_unit=support_unit,
        sources=sources,
        diagnostic=diagnostic,
        result_sha256=_load_sha(data.get("result_sha256"), f"{location}.result_sha256"),
    )
    if sha256_json(result.identity_payload()) != result.result_sha256:
        raise ValueError(f"Evidence {location} identity does not match its payload")
    return result


def _load_mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Evidence {location} must be a mapping")
    return value


def _load_text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Evidence {location} must be non-empty text")
    return value


def _load_optional_text(value: Any, location: str) -> str | None:
    if value is None:
        return None
    return _load_text(value, location)


def _load_sha(value: Any, location: str) -> str:
    text = _load_text(value, location)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"Evidence {location} must be a lowercase SHA-256")
    return text


def _load_nonnegative_integer(value: Any, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Evidence {location} must be a non-negative integer")
    return value


def _load_text_tuple(value: Any, location: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"Evidence {location} must be a list")
    return tuple(_load_text(item, location) for item in value)


def _selected_cells(study: PreparedStudy, cell_ids: Sequence[str]) -> tuple[str, ...]:
    requested = tuple(cell_ids)
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("RecordCorpus requires non-empty unique Cell ids")
    authored = [cell.id for cell in study.definition.cells]
    unknown = sorted(set(requested) - set(authored))
    if unknown:
        raise ValueError(f"RecordCorpus references unknown Cells: {', '.join(unknown)}")
    requested_set = set(requested)
    return tuple(cell_id for cell_id in authored if cell_id in requested_set)


def _expected_records(study: PreparedStudy, cell_ids: Sequence[str]) -> dict[str, int]:
    groups = {group.id: group for group in study.execution_groups}
    expected: dict[str, int] = {}
    for cell in study.definition.cells:
        if cell.id not in cell_ids:
            continue
        runs = groups[cell.execution_group].prepared_assembly.assembly["runs"]
        run = next(item for item in runs if item["name"] == cell.assembly_run)
        expected[cell.id] = int(run["matches"])
    return expected


def _current_entries(
    study: PreparedStudy,
    cell_ids: Sequence[str],
    executions: Sequence[StudyExecution],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if any(execution.plan_sha256 != study.plan_sha256 for execution in executions):
        raise ValueError("All StudyExecution receipts must share the PreparedStudy plan")
    all_groups = [
        group_id for execution in executions for group_id in execution.execution_group_ids
    ]
    if len(set(all_groups)) != len(all_groups):
        raise ValueError("StudyExecution receipts overlap in selected ExecutionGroups")
    group_order = {group.id: index for index, group in enumerate(study.definition.execution_groups)}
    ordered = tuple(
        sorted(executions, key=lambda item: min(group_order[g] for g in item.execution_group_ids))
    )
    origin_payload = {
        "kind": "study_execution",
        "executions": [execution.execution_sha256 for execution in ordered],
    }
    origin = {**origin_payload, "identity_sha256": sha256_json(origin_payload)}
    entries: list[dict[str, Any]] = []
    selected = set(cell_ids)
    for execution in ordered:
        for record in execution.records:
            if record.cell_id in selected:
                entries.append(_entry_from_receipt(record, execution))
    return origin, tuple(entries)


def _entry_from_receipt(
    receipt: StudyRecordReceipt,
    execution: StudyExecution,
) -> dict[str, Any]:
    return {
        **receipt.as_dict(),
        "path_object": receipt.path,
        "source_identity": execution.execution_sha256,
    }


def _imported_entries(
    study: PreparedStudy,
    cell_ids: Sequence[str],
    manifest_path: str | Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    path = Path(manifest_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Imported corpus manifest is missing: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Imported corpus manifest could not be read: {exc}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("Imported corpus manifest schema_version must equal 1")
    if set(payload) != {"schema_version", "source", "records"}:
        raise ValueError("Imported corpus manifest must contain schema_version, source, records")
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Imported corpus source must be a mapping")
    if not isinstance(source.get("id"), str) or not isinstance(source.get("revision"), str):
        raise ValueError("Imported corpus source requires id and pinned revision")
    manifest_hash = sha256_file(path)
    origin_payload = {
        "kind": "imported",
        "source": dict(source),
        "manifest_sha256": manifest_hash,
    }
    origin = {**origin_payload, "identity_sha256": sha256_json(origin_payload)}
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise ValueError("Imported corpus records must be a list")
    selected = set(cell_ids)
    cells = {cell.id: cell for cell in study.definition.cells}
    groups = {group.id: group for group in study.definition.execution_groups}
    phases = {phase.id: phase for phase in study.definition.phases}
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, Mapping):
            raise ValueError(f"Imported corpus records[{index}] must be a mapping")
        cell_id = raw.get("cell_id")
        if cell_id not in selected:
            continue
        cell = cells[cell_id]
        group = groups[cell.execution_group]
        expected_binding = {
            "phase_id": group.phase,
            "phase_kind": phases[group.phase].kind,
            "execution_group_id": group.id,
            "assembly_run": cell.assembly_run,
        }
        for key, expected_value in expected_binding.items():
            if raw.get(key) != expected_value:
                raise ValueError(
                    f"Imported corpus records[{index}].{key} does not match "
                    f"Cell {cell_id!r}: expected {expected_value!r}"
                )
        relative = raw.get("path")
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ValueError(f"Imported corpus records[{index}].path must be portable")
        record_path = (path.parent / relative).resolve()
        if not record_path.is_relative_to(path.parent) or not record_path.is_file():
            raise ValueError(f"Imported Record must remain inside manifest root: {relative}")
        entry = dict(raw)
        entry["path_object"] = record_path
        entry["source_identity"] = origin["identity_sha256"]
        entry["plan_sha256"] = study.plan_sha256
        entries.append(entry)
    return origin, tuple(entries)


def _load_corpus_record(
    study: PreparedStudy,
    entry: Mapping[str, Any],
    origin_identity: str,
    authority: str,
) -> CorpusRecord:
    path = entry.get("path_object")
    if not isinstance(path, Path):
        raise ValueError("Corpus entry has no resolved Record path")
    payload_bytes = path.read_bytes()
    observed_hash = hashlib.sha256(payload_bytes).hexdigest()
    expected_hash = entry.get("record_sha256")
    if observed_hash != expected_hash:
        raise ValueError(
            f"Record hash mismatch for {path.name}: {expected_hash} != {observed_hash}"
        )
    payload = json.loads(payload_bytes)
    if not isinstance(payload, Mapping) or str(payload.get("schema_version")) != "2.0":
        raise ValueError(f"Record {path.name!r} is not current schema 2.0")
    values = {
        "match_id": entry.get("match_id"),
        "cell_id": entry.get("cell_id"),
        "phase_id": entry.get("phase_id"),
        "phase_kind": entry.get("phase_kind"),
        "execution_group_id": entry.get("execution_group_id"),
        "assembly_run": entry.get("assembly_run"),
    }
    if any(not isinstance(value, str) or not value for value in values.values()):
        raise ValueError(f"Corpus entry for {path.name!r} has incomplete semantic binding")
    if payload.get("match_id") != values["match_id"]:
        raise ValueError(f"Record match_id does not match receipt for {path.name!r}")
    match_index = entry.get("match_index")
    effective_seed = entry.get("effective_seed")
    if not isinstance(match_index, int) or isinstance(match_index, bool) or match_index < 0:
        raise ValueError(f"Corpus entry for {path.name!r} has invalid match_index")
    if not isinstance(effective_seed, int) or isinstance(effective_seed, bool):
        raise ValueError(f"Corpus entry for {path.name!r} has invalid effective_seed")
    metadata = payload.get("metadata") or {}
    context = metadata.get("context") if isinstance(metadata, Mapping) else {}
    if authority == "execution_receipt":
        if not isinstance(context, Mapping) or context.get("match_index") != match_index:
            raise ValueError(f"Record slot does not match receipt for {path.name!r}")
        if payload.get("seed") != effective_seed:
            raise ValueError(f"Record effective seed does not match receipt for {path.name!r}")
    relative_path = entry.get("path")
    if not isinstance(relative_path, str) or relative_path.startswith("/"):
        raise ValueError(f"Corpus entry for {path.name!r} has non-portable path")
    return CorpusRecord(
        record_sha256=observed_hash,
        schema_version="2.0",
        match_id=cast(str, values["match_id"]),
        source_identity=str(entry.get("source_identity") or origin_identity),
        relative_path=relative_path,
        study_id=study.definition.id,
        plan_sha256=study.plan_sha256,
        phase_id=cast(str, values["phase_id"]),
        phase_kind=cast(str, values["phase_kind"]),
        execution_group_id=cast(str, values["execution_group_id"]),
        assembly_run=cast(str, values["assembly_run"]),
        cell_id=cast(str, values["cell_id"]),
        match_index=match_index,
        effective_seed=effective_seed,
        binding_authority=authority,
        payload=payload,
        path=path,
    )


def _validate_unique_records(records: Sequence[CorpusRecord]) -> None:
    hashes = [item.record_sha256 for item in records]
    match_ids = [item.match_id for item in records]
    bindings = [(item.cell_id, item.match_index) for item in records]
    if len(set(hashes)) != len(hashes):
        raise ValueError("RecordCorpus contains duplicate Record hashes")
    if len(set(match_ids)) != len(match_ids):
        raise ValueError("RecordCorpus contains duplicate match_id values")
    if len(set(bindings)) != len(bindings):
        raise ValueError("RecordCorpus contains duplicate Cell match slots")


__all__ = [
    "CorpusRecord",
    "Evidence",
    "EvidenceDiagnostic",
    "RecordCorpus",
    "build_record_corpus",
    "derive_evidence",
    "load_evidence",
]
