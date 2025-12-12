"""Replay engine for AgentDeck framework."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Union, cast

from .base.spectator import Spectator
from .event_bus import EventBus
from .replay_utils import ReplayScheduler, rehydrate_context, rehydrate_players
from .types import ActionResult, Event, EventContext, EventType, MatchResult


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
        self._pending_conclusions: List[tuple[Dict[str, Any], Dict[str, Any]]] = []
        self._handshake_started: Set[str] = set()

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

            handshake_types = {
                EventType.PLAYER_HANDSHAKE_START.value,
                EventType.PLAYER_HANDSHAKE_COMPLETE.value,
                EventType.PLAYER_HANDSHAKE_ABORT.value,
            }
            start_index = 0
            total_events = len(self.events)
            while start_index < total_events:
                event = self.events[start_index]
                event_type = event.type.value if isinstance(event.type, EventType) else event.type
                if event_type not in handshake_types:
                    break
                delay = self.scheduler.compute_delay(last_event, event)
                if delay > 0:
                    time.sleep(delay)

                self._emit_recorded_event(event)
                last_event = event
                start_index += 1

            game_name = self.metadata.get("game") or self.match_metadata.get("game") or "ReplayGame"
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

            for event in self.events[start_index:]:
                delay = self.scheduler.compute_delay(last_event, event)
                if delay > 0:
                    time.sleep(delay)

                self._emit_recorded_event(event)
                last_event = event

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
            for payload, context in self._pending_conclusions:
                payload_copy = copy.deepcopy(payload)
                self._apply_event_context(context)
                self.event_bus.emit(EventType.PLAYER_CONCLUSION, **payload_copy)
            self._pending_conclusions.clear()
            self._handshake_started.clear()

        finally:
            self._cleanup_spectators(spectators)

    def _deserialize_events(self, events_data: List[Dict]) -> List[Event]:
        """Convert dictionary events to Event objects."""
        events = []
        for data in events_data:
            entry = dict(data)
            payload = dict(entry.get("data", {}))
            context_dict = dict(entry.get("context", {}))
            # Provide legacy fallback for turn_index
            if "phase_index" not in context_dict and "turn_index" in context_dict:
                context_dict["phase_index"] = context_dict["turn_index"]
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

        if event_type == EventType.MATCH_END.value:
            return

        if event_type == EventType.PLAYER_HANDSHAKE_START.value:
            player = payload.get("player")
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
            self._pending_conclusions.append((payload, context))
            return

        if event_type in {"turn", "gameplay"}:
            action_payload = payload.get("action")
            if isinstance(action_payload, dict):
                payload["action"] = self._rehydrate_action(action_payload)
        elif event_type == "event":
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

        phase_index = context.phase_index if context.phase_index is not None else context.turn_index
        if phase_index is not None:
            updates["phase_index"] = phase_index
            updates["turn_index"] = phase_index
        else:
            self.event_bus.clear_context("phase_index", "turn_index")

        if updates:
            self.event_bus.update_context(**updates)

    def _emit_handshake_start(self, payload: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Emit synthetic PLAYER_HANDSHAKE_START before COMPLETE/ABORT events."""
        start_payload: Dict[str, Any] = {
            "player": payload.get("player"),
        }
        match_id = context.get("match_id") or self.metadata.get("match_id")
        if match_id:
            start_payload["match_id"] = match_id
        self.event_bus.emit(EventType.PLAYER_HANDSHAKE_START, **start_payload)
        player = start_payload.get("player")
        if player:
            self._handshake_started.add(player)

    def _rehydrate_action(self, action_payload: Dict[str, Any]) -> ActionResult:
        """Convert serialized action payload back into ActionResult."""
        metadata = action_payload.get("metadata")
        metadata_copy = copy.deepcopy(metadata) if metadata else None
        action = ActionResult(
            action=action_payload.get("action"),
            reasoning=action_payload.get("reasoning"),
            metadata=metadata_copy,
        )
        raw_response = action_payload.get("raw_response")
        if raw_response is not None:
            action.raw_response = raw_response
        return action

    def _validate_schema_version(self, payload: Dict[str, Any]) -> str:
        """Ensure recordings declare a supported schema_version."""
        schema_version_value = payload.get("schema_version")
        schema_version = str(schema_version_value).strip() if schema_version_value else ""
        if not schema_version:
            raise ValueError(
                "ReplayEngine requires recording schema_version (expected 1.x). "
                "Re-export the match with Recorder v1.3+."
            )
        if not schema_version.startswith("1"):
            raise ValueError(
                f"Unsupported recording schema_version '{schema_version}'. "
                "ReplayEngine only supports Recorder v1.x artifacts."
            )
        return schema_version
