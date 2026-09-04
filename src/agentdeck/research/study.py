"""Portable Study loading and preparation above canonical AgentDeck Assemblies."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import yaml

from agentdeck.core.assembly import PreparedAssembly, prepare_assembly

RESEARCH_CONTRACT_VERSION = "0.1.0"
_PORTABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_PHASE_KINDS = {"preflight", "pilot", "study", "supplemental"}
_STUDY_INTENTS = {"exploratory", "confirmatory"}
_LINEAGE_RELATIONS = {"reproduction", "replication", "extension"}
_ROOT_FIELDS = {
    "schema_version",
    "study",
    "execution_groups",
    "phases",
    "conditions",
    "cells",
    "lineage",
}


@dataclass(frozen=True)
class StudyDiagnostic:
    """One stable, location-aware Study validation diagnostic."""

    code: str
    severity: str
    location: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "location": self.location,
            "message": self.message,
        }


class StudyValidationError(ValueError):
    """Raised when authored Study input cannot become a valid PreparedStudy."""

    def __init__(
        self,
        diagnostics: Sequence[StudyDiagnostic],
        *,
        study_id: str | None = None,
    ) -> None:
        ordered = tuple(diagnostics)
        if not ordered:
            raise ValueError("StudyValidationError requires at least one diagnostic")
        self.diagnostics = ordered
        self.study_id = study_id
        summary = "; ".join(
            f"{item.location}: {item.message}" if item.location else item.message
            for item in ordered
        )
        super().__init__(summary)


@dataclass(frozen=True)
class Hypothesis:
    id: str
    statement: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "statement": self.statement}


@dataclass(frozen=True)
class StudyPhase:
    id: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "kind": self.kind}


@dataclass(frozen=True)
class StudyExecutionGroup:
    id: str
    phase: str
    entrypoint: str
    artifacts: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "phase": self.phase,
            "entrypoint": self.entrypoint,
        }
        if self.artifacts:
            result["artifacts"] = list(self.artifacts)
        return result


@dataclass(frozen=True)
class StudyCondition:
    id: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "description": self.description}


@dataclass(frozen=True)
class ConditionTarget:
    scope: str
    name: str | None = None

    def as_dict(self) -> dict[str, str]:
        result = {"scope": self.scope}
        if self.name is not None:
            result["name"] = self.name
        return result


@dataclass(frozen=True)
class ConditionAssignment:
    condition: str
    target: ConditionTarget

    def as_dict(self) -> dict[str, Any]:
        return {"condition": self.condition, "target": self.target.as_dict()}


@dataclass(frozen=True)
class StudyCell:
    id: str
    execution_group: str
    assembly_run: str
    assignments: tuple[ConditionAssignment, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "execution_group": self.execution_group,
            "assembly_run": self.assembly_run,
        }
        if self.assignments:
            result["assignments"] = [item.as_dict() for item in self.assignments]
        return result


@dataclass(frozen=True)
class StudyLineage:
    parent: str
    relation: str

    def as_dict(self) -> dict[str, str]:
        return {"parent": self.parent, "relation": self.relation}


@dataclass(frozen=True)
class StudyDefinition:
    """Structurally valid authored Study content, without imported Assemblies."""

    schema_version: int
    id: str
    title: str
    question: str
    intent: str
    hypotheses: tuple[Hypothesis, ...]
    execution_groups: tuple[StudyExecutionGroup, ...]
    phases: tuple[StudyPhase, ...]
    conditions: tuple[StudyCondition, ...]
    cells: tuple[StudyCell, ...]
    lineage: StudyLineage | None = None
    source_path: Path = field(default=Path(), compare=False, repr=False)
    package_root: Path = field(default=Path(), compare=False, repr=False)

    def as_dict(self) -> dict[str, Any]:
        study: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "question": self.question,
            "intent": self.intent,
        }
        if self.hypotheses:
            study["hypotheses"] = [item.as_dict() for item in self.hypotheses]
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "study": study,
            "execution_groups": [item.as_dict() for item in self.execution_groups],
            "phases": [item.as_dict() for item in self.phases],
            "conditions": [item.as_dict() for item in self.conditions],
            "cells": [item.as_dict() for item in self.cells],
        }
        if self.lineage is not None:
            result["lineage"] = self.lineage.as_dict()
        return result


@dataclass(frozen=True)
class PreparedExecutionGroup:
    id: str
    phase: str
    entrypoint: str
    artifacts: tuple[str, ...]
    prepared_assembly: PreparedAssembly

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase,
            "entrypoint": self.entrypoint,
            "artifacts": list(self.artifacts),
            "prepared_assembly": self.prepared_assembly.as_dict(),
        }


@dataclass(frozen=True)
class PreparedStudy:
    """Portable Study plan bound to exact PreparedAssembly identities."""

    schema_version: int
    research_contract_version: str
    definition: StudyDefinition
    definition_sha256: str
    execution_groups: tuple[PreparedExecutionGroup, ...]
    total_matches: int
    provider_requirements: tuple[Mapping[str, str], ...]
    plan_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "execution_groups", tuple(self.execution_groups))
        object.__setattr__(
            self,
            "provider_requirements",
            tuple(MappingProxyType(dict(item)) for item in self.provider_requirements),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "research_contract_version": self.research_contract_version,
            "definition": self.definition.as_dict(),
            "definition_sha256": self.definition_sha256,
            "execution_groups": [item.as_dict() for item in self.execution_groups],
            "total_matches": self.total_matches,
            "provider_requirements": [dict(item) for item in self.provider_requirements],
            "plan_sha256": self.plan_sha256,
        }


class _Diagnostics:
    def __init__(self) -> None:
        self.items: list[StudyDiagnostic] = []

    def add(self, code: str, location: str, message: str) -> None:
        self.items.append(
            StudyDiagnostic(code=code, severity="error", location=location, message=message)
        )

    def check_fields(
        self,
        value: Mapping[str, Any],
        *,
        location: str,
        allowed: set[str],
        required: set[str] | None = None,
    ) -> None:
        present: set[str] = set()
        for key in sorted(value, key=str):
            if not isinstance(key, str):
                self.add(
                    "study.field_name",
                    location,
                    f"field names must be strings; observed {key!r}",
                )
                continue
            present.add(key)
            if key not in allowed:
                self.add("study.unknown_field", f"{location}.{key}", "field is not allowed")
        for key in sorted((required or set()) - present):
            self.add("study.missing_field", f"{location}.{key}", "field is required")


def load_study(path: str | Path) -> StudyDefinition:
    """Load and structurally validate a Study without importing Assembly Python."""

    diagnostics = _Diagnostics()
    source_path = _manifest_path(path, diagnostics)
    if diagnostics.items:
        raise StudyValidationError(diagnostics.items)
    assert source_path is not None

    try:
        payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        diagnostics.add("study.yaml", "study.yaml", f"could not be read as YAML: {exc}")
        raise StudyValidationError(diagnostics.items) from exc
    if not isinstance(payload, Mapping):
        diagnostics.add("study.schema", "study.yaml", "document root must be a mapping")
        raise StudyValidationError(diagnostics.items)

    root = dict(payload)
    diagnostics.check_fields(
        root,
        location="study.yaml",
        allowed=_ROOT_FIELDS,
        required={"schema_version", "study", "execution_groups", "phases", "cells"},
    )
    schema_version = _integer(root.get("schema_version"), "schema_version", diagnostics)
    if schema_version is not None and schema_version != 1:
        diagnostics.add("study.schema_version", "schema_version", "must equal 1")

    metadata = _mapping(root.get("study"), "study", diagnostics)
    diagnostics.check_fields(
        metadata,
        location="study",
        allowed={"id", "title", "question", "intent", "hypotheses"},
        required={"id", "title", "question", "intent"},
    )
    study_id = _identifier(metadata.get("id"), "study.id", diagnostics)
    title = _text(metadata.get("title"), "study.title", diagnostics)
    question = _text(metadata.get("question"), "study.question", diagnostics)
    intent = _choice(metadata.get("intent"), "study.intent", _STUDY_INTENTS, diagnostics)
    hypotheses = _parse_hypotheses(metadata.get("hypotheses"), diagnostics)
    phases = _parse_phases(root.get("phases"), diagnostics)
    execution_groups = _parse_execution_groups(root.get("execution_groups"), diagnostics)
    conditions = _parse_conditions(root.get("conditions"), diagnostics)
    cells = _parse_cells(root.get("cells"), diagnostics)
    lineage = _parse_lineage(root.get("lineage"), diagnostics)

    _validate_unique("hypothesis", [item.id for item in hypotheses], diagnostics)
    _validate_unique("phase", [item.id for item in phases], diagnostics)
    _validate_unique("execution_group", [item.id for item in execution_groups], diagnostics)
    _validate_unique("condition", [item.id for item in conditions], diagnostics)
    _validate_unique("cell", [item.id for item in cells], diagnostics)
    _validate_authored_references(phases, execution_groups, conditions, cells, diagnostics)

    if diagnostics.items:
        raise StudyValidationError(diagnostics.items, study_id=study_id)
    assert schema_version is not None
    assert (
        study_id is not None and title is not None and question is not None and intent is not None
    )
    return StudyDefinition(
        schema_version=schema_version,
        id=study_id,
        title=title,
        question=question,
        intent=intent,
        hypotheses=hypotheses,
        execution_groups=execution_groups,
        phases=phases,
        conditions=conditions,
        cells=cells,
        lineage=lineage,
        source_path=source_path,
        package_root=source_path.parent,
    )


def prepare_study(path: str | Path) -> PreparedStudy:
    """Bind a structurally valid Study to exact PreparedAssembly identities."""

    definition = load_study(path)
    diagnostics = _Diagnostics()
    _validate_package_hygiene(definition.package_root, diagnostics)
    before = _package_snapshot(definition.package_root, diagnostics)
    if diagnostics.items:
        raise StudyValidationError(diagnostics.items, study_id=definition.id)
    prepared_groups: list[PreparedExecutionGroup] = []

    for group in definition.execution_groups:
        entrypoint = _resolve_entrypoint(definition.package_root, group, diagnostics)
        if entrypoint is None:
            continue
        try:
            prepared_assembly = prepare_assembly(entrypoint, artifacts=group.artifacts)
        except Exception as exc:  # trusted Assembly errors become authored diagnostics
            diagnostics.add(
                "study.assembly_preparation",
                f"execution_groups.{group.id}",
                f"Assembly preparation failed: {exc}",
            )
            continue
        prepared_groups.append(
            PreparedExecutionGroup(
                id=group.id,
                phase=group.phase,
                entrypoint=group.entrypoint,
                artifacts=group.artifacts,
                prepared_assembly=prepared_assembly,
            )
        )

    after = _package_snapshot(definition.package_root, diagnostics)
    if before != after:
        diagnostics.add(
            "study.source_mutation",
            "study.yaml",
            "authored Study package changed during preparation",
        )

    by_id = {group.id: group for group in prepared_groups}
    _validate_prepared_references(definition, by_id, diagnostics)
    if diagnostics.items:
        raise StudyValidationError(diagnostics.items, study_id=definition.id)

    providers: list[dict[str, str]] = []
    seen_providers: set[tuple[str, str]] = set()
    for prepared_group in prepared_groups:
        for requirement in prepared_group.prepared_assembly.provider_requirements:
            key = (requirement["provider"], requirement["model"])
            if key not in seen_providers:
                seen_providers.add(key)
                providers.append(dict(requirement))

    definition_payload = definition.as_dict()
    definition_sha256 = _sha256(definition_payload)
    identity = {
        "schema_version": 1,
        "research_contract_version": RESEARCH_CONTRACT_VERSION,
        "definition": definition_payload,
        "definition_sha256": definition_sha256,
        "execution_groups": [group.as_dict() for group in prepared_groups],
    }
    return PreparedStudy(
        schema_version=1,
        research_contract_version=RESEARCH_CONTRACT_VERSION,
        definition=definition,
        definition_sha256=definition_sha256,
        execution_groups=tuple(prepared_groups),
        total_matches=sum(group.prepared_assembly.total_matches for group in prepared_groups),
        provider_requirements=tuple(providers),
        plan_sha256=_sha256(identity),
    )


def _manifest_path(path: str | Path, diagnostics: _Diagnostics) -> Path | None:
    candidate = Path(path).expanduser().resolve()
    if candidate.is_dir():
        candidate = candidate / "study.yaml"
    if candidate.name != "study.yaml":
        diagnostics.add("study.package", str(path), "Study manifest must be named study.yaml")
        return None
    if not candidate.is_file():
        diagnostics.add("study.package", str(path), "study.yaml is missing or not a regular file")
        return None
    return candidate


def _parse_hypotheses(value: Any, diagnostics: _Diagnostics) -> tuple[Hypothesis, ...]:
    if value is None:
        return ()
    result: list[Hypothesis] = []
    for index, item in enumerate(_sequence(value, "study.hypotheses", diagnostics)):
        location = f"study.hypotheses[{index}]"
        mapping = _mapping(item, location, diagnostics)
        diagnostics.check_fields(
            mapping,
            location=location,
            allowed={"id", "statement"},
            required={"id", "statement"},
        )
        item_id = _identifier(mapping.get("id"), f"{location}.id", diagnostics)
        statement = _text(mapping.get("statement"), f"{location}.statement", diagnostics)
        if item_id is not None and statement is not None:
            result.append(Hypothesis(item_id, statement))
    return tuple(result)


def _parse_phases(value: Any, diagnostics: _Diagnostics) -> tuple[StudyPhase, ...]:
    result: list[StudyPhase] = []
    for index, item in enumerate(_sequence(value, "phases", diagnostics, non_empty=True)):
        location = f"phases[{index}]"
        mapping = _mapping(item, location, diagnostics)
        diagnostics.check_fields(
            mapping, location=location, allowed={"id", "kind"}, required={"id", "kind"}
        )
        item_id = _identifier(mapping.get("id"), f"{location}.id", diagnostics)
        kind = _choice(mapping.get("kind"), f"{location}.kind", _PHASE_KINDS, diagnostics)
        if item_id is not None and kind is not None:
            result.append(StudyPhase(item_id, kind))
    return tuple(result)


def _parse_execution_groups(
    value: Any, diagnostics: _Diagnostics
) -> tuple[StudyExecutionGroup, ...]:
    result: list[StudyExecutionGroup] = []
    for index, item in enumerate(_sequence(value, "execution_groups", diagnostics, non_empty=True)):
        location = f"execution_groups[{index}]"
        mapping = _mapping(item, location, diagnostics)
        diagnostics.check_fields(
            mapping,
            location=location,
            allowed={"id", "phase", "entrypoint", "artifacts"},
            required={"id", "phase", "entrypoint"},
        )
        item_id = _identifier(mapping.get("id"), f"{location}.id", diagnostics)
        phase = _identifier(mapping.get("phase"), f"{location}.phase", diagnostics)
        entrypoint = _portable_path(
            mapping.get("entrypoint"), f"{location}.entrypoint", diagnostics
        )
        artifacts: list[str] = []
        for artifact_index, artifact in enumerate(
            _sequence(mapping.get("artifacts"), f"{location}.artifacts", diagnostics)
        ):
            parsed = _portable_path(
                artifact, f"{location}.artifacts[{artifact_index}]", diagnostics
            )
            if parsed is not None:
                artifacts.append(parsed)
        if item_id is not None and phase is not None and entrypoint is not None:
            result.append(StudyExecutionGroup(item_id, phase, entrypoint, tuple(artifacts)))
    return tuple(result)


def _parse_conditions(value: Any, diagnostics: _Diagnostics) -> tuple[StudyCondition, ...]:
    if value is None:
        return ()
    result: list[StudyCondition] = []
    for index, item in enumerate(_sequence(value, "conditions", diagnostics)):
        location = f"conditions[{index}]"
        mapping = _mapping(item, location, diagnostics)
        diagnostics.check_fields(
            mapping,
            location=location,
            allowed={"id", "description"},
            required={"id", "description"},
        )
        item_id = _identifier(mapping.get("id"), f"{location}.id", diagnostics)
        description = _text(mapping.get("description"), f"{location}.description", diagnostics)
        if item_id is not None and description is not None:
            result.append(StudyCondition(item_id, description))
    return tuple(result)


def _parse_cells(value: Any, diagnostics: _Diagnostics) -> tuple[StudyCell, ...]:
    result: list[StudyCell] = []
    for index, item in enumerate(_sequence(value, "cells", diagnostics, non_empty=True)):
        location = f"cells[{index}]"
        mapping = _mapping(item, location, diagnostics)
        diagnostics.check_fields(
            mapping,
            location=location,
            allowed={"id", "execution_group", "assembly_run", "assignments"},
            required={"id", "execution_group", "assembly_run"},
        )
        item_id = _identifier(mapping.get("id"), f"{location}.id", diagnostics)
        group = _identifier(
            mapping.get("execution_group"), f"{location}.execution_group", diagnostics
        )
        assembly_run = _text(mapping.get("assembly_run"), f"{location}.assembly_run", diagnostics)
        assignments = _parse_assignments(mapping.get("assignments"), location, diagnostics)
        if item_id is not None and group is not None and assembly_run is not None:
            result.append(StudyCell(item_id, group, assembly_run, assignments))
    return tuple(result)


def _parse_assignments(
    value: Any, cell_location: str, diagnostics: _Diagnostics
) -> tuple[ConditionAssignment, ...]:
    if value is None:
        return ()
    result: list[ConditionAssignment] = []
    for index, item in enumerate(_sequence(value, f"{cell_location}.assignments", diagnostics)):
        location = f"{cell_location}.assignments[{index}]"
        mapping = _mapping(item, location, diagnostics)
        diagnostics.check_fields(
            mapping,
            location=location,
            allowed={"condition", "target"},
            required={"condition", "target"},
        )
        condition = _identifier(mapping.get("condition"), f"{location}.condition", diagnostics)
        target_mapping = _mapping(mapping.get("target"), f"{location}.target", diagnostics)
        diagnostics.check_fields(
            target_mapping,
            location=f"{location}.target",
            allowed={"scope", "name"},
            required={"scope"},
        )
        scope = _choice(
            target_mapping.get("scope"), f"{location}.target.scope", {"run", "player"}, diagnostics
        )
        name = target_mapping.get("name")
        parsed_name: str | None = None
        if scope == "run":
            if name is not None:
                diagnostics.add(
                    "study.condition_target",
                    f"{location}.target.name",
                    "run targets must not name a Player",
                )
        elif scope == "player":
            parsed_name = _text(name, f"{location}.target.name", diagnostics)
        if condition is not None and scope is not None:
            result.append(ConditionAssignment(condition, ConditionTarget(scope, parsed_name)))
    return tuple(result)


def _parse_lineage(value: Any, diagnostics: _Diagnostics) -> StudyLineage | None:
    if value is None:
        return None
    mapping = _mapping(value, "lineage", diagnostics)
    diagnostics.check_fields(
        mapping,
        location="lineage",
        allowed={"parent", "relation"},
        required={"parent", "relation"},
    )
    parent = _text(mapping.get("parent"), "lineage.parent", diagnostics)
    relation = _choice(mapping.get("relation"), "lineage.relation", _LINEAGE_RELATIONS, diagnostics)
    if parent is None or relation is None:
        return None
    return StudyLineage(parent, relation)


def _validate_authored_references(
    phases: Sequence[StudyPhase],
    groups: Sequence[StudyExecutionGroup],
    conditions: Sequence[StudyCondition],
    cells: Sequence[StudyCell],
    diagnostics: _Diagnostics,
) -> None:
    phase_ids = {item.id for item in phases}
    group_ids = {item.id for item in groups}
    condition_ids = {item.id for item in conditions}
    for group in groups:
        if group.phase not in phase_ids:
            diagnostics.add(
                "study.unknown_phase",
                f"execution_groups.{group.id}.phase",
                f"references unknown phase {group.phase!r}",
            )
    for cell in cells:
        if cell.execution_group not in group_ids:
            diagnostics.add(
                "study.unknown_execution_group",
                f"cells.{cell.id}.execution_group",
                f"references unknown execution group {cell.execution_group!r}",
            )
        for index, assignment in enumerate(cell.assignments):
            if assignment.condition not in condition_ids:
                diagnostics.add(
                    "study.unknown_condition",
                    f"cells.{cell.id}.assignments[{index}].condition",
                    f"references unknown condition {assignment.condition!r}",
                )


def _validate_prepared_references(
    definition: StudyDefinition,
    prepared_groups: Mapping[str, PreparedExecutionGroup],
    diagnostics: _Diagnostics,
) -> None:
    mappings: dict[tuple[str, str], list[str]] = {}
    for cell in definition.cells:
        group = prepared_groups.get(cell.execution_group)
        if group is None:
            continue
        runs = {str(run["name"]): run for run in group.prepared_assembly.assembly.get("runs", ())}
        run = runs.get(cell.assembly_run)
        if run is None:
            diagnostics.add(
                "study.unknown_assembly_run",
                f"cells.{cell.id}.assembly_run",
                f"references unknown AssemblyRun {cell.assembly_run!r} in group {group.id!r}",
            )
            continue
        mappings.setdefault((group.id, cell.assembly_run), []).append(cell.id)
        player_names = {
            str(player.get("kwargs", {}).get("name")) for player in run.get("players", ())
        }
        for index, assignment in enumerate(cell.assignments):
            target = assignment.target
            if target.scope == "player" and target.name not in player_names:
                diagnostics.add(
                    "study.unknown_player",
                    f"cells.{cell.id}.assignments[{index}].target.name",
                    f"references unknown Player {target.name!r} in AssemblyRun {cell.assembly_run!r}",
                )

    for group in prepared_groups.values():
        for run in group.prepared_assembly.assembly.get("runs", ()):
            run_name = str(run["name"])
            mapped = mappings.get((group.id, run_name), [])
            if not mapped:
                diagnostics.add(
                    "study.unmapped_assembly_run",
                    f"execution_groups.{group.id}.runs.{run_name}",
                    "AssemblyRun must map to exactly one Cell",
                )
            elif len(mapped) > 1:
                diagnostics.add(
                    "study.duplicate_run_mapping",
                    f"execution_groups.{group.id}.runs.{run_name}",
                    f"AssemblyRun maps to multiple Cells: {', '.join(mapped)}",
                )


def _validate_unique(kind: str, values: Sequence[str], diagnostics: _Diagnostics) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            diagnostics.add(
                "study.duplicate_identifier",
                f"{kind}.{value}",
                f"duplicate {kind} identifier {value!r}",
            )
        seen.add(value)


def _validate_package_hygiene(root: Path, diagnostics: _Diagnostics) -> None:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir() and path.name == "__pycache__":
            diagnostics.add(
                "study.generated_source", relative, "interpreter cache is not authored content"
            )
        elif path.is_file() and path.suffix in {".pyc", ".pyo"}:
            diagnostics.add(
                "study.generated_source", relative, "bytecode cache is not authored content"
            )


def _resolve_entrypoint(
    package_root: Path,
    group: StudyExecutionGroup,
    diagnostics: _Diagnostics,
) -> Path | None:
    candidate = package_root / PurePosixPath(group.entrypoint)
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        diagnostics.add(
            "study.entrypoint",
            f"execution_groups.{group.id}.entrypoint",
            f"could not resolve Assembly entrypoint: {exc}",
        )
        return None
    if not resolved.is_relative_to(package_root.resolve()):
        diagnostics.add(
            "study.entrypoint",
            f"execution_groups.{group.id}.entrypoint",
            "Assembly entrypoint resolves outside the Study package",
        )
        return None
    if not resolved.is_file():
        diagnostics.add(
            "study.entrypoint",
            f"execution_groups.{group.id}.entrypoint",
            "Assembly entrypoint is missing or not a regular file",
        )
        return None
    return resolved


def _package_snapshot(root: Path, diagnostics: _Diagnostics) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    try:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                snapshot[path.relative_to(root).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    except OSError as exc:
        diagnostics.add("study.package_read", "study.yaml", f"could not snapshot package: {exc}")
    return snapshot


def _mapping(value: Any, location: str, diagnostics: _Diagnostics) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if value is not None:
        diagnostics.add("study.type", location, "must be a mapping")
    return {}


def _sequence(
    value: Any, location: str, diagnostics: _Diagnostics, *, non_empty: bool = False
) -> tuple[Any, ...]:
    if isinstance(value, list):
        if non_empty and not value:
            diagnostics.add("study.empty", location, "must contain at least one item")
        return tuple(value)
    if value is not None:
        diagnostics.add("study.type", location, "must be a list")
    elif non_empty:
        diagnostics.add("study.empty", location, "must contain at least one item")
    return ()


def _text(value: Any, location: str, diagnostics: _Diagnostics) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    diagnostics.add("study.value", location, "must be a non-empty string")
    return None


def _identifier(value: Any, location: str, diagnostics: _Diagnostics) -> str | None:
    parsed = _text(value, location, diagnostics)
    if parsed is not None and not _PORTABLE_ID.fullmatch(parsed):
        diagnostics.add(
            "study.identifier",
            location,
            "must match [a-z0-9][a-z0-9._-]*",
        )
        return None
    return parsed


def _integer(value: Any, location: str, diagnostics: _Diagnostics) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    diagnostics.add("study.type", location, "must be an integer")
    return None


def _choice(
    value: Any,
    location: str,
    allowed: set[str],
    diagnostics: _Diagnostics,
) -> str | None:
    parsed = _text(value, location, diagnostics)
    if parsed is not None and parsed not in allowed:
        diagnostics.add(
            "study.value",
            location,
            f"must be one of: {', '.join(sorted(allowed))}",
        )
        return None
    return parsed


def _portable_path(value: Any, location: str, diagnostics: _Diagnostics) -> str | None:
    parsed = _text(value, location, diagnostics)
    if parsed is None:
        return None
    if "\\" in parsed:
        diagnostics.add("study.path", location, "must use POSIX separators")
        return None
    path = PurePosixPath(parsed)
    if path.is_absolute() or ".." in path.parts or parsed in {".", ""}:
        diagnostics.add("study.path", location, "must be a relative path inside the package")
        return None
    return path.as_posix()


def _sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "RESEARCH_CONTRACT_VERSION",
    "ConditionAssignment",
    "ConditionTarget",
    "Hypothesis",
    "PreparedExecutionGroup",
    "PreparedStudy",
    "StudyCell",
    "StudyCondition",
    "StudyDefinition",
    "StudyDiagnostic",
    "StudyExecutionGroup",
    "StudyLineage",
    "StudyPhase",
    "StudyValidationError",
    "load_study",
    "prepare_study",
]
