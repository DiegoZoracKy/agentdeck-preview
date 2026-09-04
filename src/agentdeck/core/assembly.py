"""Content-addressed preparation and execution of complete AgentDeck assemblies."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import os
import re
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

from .agentdeck import AgentDeck
from .base import Game, Player, Spectator
from .provider_call_journal import (
    FilesystemProviderCallJournal,
    ProviderCallJournal,
)
from .session import AgentDeckConfig
from ..monitors.base import Monitor

_CREDENTIAL_KEYS = {
    "api_key",
    "access_token",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}
_SAFE_RUN_NAME = re.compile(r"[^a-zA-Z0-9_.-]+")
_PREPARATION_LOCK = threading.RLock()
_EXECUTION_RECEIPT_NAME = "assembly-execution.json"


@dataclass(frozen=True)
class PlayerFactory:
    """Credential-free declaration of one Player constructor."""

    player_type: type[Player]
    kwargs: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not inspect.isclass(self.player_type) or not issubclass(self.player_type, Player):
            raise ValueError("PlayerFactory.player_type must be an AgentDeck Player class")
        if not isinstance(self.kwargs, Mapping):
            raise ValueError("PlayerFactory.kwargs must be a mapping")
        name = self.kwargs.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("PlayerFactory.kwargs must contain a non-empty Player name")
        forbidden = sorted(_credential_locations(self.kwargs, "player.kwargs"))
        if forbidden:
            raise ValueError(
                "PlayerFactory credentials are execution-host capabilities, not assembly "
                f"configuration: {', '.join(forbidden)}"
            )

    @property
    def name(self) -> str:
        return str(self.kwargs["name"])

    def create(self) -> Player:
        """Instantiate the declared Player when execution has authority."""

        return self.player_type(**copy.deepcopy(dict(self.kwargs)))

    def describe(self) -> dict[str, Any]:
        provider = getattr(self.player_type, "PROVIDER", None)
        descriptor: dict[str, Any] = {
            "player_type": _class_identity(self.player_type),
            "kwargs": _describe_value(dict(self.kwargs), "player.kwargs"),
        }
        if provider:
            descriptor["provider"] = str(provider)
        model = self.kwargs.get("model")
        if model is not None:
            descriptor["model"] = str(model)
        return descriptor


@dataclass(frozen=True)
class AssemblyRun:
    """One exact AgentDeck.play call inside an Assembly."""

    name: str
    game: Game
    players: Sequence[PlayerFactory]
    matches: int = 1
    seed: int | None = None
    session: AgentDeckConfig = field(default_factory=AgentDeckConfig)
    spectators: Sequence[Spectator] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("AssemblyRun.name must be non-empty")
        if not isinstance(self.game, Game):
            raise ValueError("AssemblyRun.game must be an AgentDeck Game")
        if not isinstance(self.matches, int) or self.matches < 1:
            raise ValueError("AssemblyRun.matches must be an integer >= 1")
        if self.seed is not None and not isinstance(self.seed, int):
            raise ValueError("AssemblyRun.seed must be an integer or None")
        if not isinstance(self.session, AgentDeckConfig):
            raise ValueError("AssemblyRun.session must be AgentDeckConfig")
        players = tuple(self.players)
        if not players:
            raise ValueError("AssemblyRun.players cannot be empty")
        if any(not isinstance(player, PlayerFactory) for player in players):
            raise ValueError("AssemblyRun.players must contain only PlayerFactory values")
        names = [player.name for player in players]
        if len(names) != len(set(names)):
            raise ValueError("AssemblyRun Player names must be unique")
        if any(not isinstance(spectator, Spectator) for spectator in self.spectators):
            raise ValueError("AssemblyRun.spectators must contain only AgentDeck Spectators")

    def describe(self) -> dict[str, Any]:
        session = {
            item.name: _describe_value(getattr(self.session, item.name), f"session.{item.name}")
            for item in fields(self.session)
            if item.name != "run_dir"
            and not (
                item.metadata.get("prepared_identity_omit_default")
                and getattr(self.session, item.name) == item.default
            )
        }
        return {
            "name": self.name,
            "game": {
                "configuration": _describe_value(self.game.describe(), "game.describe"),
                "version": _describe_value(self.game.describe_version(), "game.version"),
            },
            "players": [player.describe() for player in self.players],
            "matches": self.matches,
            "seed": self.seed,
            "session": session,
            "output_root": "execution_host",
            "spectators": [
                _describe_value(spectator, f"spectators[{index}]")
                for index, spectator in enumerate(self.spectators)
            ],
        }


@dataclass(frozen=True)
class Assembly:
    """Complete AgentDeck execution composition."""

    runs: Sequence[AssemblyRun]

    def __post_init__(self) -> None:
        runs = tuple(self.runs)
        if not runs:
            raise ValueError("Assembly.runs cannot be empty")
        if any(not isinstance(run, AssemblyRun) for run in runs):
            raise ValueError("Assembly.runs must contain only AssemblyRun values")
        names = [run.name for run in runs]
        if len(names) != len(set(names)):
            raise ValueError("Assembly run names must be unique")

    def describe(self) -> dict[str, Any]:
        return {"runs": [run.describe() for run in self.runs]}


@dataclass(frozen=True)
class AssemblyArtifact:
    path: str
    sha256: str
    size: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreparedAssembly:
    schema_version: int
    engine: str
    engine_version: str
    entrypoint: str
    artifacts: tuple[AssemblyArtifact, ...]
    assembly: Mapping[str, Any]
    plan_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "assembly", _freeze_json(self.assembly))

    @property
    def total_matches(self) -> int:
        return sum(int(run["matches"]) for run in self.assembly["runs"])

    @property
    def provider_requirements(self) -> tuple[Mapping[str, str], ...]:
        requirements: list[Mapping[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for run in self.assembly["runs"]:
            for player in run["players"]:
                provider = player.get("provider")
                model = player.get("model")
                if not provider or not model:
                    continue
                key = (str(provider), str(model))
                if key in seen:
                    continue
                seen.add(key)
                requirements.append(MappingProxyType({"provider": key[0], "model": key[1]}))
        return tuple(requirements)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "entrypoint": self.entrypoint,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "assembly": _thaw_json(self.assembly),
            "total_matches": self.total_matches,
            "provider_requirements": [dict(item) for item in self.provider_requirements],
            "plan_sha256": self.plan_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PreparedAssembly":
        return cls(
            schema_version=int(value["schema_version"]),
            engine=str(value["engine"]),
            engine_version=str(value["engine_version"]),
            entrypoint=str(value["entrypoint"]),
            artifacts=tuple(
                AssemblyArtifact(
                    path=str(artifact["path"]),
                    sha256=str(artifact["sha256"]),
                    size=int(artifact["size"]),
                )
                for artifact in value["artifacts"]
            ),
            assembly=dict(value["assembly"]),
            plan_sha256=str(value["plan_sha256"]),
        )


@dataclass(frozen=True)
class AssemblyRecordReceipt:
    """Exact binding from one canonical Record to its Assembly match slot."""

    run_name: str
    match_index: int
    effective_seed: int
    match_id: str
    record_sha256: str
    path: Path
    relative_path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_name": self.run_name,
            "match_index": self.match_index,
            "effective_seed": self.effective_seed,
            "match_id": self.match_id,
            "record_sha256": self.record_sha256,
            "path": self.relative_path,
        }


@dataclass(frozen=True)
class AssemblyRunExecution:
    """Execution receipt for one exact AssemblyRun."""

    run_name: str
    expected_matches: int
    records: tuple[AssemblyRecordReceipt, ...]
    complete: bool
    custody: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "custody", MappingProxyType(dict(self.custody)))

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "run_name": self.run_name,
            "expected_matches": self.expected_matches,
            "record_count": len(self.records),
            "complete": self.complete,
            "records": [record.as_dict() for record in self.records],
            "provider_call_custody": _thaw_json(self.custody),
        }
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class AssemblyExecution:
    plan_sha256: str
    runs: tuple[AssemblyRunExecution, ...]
    complete: bool
    cost_usd: float
    calls: int
    tokens: int
    by_player: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "runs", tuple(self.runs))
        object.__setattr__(self, "by_player", MappingProxyType(dict(self.by_player)))

    @property
    def records(self) -> tuple[Path, ...]:
        return tuple(record.path for run in self.runs for record in run.records)

    @property
    def provider_call_custody(self) -> dict[str, Any]:
        summaries = [{"run_name": run.run_name, **_thaw_json(run.custody)} for run in self.runs]
        return {
            "runs": summaries,
            "outcome_unknown": sum(
                int(run.custody.get("outcome_unknown") or 0) for run in self.runs
            ),
            "response_committed": sum(
                int(run.custody.get("response_committed") or 0) for run in self.runs
            ),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_sha256": self.plan_sha256,
            "complete": self.complete,
            "runs": [run.as_dict() for run in self.runs],
            "provider_call_custody": self.provider_call_custody,
            "usage": {
                "cost_usd": self.cost_usd,
                "calls": self.calls,
                "tokens": self.tokens,
                "by_player": dict(self.by_player),
            },
        }


class AssemblyExecutionError(RuntimeError):
    """Raised with the best available receipt for a partial Assembly execution."""

    def __init__(self, message: str, execution: AssemblyExecution) -> None:
        self.execution = execution
        super().__init__(message)


def prepare_assembly(
    entrypoint: str | Path,
    *,
    artifacts: Iterable[str | Path] = (),
) -> PreparedAssembly:
    """Load and content-address a complete Assembly without creating Players."""

    prepared, _ = _load_and_prepare(entrypoint, artifacts=artifacts)
    return prepared


def execute_prepared_assembly(
    entrypoint: str | Path,
    prepared: PreparedAssembly,
    *,
    output_root: str | Path,
    runtime_monitor_factory: Callable[[str], Iterable[Monitor]] | None = None,
) -> AssemblyExecution:
    """Reload and execute an Assembly only when its prepared identity still matches."""

    source_root = Path(entrypoint).resolve().parent
    artifact_paths = [source_root / artifact.path for artifact in prepared.artifacts]
    current, assembly = _load_and_prepare(entrypoint, artifacts=artifact_paths)
    if current.plan_sha256 != prepared.plan_sha256:
        raise ValueError(
            "Prepared AgentDeck assembly changed before execution: "
            f"expected {prepared.plan_sha256}, observed {current.plan_sha256}"
        )

    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt_path = root / _EXECUTION_RECEIPT_NAME
    if receipt_path.exists():
        raise ValueError(
            "Assembly output root already contains an execution receipt: " f"{receipt_path}"
        )
    run_receipts: list[AssemblyRunExecution] = []
    for index, run in enumerate(assembly.runs, start=1):
        run_dir = root / f"{index:02d}_{_safe_run_name(run.name)}"
        config = replace(run.session, run_dir=str(run_dir))
        results_count = 0
        failure: Exception | None = None
        record_directory: Path | None = None
        provider_call_journal: ProviderCallJournal | None = None
        try:
            runtime_monitors = (
                list(runtime_monitor_factory(run.name))
                if runtime_monitor_factory is not None
                else []
            )
            players = [factory.create() for factory in run.players]
            with AgentDeck(
                game=run.game,
                spectators=list(run.spectators) or None,
                session=config,
                runtime_monitors=runtime_monitors,
            ) as deck:
                record_directory = Path(deck.session.record_directory)
                provider_call_journal = deck.provider_call_journal
                results = deck.play(players=players, matches=run.matches, seed=run.seed)
                results_count = len(results)
        except Exception as exc:
            failure = exc

        paths = (
            sorted(record_directory.glob("match_*.json"))
            if record_directory is not None and record_directory.exists()
            else []
        )
        try:
            records = _assembly_record_receipts(run.name, paths, root)
        except Exception as exc:
            records = ()
            failure = failure or exc

        custody = _provider_call_custody_summary(
            required_mode=run.session.provider_call_custody,
            journal=provider_call_journal,
            record_paths=paths,
        )

        complete = failure is None and results_count == run.matches and len(records) == run.matches
        if not complete:
            detail = (
                str(failure)
                if failure is not None
                else (
                    f"expected {run.matches} canonical Records; "
                    f"observed results={results_count} records={len(records)}"
                )
            )
            run_receipts.append(
                AssemblyRunExecution(
                    run_name=run.name,
                    expected_matches=run.matches,
                    records=records,
                    complete=False,
                    custody=custody,
                    error=detail,
                )
            )
            partial = _assembly_execution(prepared.plan_sha256, run_receipts, complete=False)
            _persist_execution_receipt(receipt_path, partial)
            error = AssemblyExecutionError(
                f"Assembly run {run.name!r} failed: {detail}",
                partial,
            )
            if failure is not None:
                raise error from failure
            raise error

        run_receipts.append(
            AssemblyRunExecution(
                run_name=run.name,
                expected_matches=run.matches,
                records=records,
                complete=True,
                custody=custody,
            )
        )

    execution = _assembly_execution(prepared.plan_sha256, run_receipts, complete=True)
    _persist_execution_receipt(receipt_path, execution)
    return execution


def _persist_execution_receipt(path: Path, execution: AssemblyExecution) -> None:
    """Commit one terminal Assembly receipt before control returns downstream."""

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(
                execution.as_dict(),
                stream,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise ValueError(f"Assembly execution receipt already exists: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _load_and_prepare(
    entrypoint: str | Path,
    *,
    artifacts: Iterable[str | Path],
) -> tuple[PreparedAssembly, Assembly]:
    with _PREPARATION_LOCK:
        return _load_and_prepare_unlocked(entrypoint, artifacts=artifacts)


def _load_and_prepare_unlocked(
    entrypoint: str | Path,
    *,
    artifacts: Iterable[str | Path],
) -> tuple[PreparedAssembly, Assembly]:
    path = Path(entrypoint).resolve()
    if not path.is_file():
        raise ValueError(f"AgentDeck assembly entrypoint is missing: {path}")

    source_root = path.parent
    declared = {_resolve_source_artifact(source_root, Path(artifact)) for artifact in artifacts}
    declared.add(path)
    identities = tuple(_artifact_identity(artifact, source_root) for artifact in sorted(declared))
    entrypoint_identity = next(
        identity
        for identity in identities
        if identity.path == path.relative_to(source_root).as_posix()
    )
    module_name = f"agentdeck_assembly_{entrypoint_identity.sha256[:24]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"AgentDeck could not load assembly entrypoint: {path}")
    module = importlib.util.module_from_spec(spec)
    shadowed_modules = _remove_source_modules(source_root)
    sys.modules[module_name] = module
    sys.path.insert(0, str(path.parent))
    previous_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
        factory = getattr(module, "create_assembly", None)
        if not callable(factory):
            raise ValueError("AgentDeck assembly entrypoint must export create_assembly()")
        assembly = factory()
        if not isinstance(assembly, Assembly):
            raise ValueError("create_assembly() must return agentdeck.Assembly")
        descriptor = assembly.describe()
        _bind_prepared_game_versions(assembly, descriptor)
        engine_version = _engine_version()
        payload = {
            "schema_version": 1,
            "engine": "agentdeck",
            "engine_version": engine_version,
            "entrypoint": path.relative_to(source_root).as_posix(),
            "artifacts": [artifact.as_dict() for artifact in identities],
            "assembly": descriptor,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        prepared = PreparedAssembly(
            schema_version=1,
            engine="agentdeck",
            engine_version=engine_version,
            entrypoint=path.relative_to(source_root).as_posix(),
            artifacts=identities,
            assembly=descriptor,
            plan_sha256=hashlib.sha256(canonical).hexdigest(),
        )
        return prepared, assembly
    finally:
        sys.dont_write_bytecode = previous_dont_write_bytecode
        if sys.path and sys.path[0] == str(path.parent):
            sys.path.pop(0)
        _remove_source_modules(source_root)
        sys.modules.update(shadowed_modules)


def _bind_prepared_game_versions(
    assembly: Assembly,
    descriptor: Mapping[str, Any],
) -> None:
    """Keep the prepared Game identity available after source modules unload."""

    described_runs = descriptor.get("runs")
    if not isinstance(described_runs, list) or len(described_runs) != len(assembly.runs):
        raise ValueError("Prepared Assembly Game identities do not match its runs")
    for run, described_run in zip(assembly.runs, described_runs):
        game_version = described_run.get("game", {}).get("version")
        if not isinstance(game_version, Mapping):
            raise ValueError(f"Assembly run {run.name!r} has no prepared Game identity")
        setattr(
            run.game,
            "_agentdeck_prepared_game_version",
            copy.deepcopy(dict(game_version)),
        )


def _resolve_source_artifact(source_root: Path, path: Path) -> Path:
    resolved = path.resolve() if path.is_absolute() else (source_root / path).resolve()
    if not resolved.is_relative_to(source_root):
        raise ValueError("AgentDeck assembly artifacts must be inside the entrypoint directory")
    return resolved


def _credential_locations(value: Any, location: str) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child = f"{location}.{key_text}"
            if key_text.strip().lower() in _CREDENTIAL_KEYS:
                found.add(child)
            found.update(_credential_locations(item, child))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.update(_credential_locations(item, f"{location}[{index}]"))
    return found


def _remove_source_modules(source_root: Path) -> dict[str, Any]:
    removed: dict[str, Any] = {}
    for name, module in tuple(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            candidate = Path(module_file).resolve()
        except (OSError, RuntimeError):
            continue
        if candidate.is_relative_to(source_root):
            removed[name] = module
            sys.modules.pop(name, None)
    return removed


def _artifact_identity(path: Path, source_root: Path) -> AssemblyArtifact:
    if not path.is_file():
        raise ValueError(f"AgentDeck assembly artifact is missing: {path}")
    payload = path.read_bytes()
    return AssemblyArtifact(
        path=path.relative_to(source_root).as_posix(),
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
    )


def _class_identity(value: type[Any]) -> dict[str, str]:
    return {"module": value.__module__, "name": value.__qualname__}


def _describe_value(value: Any, location: str) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError(f"AgentDeck assembly contains a non-finite float at {location}")
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, type):
        return {"class": _class_identity(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _describe_value(item, f"{location}.{key}")
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_describe_value(item, f"{location}[{index}]") for index, item in enumerate(value)]
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "type": _class_identity(value.__class__),
            "fields": _describe_value(asdict(value), f"{location}.fields"),
        }
    describe = getattr(value, "describe", None)
    if callable(describe):
        return {
            "type": _class_identity(value.__class__),
            "configuration": _describe_value(describe(), f"{location}.describe"),
        }
    state = {
        key: item
        for key, item in vars(value).items()
        if not key.startswith("_") and not callable(item)
    }
    if state:
        return {
            "type": _class_identity(value.__class__),
            "configuration": _describe_value(state, f"{location}.state"),
        }
    if hasattr(value, "__class__"):
        return {"type": _class_identity(value.__class__)}
    raise ValueError(
        f"AgentDeck assembly value at {location} is not describable: {type(value).__name__}"
    )


def _freeze_json(value: Any) -> Any:
    """Return a deeply immutable representation of one JSON-compatible value."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    """Return a detached mutable JSON representation for serialization."""

    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _safe_run_name(name: str) -> str:
    value = _SAFE_RUN_NAME.sub("_", name.strip()).strip("._")
    if not value:
        raise ValueError(f"Assembly run name has no safe output representation: {name!r}")
    return value[:80]


def _engine_version() -> str:
    try:
        from agentdeck import __version__

        return str(__version__)
    except (ImportError, AttributeError):
        return "unknown"


def _assembly_record_receipts(
    run_name: str,
    paths: Sequence[Path],
    output_root: Path,
) -> tuple[AssemblyRecordReceipt, ...]:
    receipts: list[AssemblyRecordReceipt] = []
    seen_indices: set[int] = set()
    seen_match_ids: set[str] = set()
    for path in paths:
        payload_bytes = path.read_bytes()
        payload = json.loads(payload_bytes)
        metadata = payload.get("metadata")
        context = metadata.get("context") if isinstance(metadata, Mapping) else None
        match_index = context.get("match_index") if isinstance(context, Mapping) else None
        match_id = payload.get("match_id")
        effective_seed = payload.get("seed")
        if not isinstance(match_index, int) or isinstance(match_index, bool) or match_index < 0:
            raise ValueError(f"canonical Record {path.name!r} has no valid match slot")
        if not isinstance(match_id, str) or not match_id:
            raise ValueError(f"canonical Record {path.name!r} has no valid match_id")
        if not isinstance(effective_seed, int) or isinstance(effective_seed, bool):
            raise ValueError(f"canonical Record {path.name!r} has no valid effective seed")
        if match_index in seen_indices:
            raise ValueError(
                f"Assembly run {run_name!r} emitted duplicate match slot {match_index}"
            )
        if match_id in seen_match_ids:
            raise ValueError(f"Assembly run {run_name!r} emitted duplicate match_id {match_id!r}")
        seen_indices.add(match_index)
        seen_match_ids.add(match_id)
        resolved = path.resolve()
        receipts.append(
            AssemblyRecordReceipt(
                run_name=run_name,
                match_index=match_index,
                effective_seed=effective_seed,
                match_id=match_id,
                record_sha256=hashlib.sha256(payload_bytes).hexdigest(),
                path=resolved,
                relative_path=resolved.relative_to(output_root).as_posix(),
            )
        )
    receipts.sort(key=lambda receipt: receipt.match_index)
    return tuple(receipts)


def _assembly_execution(
    plan_sha256: str,
    runs: Sequence[AssemblyRunExecution],
    *,
    complete: bool,
) -> AssemblyExecution:
    paths = [record.path for run in runs for record in run.records]
    usage = _usage_from_records(paths)
    for run in runs:
        extra = run.custody.get("known_unincorporated_usage") or {}
        usage["cost_usd"] += float(extra.get("cost_usd") or 0.0)
        usage["calls"] += int(extra.get("calls") or 0)
        usage["tokens"] += int(extra.get("tokens") or 0)
        for name, amount in (extra.get("by_player") or {}).items():
            usage["by_player"][str(name)] = usage["by_player"].get(str(name), 0.0) + float(
                amount or 0.0
            )
    return AssemblyExecution(
        plan_sha256=plan_sha256,
        runs=tuple(runs),
        complete=complete,
        cost_usd=usage["cost_usd"],
        calls=usage["calls"],
        tokens=usage["tokens"],
        by_player=usage["by_player"],
    )


def _usage_from_records(paths: Sequence[Path]) -> dict[str, Any]:
    cost = 0.0
    calls = 0
    tokens = 0
    by_player: dict[str, float] = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = payload.get("metadata") or {}
        match = metadata.get("match") or {}
        known_cost = match.get("cost")
        if known_cost is None:
            known_cost = match.get("known_cost_usd")
        cost += float(known_cost or 0.0)
        for name, amount in (match.get("player_costs") or {}).items():
            by_player[str(name)] = by_player.get(str(name), 0.0) + float(amount or 0.0)
        summary = payload.get("api_usage_summary") or {}
        calls += int(summary.get("total_calls") or 0)
        tokens += int(summary.get("total_tokens") or 0)
    return {"cost_usd": cost, "calls": calls, "tokens": tokens, "by_player": by_player}


def inspect_provider_call_custody(output_root: str | Path) -> dict[str, Any]:
    """Inspect durable call custody after an execution process stopped."""

    root = Path(output_root).resolve()
    record_paths = sorted(root.glob("**/records/match_*.json"))
    entries: list[dict[str, Any]] = []
    for directory in sorted(root.glob("**/provider_calls")):
        if directory.is_dir():
            entries.extend(FilesystemProviderCallJournal(directory).entries())
    summary = _provider_call_custody_summary_from_entries(
        required_mode="durable",
        effective={
            "mode": "durable",
            "backend": "filesystem",
            "process_restart_recovery": True,
        },
        entries=entries,
        record_paths=record_paths,
    )
    usage = _usage_from_records(record_paths)
    extra = summary["known_unincorporated_usage"]
    usage["cost_usd"] += float(extra["cost_usd"])
    usage["calls"] += int(extra["calls"])
    usage["tokens"] += int(extra["tokens"])
    for name, amount in extra["by_player"].items():
        usage["by_player"][name] = usage["by_player"].get(name, 0.0) + float(amount)
    return {**summary, "usage": usage}


def _provider_call_custody_summary(
    *,
    required_mode: str,
    journal: ProviderCallJournal | None,
    record_paths: Sequence[Path],
) -> dict[str, Any]:
    if journal is None:
        return {
            "required": required_mode,
            "effective": None,
            "attempts": 0,
            "response_committed": 0,
            "outcome_unknown": 0,
            "known_unincorporated_usage": _empty_usage(),
        }
    return _provider_call_custody_summary_from_entries(
        required_mode=required_mode,
        effective=journal.describe(),
        entries=journal.entries(),
        record_paths=record_paths,
    )


def _provider_call_custody_summary_from_entries(
    *,
    required_mode: str,
    effective: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
    record_paths: Sequence[Path],
) -> dict[str, Any]:
    incorporated = _provider_call_ids_from_records(record_paths)
    response_entries = [entry for entry in entries if entry.get("state") == "response_committed"]
    unknown = [
        entry
        for entry in entries
        if entry.get("state") == "dispatch_started"
        or (entry.get("state") == "attempt_failed" and entry.get("provider_outcome") == "unknown")
    ]
    extra = _empty_usage()
    # A terminal error Record can include paid cost before the corresponding
    # gameplay event exists. Its aggregate player ledger already covers that
    # money, while call/token counts still need the journal-only response.
    credited_cost: dict[tuple[str, str], float] = {}
    for path in record_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not record.get("match_id"):
            continue
        match = (record.get("metadata") or {}).get("match") or {}
        for name, amount in (match.get("player_costs") or {}).items():
            credited_cost[(record["match_id"], str(name))] = float(amount or 0.0)
    deducted: set[str] = set()
    for entry in response_entries:
        call_id = str(entry.get("call_id") or "")
        if call_id not in incorporated or call_id in deducted:
            continue
        deducted.add(call_id)
        intent = entry.get("intent") or {}
        key = (str(intent.get("match_id") or ""), str(intent.get("player") or "unknown"))
        usage = (entry.get("result") or {}).get("usage_info") or {}
        credited_cost[key] = max(0.0, credited_cost.get(key, 0.0) - float(usage.get("cost") or 0.0))
    seen: set[str] = set()
    for entry in response_entries:
        call_id = str(entry.get("call_id") or "")
        if not call_id or call_id in incorporated or call_id in seen:
            continue
        seen.add(call_id)
        result = entry.get("result") or {}
        usage = result.get("usage_info") or {}
        player = str((entry.get("intent") or {}).get("player") or "unknown")
        key = (str((entry.get("intent") or {}).get("match_id") or ""), player)
        cost = float(usage.get("cost") or 0.0)
        covered = min(cost, credited_cost.get(key, 0.0))
        credited_cost[key] = credited_cost.get(key, 0.0) - covered
        uncounted_cost = cost - covered
        extra["cost_usd"] += uncounted_cost
        extra["calls"] += 1
        extra["tokens"] += int(usage.get("tokens") or 0)
        extra["by_player"][player] = extra["by_player"].get(player, 0.0) + uncounted_cost
    return {
        "required": required_mode,
        "effective": dict(effective),
        "attempts": len(entries),
        "response_committed": len(response_entries),
        "outcome_unknown": len(unknown),
        "known_unincorporated_usage": extra,
    }


def _provider_call_ids_from_records(paths: Sequence[Path]) -> set[str]:
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            provider_call = value.get("provider_call")
            if isinstance(provider_call, Mapping):
                call_id = provider_call.get("call_id")
                if isinstance(call_id, str) and call_id:
                    found.add(call_id)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for path in paths:
        visit(json.loads(path.read_text(encoding="utf-8")))
    return found


def _empty_usage() -> dict[str, Any]:
    return {"cost_usd": 0.0, "calls": 0, "tokens": 0, "by_player": {}}


__all__ = [
    "Assembly",
    "AssemblyArtifact",
    "AssemblyExecution",
    "AssemblyExecutionError",
    "AssemblyRecordReceipt",
    "AssemblyRun",
    "AssemblyRunExecution",
    "PlayerFactory",
    "PreparedAssembly",
    "execute_prepared_assembly",
    "inspect_provider_call_custody",
    "prepare_assembly",
]
