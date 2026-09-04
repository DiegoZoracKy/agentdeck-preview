"""Deterministic Measure declarations and evaluation over exact Record corpora."""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import math
import re
import sys
import threading
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, Sequence

import yaml

from ._canonical import freeze_json, sha256_file, sha256_json, thaw_json

_PORTABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_PREPARATION_LOCK = threading.RLock()


class CorpusRecordLike(Protocol):
    record_sha256: str
    payload: Mapping[str, Any]
    cell_id: str
    phase_id: str
    phase_kind: str
    execution_group_id: str
    assembly_run: str
    match_index: int
    effective_seed: int
    match_id: str


class RecordCorpusLike(Protocol):
    @property
    def corpus_sha256(self) -> str: ...

    @property
    def records(self) -> Sequence[Any]: ...


@dataclass(frozen=True)
class MeasureArtifact:
    path: str
    sha256: str
    size: int

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "size": self.size}


@dataclass(frozen=True)
class MeasureDeclaration:
    id: str
    implementation_kind: str
    implementation: str
    parameters: Mapping[str, Any]
    artifacts: tuple[str, ...]
    material_distributions: tuple[str, ...]
    source_path: Path = field(compare=False, repr=False)
    package_root: Path = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", freeze_json(self.parameters))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "material_distributions", tuple(self.material_distributions))

    def as_dict(self) -> dict[str, Any]:
        implementation: dict[str, Any]
        if self.implementation_kind == "builtin":
            implementation = {"builtin": self.implementation}
        else:
            implementation = {
                "entrypoint": self.implementation,
                "artifacts": list(self.artifacts),
            }
        return {
            "id": self.id,
            "implementation": implementation,
            "parameters": thaw_json(self.parameters),
            "material_distributions": list(self.material_distributions),
        }


@dataclass(frozen=True)
class PreparedMeasure:
    schema_version: int
    research_contract_version: str
    declaration: MeasureDeclaration
    implementation_sha256: str
    artifacts: tuple[MeasureArtifact, ...]
    material_environment: Mapping[str, str]
    material_environment_sha256: str
    measure_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(
            self,
            "material_environment",
            MappingProxyType(dict(self.material_environment)),
        )

    @property
    def id(self) -> str:
        return self.declaration.id

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "research_contract_version": self.research_contract_version,
            "declaration": self.declaration.as_dict(),
            "implementation_sha256": self.implementation_sha256,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "material_environment": dict(self.material_environment),
            "material_environment_sha256": self.material_environment_sha256,
            "measure_sha256": self.measure_sha256,
        }


@dataclass(frozen=True)
class MeasureInput:
    corpus_sha256: str
    records: tuple[CorpusRecordLike, ...]
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "parameters", freeze_json(self.parameters))


@dataclass(frozen=True)
class SourceLocator:
    record_sha256: str
    pointer: str

    def as_dict(self) -> dict[str, str]:
        return {"record_sha256": self.record_sha256, "pointer": self.pointer}


@dataclass(frozen=True)
class MeasureDiagnostic:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class MeasureResult:
    metric: str
    dimensions: Mapping[str, Any]
    status: str
    value: Any = None
    unit: str | None = None
    support_count: int | None = None
    support_unit: str | None = None
    sources: tuple[SourceLocator, ...] = ()
    diagnostic: MeasureDiagnostic | None = None
    result_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimensions", freeze_json(self.dimensions))
        object.__setattr__(self, "value", freeze_json(self.value))
        object.__setattr__(self, "sources", tuple(self.sources))

    def identity_payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "metric": self.metric,
            "dimensions": thaw_json(self.dimensions),
            "status": self.status,
        }
        if self.status == "available":
            result["value"] = thaw_json(self.value)
        if self.unit is not None:
            result["unit"] = self.unit
        if self.support_count is not None:
            result["support"] = {"count": self.support_count, "unit": self.support_unit}
        if self.sources:
            result["sources"] = [source.as_dict() for source in self.sources]
        if self.diagnostic is not None:
            result["diagnostic"] = self.diagnostic.as_dict()
        return result

    def as_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "result_sha256": self.result_sha256}


@dataclass(frozen=True)
class MeasureOutput:
    measure_sha256: str
    corpus_sha256: str
    results: tuple[MeasureResult, ...]
    diagnostics: tuple[MeasureDiagnostic, ...]
    output_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "results", tuple(self.results))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "measure_sha256": self.measure_sha256,
            "corpus_sha256": self.corpus_sha256,
            "results": [result.as_dict() for result in self.results],
            "diagnostics": [item.as_dict() for item in self.diagnostics],
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "output_sha256": self.output_sha256}


def load_measure(path: str | Path, measure_id: str) -> MeasureDeclaration:
    """Load one explicit Measure declaration without loading a Study or Records."""

    source = Path(path).expanduser().resolve()
    if source.is_dir():
        source = source / "measures.yaml"
    if not source.is_file():
        raise ValueError(f"Measure manifest is missing: {source}")
    try:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Measure manifest could not be read: {exc}") from exc
    if not isinstance(payload, Mapping) or set(payload) != {"schema_version", "measures"}:
        raise ValueError("Measure manifest must contain only schema_version and measures")
    if payload.get("schema_version") != 1:
        raise ValueError("Measure manifest schema_version must equal 1")
    items = payload.get("measures")
    if not isinstance(items, list) or not items:
        raise ValueError("Measure manifest must contain a non-empty measures list")

    declarations = [_parse_measure(item, index, source) for index, item in enumerate(items)]
    ids = [item.id for item in declarations]
    if len(set(ids)) != len(ids):
        raise ValueError("Measure manifest contains duplicate ids")
    matches = [item for item in declarations if item.id == measure_id]
    if len(matches) != 1:
        raise ValueError(f"Measure id {measure_id!r} is not declared exactly once")
    return matches[0]


def prepare_measure(declaration: MeasureDeclaration) -> PreparedMeasure:
    """Resolve one Measure implementation and its material identity."""

    from agentdeck import __version__
    from .study import RESEARCH_CONTRACT_VERSION

    artifacts: tuple[MeasureArtifact, ...]
    if declaration.implementation_kind == "builtin":
        function = _BUILTINS.get(declaration.implementation)
        if function is None:
            raise ValueError(f"Unknown built-in Measure {declaration.implementation!r}")
        source = inspect.getsource(function).encode("utf-8")
        implementation_sha256 = hashlib.sha256(source).hexdigest()
        artifacts = ()
    else:
        artifacts, function = _prepare_custom_function(declaration)
        implementation_sha256 = next(
            artifact.sha256
            for artifact in artifacts
            if artifact.path == declaration.implementation.split(":", 1)[0]
        )
        if not callable(function):
            raise ValueError("Custom Measure entrypoint must resolve to a callable")

    environment: dict[str, str] = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "agentdeck": str(__version__),
    }
    for distribution in declaration.material_distributions:
        try:
            environment[f"distribution:{distribution}"] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ValueError(f"Material distribution is unavailable: {distribution}") from exc
    environment_sha256 = sha256_json(environment)
    identity = {
        "schema_version": 1,
        "research_contract_version": RESEARCH_CONTRACT_VERSION,
        "declaration": declaration.as_dict(),
        "implementation_sha256": implementation_sha256,
        "artifacts": [artifact.as_dict() for artifact in artifacts],
        "material_environment": environment,
    }
    return PreparedMeasure(
        schema_version=1,
        research_contract_version=RESEARCH_CONTRACT_VERSION,
        declaration=declaration,
        implementation_sha256=implementation_sha256,
        artifacts=artifacts,
        material_environment=environment,
        material_environment_sha256=environment_sha256,
        measure_sha256=sha256_json(identity),
    )


def evaluate_measure(prepared: PreparedMeasure, corpus: RecordCorpusLike) -> MeasureOutput:
    """Evaluate one prepared deterministic Measure over one exact Record corpus."""

    current = prepare_measure(prepared.declaration)
    if current.measure_sha256 != prepared.measure_sha256:
        raise ValueError(
            "Prepared Measure changed before evaluation: "
            f"expected {prepared.measure_sha256}, observed {current.measure_sha256}"
        )
    if not isinstance(corpus.corpus_sha256, str) or len(corpus.corpus_sha256) != 64:
        raise ValueError("Measure requires an identified RecordCorpus")
    measure_input = MeasureInput(
        corpus_sha256=corpus.corpus_sha256,
        records=tuple(corpus.records),
        parameters=prepared.declaration.parameters,
    )
    function = _resolve_function(prepared.declaration)
    raw = function(measure_input)
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise ValueError("Measure implementation must return a sequence of results")
    results = tuple(_prepare_result(item, corpus) for item in raw)
    if not results:
        raise ValueError("Measure implementation must return at least one result")
    identities = [
        (item.metric, json.dumps(thaw_json(item.dimensions), sort_keys=True)) for item in results
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("Measure output contains duplicate metric/dimensions pairs")
    ordered = tuple(
        sorted(
            results,
            key=lambda item: (
                item.metric,
                json.dumps(thaw_json(item.dimensions), sort_keys=True),
            ),
        )
    )
    identity = {
        "schema_version": 1,
        "measure_sha256": prepared.measure_sha256,
        "corpus_sha256": corpus.corpus_sha256,
        "results": [item.as_dict() for item in ordered],
        "diagnostics": [],
    }
    return MeasureOutput(
        measure_sha256=prepared.measure_sha256,
        corpus_sha256=corpus.corpus_sha256,
        results=ordered,
        diagnostics=(),
        output_sha256=sha256_json(identity),
    )


def _parse_measure(value: Any, index: int, source: Path) -> MeasureDeclaration:
    location = f"measures[{index}]"
    if not isinstance(value, Mapping):
        raise ValueError(f"{location} must be a mapping")
    allowed = {"id", "implementation", "parameters", "material_distributions"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{location} contains unsupported fields: {', '.join(sorted(unknown))}")
    measure_id = value.get("id")
    if not isinstance(measure_id, str) or not _PORTABLE_ID.fullmatch(measure_id):
        raise ValueError(f"{location}.id must be a portable lowercase identifier")
    implementation = value.get("implementation")
    if not isinstance(implementation, Mapping):
        raise ValueError(f"{location}.implementation must be a mapping")
    implementation_keys = set(implementation)
    if "builtin" in implementation_keys:
        if implementation_keys != {"builtin"}:
            raise ValueError(f"{location}.implementation builtin cannot have other fields")
        kind = "builtin"
        target = implementation.get("builtin")
        artifacts: tuple[str, ...] = ()
    else:
        if implementation_keys - {"entrypoint", "artifacts"} or "entrypoint" not in implementation:
            raise ValueError(f"{location}.implementation must declare builtin or entrypoint")
        kind = "custom"
        target = implementation.get("entrypoint")
        raw_artifacts = implementation.get("artifacts", [])
        if not isinstance(raw_artifacts, list):
            raise ValueError(f"{location}.implementation.artifacts must be a list")
        artifacts = tuple(
            _portable_path(item, f"{location}.implementation.artifacts") for item in raw_artifacts
        )
    if not isinstance(target, str) or not target:
        raise ValueError(f"{location}.implementation target must be non-empty")
    if kind == "custom":
        if target.count(":") != 1:
            raise ValueError(f"{location}.implementation.entrypoint must be path.py:function")
        file_name, function_name = target.split(":", 1)
        _portable_path(file_name, f"{location}.implementation.entrypoint")
        if not function_name.isidentifier():
            raise ValueError(f"{location}.implementation function must be an identifier")
    parameters = value.get("parameters", {})
    if not isinstance(parameters, Mapping):
        raise ValueError(f"{location}.parameters must be a mapping")
    sha256_json(parameters)
    distributions = value.get("material_distributions", [])
    if not isinstance(distributions, list) or any(
        not isinstance(item, str) or not item for item in distributions
    ):
        raise ValueError(f"{location}.material_distributions must be a list of names")
    if len(set(distributions)) != len(distributions):
        raise ValueError(f"{location}.material_distributions contains duplicates")
    return MeasureDeclaration(
        id=measure_id,
        implementation_kind=kind,
        implementation=target,
        parameters=parameters,
        artifacts=artifacts,
        material_distributions=tuple(distributions),
        source_path=source,
        package_root=source.parent,
    )


def _prepare_custom_function(
    declaration: MeasureDeclaration,
) -> tuple[tuple[MeasureArtifact, ...], Callable[[MeasureInput], Sequence[Any]]]:
    file_name = declaration.implementation.split(":", 1)[0]
    paths = {file_name, *declaration.artifacts}
    artifacts: list[MeasureArtifact] = []
    for relative in sorted(paths):
        path = _resolve_inside(declaration.package_root, relative)
        payload = path.read_bytes()
        artifacts.append(
            MeasureArtifact(
                path=relative,
                sha256=hashlib.sha256(payload).hexdigest(),
                size=len(payload),
            )
        )
    return tuple(artifacts), _load_custom_function(declaration)


def _resolve_function(
    declaration: MeasureDeclaration,
) -> Callable[[MeasureInput], Sequence[Any]]:
    if declaration.implementation_kind == "builtin":
        return _BUILTINS[declaration.implementation]
    return _load_custom_function(declaration)


def _load_custom_function(
    declaration: MeasureDeclaration,
) -> Callable[[MeasureInput], Sequence[Any]]:
    file_name, function_name = declaration.implementation.split(":", 1)
    path = _resolve_inside(declaration.package_root, file_name)
    module_name = f"agentdeck_measure_{sha256_file(path)[:24]}"
    with _PREPARATION_LOCK:
        package_root = declaration.package_root.resolve()
        previous_modules = {
            name: module
            for name, module in sys.modules.items()
            if _module_is_inside(module, package_root)
        }
        for name in previous_modules:
            sys.modules.pop(name, None)
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not load custom Measure entrypoint: {file_name}")
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(declaration.package_root))
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            function = getattr(module, function_name, None)
            if not callable(function):
                raise ValueError(f"Custom Measure function is missing: {function_name}")
            return function
        finally:
            sys.modules.pop(module_name, None)
            for name in tuple(sys.modules):
                candidate_module = sys.modules.get(name)
                if candidate_module is not None and _module_is_inside(
                    candidate_module, package_root
                ):
                    sys.modules.pop(name, None)
            sys.modules.update(previous_modules)
            sys.path.pop(0)
            sys.dont_write_bytecode = previous


def _module_is_inside(module: Any, root: Path) -> bool:
    source = getattr(module, "__file__", None)
    if not isinstance(source, str):
        return False
    try:
        return Path(source).resolve().is_relative_to(root)
    except (OSError, RuntimeError):
        return False


def _prepare_result(value: Any, corpus: RecordCorpusLike) -> MeasureResult:
    if isinstance(value, MeasureResult):
        payload = value.identity_payload()
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise ValueError("Measure results must be mappings or MeasureResult values")
    allowed = {
        "metric",
        "dimensions",
        "status",
        "value",
        "unit",
        "support",
        "sources",
        "diagnostic",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(
            f"Measure result contains unsupported fields: {', '.join(sorted(unknown))}"
        )
    metric = payload.get("metric")
    if not isinstance(metric, str) or not _PORTABLE_ID.fullmatch(metric):
        raise ValueError("Measure result metric must be a portable lowercase identifier")
    dimensions = payload.get("dimensions", {})
    if not isinstance(dimensions, Mapping) or any(
        not isinstance(key, str) or not _PORTABLE_ID.fullmatch(key) for key in dimensions
    ):
        raise ValueError("Measure result dimensions must be a flat portable mapping")
    for item in dimensions.values():
        _validate_scalar(item, "Measure result dimension")
    status = payload.get("status")
    if status not in {"available", "unavailable"}:
        raise ValueError("Measure result status must be available or unavailable")
    raw_value = payload.get("value")
    raw_diagnostic = payload.get("diagnostic")
    if status == "available":
        if "value" not in payload:
            raise ValueError("Available Measure result requires value")
        _validate_result_value(raw_value)
        if raw_diagnostic is not None:
            raise ValueError("Available Measure result cannot have a diagnostic")
    else:
        if "value" in payload:
            raise ValueError("Unavailable Measure result cannot have a value")
        if not isinstance(raw_diagnostic, Mapping):
            raise ValueError("Unavailable Measure result requires diagnostic")
    unit = payload.get("unit")
    if unit is not None and (not isinstance(unit, str) or not _PORTABLE_ID.fullmatch(unit)):
        raise ValueError("Measure result unit must be a portable identifier")
    support = payload.get("support")
    support_count: int | None = None
    support_unit: str | None = None
    if support is not None:
        if not isinstance(support, Mapping) or set(support) != {"count", "unit"}:
            raise ValueError("Measure result support must contain count and unit")
        support_count = support.get("count")
        support_unit = support.get("unit")
        if (
            not isinstance(support_count, int)
            or isinstance(support_count, bool)
            or support_count < 0
        ):
            raise ValueError("Measure result support count must be an integer >= 0")
        if not isinstance(support_unit, str) or not _PORTABLE_ID.fullmatch(support_unit):
            raise ValueError("Measure result support unit must be portable")
    sources = tuple(_source_locator(item, corpus) for item in payload.get("sources", []))
    diagnostic = None
    if raw_diagnostic is not None:
        code = raw_diagnostic.get("code")
        message = raw_diagnostic.get("message")
        if not isinstance(code, str) or not _PORTABLE_ID.fullmatch(code):
            raise ValueError("Measure diagnostic code must be portable")
        if not isinstance(message, str) or not message:
            raise ValueError("Measure diagnostic message must be non-empty")
        diagnostic = MeasureDiagnostic(code, message)
    provisional = MeasureResult(
        metric=metric,
        dimensions=dimensions,
        status=status,
        value=raw_value,
        unit=unit,
        support_count=support_count,
        support_unit=support_unit,
        sources=sources,
        diagnostic=diagnostic,
    )
    return replace(
        provisional,
        result_sha256=sha256_json(provisional.identity_payload()),
    )


def _source_locator(value: Any, corpus: RecordCorpusLike) -> SourceLocator:
    if not isinstance(value, Mapping) or set(value) != {"record_sha256", "pointer"}:
        raise ValueError("SourceLocator must contain record_sha256 and pointer")
    record_hash = value.get("record_sha256")
    pointer = value.get("pointer")
    if not isinstance(record_hash, str) or not isinstance(pointer, str):
        raise ValueError("SourceLocator fields must be strings")
    records = {record.record_sha256: record for record in corpus.records}
    if record_hash not in records:
        raise ValueError(f"SourceLocator references Record outside corpus: {record_hash}")
    _resolve_json_pointer(records[record_hash].payload, pointer)
    return SourceLocator(record_hash, pointer)


def _resolve_json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid RFC 6901 JSON Pointer: {pointer!r}")
    current = value
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if part not in current:
                raise ValueError(f"JSON Pointer does not resolve: {pointer!r}")
            current = current[part]
        elif isinstance(current, (list, tuple)):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"JSON Pointer does not resolve: {pointer!r}") from exc
        else:
            raise ValueError(f"JSON Pointer does not resolve: {pointer!r}")
    return current


def _portable_path(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"{location} must be a non-empty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value == ".":
        raise ValueError(f"{location} must remain inside the Measure package")
    return path.as_posix()


def _resolve_inside(root: Path, relative: str) -> Path:
    path = (root / PurePosixPath(relative)).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Measure source must be a regular file inside its package: {relative}")
    return path


def _validate_scalar(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    raise ValueError(f"{label} must be a finite JSON scalar")


def _validate_result_value(value: Any) -> None:
    if isinstance(value, (list, tuple)):
        if not value:
            raise ValueError("Available Measure result list cannot be empty")
        for item in value:
            _validate_scalar(item, "Measure result value")
        return
    if value is None:
        raise ValueError("Available Measure result value cannot be null")
    _validate_scalar(value, "Measure result value")


def _builtin_record_count(input_value: MeasureInput) -> Sequence[Mapping[str, Any]]:
    counts: dict[str, int] = {}
    for record in input_value.records:
        counts[record.cell_id] = counts.get(record.cell_id, 0) + 1
    return [
        {
            "metric": "record-count",
            "dimensions": {"cell": cell},
            "status": "available",
            "value": count,
            "unit": "count",
            "support": {"count": count, "unit": "records"},
        }
        for cell, count in sorted(counts.items())
    ]


def _builtin_total_cost(input_value: MeasureInput) -> Sequence[Mapping[str, Any]]:
    totals: dict[str, float] = {}
    for record in input_value.records:
        metadata = record.payload.get("metadata") or {}
        match = metadata.get("match") if isinstance(metadata, Mapping) else {}
        cost = match.get("cost") if isinstance(match, Mapping) else None
        if cost is None:
            return [
                {
                    "metric": "total-cost",
                    "dimensions": {},
                    "status": "unavailable",
                    "diagnostic": {
                        "code": "measure.input-missing",
                        "message": "at least one Record has no metadata.match.cost",
                    },
                }
            ]
        totals[record.cell_id] = totals.get(record.cell_id, 0.0) + float(cost)
    return [
        {
            "metric": "total-cost",
            "dimensions": {"cell": cell},
            "status": "available",
            "value": value,
            "unit": "usd",
            "support": {
                "count": sum(1 for record in input_value.records if record.cell_id == cell),
                "unit": "records",
            },
        }
        for cell, value in sorted(totals.items())
    ]


_BUILTINS: dict[str, Callable[[MeasureInput], Sequence[Any]]] = {
    "record-count": _builtin_record_count,
    "total-cost": _builtin_total_cost,
}


__all__ = [
    "MeasureArtifact",
    "MeasureDeclaration",
    "MeasureDiagnostic",
    "MeasureInput",
    "MeasureOutput",
    "MeasureResult",
    "PreparedMeasure",
    "SourceLocator",
    "evaluate_measure",
    "load_measure",
    "prepare_measure",
]
