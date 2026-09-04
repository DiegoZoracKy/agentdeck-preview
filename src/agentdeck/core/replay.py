"""Replay engine for AgentDeck framework."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Union, cast

from .base.spectator import Spectator
from .event_bus import EventBus
from .replay_utils import ReplayScheduler, rehydrate_context, rehydrate_players
from .types import Event, EventContext, EventType, MatchResult


@dataclass
class _ReplayContext:
    match_id: Optional[str]
    players: List[str]
    metadata: Dict[str, Any]


class ReplayEngine:
    """Replays recorded matches through spectators."""

    def __init__(
        self,
        match_result: Union[MatchResult, Dict[str, Any]],
        *,
        scheduler: Optional[ReplayScheduler] = None,
    ):
        """
        Load match for replay.

        Args:
            match_result: MatchResult object or dictionary with match data
        """
        if isinstance(match_result, MatchResult):
            self.schema_version = self._validate_schema_version(match_result.metadata or {})
            self.events = match_result.events
            self.metadata = dict(match_result.metadata or {})
            self.match_metadata = dict(match_result.metadata or {})
            self.winner = match_result.winner
            self.final_state = match_result.final_state
            self.seed = match_result.seed
        else:
            # Load from dictionary
            self.schema_version = self._validate_schema_version(match_result)
            self.events = self._deserialize_events(match_result.get("events", []))
            raw_metadata = match_result.get("metadata", {}) or {}
            self.metadata = dict(raw_metadata)
            raw_match_meta = raw_metadata.get("match")
            if isinstance(raw_match_meta, dict):
                self.match_metadata = dict(raw_match_meta)
            else:
                fallback_meta: Dict[str, Any] = {}
                for key in (
                    "game",
                    "players",
                    "duration",
                    "turns",
                    "truncated_by_max_turns",
                    "first_player",
                ):
                    if key in raw_metadata:
                        fallback_meta[key] = raw_metadata[key]
                self.match_metadata = fallback_meta
            self.winner = match_result.get("winner")
            self.final_state = match_result.get("final_state", {})
            self.seed = match_result.get("seed")

        self.event_bus = EventBus()
        self.scheduler = scheduler or ReplayScheduler()
        self.replay_context = _ReplayContext(
            match_id=self.metadata.get("match_id"),
            players=self.metadata.get("players", []),
            metadata=self.metadata,
        )
        self._handshake_started: Set[str] = set()
        self._handshake_prompt_cache: Dict[str, Dict[str, Any]] = {}

    def replay(self, spectators: List[Spectator], speed: Optional[float] = None) -> None:
        """
        Replay match through spectators.

        Args:
            spectators: Observers for replay
            speed: Playback speed multiplier (2.0 = 2x speed, 0.5 = half speed)
        """
        if speed is not None:
            self.scheduler.speed = max(speed, 0.0)

        # Subscribe spectators
        for spectator in spectators:
            if getattr(spectator, "logger", None) is None:
                spectator.logger = getattr(self, "logger", None)
            self.event_bus.subscribe(spectator)

        # Hydrate EventBus base context from recording metadata
        base_context: Dict[str, Any] = {}
        for key in ("session_id", "batch_id", "match_id"):
            value = self.metadata.get(key)
            if value:
                base_context[key] = value
        if self.replay_context.match_id and "match_id" not in base_context:
            base_context["match_id"] = self.replay_context.match_id
        if base_context:
            self.event_bus.update_context(**base_context)

        try:
            last_event: Optional[Event] = None

            self._build_handshake_prompt_cache()
            start_index = 0
            total_events = len(self.events)
            emitted_match_start = False
            if total_events:
                first_event = self.events[0]
                first_type = (
                    first_event.type.value
                    if isinstance(first_event.type, EventType)
                    else first_event.type
                )
                if first_type == EventType.MATCH_START.value:
                    delay = self.scheduler.compute_delay(last_event, first_event)
                    if delay > 0:
                        time.sleep(delay)
                    self._emit_recorded_event(first_event)
                    last_event = first_event
                    start_index = 1
                    emitted_match_start = True

            if not emitted_match_start:
                game_name = (
                    self.metadata.get("game") or self.match_metadata.get("game") or "ReplayGame"
                )
                mock_game = type(game_name, (), {})()
                player_names = (
                    self.match_metadata.get("players")
                    or self.metadata.get("players")
                    or self.replay_context.players
                    or []
                )
                mock_players = rehydrate_players(player_names)
                self.event_bus.emit(
                    EventType.MATCH_START,
                    game=mock_game,
                    players=mock_players,
                    match_id=self.metadata.get("match_id") or self.replay_context.match_id,
                )

            emitted_match_end = False
            for event in self.events[start_index:]:
                delay = self.scheduler.compute_delay(last_event, event)
                if delay > 0:
                    time.sleep(delay)

                self._emit_recorded_event(event)
                last_event = event
                event_type = event.type.value if isinstance(event.type, EventType) else event.type
                if event_type == EventType.MATCH_END.value:
                    emitted_match_end = True

            if not emitted_match_end:
                match_metadata = dict(self.match_metadata or {})
                match_result = MatchResult(
                    winner=self.winner,
                    final_state=self.final_state,
                    events=self.events,
                    seed=self.seed,
                    metadata=match_metadata,
                )
                self.event_bus.emit(
                    EventType.MATCH_END,
                    result=match_result,
                )
            self._handshake_started.clear()
            self._handshake_prompt_cache.clear()

        finally:
            self._cleanup_spectators(spectators)

    def _deserialize_events(self, events_data: List[Dict]) -> List[Event]:
        """Convert dictionary events to Event objects."""
        events = []
        for data in events_data:
            entry = dict(data)
            payload = dict(entry.get("data", {}))
            context_dict = dict(entry.get("context", {}))
            events.append(
                Event(
                    type=entry["type"],
                    data=payload,
                    context=cast(EventContext, context_dict),
                    timestamp=entry.get("timestamp", 0),
                    duration=entry.get("duration", 0.1),
                )
            )
        return events

    def _cleanup_spectators(self, spectators: List[Spectator]) -> None:
        """
        Unsubscribe all spectators after replay completes.

        Per SPEC-REPLAY SI2: MUST unsubscribe spectators to prevent cross-replay
        interference and leave spectators in clean state for reuse.
        """
        for spectator in spectators:
            self.event_bus.unsubscribe(spectator)

    def _emit_recorded_event(self, event: Event) -> None:
        """Emit a recorded event through the replay EventBus."""
        event_type = event.type.value if isinstance(event.type, EventType) else event.type
        payload = copy.deepcopy(event.data or {})
        stored_context = payload.pop("context", None)
        context = event.context or stored_context or {}

        self._apply_event_context(context)

        if event_type == EventType.PLAYER_HANDSHAKE_START.value:
            player = payload.get("player")
            if player:
                cached = self._handshake_prompt_cache.get(player, {})
                if not payload.get("prompt_text") and cached.get("prompt_text"):
                    payload["prompt_text"] = cached["prompt_text"]
                if "prompt_blocks" not in payload and "prompt_blocks" in cached:
                    payload["prompt_blocks"] = cached["prompt_blocks"]
                if not payload.get("controller_format") and cached.get("controller_format"):
                    payload["controller_format"] = cached["controller_format"]
            if player:
                self._handshake_started.add(player)
            self.event_bus.emit(event_type, **payload)
            return

        if event_type in {
            EventType.PLAYER_HANDSHAKE_COMPLETE.value,
            EventType.PLAYER_HANDSHAKE_ABORT.value,
        }:
            player = payload.get("player")
            if player and player not in self._handshake_started:
                self._emit_handshake_start(payload, context)
            if player:
                self._handshake_started.add(player)
            self.event_bus.emit(event_type, **payload)
            return

        if event_type == EventType.PLAYER_CONCLUSION.value:
            self.event_bus.emit(event_type, **payload)
            return

        if event_type == "event":
            # Legacy custom events already contain Event objects
            payload = {"event": event}

        self.event_bus.emit(event_type, **payload)

    def _apply_event_context(self, ctx: Dict[str, Any]) -> None:
        """Update EventBus context for the next emission."""
        context = rehydrate_context(ctx)
        updates: Dict[str, Any] = {}

        if context.match_id:
            updates["match_id"] = context.match_id
        if context.session_id:
            updates["session_id"] = context.session_id
        if context.batch_id:
            updates["batch_id"] = context.batch_id

        phase_index = context.phase_index
        if phase_index is not None:
            updates["phase_index"] = phase_index
        else:
            self.event_bus.clear_context("phase_index")

        if updates:
            self.event_bus.update_context(**updates)

    def _build_handshake_prompt_cache(self) -> None:
        """Populate prompt metadata for handshake START backfill."""
        self._handshake_prompt_cache.clear()
        for event in self.events:
            event_type = event.type.value if isinstance(event.type, EventType) else event.type
            if event_type not in {
                EventType.PLAYER_HANDSHAKE_COMPLETE.value,
                EventType.PLAYER_HANDSHAKE_ABORT.value,
            }:
                continue
            payload = event.data or {}
            player = payload.get("player")
            if not player:
                continue
            prompt_text = payload.get("prompt_text")
            prompt_blocks = payload.get("prompt_blocks")
            controller_format = payload.get("controller_format")
            cached = self._handshake_prompt_cache.setdefault(player, {})
            if prompt_text and not cached.get("prompt_text"):
                cached["prompt_text"] = prompt_text
            if prompt_blocks is not None and "prompt_blocks" not in cached:
                cached["prompt_blocks"] = prompt_blocks
            if controller_format and not cached.get("controller_format"):
                cached["controller_format"] = controller_format

    def _emit_handshake_start(self, payload: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Emit synthetic PLAYER_HANDSHAKE_START before COMPLETE/ABORT events."""
        start_payload: Dict[str, Any] = {
            "player": payload.get("player"),
        }
        prompt_text = payload.get("prompt_text")
        prompt_blocks = payload.get("prompt_blocks")
        controller_format = payload.get("controller_format")
        player = start_payload.get("player")
        cached = self._handshake_prompt_cache.get(player, {}) if player else {}
        if not prompt_text:
            prompt_text = cached.get("prompt_text")
        if prompt_blocks is None and "prompt_blocks" in cached:
            prompt_blocks = cached.get("prompt_blocks")
        if not controller_format:
            controller_format = cached.get("controller_format")
        match_id = context.get("match_id") or self.metadata.get("match_id")
        if match_id:
            start_payload["match_id"] = match_id
        if prompt_text:
            start_payload["prompt_text"] = prompt_text
        if prompt_blocks is not None:
            start_payload["prompt_blocks"] = prompt_blocks
        if controller_format:
            start_payload["controller_format"] = controller_format
        self.event_bus.emit(EventType.PLAYER_HANDSHAKE_START, **start_payload)
        player = start_payload.get("player")
        if player:
            self._handshake_started.add(player)

    def _validate_schema_version(self, payload: Dict[str, Any]) -> str:
        """Ensure recordings declare a supported schema_version."""
        schema_version_value = payload.get("schema_version")
        schema_version = str(schema_version_value).strip() if schema_version_value else ""
        if not schema_version:
            raise ValueError(
                "ReplayEngine requires recording schema_version (expected 2.0). "
                "Re-export the match with Recorder v2.0."
            )
        if schema_version != "2.0":
            raise ValueError(
                f"Unsupported recording schema_version '{schema_version}'. "
                "ReplayEngine only supports Recorder v2.0 artifacts."
            )
        return schema_version
