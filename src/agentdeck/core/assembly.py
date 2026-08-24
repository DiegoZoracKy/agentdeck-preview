"""Content-addressed preparation and execution of complete AgentDeck assemblies."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import re
import sys
import threading
from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .agentdeck import AgentDeck
from .base import Game, Player, Spectator
from .session import AgentDeckConfig

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
    assembly: dict[str, Any]
    plan_sha256: str

    @property
    def total_matches(self) -> int:
        return sum(int(run["matches"]) for run in self.assembly["runs"])

    @property
    def provider_requirements(self) -> tuple[dict[str, str], ...]:
        requirements = []
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
                requirements.append({"provider": key[0], "model": key[1]})
        return tuple(requirements)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "entrypoint": self.entrypoint,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "assembly": copy.deepcopy(self.assembly),
            "total_matches": self.total_matches,
            "provider_requirements": list(self.provider_requirements),
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
            assembly=copy.deepcopy(dict(value["assembly"])),
            plan_sha256=str(value["plan_sha256"]),
        )


@dataclass(frozen=True)
class AssemblyExecution:
    plan_sha256: str
    records: tuple[Path, ...]
    cost_usd: float
    calls: int
    tokens: int
    by_player: dict[str, float]


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
    records: list[Path] = []
    for index, run in enumerate(assembly.runs, start=1):
        run_dir = root / f"{index:02d}_{_safe_run_name(run.name)}"
        config = replace(run.session, run_dir=str(run_dir))
        players = [factory.create() for factory in run.players]
        with AgentDeck(
            game=run.game,
            spectators=list(run.spectators) or None,
            session=config,
        ) as deck:
            results = deck.play(players=players, matches=run.matches, seed=run.seed)
            paths = sorted(Path(deck.session.record_directory).glob("match_*.json"))
        if len(results) != run.matches or len(paths) != run.matches:
            raise RuntimeError(
                f"Assembly run {run.name!r} expected {run.matches} canonical Records; "
                f"observed results={len(results)} records={len(paths)}"
            )
        records.extend(paths)

    usage = _usage_from_records(records)
    return AssemblyExecution(
        plan_sha256=prepared.plan_sha256,
        records=tuple(records),
        cost_usd=usage["cost_usd"],
        calls=usage["calls"],
        tokens=usage["tokens"],
        by_player=usage["by_player"],
    )


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
    try:
        spec.loader.exec_module(module)
        factory = getattr(module, "create_assembly", None)
        if not callable(factory):
            raise ValueError("AgentDeck assembly entrypoint must export create_assembly()")
        assembly = factory()
        if not isinstance(assembly, Assembly):
            raise ValueError("create_assembly() must return agentdeck.Assembly")
        descriptor = assembly.describe()
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
        if sys.path and sys.path[0] == str(path.parent):
            sys.path.pop(0)
        _remove_source_modules(source_root)
        sys.modules.update(shadowed_modules)


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


def _usage_from_records(paths: Sequence[Path]) -> dict[str, Any]:
    cost = 0.0
    calls = 0
    tokens = 0
    by_player: dict[str, float] = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = payload.get("metadata") or {}
        match = metadata.get("match") or {}
        cost += float(match.get("cost") or 0.0)
        for name, amount in (match.get("player_costs") or {}).items():
            by_player[str(name)] = by_player.get(str(name), 0.0) + float(amount or 0.0)
        summary = payload.get("api_usage_summary") or {}
        calls += int(summary.get("total_calls") or 0)
        tokens += int(summary.get("total_tokens") or 0)
    return {"cost_usd": cost, "calls": calls, "tokens": tokens, "by_player": by_player}


__all__ = [
    "Assembly",
    "AssemblyArtifact",
    "AssemblyExecution",
    "AssemblyRun",
    "PlayerFactory",
    "PreparedAssembly",
    "execute_prepared_assembly",
    "prepare_assembly",
]
