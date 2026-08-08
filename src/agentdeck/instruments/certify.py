"""Trusted execution certifier for external Instrument Packages."""

from __future__ import annotations

import copy
import importlib
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Sequence

from agentdeck.core.artifact_safety import (
    atomic_write_text,
    ensure_contained_path,
    require_json_value,
)
from agentdeck.core.agentdeck import AgentDeck
from agentdeck.core.base import Game, Player
from agentdeck.core.replay import ReplayEngine
from agentdeck.core.session import AgentDeckConfig
from agentdeck.research.behavioral import BehavioralScorer
from agentdeck.spectators.match_surface import InMemorySink, MatchSurfaceProjector

from .manifest import InstrumentManifestError, load_validated_manifest
from .models import InstrumentReport
from .profile import load_behavioral_profile, resolve_json_pointer

EXECUTABLE_TRUST_MODES = {"trusted-local", "isolated"}


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@contextmanager
def _package_import_scope(root: Path) -> Iterator[Callable[[str], Any]]:
    """Import contained package code, then remove it from process module state."""
    previous_path = list(sys.path)
    previous_bytecode = sys.dont_write_bytecode
    before_modules = set(sys.modules)
    sys.path.insert(0, str(root))
    sys.dont_write_bytecode = True

    def load(entry_point: str) -> Any:
        module_name, symbol_name = entry_point.split(":", 1)
        top_level = module_name.split(".", 1)[0]
        existing = sys.modules.get(top_level)
        if existing is not None:
            origin = getattr(existing, "__file__", None)
            if not origin or not _inside(root, Path(origin)):
                raise InstrumentManifestError(
                    f"Package module name collides with an existing import: {top_level}"
                )
        module = importlib.import_module(module_name)
        origin = getattr(module, "__file__", None)
        if not origin or not _inside(root, Path(origin)):
            raise InstrumentManifestError(f"Entry point escaped package root: {entry_point}")
        try:
            return getattr(module, symbol_name)
        except AttributeError as exc:
            raise InstrumentManifestError(
                f"Entry point symbol does not exist: {entry_point}"
            ) from exc

    try:
        yield load
    finally:
        sys.path[:] = previous_path
        sys.dont_write_bytecode = previous_bytecode
        for name in list(sys.modules):
            if name in before_modules:
                continue
            module = sys.modules.get(name)
            origin = getattr(module, "__file__", None)
            if origin and _inside(root, Path(origin)):
                sys.modules.pop(name, None)


class _EventCapture:
    """Capture every replay event through EventBus's documented fallback."""

    def __init__(self) -> None:
        self.events: List[Any] = []

    def on_event(self, event: Any) -> None:
        self.events.append(event)


def _plain(value: Any) -> Any:
    """Convert runtime wrappers to the canonical values used in records."""
    if isinstance(value, Game):
        return value.__class__.__name__
    if isinstance(value, Player):
        return value.name
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if hasattr(value, "winner") and hasattr(value, "final_state"):
        return {
            "winner": value.winner,
            "final_state": _plain(value.final_state),
            "seed": value.seed,
        }
    return value


def _event_signature(event: Mapping[str, Any]) -> Dict[str, Any]:
    return {"type": event["type"], "data": _plain(event.get("data", {}))}


def _captured_signature(event: Any) -> Dict[str, Any]:
    event_type = event.type.value if hasattr(event.type, "value") else event.type
    return {"type": event_type, "data": _plain(event.data)}


def _semantic(value: Any) -> Any:
    """Remove recorder identity and timing without weakening behavioral comparison."""
    volatile = {
        "batch_id",
        "duration",
        "duration_seconds",
        "ended_at",
        "match_id",
        "monotonic_time",
        "run_id",
        "session_id",
        "started_at",
        "timestamp",
    }
    if isinstance(value, dict):
        return {key: _semantic(item) for key, item in value.items() if key not in volatile}
    if isinstance(value, list):
        return [_semantic(item) for item in value]
    return value


def _deterministic_signature(payloads: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    signature = []
    for payload in payloads:
        gameplay = [
            _semantic(_event_signature(event))
            for event in payload.get("events", [])
            if event.get("type") == "gameplay"
        ]
        signature.append(
            {
                "winner": payload.get("winner"),
                "final_state": payload.get("final_state"),
                "seed": payload.get("seed"),
                "gameplay": gameplay,
            }
        )
    require_json_value(signature, field="instrument deterministic signature")
    return signature


def _read_match_payloads(record_directory: Path) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    for path in sorted(record_directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_type") == "match":
            payloads.append(payload)
    return sorted(payloads, key=lambda payload: int(payload.get("seed") or 0))


def _assert_lifecycle(payloads: Sequence[Mapping[str, Any]]) -> None:
    for index, payload in enumerate(payloads):
        types = [event.get("type") for event in payload.get("events", [])]
        if "player_handshake_complete" not in types or "gameplay" not in types:
            raise AssertionError(f"match {index} lacks handshake or gameplay events")
        if types.index("player_handshake_complete") > types.index("gameplay"):
            raise AssertionError(f"match {index} records gameplay before handshake completion")
        if "player_conclusion" not in types:
            raise AssertionError(f"match {index} lacks conclusion events")
        if types.index("player_conclusion") < types.index("gameplay"):
            raise AssertionError(f"match {index} records conclusion before gameplay")


def _assert_replay_parity(payloads: Sequence[Mapping[str, Any]]) -> None:
    for index, payload in enumerate(payloads):
        capture = _EventCapture()
        ReplayEngine(dict(payload)).replay(spectators=[capture], speed=0.0)
        expected = [_event_signature(event) for event in payload.get("events", [])]
        actual = [_captured_signature(event) for event in capture.events]
        # Recorder persists handshake/gameplay/conclusion and materializes MATCH_START
        # plus MATCH_END from canonical metadata during replay. Compare every persisted
        # event/data pair exactly, then require both reconstructed lifecycle boundaries.
        persisted_actual = [
            event for event in actual if event["type"] not in {"match_start", "match_end"}
        ]
        reconstructed = [
            event["type"] for event in actual if event["type"] in {"match_start", "match_end"}
        ]
        if persisted_actual != expected or reconstructed != ["match_start", "match_end"]:
            raise AssertionError(f"match {index} replay event/data parity mismatch")


def _run_once(
    *,
    root: Path,
    manifest: Mapping[str, Any],
    load: Callable[[str], Any],
    run_root: Path,
) -> tuple[List[Dict[str, Any]], List[str], List[Dict[str, Any]]]:
    game_declaration = manifest["game"]
    fixture = manifest["fixture"]
    game_type = load(game_declaration["entry_point"])
    fixture_factory = load(fixture["entry_point"])
    if not isinstance(game_type, type) or not issubclass(game_type, Game):
        raise TypeError("game.entry_point must name an AgentDeck Game subclass")
    if not callable(fixture_factory):
        raise TypeError("fixture.entry_point must name a callable")

    game = game_type(**copy.deepcopy(game_declaration["config"]))
    players = fixture_factory()
    if not isinstance(players, list) or not all(isinstance(player, Player) for player in players):
        raise TypeError("fixture must return list[Player]")
    if len(players) != fixture["player_count"]:
        raise ValueError("fixture player count does not match the manifest")
    if len({player.name for player in players}) != len(players):
        raise ValueError("fixture player names must be unique")

    descriptor = game.describe()
    require_json_value(descriptor, field="Game.describe()")
    if descriptor.get("config") != game_declaration["config"]:
        raise ValueError("Game.describe().config does not equal the declared effective config")

    session = AgentDeckConfig(
        seed=fixture["seed"],
        run_dir=str(run_root),
        max_turns=fixture["max_turns"],
        log_level=None,
        log_file_levels=[],
        concurrency=1,
        first_player_policy="fixed",
        fixed_first_player_index=0,
    )
    with AgentDeck(game=game, session=session, spectators=[]) as deck:
        results = deck.play(players=players, matches=fixture["matches"], seed=fixture["seed"])
        record_directory = Path(deck.session.record_directory)

    winners = [match.winner for match in results.matches]
    if winners != fixture["expected_winners"]:
        raise AssertionError(
            f"fixture winner sequence differs: expected {fixture['expected_winners']}, got {winners}"
        )
    payloads = _read_match_payloads(record_directory)
    if len(payloads) != fixture["matches"]:
        raise AssertionError("Recorder did not produce one canonical payload per match")
    for payload in payloads:
        recorded = (payload.get("metadata") or {}).get("game_config") or {}
        if recorded.get("config") != game_declaration["config"]:
            raise AssertionError("recorded Game config differs from the manifest")
        require_json_value(payload, field="recorded match")
    _assert_lifecycle(payloads)
    _assert_replay_parity(payloads)
    relative_records = [
        path.relative_to(run_root).as_posix() for path in sorted(record_directory.glob("*.json"))
    ]
    summaries = [copy.deepcopy(player.get_summary()) for player in players]
    return payloads, relative_records, summaries


def _score_evidence(
    *,
    root: Path,
    manifest: Mapping[str, Any],
    load: Callable[[str], Any],
    first_payloads: Sequence[Mapping[str, Any]],
    second_payloads: Sequence[Mapping[str, Any]],
    players: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    declaration = manifest["evidence"]
    scorer_type = load(declaration["scorer_entry_point"])
    if not isinstance(scorer_type, type) or not issubclass(scorer_type, BehavioralScorer):
        raise TypeError("evidence.scorer_entry_point must name a BehavioralScorer subclass")
    scorer = scorer_type()
    if not scorer.supports(match_payloads=first_payloads):
        raise ValueError("declared BehavioralScorer does not support generated records")
    first = scorer.score(
        players=copy.deepcopy(players),
        match_payloads=copy.deepcopy(list(first_payloads)),
        config=copy.deepcopy(manifest["game"]["config"]),
    )
    second = scorer.score(
        players=copy.deepcopy(players),
        match_payloads=copy.deepcopy(list(second_payloads)),
        config=copy.deepcopy(manifest["game"]["config"]),
    )
    require_json_value(first, field="behavioral scorer output")
    require_json_value(second, field="behavioral scorer output")
    if first != second:
        raise AssertionError("behavioral scorer output is not deterministic")
    profile_path = ensure_contained_path(root, root / declaration["profile"])
    profile = load_behavioral_profile(profile_path)
    if first.get("profile_id") != profile["profile_id"]:
        raise AssertionError("scorer profile_id differs from behavioral profile")
    if first.get("profile_version") != profile["profile_version"]:
        raise AssertionError("scorer profile_version differs from behavioral profile")
    for metric in profile["metrics"]:
        value = resolve_json_pointer(first, metric["output_pointer"])
        if value is None and not metric["allow_unsupported"]:
            raise AssertionError(f"required metric is unsupported: {metric['id']}")
        for pointer in metric["record_pointers"]:
            resolve_json_pointer(list(first_payloads), pointer)
    for pointer, expected in profile["calibration"]["expected"].items():
        actual = resolve_json_pointer(first, pointer)
        if actual != expected or type(actual) is not type(expected):
            raise AssertionError(
                f"calibration mismatch at {pointer}: expected {expected!r}, got {actual!r}"
            )
    return first


def _visible_state(
    redactor: Callable[..., Any],
    state: Mapping[str, Any],
    player: str,
    config: Mapping[str, Any],
) -> Dict[str, Any]:
    candidate = copy.deepcopy(dict(state))
    before = copy.deepcopy(candidate)
    first = redactor(candidate, player, copy.deepcopy(dict(config)))
    if candidate != before:
        raise AssertionError("presentation redactor mutated canonical state")
    second = redactor(copy.deepcopy(dict(state)), player, copy.deepcopy(dict(config)))
    if first != second:
        raise AssertionError("presentation redactor is not deterministic")
    if not isinstance(first, dict):
        raise TypeError("presentation redactor must return a dict")
    require_json_value(first, field="visible state")
    return first


def _assert_pointer_absent(document: Any, pointer: str) -> None:
    try:
        resolve_json_pointer(document, pointer)
    except InstrumentManifestError:
        return
    raise AssertionError(f"declared oracle path is visible: {pointer}")


def _project_surface(
    *,
    payload: Mapping[str, Any],
    redactor: Callable[..., Any],
    config: Mapping[str, Any],
    oracle_paths: Mapping[str, Sequence[str]],
) -> Dict[str, Any]:
    def redact_document(document: Dict[str, Any]) -> Dict[str, Any]:
        redacted = copy.deepcopy(document)
        for frame in redacted.get("frames", []):
            player = frame.get("player")
            if not isinstance(player, str):
                raise AssertionError("Match Surface frame lacks acting Player")
            for field in ("state_before", "state_after"):
                view = _visible_state(redactor, frame[field], player, config)
                for pointer in oracle_paths.get(player, []):
                    _assert_pointer_absent(view, pointer)
                frame[field] = view
            frame.pop("state_delta", None)
        match = redacted.get("match") or {}
        final_state = match.pop("final_state", None)
        if isinstance(final_state, dict):
            players = [
                item.get("name")
                for item in redacted.get("players", [])
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            ]
            final_views = {}
            for player in players:
                view = _visible_state(redactor, final_state, player, config)
                for pointer in oracle_paths.get(player, []):
                    _assert_pointer_absent(view, pointer)
                final_views[player] = view
            match["final_state_views"] = final_views
        return redacted

    sink = InMemorySink()
    projector = MatchSurfaceProjector(sink=sink, redactor=redact_document)
    ReplayEngine(dict(payload)).replay(spectators=[projector], speed=0.0)
    if sink.document is None or projector.diagnostics:
        raise AssertionError("generic Match Surface projection did not complete cleanly")
    document = sink.document
    if not document.get("frames") or not document.get("handshakes"):
        raise AssertionError("Match Surface lacks gameplay or handshake lifecycle")
    if not document.get("conclusions"):
        raise AssertionError("Match Surface lacks conclusion lifecycle")
    require_json_value(document, field="Match Surface")
    return document


def _certify_presentation(
    *,
    manifest: Mapping[str, Any],
    load: Callable[[str], Any],
    first_payloads: Sequence[Mapping[str, Any]],
    second_payloads: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    declaration = manifest["presentation"]
    redactor = load(declaration["redactor_entry_point"])
    if not callable(redactor):
        raise TypeError("presentation.redactor_entry_point must name a callable")
    config = manifest["game"]["config"]
    oracle_paths = declaration.get("oracle_paths", {})
    for payload in first_payloads:
        for event in payload.get("events", []):
            if event.get("type") != "gameplay":
                continue
            data = event.get("data") or {}
            player = data.get("player")
            if not isinstance(player, str):
                raise AssertionError("gameplay evidence lacks acting Player")
            for field in ("state_before", "state_after"):
                view = _visible_state(redactor, data[field], player, config)
                for pointer in oracle_paths.get(player, []):
                    _assert_pointer_absent(view, pointer)
    first = [
        _project_surface(
            payload=payload,
            redactor=redactor,
            config=config,
            oracle_paths=oracle_paths,
        )
        for payload in first_payloads
    ]
    second = [
        _project_surface(
            payload=payload,
            redactor=redactor,
            config=config,
            oracle_paths=oracle_paths,
        )
        for payload in second_payloads
    ]
    if _semantic(first) != _semantic(second):
        raise AssertionError("repeated Match Surface projections differ semantically")
    oracle_values = declaration.get("oracle_values", [])
    serialized = json.dumps(first, sort_keys=True, ensure_ascii=True, allow_nan=False)
    for value in oracle_values:
        if value in serialized:
            raise AssertionError("declared oracle value leaked into Match Surface")
    return first


def _write_json_artifact(output_root: Path, relative: str, value: Any) -> None:
    target = ensure_contained_path(output_root, output_root / relative)
    require_json_value(value, field=relative)
    atomic_write_text(
        target,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
    )


def _write_report(output_root: Path, report: InstrumentReport) -> None:
    path = ensure_contained_path(output_root, output_root / "certification.json")
    if not report.valid and path.exists():
        return
    payload = report.canonical_json() + "\n"
    atomic_write_text(path, payload)


def certify_instrument(
    package_root: str | Path,
    *,
    trust_mode: str,
    output_dir: str | Path | None = None,
) -> InstrumentReport:
    root, manifest, report = load_validated_manifest(package_root)
    report.operation = "certify"
    report.trust_mode = trust_mode
    if not report.valid:
        return report
    if trust_mode not in EXECUTABLE_TRUST_MODES:
        report.checked(
            "IP2",
            False,
            "Certification executes Python and requires trusted-local or caller-provided isolated mode",
        )
        return report

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if output_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="agentdeck-certify-")
        output_root = Path(temporary.name).resolve()
    else:
        output_root = Path(output_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)

    current_check = "IP5"
    try:
        with _package_import_scope(root) as load:
            first_payloads, first_records, player_summaries = _run_once(
                root=root,
                manifest=manifest,
                load=load,
                run_root=ensure_contained_path(output_root, output_root / "execution-1"),
            )
            second_payloads, second_records, _ = _run_once(
                root=root,
                manifest=manifest,
                load=load,
                run_root=ensure_contained_path(output_root, output_root / "execution-2"),
            )
            report.checked("IP5", True, "Game and fixture satisfy public AgentDeck contracts")
            report.checked("IP6", True, "Declared, effective, and recorded Game config agree")
            report.checked(
                "IP7",
                True,
                "Core supplied no provider credential or user input; ambient isolation is caller-owned",
                details={
                    "core_supplied_provider_credentials": False,
                    "core_supplied_user_input": False,
                    "repeated_execution_checked": True,
                    "ambient_isolation": "not_proven",
                },
            )
            report.checked(
                "IP8",
                _deterministic_signature(first_payloads)
                == _deterministic_signature(second_payloads),
                "Repeated seeded executions have equal semantic traces",
            )
            report.checked("IP9", True, "Every generated match replayed with event/data parity")
            report.checked("IP10", True, "Generated runnable artifacts satisfy strict JSON")
            if not report.valid:
                return report
            report.awarded_tiers.append("runnable")
            report.artifacts = ["execution-1", "execution-2"]

            requested = manifest["claims"]["requested"]
            if "evidence_ready" in requested:
                current_check = "IP12"
                evidence = _score_evidence(
                    root=root,
                    manifest=manifest,
                    load=load,
                    first_payloads=first_payloads,
                    second_payloads=second_payloads,
                    players=player_summaries,
                )
                report.checked("IP12", True, "Every declared metric and record pointer resolved")
                report.awarded_tiers.append("evidence_ready")
                report.artifacts.append("evidence/profile.json")
                if output_dir is not None:
                    _write_json_artifact(output_root, "evidence/profile.json", evidence)

            if "presentable" in requested:
                current_check = "IP13"
                surfaces = _certify_presentation(
                    manifest=manifest,
                    load=load,
                    first_payloads=first_payloads,
                    second_payloads=second_payloads,
                )
                report.checked(
                    "IP13", True, "Visible states and Match Surfaces exclude declared oracles"
                )
                report.awarded_tiers.append("presentable")
                report.artifacts.append("presentation/match-surfaces.json")
                if output_dir is not None:
                    _write_json_artifact(output_root, "presentation/match-surfaces.json", surfaces)
        current_check = "IP11"
        report.checked(
            "IP11", True, "Only requested tiers with completed checks were mechanically awarded"
        )
        report.checked("IP15", True, "Report excludes volatile execution identifiers and timing")
        if output_dir is not None:
            _write_report(output_root, report)
        del first_records, second_records
        return report
    except Exception as exc:  # Certification must preserve the failed check as data.
        report.checked(
            current_check,
            False,
            f"Trusted certification failed: {type(exc).__name__}: {exc}",
        )
        if output_dir is not None:
            _write_report(output_root, report)
        return report
    finally:
        if temporary is not None:
            temporary.cleanup()
