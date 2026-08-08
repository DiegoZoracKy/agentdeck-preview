"""Match recorder for AgentDeck framework."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union, cast

from .artifact_safety import (
    ensure_contained_path,
    require_json_value,
    validate_artifact_id,
)
from .session import SessionContext
from .types import Event, EventContext, MatchResult


class RecorderCollector(Protocol):
    """Extension hook for attaching additional recorder metrics."""

    def on_match_start(
        self, match_id: str, metadata: Dict[str, Any]
    ) -> None:  # pragma: no cover - protocol
        ...

    def on_gameplay(self, event: Event) -> None:  # pragma: no cover - protocol
        ...

    def on_match_end(self) -> Dict[str, Any]:  # pragma: no cover - protocol
        ...


@dataclass
class APIUsageTracker:
    """Accumulates API usage statistics for a single match."""

    total_calls: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    models_used: Dict[str, int] = field(default_factory=dict)

    def record(self, usage: Dict[str, Any]) -> None:
        self.total_calls += 1
        self.total_tokens += usage.get("tokens", 0)
        self.total_prompt_tokens += usage.get("prompt_tokens", 0)
        self.total_completion_tokens += usage.get("completion_tokens", 0)
        self.total_cost += usage.get("cost", 0.0)
        self.total_latency_ms += usage.get("latency_ms", 0.0)
        model = usage.get("model", "unknown")
        self.models_used[model] = self.models_used.get(model, 0) + 1

    def summary(self) -> Dict[str, Any]:
        if self.total_calls == 0:
            return {}
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_cost": round(self.total_cost, 5),
            "average_latency_ms": (
                round(self.total_latency_ms / self.total_calls, 1) if self.total_calls else 0
            ),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "models_used": dict(self.models_used),
        }


@dataclass
class MatchRecording:
    """In-memory structure representing a match recording."""

    match_id: str
    game_name: str
    players: List[str]
    schema_version: str
    metadata: Dict[str, Any]
    events: List[Dict[str, Any]] = field(default_factory=list)
    usage: APIUsageTracker = field(default_factory=APIUsageTracker)
    collector_results: Dict[str, Any] = field(default_factory=dict)
    winner: Optional[str] = None
    final_state: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        metadata = copy.deepcopy(self.metadata)
        metadata.setdefault("players", list(self.players))
        metadata.setdefault("game", self.game_name)
        metadata.setdefault("match_id", self.match_id)
        if self.winner is not None:
            metadata.setdefault("winner", self.winner)
        if self.seed is not None:
            metadata.setdefault("seed", self.seed)

        started_at = metadata.get("started_at")
        ended_at = metadata.get("ended_at")
        duration_seconds = metadata.get("duration_seconds")

        match_metadata = metadata.get("match")
        if isinstance(match_metadata, dict):
            if started_at is None:
                started_at = match_metadata.get("started_at")
            if ended_at is None:
                ended_at = match_metadata.get("ended_at")
            if duration_seconds is None:
                duration_seconds = match_metadata.get("duration_seconds")
            if duration_seconds is None:
                duration_seconds = match_metadata.get("duration")

        payload: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "schema_type": "match",
            "match_id": self.match_id,
            "game": self.game_name,
            "players": list(self.players),
            "winner": self.winner,
            "final_state": copy.deepcopy(self.final_state),
            "seed": self.seed,
            "events": copy.deepcopy(self.events),
            "metadata": metadata,
            "batch_id": metadata.get("batch_id"),
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": duration_seconds,
        }
        summary = self.usage.summary()
        if summary:
            payload["api_usage_summary"] = summary
        if self.collector_results:
            payload["collector_data"] = copy.deepcopy(self.collector_results)
        return payload


@dataclass
class BatchRecording:
    """Aggregated batch metadata."""

    batch_id: str
    schema_version: str
    metadata: Dict[str, Any]
    match_refs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload_metadata = copy.deepcopy(self.metadata)
        payload_metadata.setdefault("batch_id", self.batch_id)

        return {
            "schema_version": self.schema_version,
            "schema_type": "batch",
            "batch_id": self.batch_id,
            "match_refs": copy.deepcopy(self.match_refs),
            "metadata": payload_metadata,
        }


class Recorder:
    """Records match data for persistence and replay.

    Responds to event callbacks via duck typing (``on_*`` methods).
    """

    SCHEMA_VERSION = "2.0"
    BATCH_SCHEMA_VERSION = "1.0"  # SPEC-RECORDER SV1: batch schema remains 1.0

    def __init__(
        self,
        output_dir: str = "agentdeck_records",
        *,
        session: Optional[SessionContext] = None,
        collectors: Optional[List[RecorderCollector]] = None,
        schema_version: str = SCHEMA_VERSION,
    ) -> None:
        self.session = session
        self.schema_version = schema_version
        self.collectors = collectors or []

        base_dir = session.record_directory if session else output_dir
        self.output_dir = base_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.current_match: Optional[MatchRecording] = None
        self.current_match_path: Optional[str] = None
        self.current_match_id: Optional[str] = None
        self.current_batch: Optional[BatchRecording] = None
        self.batch_match_ids: List[str] = []

        # Pre-match event buffer (handshake events arrive before MATCH_START)
        self._pending_events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def bind_session(self, session: SessionContext) -> None:
        """Attach a session context after initialization."""
        self.session = session
        self.output_dir = session.record_directory
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _normalize_usage_payload(payload: Any) -> Optional[Dict[str, Any]]:
        """Normalize usage metadata across lifecycle and gameplay payload shapes."""
        if not isinstance(payload, dict):
            return None

        prompt_tokens = payload.get("prompt_tokens", payload.get("input_tokens", 0)) or 0
        completion_tokens = payload.get("completion_tokens", payload.get("output_tokens", 0)) or 0
        total_tokens = payload.get("tokens")
        if total_tokens is None:
            total_tokens = payload.get("total_tokens")
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens

        cost = payload.get("cost", 0.0) or 0.0
        if not any([prompt_tokens, completion_tokens, total_tokens, cost]):
            return None

        return {
            "tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "latency_ms": payload.get("latency_ms", 0.0) or 0.0,
            "model": payload.get("model") or payload.get("provider_model") or "unknown",
        }

    def _extract_usage_payload(self, data: Any) -> Optional[Dict[str, Any]]:
        """Extract usage metadata from canonical event payloads."""
        if not isinstance(data, dict):
            return None

        interaction = data.get("interaction")
        metadata = data.get("metadata")

        candidates = [
            interaction.get("usage_info") if isinstance(interaction, dict) else None,
            data.get("usage_info"),  # lifecycle events
            metadata.get("usage_info") if isinstance(metadata, dict) else None,
        ]

        for candidate in candidates:
            normalized = self._normalize_usage_payload(candidate)
            if normalized:
                return normalized
        return None

    def _record_usage_from_payload(self, data: Any) -> None:
        """Accumulate API usage into the current match summary when available."""
        if not self.current_match:
            return
        usage = self._extract_usage_payload(data)
        if usage:
            self.current_match.usage.record(usage)

    @staticmethod
    def _sanitize_gameplay_state_for_recording(state: Any) -> Any:
        """
        Remove engine-internal runtime keys from recorded gameplay state snapshots.

        We keep gameplay artifacts focused on game-domain state. Runtime mechanics
        internals (e.g. _turn_count, _first_player_idx) remain available elsewhere
        in metadata/final_state when needed for reproducibility.
        """
        if not isinstance(state, dict):
            return copy.deepcopy(state)
        return {
            key: copy.deepcopy(value)
            for key, value in state.items()
            if not (isinstance(key, str) and key.startswith("_"))
        }

    # ------------------------------------------------------------------
    # Event handlers (duck-typed)
    # ------------------------------------------------------------------
    def on_batch_start(
        self,
        batch_id: str,
        game,
        players,
        matches: int,
        context: Optional[EventContext] = None,
        **kwargs: Any,
    ) -> None:
        validate_artifact_id(batch_id, field="batch_id")
        started_at = self._context_iso_timestamp(context) or datetime.now(timezone.utc).isoformat()
        metadata = {
            "session_id": self._context_value(context, "session_id"),
            "game": game.__class__.__name__,
            "players": [p.name for p in players],
            "matches_planned": matches,
            "started_at": started_at,
            "git_info": self._get_git_info(),
            "configuration": self._get_configuration(game, players),
        }
        if kwargs:
            metadata.update(copy.deepcopy(kwargs))
        self.current_batch = BatchRecording(
            batch_id=batch_id,
            schema_version=self.BATCH_SCHEMA_VERSION,
            metadata=metadata,
        )
        self.batch_match_ids = []

    def on_match_start(
        self,
        game,
        players,
        match_id: Optional[str] = None,
        context: Optional[EventContext] = None,
        **kwargs: Any,  # Accept player ordering fields (seed, player_order, etc.)
    ) -> None:
        match_id = match_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        validate_artifact_id(match_id, field="match_id")
        self.current_match_id = match_id
        match_index = len(self.current_batch.match_refs) if self.current_batch else 0
        batch_id = self._context_value(context, "batch_id")
        if not isinstance(batch_id, str) or not batch_id:
            raise ValueError("Recorder.on_match_start requires context['batch_id']")
        started_at = self._context_iso_timestamp(context) or datetime.now(timezone.utc).isoformat()

        metadata = {
            "started_at": started_at,
            "session_id": self._context_value(context, "session_id"),
            "batch_id": batch_id,
            "context": {
                "session_id": self._context_value(context, "session_id"),
                "batch_id": batch_id,
                "match_index": match_index,
                "total_matches_in_batch": (
                    self.current_batch.metadata["matches_planned"] if self.current_batch else None
                ),
            },
            "environment": {
                "agentdeck_version": self._get_agentdeck_version(),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "git_info": self._get_git_info(),
            },
            "player_configs": self._get_player_configs(players),
            "player_summaries": [
                player.get_summary() if hasattr(player, "get_summary") else {"name": player.name}
                for player in players
            ],  # Per SPEC-RECORDER MC3
            "game_config": self._get_game_config(game),
        }
        match_metadata = {
            key: copy.deepcopy(value)
            for key, value in kwargs.items()
            if key
            in {
                "seed",
                "player_order",
                "player_order_source",
                "first_player",
                "fairness_policy",
            }
        }
        if match_metadata:
            metadata["match"] = match_metadata

        if self.session:
            metadata.setdefault(
                "session",
                {
                    "session_id": self.session.session_id,
                    "started_at": self.session.started_at,
                    "seed": self.session.seed,
                },
            )

        self.current_match = MatchRecording(
            match_id=match_id,
            game_name=game.__class__.__name__,
            players=[p.name for p in players],
            schema_version=self.schema_version,
            metadata=metadata,
        )
        self.current_match_path = str(
            ensure_contained_path(
                self.output_dir,
                Path(self.output_dir) / f"{match_id}.json",
            )
        )

        # Flush buffered pre-match events (handshakes) to match recording
        for event_data in self._pending_events:
            self._record_usage_from_payload(event_data.get("data"))
            self.current_match.events.append(event_data)
        self._pending_events.clear()

        for collector in self.collectors:
            if hasattr(collector, "on_match_start"):
                collector.on_match_start(match_id, copy.deepcopy(metadata))

        # Persist initial match stub
        self._flush_current_match()

    def on_player_instructed(
        self,
        player: str,
        instructions: str,
        context: Optional[EventContext] = None,
    ) -> None:
        if not self.current_match:
            return
        event_context = cast(EventContext, dict(context) if context else {})
        event = Event(
            type="player_instructed",
            data={"player": player, "instructions": instructions},
            context=event_context,
        )
        event_data = self._serialize_event(event)
        if context:
            event_data["context"] = dict(context)
        elif event_context:
            event_data["context"] = dict(event_context)
        self.current_match.events.append(event_data)
        self._flush_current_match()

    def on_gameplay(self, event: Event) -> None:
        if not self.current_match:
            return

        event_context = cast(EventContext, dict(event.context) if event.context else {})
        event_duration = event.duration
        if event.data.get("turn_context") is not None:
            turn_context = event.data["turn_context"]
            if isinstance(turn_context, dict) and isinstance(
                turn_context.get("duration"), (int, float)
            ):
                event_duration = float(turn_context["duration"])

        turn_payload = copy.deepcopy(event.data)
        if "state_before" in turn_payload:
            turn_payload["state_before"] = self._sanitize_gameplay_state_for_recording(
                turn_payload.get("state_before")
            )
        if "state_after" in turn_payload:
            turn_payload["state_after"] = self._sanitize_gameplay_state_for_recording(
                turn_payload.get("state_after")
            )

        recorded_event = Event(
            type="gameplay",
            data=turn_payload,
            context=event_context,
            timestamp=event.timestamp,
            duration=event_duration,
        )
        event_data = self._serialize_event(recorded_event)
        if event_context:
            event_data["context"] = dict(event_context)

        self.current_match.events.append(event_data)
        self._record_usage_from_payload(event.data)

        for collector in self.collectors:
            if hasattr(collector, "on_gameplay"):
                collector.on_gameplay(recorded_event)

        self._flush_current_match()

    def on_event(self, event: Event, context: Optional[EventContext] = None):
        if not self.current_match:
            return
        event_data = self._serialize_event(event)
        if context:
            event_data["context"] = dict(context)
        elif event.context:
            event_data["context"] = dict(event.context)
        self.current_match.events.append(event_data)
        self._flush_current_match()

    def on_player_handshake_complete(self, event: Event) -> None:
        """Record PLAYER_HANDSHAKE_COMPLETE exactly as emitted."""
        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        event_data["data"]["accepted"] = True

        if not self.current_match:
            # Pre-match: buffer until MATCH_START
            self._pending_events.append(event_data)
        else:
            # Normal path: append to match events
            self.current_match.events.append(event_data)
            self._record_usage_from_payload(event.data)
            self._flush_current_match()

    def on_player_handshake_start(self, event: Event) -> None:
        """
        Record PLAYER_HANDSHAKE_START event with prompt metadata.

        Handshake start events arrive before MATCH_START, so they are buffered
        until the match recording is created.
        """
        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        if not self.current_match:
            self._pending_events.append(event_data)
        else:
            self.current_match.events.append(event_data)
            self._flush_current_match()

    def on_player_handshake_abort(self, event: Event) -> None:
        """Record PLAYER_HANDSHAKE_ABORT exactly as emitted."""
        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        event_data["data"]["accepted"] = False
        event_data["data"]["reason"] = event.data.get("reason", "No reason provided")

        if not self.current_match:
            # Pre-match: buffer until MATCH_START
            self._pending_events.append(event_data)
        else:
            # Normal path: append to match events
            self.current_match.events.append(event_data)
            self._record_usage_from_payload(event.data)
            self._flush_current_match()

    def on_player_action_parse_failed(self, event: Event) -> None:
        """Record action parsing failure exactly as emitted."""
        if not self.current_match:
            return

        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        self.current_match.events.append(event_data)
        self._record_usage_from_payload(event.data)

        # Flush immediately to ensure failure is durable
        self._flush_current_match()

    def on_player_conclusion(self, event: Event) -> None:
        """Record PLAYER_CONCLUSION exactly as emitted."""
        if not self.current_match:
            return

        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        self.current_match.events.append(event_data)
        self._record_usage_from_payload(event.data)
        self._flush_current_match()

    def on_match_end(self, result: MatchResult, context: Optional[EventContext] = None):
        if not self.current_match:
            return

        self.current_match.winner = result.winner
        self.current_match.final_state = copy.deepcopy(result.final_state)
        self.current_match.seed = result.seed
        if result.metadata:
            self.current_match.metadata.setdefault("match", {}).update(
                copy.deepcopy(result.metadata)
            )
            # Keep player_summaries cost fields aligned with finalized per-match costs.
            player_costs = result.metadata.get("player_costs")
            summaries = self.current_match.metadata.get("player_summaries")
            if isinstance(player_costs, dict) and isinstance(summaries, list):
                for summary in summaries:
                    if not isinstance(summary, dict):
                        continue
                    player_name = summary.get("name")
                    if not isinstance(player_name, str):
                        continue
                    if player_name in player_costs:
                        try:
                            summary["total_cost"] = float(player_costs[player_name])
                        except (TypeError, ValueError):
                            continue

        match_metadata = self.current_match.metadata.get("match", {})
        if not isinstance(match_metadata, dict):
            match_metadata = {}

        started_at = match_metadata.get("started_at") or self.current_match.metadata.get(
            "started_at"
        )
        ended_at = (
            match_metadata.get("ended_at")
            or self._context_iso_timestamp(context)
            or datetime.now(timezone.utc).isoformat()
        )
        duration_seconds = match_metadata.get("duration_seconds")
        if duration_seconds is None:
            duration_seconds = match_metadata.get("duration")

        if duration_seconds is None and isinstance(started_at, str) and isinstance(ended_at, str):
            try:
                start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                duration_seconds = max(0.0, (end_dt - start_dt).total_seconds())
            except ValueError:
                duration_seconds = None

        self.current_match.metadata["started_at"] = started_at
        self.current_match.metadata["ended_at"] = ended_at
        if duration_seconds is not None:
            self.current_match.metadata["duration_seconds"] = duration_seconds

        if context:
            self.current_match.metadata.setdefault("context", {})["end"] = dict(context)

        collector_payload: Dict[str, Any] = {}
        collector_counts: Dict[str, int] = {}
        for collector in self.collectors:
            if hasattr(collector, "on_match_end"):
                payload = collector.on_match_end()
                if payload:
                    # Enumerate duplicate class names to prevent key collisions
                    class_name = collector.__class__.__name__
                    count = collector_counts.get(class_name, 0)
                    collector_counts[class_name] = count + 1

                    key = class_name if count == 0 else f"{class_name}_{count}"
                    collector_payload[key] = payload
        if collector_payload:
            self.current_match.collector_results = collector_payload

        self._flush_current_match()

        if self.current_batch:
            match_metadata = self.current_match.metadata.get("match", {})
            if not isinstance(match_metadata, dict):
                match_metadata = {}

            match_started_at = match_metadata.get("started_at") or self.current_match.metadata.get(
                "started_at"
            )
            match_ended_at = match_metadata.get("ended_at") or self.current_match.metadata.get(
                "ended_at"
            )
            match_duration_seconds = match_metadata.get("duration_seconds")
            if match_duration_seconds is None:
                match_duration_seconds = match_metadata.get("duration")
            if match_duration_seconds is None:
                match_duration_seconds = self.current_match.metadata.get("duration_seconds")
            if (
                match_duration_seconds is None
                and isinstance(match_started_at, str)
                and isinstance(match_ended_at, str)
            ):
                try:
                    start_dt = datetime.fromisoformat(match_started_at.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(match_ended_at.replace("Z", "+00:00"))
                    match_duration_seconds = max(0.0, (end_dt - start_dt).total_seconds())
                except ValueError:
                    match_duration_seconds = None

            # Derive ended_at only when duration is known and ended_at missing.
            if (
                not match_ended_at
                and match_duration_seconds is not None
                and isinstance(match_started_at, str)
            ):
                try:
                    start_dt = datetime.fromisoformat(match_started_at.replace("Z", "+00:00"))
                    end_dt = start_dt + timedelta(seconds=float(match_duration_seconds))
                    match_ended_at = end_dt.isoformat()
                except ValueError:
                    pass

            # Use actual turn count from match metadata if available
            # Fallback: count gameplay events (for old recordings or incomplete metadata)
            actual_turns = match_metadata.get("turns")
            if actual_turns is None:
                # Fallback path: old recordings may lack metadata.match.turns
                actual_turns = len(
                    [e for e in self.current_match.events if e["type"] == "gameplay"]
                )

            match_ref = {
                "match_id": self.current_match.match_id,
                "filename": os.path.basename(self.current_match_path),
                "winner": result.winner,
                "turns": actual_turns,
                "started_at": match_started_at,
                "ended_at": match_ended_at,
                "duration_seconds": match_duration_seconds,
                "player_summaries": self.current_match.metadata.get(
                    "player_summaries", []
                ),  # Per SPEC-RECORDER batch provenance
            }

            # Include player_costs and cost from match metadata for post-hoc analysis (SPEC-RESEARCH MA1, MA3)
            if "player_costs" in match_metadata:
                match_ref["player_costs"] = match_metadata["player_costs"]
            if "cost" in match_metadata:
                match_ref["cost"] = match_metadata["cost"]
            if "duration" in match_metadata:
                match_ref["duration"] = match_metadata["duration"]

            self.current_batch.match_refs.append(match_ref)
            self.batch_match_ids.append(self.current_match.match_id)

        self.current_match = None
        self.current_match_path = None
        self.current_match_id = None

        # Defensive: clear buffer to prevent cross-match leaks
        self._pending_events.clear()

    def on_batch_end(
        self,
        batch_id: str,
        results: List[MatchResult],
        context: Optional[EventContext] = None,
        **kwargs: Any,  # Accept T3 metadata (matches_completed, duration, seeds_used, etc.)
    ):
        if not self.current_batch:
            return

        self.current_batch.metadata["ended_at"] = (
            self._context_iso_timestamp(context) or datetime.now(timezone.utc).isoformat()
        )
        self.current_batch.metadata["matches_completed"] = len(results)
        self.current_batch.metadata["statistics"] = self._calculate_batch_statistics(results)

        # Include T3 metadata if provided
        if "duration" in kwargs:
            self.current_batch.metadata["duration"] = kwargs["duration"]
        if "seeds_used" in kwargs:
            self.current_batch.metadata["seeds_used"] = kwargs["seeds_used"]

        validate_artifact_id(batch_id, field="batch_id")
        batch_path = ensure_contained_path(
            self.output_dir,
            Path(self.output_dir) / f"batch_{batch_id}.json",
        )
        self._atomic_write(str(batch_path), self.current_batch.to_dict())
        self.current_batch = None
        self.batch_match_ids = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _timestamp_to_iso(timestamp: Optional[Any]) -> Optional[str]:
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
        return None

    def _context_iso_timestamp(self, context: Optional[EventContext]) -> Optional[str]:
        if not context:
            return None
        return self._timestamp_to_iso(context.get("timestamp"))

    def _flush_current_match(self) -> None:
        if not self.current_match or not self.current_match_path:
            return
        self._atomic_write(self.current_match_path, self.current_match.to_dict())

    def _serialize_event(self, event: Event) -> Dict[str, Any]:
        return {
            "type": event.type.value if hasattr(event.type, "value") else event.type,
            "data": event.data,
            "timestamp": event.timestamp,
            "duration": event.duration,
        }

    def _atomic_write(self, path: str, payload: Dict[str, Any]) -> None:
        target = ensure_contained_path(self.output_dir, path)
        require_json_value(payload, field="recorder payload")
        serialized = json.dumps(payload, indent=2, allow_nan=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=target.parent,
            encoding="utf-8",
        ) as tmp_file:
            tmp_file.write(serialized)
            tmp_path = tmp_file.name
        os.replace(tmp_path, target)

    @staticmethod
    def load_match(path: Union[str, os.PathLike[str]]) -> Dict[str, Any]:
        """Load a match recording from disk.

        Args:
            path: Path to the match JSON file

        Returns:
            Normalized match data dictionary

        Raises:
            ValueError: If schema version is unsupported or missing
        """
        resolved = os.fspath(path)
        with open(resolved, "r", encoding="utf-8") as handle:
            raw: Dict[str, Any] = json.load(handle)

        # Enforce schema version
        schema_version = raw.get("schema_version")
        if not schema_version:
            raise ValueError(
                f"Missing schema_version in {Path(resolved).name}. "
                f"Expected schema version {Recorder.SCHEMA_VERSION}"
            )
        if str(schema_version) != Recorder.SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema version: {schema_version}. "
                f"Expected schema version {Recorder.SCHEMA_VERSION}"
            )

        # Extract metadata
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError("Invalid metadata format: expected dict")

        # Ensure match_id is present
        metadata.setdefault("match_id", raw.get("match_id") or Path(resolved).stem)

        return {
            "schema_version": schema_version,
            "events": raw.get("events", []),
            "winner": raw.get("winner"),
            "final_state": raw.get("final_state", {}),
            "seed": raw.get("seed"),
            "metadata": metadata,
            "api_usage_summary": raw.get("api_usage_summary"),
            "collector_data": raw.get("collector_data"),
        }

    def _context_value(self, context: Optional[EventContext], key: str) -> Optional[Any]:
        if context and key in context:
            return context[key]
        if self.session and key == "session_id":
            return self.session.session_id
        return None

    def _get_agentdeck_version(self) -> str:
        try:
            from .. import __version__

            return __version__
        except ImportError:
            return "unknown"

    def _get_git_info(self) -> Optional[Dict[str, Any]]:
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"], capture_output=True, check=True, text=True
            )
            commit_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "branch", "--show-current"], capture_output=True, text=True, check=True
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                capture_output=True,
                text=True,
                check=True,
            )
            dirty = bool(status.stdout.strip())
            return {"commit": commit_hash, "branch": branch, "dirty": dirty}
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Git not available or not a git repository
            return None

    def _get_player_configs(self, players) -> Dict[str, Dict[str, Any]]:
        configs: Dict[str, Dict[str, Any]] = {}
        for player in players:
            if hasattr(player, "describe"):
                config = copy.deepcopy(player.describe())
            else:
                config = {
                    "name": player.name,
                    "type": player.__class__.__name__,
                    "module": player.__class__.__module__,
                }
            require_json_value(config, field=f"player_configs.{player.name}")
            configs[player.name] = config
        return configs

    def _get_game_config(self, game) -> Dict[str, Any]:
        if hasattr(game, "describe"):
            config = copy.deepcopy(game.describe())
        else:
            config = {
                "name": game.__class__.__name__,
                "module": game.__class__.__module__,
                "allowed_actions": list(getattr(game, "allowed_actions", [])),
                "config": {},
            }
        require_json_value(config, field="game_config")
        return config

    def _get_configuration(self, game, players) -> Dict[str, Any]:
        configuration = {
            "agentdeck_version": self._get_agentdeck_version(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "game": self._get_game_config(game),
            "players": list(self._get_player_configs(players).values()),
        }
        return configuration

    def _calculate_batch_statistics(self, results: List[MatchResult]) -> Dict[str, Any]:
        total_matches = len(results)
        if total_matches == 0:
            return {"total_matches": 0}

        all_players = set()
        for result in results:
            if result.metadata and "players" in result.metadata:
                all_players.update(result.metadata["players"])

        player_stats = {
            player: {
                "matches_played": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_turns_in_wins": 0,
                "total_turns_in_losses": 0,
                "as_first_player": {"played": 0, "wins": 0},
            }
            for player in all_players
        }

        for result in results:
            metadata = result.metadata or {}
            players = metadata.get("players", [])
            first_player = metadata.get("first_player", {}).get("name")
            turns = metadata.get("turns", 0)

            for player in players:
                # Ensure player exists in stats (defensive)
                if player not in player_stats:
                    player_stats[player] = {
                        "matches_played": 0,
                        "wins": 0,
                        "losses": 0,
                        "win_rate": 0.0,
                        "total_turns_in_wins": 0,
                        "total_turns_in_losses": 0,
                        "as_first_player": {"played": 0, "wins": 0},
                    }
                player_stats[player]["matches_played"] += 1

            winner = result.winner
            if winner:
                # Ensure winner exists in stats (defensive)
                if winner not in player_stats:
                    player_stats[winner] = {
                        "matches_played": 0,
                        "wins": 0,
                        "losses": 0,
                        "win_rate": 0.0,
                        "total_turns_in_wins": 0,
                        "total_turns_in_losses": 0,
                        "as_first_player": {"played": 0, "wins": 0},
                    }
                player_stats[winner]["wins"] += 1
                player_stats[winner]["total_turns_in_wins"] += turns
                if first_player == winner:
                    player_stats[winner]["as_first_player"]["wins"] += 1
            else:
                # Draw
                continue

            for player in players:
                if player != winner:
                    player_stats[player]["losses"] += 1
                    player_stats[player]["total_turns_in_losses"] += turns

            if first_player and first_player in player_stats:
                player_stats[first_player]["as_first_player"]["played"] += 1

        for stats in player_stats.values():
            played = stats["matches_played"]
            stats["win_rate"] = stats["wins"] / played if played else 0.0

        return {
            "total_matches": total_matches,
            "players": player_stats,
        }


__all__ = ["Recorder", "RecorderCollector"]
