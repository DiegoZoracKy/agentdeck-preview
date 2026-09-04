"""Explicit Study selection and execution over sealed AgentDeck Assemblies."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from uuid import uuid4

from agentdeck.core.assembly import (
    AssemblyExecution,
    AssemblyExecutionError,
    AssemblyRunExecution,
    execute_prepared_assembly,
)

from ._canonical import sha256_json, write_json_once
from .study import PreparedExecutionGroup, PreparedStudy, prepare_study


@dataclass(frozen=True)
class StudySelection:
    plan_sha256: str
    execution_group_ids: tuple[str, ...]
    selection_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "execution_group_ids", tuple(self.execution_group_ids))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "plan_sha256": self.plan_sha256,
            "execution_group_ids": list(self.execution_group_ids),
            "selection_sha256": self.selection_sha256,
        }


@dataclass(frozen=True)
class StudyRecordReceipt:
    phase_id: str
    phase_kind: str
    execution_group_id: str
    assembly_run: str
    cell_id: str
    match_index: int
    effective_seed: int
    match_id: str
    record_sha256: str
    path: Path = field(compare=False, repr=False)
    relative_path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "phase_kind": self.phase_kind,
            "execution_group_id": self.execution_group_id,
            "assembly_run": self.assembly_run,
            "cell_id": self.cell_id,
            "match_index": self.match_index,
            "effective_seed": self.effective_seed,
            "match_id": self.match_id,
            "record_sha256": self.record_sha256,
            "path": self.relative_path,
        }


@dataclass(frozen=True)
class StudyRunExecution:
    assembly_run: str
    cell_id: str
    expected_matches: int
    records: tuple[StudyRecordReceipt, ...]
    complete: bool
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "assembly_run": self.assembly_run,
            "cell_id": self.cell_id,
            "expected_matches": self.expected_matches,
            "record_count": len(self.records),
            "complete": self.complete,
            "records": [record.as_dict() for record in self.records],
        }
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class StudyGroupExecution:
    execution_group_id: str
    phase_id: str
    phase_kind: str
    assembly_plan_sha256: str
    runs: tuple[StudyRunExecution, ...]
    complete: bool
    cost_usd: float
    calls: int
    tokens: int
    by_player: Mapping[str, float]
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "runs", tuple(self.runs))
        object.__setattr__(self, "by_player", MappingProxyType(dict(self.by_player)))

    @property
    def records(self) -> tuple[StudyRecordReceipt, ...]:
        return tuple(record for run in self.runs for record in run.records)

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "execution_group_id": self.execution_group_id,
            "phase_id": self.phase_id,
            "phase_kind": self.phase_kind,
            "assembly_plan_sha256": self.assembly_plan_sha256,
            "complete": self.complete,
            "runs": [run.as_dict() for run in self.runs],
            "usage": {
                "cost_usd": self.cost_usd,
                "calls": self.calls,
                "tokens": self.tokens,
                "by_player": dict(self.by_player),
            },
        }
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class StudyExecution:
    study_id: str
    plan_sha256: str
    selection_sha256: str
    execution_group_ids: tuple[str, ...]
    execution_id: str
    groups: tuple[StudyGroupExecution, ...]
    complete: bool
    execution_sha256: str
    execution_root: Path = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "execution_group_ids", tuple(self.execution_group_ids))
        object.__setattr__(self, "groups", tuple(self.groups))

    @property
    def records(self) -> tuple[StudyRecordReceipt, ...]:
        return tuple(record for group in self.groups for record in group.records)

    @property
    def receipt_path(self) -> Path:
        return self.execution_root / "execution.json"

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "execution_sha256": self.execution_sha256,
        }

    def identity_payload(self) -> dict[str, Any]:
        usage = _study_usage(self.groups)
        return {
            "schema_version": 1,
            "study_id": self.study_id,
            "plan_sha256": self.plan_sha256,
            "selection_sha256": self.selection_sha256,
            "execution_group_ids": list(self.execution_group_ids),
            "execution_id": self.execution_id,
            "complete": self.complete,
            "groups": [group.as_dict() for group in self.groups],
            "record_count": len(self.records),
            "usage": usage,
        }


class StudyExecutionError(RuntimeError):
    """Raised when Study execution fails after preserving its receipt when possible."""

    def __init__(
        self,
        message: str,
        *,
        execution: StudyExecution | None = None,
        receipt_path: Path | None = None,
    ) -> None:
        self.execution = execution
        self.receipt_path = receipt_path
        super().__init__(message)


def select_study(
    prepared: PreparedStudy,
    *,
    phase_ids: Sequence[str] = (),
    execution_group_ids: Sequence[str] = (),
    all_groups: bool = False,
) -> StudySelection:
    """Select complete ExecutionGroups through exactly one explicit mode."""

    modes = int(bool(phase_ids)) + int(bool(execution_group_ids)) + int(all_groups)
    if modes != 1:
        raise ValueError("Study selection requires exactly one of phases, groups, or all_groups")

    authored_groups = [group.id for group in prepared.definition.execution_groups]
    if all_groups:
        selected = tuple(authored_groups)
    elif phase_ids:
        requested = _unique_requested("phase", phase_ids)
        known = {phase.id for phase in prepared.definition.phases}
        unknown = sorted(set(requested) - known)
        if unknown:
            raise ValueError(f"Study selection references unknown phases: {', '.join(unknown)}")
        requested_set = set(requested)
        selected = tuple(
            group.id
            for group in prepared.definition.execution_groups
            if group.phase in requested_set
        )
    else:
        requested = _unique_requested("execution group", execution_group_ids)
        unknown = sorted(set(requested) - set(authored_groups))
        if unknown:
            raise ValueError(
                f"Study selection references unknown execution groups: {', '.join(unknown)}"
            )
        requested_set = set(requested)
        selected = tuple(group_id for group_id in authored_groups if group_id in requested_set)

    if not selected:
        raise ValueError("Study selection resolved to no ExecutionGroups")
    payload = {"schema_version": 1, "plan_sha256": prepared.plan_sha256, "groups": selected}
    return StudySelection(
        plan_sha256=prepared.plan_sha256,
        execution_group_ids=selected,
        selection_sha256=sha256_json(payload),
    )


def execute_prepared_study(
    path: str | Path,
    prepared: PreparedStudy,
    selection: StudySelection,
    *,
    output_root: str | Path,
) -> StudyExecution:
    """Execute an explicitly selected, unchanged PreparedStudy."""

    current = prepare_study(path)
    if current.plan_sha256 != prepared.plan_sha256:
        raise ValueError(
            "Prepared Study changed before execution: "
            f"expected {prepared.plan_sha256}, observed {current.plan_sha256}"
        )
    expected_selection = select_study(
        current,
        execution_group_ids=selection.execution_group_ids,
    )
    if selection.plan_sha256 != current.plan_sha256 or (
        selection.selection_sha256 != expected_selection.selection_sha256
    ):
        raise ValueError("StudySelection does not match the current PreparedStudy")

    execution_id = _execution_id()
    root = Path(output_root).expanduser().resolve() / current.definition.id / execution_id
    if root.is_relative_to(current.definition.package_root.resolve()):
        raise ValueError("Study execution output must be outside the authored package")
    root.mkdir(parents=True, exist_ok=False)
    try:
        write_json_once(root / "prepared-study.json", current.as_dict())
        write_json_once(root / "selection.json", expected_selection.as_dict())
    except Exception as exc:
        raise StudyExecutionError(
            f"Study output preparation failed before execution: {exc}",
            receipt_path=None,
        ) from exc

    selected = set(expected_selection.execution_group_ids)
    groups: list[StudyGroupExecution] = []
    for group in current.execution_groups:
        if group.id not in selected:
            continue
        group_root = root / "execution-groups" / group.id
        assembly_output = group_root / "assembly-output"
        try:
            write_json_once(
                group_root / "prepared-assembly.json",
                group.prepared_assembly.as_dict(),
            )
            assembly_execution = execute_prepared_assembly(
                current.definition.package_root / group.entrypoint,
                group.prepared_assembly,
                output_root=assembly_output,
            )
            group_execution = _study_group_execution(
                current,
                group,
                assembly_execution,
                root,
            )
            groups.append(group_execution)
            write_json_once(group_root / "execution.json", group_execution.as_dict())
        except Exception as exc:
            assembly_execution = (
                exc.execution
                if isinstance(exc, AssemblyExecutionError)
                else _empty_assembly_execution(group.prepared_assembly.plan_sha256)
            )
            group_execution = _study_group_execution(
                current,
                group,
                assembly_execution,
                root,
                error=str(exc),
            )
            groups.append(group_execution)
            group_receipt = group_root / "execution.json"
            if not group_receipt.exists():
                write_json_once(group_receipt, group_execution.as_dict())
            execution = _study_execution(current, expected_selection, execution_id, groups, root)
            write_json_once(root / "execution.json", execution.as_dict())
            raise StudyExecutionError(
                f"Execution group {group.id!r} failed: {exc}",
                execution=execution,
                receipt_path=execution.receipt_path,
            ) from exc

    execution = _study_execution(current, expected_selection, execution_id, groups, root)
    write_json_once(root / "execution.json", execution.as_dict())
    return execution


def load_study_execution(path: str | Path) -> StudyExecution:
    """Load and verify one immutable Study execution receipt from local storage."""

    source = Path(path).expanduser().resolve()
    if source.is_dir():
        source = source / "execution.json"
    if not source.is_file():
        raise ValueError(f"Study execution receipt is missing: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Study execution receipt could not be read: {exc}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("Study execution receipt schema_version must equal 1")
    required = {
        "schema_version",
        "study_id",
        "plan_sha256",
        "selection_sha256",
        "execution_group_ids",
        "execution_id",
        "complete",
        "groups",
        "record_count",
        "usage",
        "execution_sha256",
    }
    if set(payload) != required:
        raise ValueError("Study execution receipt has an unsupported shape")
    execution_hash = _receipt_sha(payload.get("execution_sha256"), "execution_sha256")
    identity = dict(payload)
    identity.pop("execution_sha256")
    if sha256_json(identity) != execution_hash:
        raise ValueError("Study execution receipt identity does not match its payload")

    root = source.parent
    groups_value = payload.get("groups")
    if not isinstance(groups_value, list):
        raise ValueError("Study execution groups must be a list")
    groups = tuple(
        _load_group_receipt(item, root, index) for index, item in enumerate(groups_value)
    )
    group_ids = _receipt_text_tuple(payload.get("execution_group_ids"), "execution_group_ids")
    attempted_ids = tuple(group.execution_group_id for group in groups)
    if len(set(group_ids)) != len(group_ids) or attempted_ids != group_ids[: len(groups)]:
        raise ValueError("Study execution group order does not match execution_group_ids")
    record_count = payload.get("record_count")
    if not isinstance(record_count, int) or isinstance(record_count, bool):
        raise ValueError("Study execution record_count must be an integer")
    if sum(len(group.records) for group in groups) != record_count:
        raise ValueError("Study execution record_count does not match its runs")
    complete = payload.get("complete")
    if not isinstance(complete, bool):
        raise ValueError("Study execution complete must be boolean")
    if complete and (attempted_ids != group_ids or not all(group.complete for group in groups)):
        raise ValueError("Complete Study execution requires every selected group to be complete")
    if any(not group.complete for group in groups[:-1]):
        raise ValueError("Only the final attempted Study execution group may be incomplete")
    return StudyExecution(
        study_id=_receipt_text(payload.get("study_id"), "study_id"),
        plan_sha256=_receipt_sha(payload.get("plan_sha256"), "plan_sha256"),
        selection_sha256=_receipt_sha(payload.get("selection_sha256"), "selection_sha256"),
        execution_group_ids=group_ids,
        execution_id=_receipt_text(payload.get("execution_id"), "execution_id"),
        groups=groups,
        complete=complete,
        execution_sha256=execution_hash,
        execution_root=root,
    )


def _load_group_receipt(value: Any, root: Path, index: int) -> StudyGroupExecution:
    location = f"groups[{index}]"
    if not isinstance(value, Mapping):
        raise ValueError(f"Study execution {location} must be a mapping")
    required = {
        "execution_group_id",
        "phase_id",
        "phase_kind",
        "assembly_plan_sha256",
        "complete",
        "runs",
        "usage",
    }
    optional = {"error"}
    if set(value) - (required | optional) or not required.issubset(value):
        raise ValueError(f"Study execution {location} has an unsupported shape")
    runs_value = value.get("runs")
    if not isinstance(runs_value, list):
        raise ValueError(f"Study execution {location}.runs must be a list")
    runs = tuple(
        _load_run_receipt(item, root, f"{location}.runs[{run_index}]")
        for run_index, item in enumerate(runs_value)
    )
    usage = value.get("usage")
    if not isinstance(usage, Mapping) or set(usage) != {"cost_usd", "calls", "tokens", "by_player"}:
        raise ValueError(f"Study execution {location}.usage has an unsupported shape")
    by_player = usage.get("by_player")
    if not isinstance(by_player, Mapping) or any(
        not isinstance(key, str) or not isinstance(amount, (int, float))
        for key, amount in by_player.items()
    ):
        raise ValueError(f"Study execution {location}.usage.by_player is invalid")
    complete = value.get("complete")
    if not isinstance(complete, bool):
        raise ValueError(f"Study execution {location}.complete must be boolean")
    return StudyGroupExecution(
        execution_group_id=_receipt_text(
            value.get("execution_group_id"), f"{location}.execution_group_id"
        ),
        phase_id=_receipt_text(value.get("phase_id"), f"{location}.phase_id"),
        phase_kind=_receipt_text(value.get("phase_kind"), f"{location}.phase_kind"),
        assembly_plan_sha256=_receipt_sha(
            value.get("assembly_plan_sha256"), f"{location}.assembly_plan_sha256"
        ),
        runs=runs,
        complete=complete,
        cost_usd=_receipt_number(usage.get("cost_usd"), f"{location}.usage.cost_usd"),
        calls=_receipt_integer(usage.get("calls"), f"{location}.usage.calls"),
        tokens=_receipt_integer(usage.get("tokens"), f"{location}.usage.tokens"),
        by_player={str(key): float(amount) for key, amount in by_player.items()},
        error=_receipt_optional_text(value.get("error"), f"{location}.error"),
    )


def _load_run_receipt(value: Any, root: Path, location: str) -> StudyRunExecution:
    if not isinstance(value, Mapping):
        raise ValueError(f"Study execution {location} must be a mapping")
    required = {
        "assembly_run",
        "cell_id",
        "expected_matches",
        "record_count",
        "complete",
        "records",
    }
    optional = {"error"}
    if set(value) - (required | optional) or not required.issubset(value):
        raise ValueError(f"Study execution {location} has an unsupported shape")
    records_value = value.get("records")
    if not isinstance(records_value, list):
        raise ValueError(f"Study execution {location}.records must be a list")
    records = tuple(
        _load_record_receipt(item, root, f"{location}.records[{record_index}]")
        for record_index, item in enumerate(records_value)
    )
    count = _receipt_integer(value.get("record_count"), f"{location}.record_count")
    if count != len(records):
        raise ValueError(f"Study execution {location}.record_count does not match records")
    complete = value.get("complete")
    if not isinstance(complete, bool):
        raise ValueError(f"Study execution {location}.complete must be boolean")
    return StudyRunExecution(
        assembly_run=_receipt_text(value.get("assembly_run"), f"{location}.assembly_run"),
        cell_id=_receipt_text(value.get("cell_id"), f"{location}.cell_id"),
        expected_matches=_receipt_integer(
            value.get("expected_matches"), f"{location}.expected_matches"
        ),
        records=records,
        complete=complete,
        error=_receipt_optional_text(value.get("error"), f"{location}.error"),
    )


def _load_record_receipt(value: Any, root: Path, location: str) -> StudyRecordReceipt:
    required = {
        "phase_id",
        "phase_kind",
        "execution_group_id",
        "assembly_run",
        "cell_id",
        "match_index",
        "effective_seed",
        "match_id",
        "record_sha256",
        "path",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError(f"Study execution {location} has an unsupported shape")
    relative = _receipt_text(value.get("path"), f"{location}.path")
    if relative.startswith("/") or "\\" in relative:
        raise ValueError(f"Study execution {location}.path must be portable")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError(f"Study execution {location}.path escapes or is missing")
    return StudyRecordReceipt(
        phase_id=_receipt_text(value.get("phase_id"), f"{location}.phase_id"),
        phase_kind=_receipt_text(value.get("phase_kind"), f"{location}.phase_kind"),
        execution_group_id=_receipt_text(
            value.get("execution_group_id"), f"{location}.execution_group_id"
        ),
        assembly_run=_receipt_text(value.get("assembly_run"), f"{location}.assembly_run"),
        cell_id=_receipt_text(value.get("cell_id"), f"{location}.cell_id"),
        match_index=_receipt_integer(value.get("match_index"), f"{location}.match_index"),
        effective_seed=_receipt_integer(
            value.get("effective_seed"), f"{location}.effective_seed", nonnegative=False
        ),
        match_id=_receipt_text(value.get("match_id"), f"{location}.match_id"),
        record_sha256=_receipt_sha(value.get("record_sha256"), f"{location}.record_sha256"),
        path=resolved,
        relative_path=relative,
    )


def _receipt_text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Study execution {location} must be non-empty text")
    return value


def _receipt_optional_text(value: Any, location: str) -> str | None:
    if value is None:
        return None
    return _receipt_text(value, location)


def _receipt_sha(value: Any, location: str) -> str:
    text = _receipt_text(value, location)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"Study execution {location} must be a lowercase SHA-256")
    return text


def _receipt_integer(value: Any, location: str, *, nonnegative: bool = True) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or (nonnegative and value < 0):
        raise ValueError(f"Study execution {location} must be an integer")
    return value


def _receipt_number(value: Any, location: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Study execution {location} must be numeric")
    return float(value)


def _receipt_text_tuple(value: Any, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"Study execution {location} must be a non-empty list")
    result = tuple(_receipt_text(item, location) for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"Study execution {location} contains duplicates")
    return result


def _study_group_execution(
    study: PreparedStudy,
    group: PreparedExecutionGroup,
    assembly_execution: AssemblyExecution,
    execution_root: Path,
    *,
    error: str | None = None,
) -> StudyGroupExecution:
    phase = next(item for item in study.definition.phases if item.id == group.phase)
    cell_by_run = {
        cell.assembly_run: cell.id
        for cell in study.definition.cells
        if cell.execution_group == group.id
    }
    runs = tuple(
        _study_run_execution(
            phase.id,
            phase.kind,
            group.id,
            cell_by_run[assembly_run.run_name],
            assembly_run,
            execution_root,
        )
        for assembly_run in assembly_execution.runs
    )
    return StudyGroupExecution(
        execution_group_id=group.id,
        phase_id=phase.id,
        phase_kind=phase.kind,
        assembly_plan_sha256=group.prepared_assembly.plan_sha256,
        runs=runs,
        complete=assembly_execution.complete and all(run.complete for run in runs),
        cost_usd=assembly_execution.cost_usd,
        calls=assembly_execution.calls,
        tokens=assembly_execution.tokens,
        by_player=assembly_execution.by_player,
        error=error,
    )


def _study_run_execution(
    phase_id: str,
    phase_kind: str,
    group_id: str,
    cell_id: str,
    run: AssemblyRunExecution,
    execution_root: Path,
) -> StudyRunExecution:
    records = tuple(
        StudyRecordReceipt(
            phase_id=phase_id,
            phase_kind=phase_kind,
            execution_group_id=group_id,
            assembly_run=run.run_name,
            cell_id=cell_id,
            match_index=record.match_index,
            effective_seed=record.effective_seed,
            match_id=record.match_id,
            record_sha256=record.record_sha256,
            path=record.path,
            relative_path=record.path.relative_to(execution_root).as_posix(),
        )
        for record in run.records
    )
    return StudyRunExecution(
        assembly_run=run.run_name,
        cell_id=cell_id,
        expected_matches=run.expected_matches,
        records=records,
        complete=run.complete,
        error=run.error,
    )


def _study_execution(
    study: PreparedStudy,
    selection: StudySelection,
    execution_id: str,
    groups: Sequence[StudyGroupExecution],
    root: Path,
) -> StudyExecution:
    complete = len(groups) == len(selection.execution_group_ids) and all(
        group.complete for group in groups
    )
    provisional = StudyExecution(
        study_id=study.definition.id,
        plan_sha256=study.plan_sha256,
        selection_sha256=selection.selection_sha256,
        execution_group_ids=selection.execution_group_ids,
        execution_id=execution_id,
        groups=tuple(groups),
        complete=complete,
        execution_sha256="",
        execution_root=root,
    )
    return replace(
        provisional,
        execution_sha256=sha256_json(provisional.identity_payload()),
    )


def _empty_assembly_execution(plan_sha256: str) -> AssemblyExecution:
    return AssemblyExecution(
        plan_sha256=plan_sha256,
        runs=(),
        complete=False,
        cost_usd=0.0,
        calls=0,
        tokens=0,
        by_player={},
    )


def _study_usage(groups: Sequence[StudyGroupExecution]) -> dict[str, Any]:
    by_player: dict[str, float] = {}
    for group in groups:
        for player, value in group.by_player.items():
            by_player[player] = by_player.get(player, 0.0) + value
    return {
        "cost_usd": sum(group.cost_usd for group in groups),
        "calls": sum(group.calls for group in groups),
        "tokens": sum(group.tokens for group in groups),
        "by_player": by_player,
    }


def _unique_requested(kind: str, values: Sequence[str]) -> tuple[str, ...]:
    result = tuple(values)
    if not result or any(not isinstance(value, str) or not value for value in result):
        raise ValueError(f"Study {kind} selection must contain non-empty ids")
    if len(set(result)) != len(result):
        raise ValueError(f"Study {kind} selection contains duplicate ids")
    return result


def _execution_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{timestamp}_{uuid4().hex[:12]}"


__all__ = [
    "StudyExecution",
    "StudyExecutionError",
    "StudyGroupExecution",
    "StudyRecordReceipt",
    "StudyRunExecution",
    "StudySelection",
    "execute_prepared_study",
    "load_study_execution",
    "select_study",
]
