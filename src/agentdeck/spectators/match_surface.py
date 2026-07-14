"""Match Surface projection spectator and sinks."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

from ..core.base.spectator import Spectator
from ..core.types import Event, EventContext, MatchResult


class MarkerProvider(Protocol):
    """Provider for mechanical presentation markers."""

    def markers_for_frame(self, frame: Dict[str, Any]) -> List[Dict[str, Any]]: ...


class MatchSurfaceSink(Protocol):
    """Sink for projected Match Surface documents."""

    def start(self, document: Dict[str, Any]) -> None: ...

    def frame(self, frame: Dict[str, Any]) -> None: ...

    def finish(self, document: Dict[str, Any]) -> None: ...


class InMemorySink:
    """Store the latest completed Match Surface document in memory."""

    def __init__(self) -> None:
        self.document: Optional[Dict[str, Any]] = None
        self.frames: List[Dict[str, Any]] = []
        self.started: Optional[Dict[str, Any]] = None

    def start(self, document: Dict[str, Any]) -> None:
        self.started = copy.deepcopy(document)
        self.frames = []
        self.document = None

    def frame(self, frame: Dict[str, Any]) -> None:
        self.frames.append(copy.deepcopy(frame))

    def finish(self, document: Dict[str, Any]) -> None:
        self.document = copy.deepcopy(document)


class JsonArtifactSink:
    """Write one deterministic JSON Match Surface artifact per match."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.last_path: Optional[Path] = None

    def start(self, document: Dict[str, Any]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_path = None

    def frame(self, frame: Dict[str, Any]) -> None:
        return None

    def finish(self, document: Dict[str, Any]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        match_id = str((document.get("match") or {}).get("match_id") or "match")
        target = self.output_dir / f"{match_id}.json"
        payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=str(self.output_dir)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_name, target)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        self.last_path = target


class MatchSurfaceProjector(Spectator):
    """Project canonical Core events into the viewer-facing Match Surface protocol."""

    def __init__(
        self,
        *,
        sink: MatchSurfaceSink,
        redactor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        marker_providers: Optional[List[MarkerProvider]] = None,
        logger: Any = None,
    ) -> None:
        super().__init__(logger=logger)
        self.sink = sink
        self.redactor = redactor
        self.marker_providers = list(marker_providers or [])
        self.diagnostics: List[Dict[str, Any]] = []
        self.document: Optional[Dict[str, Any]] = None
        self.frames: List[Dict[str, Any]] = []
        self.markers: List[Dict[str, Any]] = []
        self.handshakes: List[Dict[str, Any]] = []
        self.conclusions: List[Dict[str, Any]] = []

    def on_match_start(
        self,
        game: Any,
        players: List[Any],
        match_id: Optional[str] = None,
        context: Optional[EventContext] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a Match Surface document at match start."""
        match_id = match_id or (context or {}).get("match_id") or "unknown_match"
        if (
            self.document is not None
            and (self.document.get("source") or {}).get("match_id") == match_id
        ):
            # Replay emits Handshake events before MATCH_START. Those events
            # create a provisional document; enrich it here instead of
            # resetting the lifecycle data that is already part of the match.
            match = self.document["match"]
            match["game"] = (
                game
                if isinstance(game, str)
                else (game.__class__.__name__ if game is not None else kwargs.get("game"))
            )
            if players:
                self.document["players"] = [self._player_summary(player) for player in players]
            provenance = kwargs.get("provenance")
            if provenance is not None:
                self.document["source"]["provenance"] = copy.deepcopy(provenance)
            self._emit_sink("start", self.document)
            return
        self.frames = []
        self.markers = []
        self.handshakes = []
        self.conclusions = []
        self.diagnostics = []
        self.document = {
            "schema_type": "match_surface",
            "schema_version": "0.2",
            "source": {
                "record_schema_version": "2.0",
                "match_id": match_id,
                "provenance": copy.deepcopy(kwargs.get("provenance") or {}),
            },
            "match": {
                "match_id": match_id,
                "game": (
                    game
                    if isinstance(game, str)
                    else (game.__class__.__name__ if game is not None else kwargs.get("game"))
                ),
                "seed": kwargs.get("seed"),
                "winner": None,
                "turns": None,
                "metadata": {
                    key: copy.deepcopy(value)
                    for key, value in kwargs.items()
                    if key not in {"provenance", "seed"}
                },
            },
            "players": [self._player_summary(player) for player in players],
            "handshakes": self.handshakes,
            "frames": self.frames,
            "conclusions": self.conclusions,
            "markers": self.markers,
            "economics": self._empty_economics(),
            "diagnostics": self.diagnostics,
        }
        self._emit_sink("start", self.document)

    def on_player_handshake_start(self, event: Event) -> None:
        self._append_lifecycle_event("started", event, self.handshakes)

    def on_player_handshake_complete(self, event: Event) -> None:
        self._append_lifecycle_event("accepted", event, self.handshakes)

    def on_player_handshake_abort(self, event: Event) -> None:
        self._append_lifecycle_event("rejected", event, self.handshakes)

    def on_player_conclusion(self, event: Event) -> None:
        self._append_lifecycle_event("agent_self_report", event, self.conclusions)

    def on_gameplay(self, event: Event) -> None:
        """Project one canonical gameplay event into one frame."""
        if self.document is None:
            match_id = (event.context or {}).get("match_id") or (event.data or {}).get("match_id")
            self.on_match_start(None, [], match_id=match_id)

        data = event.data or {}
        frame = self._project_frame(event, data)
        frame_markers = self._markers_for_frame(frame)
        frame["markers"] = frame_markers
        self.frames.append(frame)
        self.markers.extend(frame_markers)
        self._accumulate_economics(frame.get("economics") or {})
        self._emit_sink("frame", frame)

    def on_match_end(
        self, result: MatchResult, context: Optional[EventContext] = None, **kwargs: Any
    ) -> None:
        """Finalize and publish the Match Surface document."""
        if self.document is None:
            self.on_match_start(None, [], match_id=(context or {}).get("match_id"))

        match = self.document["match"]
        match["winner"] = result.winner
        match["turns"] = result.metadata.get("turns", len(self.frames))
        match["final_state"] = copy.deepcopy(result.final_state)
        if result.seed is not None:
            match["seed"] = result.seed
        if result.metadata:
            match["metadata"].update(copy.deepcopy(result.metadata))

        self._emit_sink("finish", self.document)

    def _append_lifecycle_event(
        self, state: str, event: Event, target: List[Dict[str, Any]]
    ) -> None:
        is_handshake = target is self.handshakes
        if self.document is None:
            match_id = (event.context or {}).get("match_id") or (event.data or {}).get("match_id")
            self.on_match_start(None, [], match_id=match_id)
        # The caller passes the current list before a provisional document is
        # created. Resolve it again after MATCH_START because initialization
        # intentionally resets per-match collections.
        target = self.handshakes if is_handshake else self.conclusions
        data = copy.deepcopy(event.data or {})
        interaction = copy.deepcopy(data.get("interaction") or {})
        target.append(
            {
                "player": data.get("player"),
                "state": state,
                "phase": "handshake" if is_handshake else "conclusion",
                "prompt_text": data.get("prompt_text") or interaction.get("prompt_text"),
                "prompt_blocks": data.get("prompt_blocks") or interaction.get("prompt_blocks"),
                "response_text": (
                    data.get("response_text")
                    or data.get("normalized_response")
                    or interaction.get("response_text")
                ),
                "controller_metadata": data.get("controller_metadata")
                or interaction.get("controller_metadata"),
                "usage_info": data.get("usage_info") or interaction.get("usage_info"),
                "timestamp": event.timestamp,
            }
        )

    def _emit_sink(self, method: str, payload: Dict[str, Any]) -> None:
        emitted = copy.deepcopy(payload)
        if self.redactor is not None:
            emitted = self.redactor(emitted)
        self._call_sink(method, emitted)

    def _project_frame(self, event: Event, data: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_canonical(data)
        interaction = copy.deepcopy(data.get("interaction") or {})
        usage_info = copy.deepcopy(interaction.get("usage_info"))
        return {
            "phase_index": data["phase_index"],
            "mechanic": data["mechanic"],
            "player": data["player"],
            "state_before": copy.deepcopy(data["state_before"]),
            "state_after": copy.deepcopy(data["state_after"]),
            "state_delta": self._state_delta(data["state_before"], data["state_after"]),
            "action": copy.deepcopy(data["action"]),
            "interaction": interaction,
            "economics": {
                "usage_info": usage_info,
                "cost": self._usage_number(usage_info, "cost"),
                "latency_ms": self._usage_number(usage_info, "latency_ms", "latency"),
            },
            "markers": [],
            "source_event": {
                "type": getattr(event.type, "value", event.type),
                "timestamp": event.timestamp,
                "context": copy.deepcopy(event.context),
            },
        }

    def _assert_canonical(self, data: Dict[str, Any]) -> None:
        required = {
            "phase_index",
            "mechanic",
            "player",
            "action",
            "interaction",
            "state_before",
            "state_after",
            "turn_context",
        }
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"Gameplay event missing canonical fields: {', '.join(missing)}")
        action = data.get("action")
        if not isinstance(action, dict) or "value" not in action:
            raise ValueError("Gameplay event action must be canonical action.value mapping")
        if "turn_index" in data or "prompt" in data:
            raise ValueError("Gameplay event contains retired v1.3 fields")

    def _markers_for_frame(self, frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        markers: List[Dict[str, Any]] = []
        for provider in self.marker_providers:
            try:
                for marker in provider.markers_for_frame(copy.deepcopy(frame)):
                    markers.append(self._normalize_marker(marker, frame["phase_index"]))
            except Exception as exc:
                self._record_diagnostic(
                    "marker_provider_error",
                    {"provider": provider.__class__.__name__, "error": str(exc)},
                )
        return markers

    def _normalize_marker(self, marker: Dict[str, Any], phase_index: int) -> Dict[str, Any]:
        normalized = copy.deepcopy(marker)
        normalized.setdefault("phase_index", phase_index)
        normalized.setdefault("source", "projector")
        normalized.setdefault("severity", "info")
        return normalized

    def _accumulate_economics(self, frame_economics: Dict[str, Any]) -> None:
        economics = self.document["economics"]
        usage_info = frame_economics.get("usage_info")
        if isinstance(usage_info, dict):
            economics["total_calls"] += 1
            economics["total_tokens"] += int(
                usage_info.get("tokens")
                or usage_info.get("total_tokens")
                or (
                    (usage_info.get("prompt_tokens") or usage_info.get("input_tokens") or 0)
                    + (usage_info.get("completion_tokens") or usage_info.get("output_tokens") or 0)
                )
                or 0
            )
        economics["total_cost"] += float(frame_economics.get("cost") or 0.0)
        economics["total_latency_ms"] += float(frame_economics.get("latency_ms") or 0.0)

    def _call_sink(self, method: str, payload: Dict[str, Any]) -> None:
        try:
            getattr(self.sink, method)(copy.deepcopy(payload))
        except Exception as exc:
            self._record_diagnostic(
                "sink_error",
                {"sink": self.sink.__class__.__name__, "method": method, "error": str(exc)},
            )

    def _record_diagnostic(self, kind: str, data: Dict[str, Any]) -> None:
        self.diagnostics.append({"kind": kind, "data": data})
        if self.logger:
            self.logger.error(f"MatchSurfaceProjector {kind}: {data}")

    @staticmethod
    def _player_summary(player: Any) -> Dict[str, Any]:
        if hasattr(player, "get_summary"):
            return copy.deepcopy(player.get_summary())
        return {
            "name": getattr(player, "name", str(player)),
            "type": player.__class__.__name__ if player is not None else "UnknownPlayer",
        }

    @staticmethod
    def _empty_economics() -> Dict[str, Any]:
        return {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_latency_ms": 0.0,
        }

    @staticmethod
    def _usage_number(usage_info: Any, *keys: str) -> float:
        if not isinstance(usage_info, dict):
            return 0.0
        for key in keys:
            value = usage_info.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return 0.0

    @classmethod
    def _state_delta(cls, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        delta: Dict[str, Any] = {}
        cls._collect_delta("", before, after, delta)
        return delta

    @classmethod
    def _collect_delta(cls, prefix: str, before: Any, after: Any, delta: Dict[str, Any]) -> None:
        if isinstance(before, dict) and isinstance(after, dict):
            keys = sorted(set(before) | set(after), key=str)
            for key in keys:
                path = f"{prefix}.{key}" if prefix else str(key)
                cls._collect_delta(path, before.get(key), after.get(key), delta)
            return
        if before != after:
            delta[prefix] = {
                "before": copy.deepcopy(before),
                "after": copy.deepcopy(after),
            }
