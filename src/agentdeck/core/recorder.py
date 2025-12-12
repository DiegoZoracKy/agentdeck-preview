"""Match recorder for AgentDeck framework."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union, cast

from .session import SessionContext
from .types import ActionResult, Event, EventContext, MatchResult


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

    SCHEMA_VERSION = "1.3"  # v1.3.0: Removed dialogue array, embed prompts in events

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

    def _extract_prompt_payload(self, event: Event, phase: str) -> Dict[str, Any]:
        """
        Extract PM1-PM6 metadata from event data and reshape into canonical prompt object.

        Per SPEC-RECORDER v1.3.0 §6.7, the prompt payload should contain:
        - PM1: prompt_text (exact text sent to LLM)
        - PM2: prompt_blocks (PromptBuilder composition)
        - PM3: response_text (raw LLM output)
        - PM4: renderer_output (RenderResult metadata)
        - PM5: controller_format (format instructions)
        - PM6: controller_metadata (parsing results)

        Args:
            event: Event to extract from
            phase: Lifecycle phase (handshake, turn, conclusion, parse_failure)

        Returns:
            Prompt payload dictionary
        """
        data = event.data
        metadata = data.get("metadata") or {}

        # Turn number - check data first, then metadata (gameplay events store it in metadata)
        turn_number = data.get("turn_number")
        if turn_number is None and "turn_number" in metadata:
            turn_number = metadata["turn_number"]

        prompt_payload: Dict[str, Any] = {
            "phase": phase,
            "turn_number": turn_number,
        }

        # PM1: prompt_text - check data first, then metadata.raw_prompt
        if "prompt_text" in data:
            prompt_payload["prompt_text"] = data["prompt_text"]
        elif "raw_prompt" in metadata:
            prompt_payload["prompt_text"] = metadata["raw_prompt"]

        # PM2: prompt_blocks - check data first, then metadata
        if "prompt_blocks" in data:
            prompt_payload["prompt_blocks"] = copy.deepcopy(data["prompt_blocks"])
        elif "prompt_blocks" in metadata:
            prompt_payload["prompt_blocks"] = copy.deepcopy(metadata["prompt_blocks"])

        # PM3: response_text - check multiple sources
        if "response_text" in data:
            prompt_payload["response_text"] = data["response_text"]
        elif "response" in data:
            prompt_payload["response_text"] = data["response"]
        elif "raw_response" in metadata:
            prompt_payload["response_text"] = metadata["raw_response"]

        # PM4: renderer_output - check data first, then metadata
        if "renderer_output" in data:
            prompt_payload["renderer_output"] = copy.deepcopy(data["renderer_output"])
        elif "renderer_output" in metadata:
            prompt_payload["renderer_output"] = copy.deepcopy(metadata["renderer_output"])

        # PM5: controller_format - check data first, then metadata
        if "controller_format" in data:
            prompt_payload["controller_format"] = data["controller_format"]
        elif "controller_format" in metadata:
            prompt_payload["controller_format"] = metadata["controller_format"]

        # PM6: controller_metadata - check data first, then metadata
        if "controller_metadata" in data:
            prompt_payload["controller_metadata"] = copy.deepcopy(data["controller_metadata"])
        elif "controller_metadata" in metadata:
            prompt_payload["controller_metadata"] = copy.deepcopy(metadata["controller_metadata"])

        # Usage info (part of PM4/PM6) - check data first, then metadata
        if "usage_info" in data:
            prompt_payload["usage_info"] = copy.deepcopy(data["usage_info"])
        elif "usage_info" in metadata:
            prompt_payload["usage_info"] = copy.deepcopy(metadata["usage_info"])

        # Duration/retries
        if hasattr(event, "duration"):
            prompt_payload["duration"] = event.duration
        if "retries" in data:
            prompt_payload["retries"] = data["retries"]
        elif "retries" in metadata:
            prompt_payload["retries"] = metadata["retries"]

        return prompt_payload

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
    ) -> None:
        metadata = {
            "session_id": self._context_value(context, "session_id"),
            "game": game.__class__.__name__,
            "players": [p.name for p in players],
            "matches_planned": matches,
            "started_at": datetime.now().isoformat(),
            "git_info": self._get_git_info(),
            "configuration": self._get_configuration(game, players),
        }
        self.current_batch = BatchRecording(
            batch_id=batch_id,
            schema_version=self.schema_version,
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
        self.current_match_id = match_id
        match_index = len(self.current_batch.match_refs) if self.current_batch else 0

        metadata = {
            "started_at": datetime.now().isoformat(),
            "session_id": self._context_value(context, "session_id"),
            "batch_id": self._context_value(context, "batch_id"),
            "context": {
                "session_id": self._context_value(context, "session_id"),
                "batch_id": self._context_value(context, "batch_id"),
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
            "game_config": {
                "name": game.__class__.__name__,
                "module": game.__class__.__module__,
            },
        }

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
        self.current_match_path = os.path.join(self.output_dir, f"{match_id}.json")

        # Flush buffered pre-match events (handshakes) to match recording
        for event_data in self._pending_events:
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

        data = event.data
        player = data.get("player")
        action_obj = data.get("action")

        if isinstance(action_obj, ActionResult):
            # ActionResult object (legacy path)
            action_value = action_obj.action
            reasoning = action_obj.reasoning
            metadata_snapshot = copy.deepcopy(action_obj.metadata) if action_obj.metadata else None
        elif isinstance(action_obj, dict):
            # Dict from Console.emit_turn() (current path)
            action_value = action_obj.get("action")
            reasoning = action_obj.get("reasoning")
            metadata_snapshot = (
                copy.deepcopy(action_obj.get("metadata")) if action_obj.get("metadata") else None
            )
        else:
            # Fallback for unknown types
            action_value = str(action_obj) if action_obj is not None else None
            reasoning = data.get("reasoning")
            metadata_snapshot = copy.deepcopy(data.get("metadata"))

        turn_payload: Dict[str, Any] = {
            "player": player,
            "action": action_value,
            "reasoning": reasoning,
            "state_before": copy.deepcopy(data.get("state_before")),
            "state_after": copy.deepcopy(data.get("state_after")),
            "metadata": metadata_snapshot,
        }
        if data.get("turn_context") is not None:
            turn_payload["turn_context"] = copy.deepcopy(data["turn_context"])
        if data.get("mechanic") is not None:
            turn_payload["mechanic"] = data["mechanic"]
        if data.get("phase_index") is not None:
            turn_payload["phase_index"] = data["phase_index"]
        if data.get("turn_index") is not None:
            turn_payload["turn_index"] = data["turn_index"]

        event_context = cast(EventContext, dict(event.context) if event.context else {})
        recorded_event = Event(
            type="gameplay",
            data=turn_payload,
            context=event_context,
            timestamp=event.timestamp,
            duration=event.duration,
        )
        event_data = self._serialize_event(recorded_event)
        if event_context:
            event_data["context"] = dict(event_context)

        # Embed prompt payload per SPEC-RECORDER v1.3.0 §6.7
        # Use original event (not recorded_event) since it has the metadata
        event_data["data"]["prompt"] = self._extract_prompt_payload(event, "turn")

        self.current_match.events.append(event_data)

        if metadata_snapshot and "usage_info" in metadata_snapshot:
            self.current_match.usage.record(metadata_snapshot["usage_info"])

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
        """
        Record PLAYER_HANDSHAKE_COMPLETE event with embedded prompt metadata.

        Per SPEC-RECORDER v1.3.0 §5, lifecycle events contain prompt payload
        in event.data["prompt"] with PM1-PM6 metadata.

        Handshakes arrive before MATCH_START, so buffer them until match recording exists.
        """
        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        # Embed prompt payload per SPEC-RECORDER v1.3.0 §6.7
        event_data["data"]["prompt"] = self._extract_prompt_payload(event, "handshake")
        event_data["data"]["accepted"] = True

        if not self.current_match:
            # Pre-match: buffer until MATCH_START
            self._pending_events.append(event_data)
        else:
            # Normal path: append to match events
            self.current_match.events.append(event_data)
            self._flush_current_match()

    def on_player_handshake_abort(self, event: Event) -> None:
        """
        Record PLAYER_HANDSHAKE_ABORT event with embedded prompt metadata.

        Per SPEC-RECORDER v1.3.0 §5, includes prompt payload plus accepted=False
        and rejection reason.

        Handshakes arrive before MATCH_START, so buffer them until match recording exists.
        """
        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        # Embed prompt payload per SPEC-RECORDER v1.3.0 §6.7
        event_data["data"]["prompt"] = self._extract_prompt_payload(event, "handshake")
        event_data["data"]["accepted"] = False
        event_data["data"]["reason"] = event.data.get("reason", "No reason provided")

        if not self.current_match:
            # Pre-match: buffer until MATCH_START
            self._pending_events.append(event_data)
        else:
            # Normal path: append to match events
            self.current_match.events.append(event_data)
            self._flush_current_match()

    def on_player_action_parse_failed(self, event: Event) -> None:
        """
        Record action parsing failure per SPEC-RECORDER v1.3.0 §5 and §6.7 PF1-PF2.

        Per SPEC-CONSOLE v0.5.0, this event is emitted before policy resolution, so we
        record the raw parse result with contextual metadata including prompt payload.
        """
        if not self.current_match:
            return

        # Serialize event exactly as emitted by Console (PF1)
        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        # Embed prompt payload per SPEC-RECORDER v1.3.0 §6.7 PF2
        event_data["data"]["prompt"] = self._extract_prompt_payload(event, "parse_failure")

        self.current_match.events.append(event_data)

        # Flush immediately to ensure failure is durable
        self._flush_current_match()

    def on_player_conclusion(self, event: Event) -> None:
        """
        Record PLAYER_CONCLUSION event with embedded prompt metadata.

        Per SPEC-RECORDER v1.3.0 §5, conclusion events contain prompt payload
        with post-match reflection metadata (PM1-PM6).
        """
        if not self.current_match:
            return

        event_data = self._serialize_event(event)
        if event.context:
            event_data["context"] = dict(event.context)

        # Embed prompt payload per SPEC-RECORDER v1.3.0 §6.7
        event_data["data"]["prompt"] = self._extract_prompt_payload(event, "conclusion")

        self.current_match.events.append(event_data)
        self._flush_current_match()

    def on_match_end(self, result: MatchResult, context: Optional[EventContext] = None):
        if not self.current_match:
            return

        self.current_match.metadata["ended_at"] = datetime.now().isoformat()
        self.current_match.winner = result.winner
        self.current_match.final_state = copy.deepcopy(result.final_state)
        self.current_match.seed = result.seed
        if result.metadata:
            self.current_match.metadata.setdefault("match", {}).update(
                copy.deepcopy(result.metadata)
            )
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
            # Extract actual match execution metadata (not recorder timing)
            match_metadata = self.current_match.metadata.get("match", {})

            # Use actual match start/end times if available from result metadata
            # Fall back to recorder timestamps if match metadata doesn't have them
            match_started_at = self.current_match.metadata.get("started_at")
            match_ended_at = self.current_match.metadata.get("ended_at")

            # Calculate actual end time from duration if available
            if "duration" in match_metadata and match_started_at:
                # Normalize ISO 8601 timezone format (Z → +00:00) for fromisoformat compatibility
                # This future-proofs against datetime.utcnow().isoformat() + "Z" timestamps
                normalized_start = match_started_at.replace("Z", "+00:00")
                start_dt = datetime.fromisoformat(normalized_start)
                end_dt = start_dt + timedelta(seconds=match_metadata["duration"])
                match_ended_at = end_dt.isoformat()

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

        self.current_batch.metadata["ended_at"] = datetime.now().isoformat()
        self.current_batch.metadata["matches_completed"] = len(results)
        self.current_batch.metadata["statistics"] = self._calculate_batch_statistics(results)

        # Include T3 metadata if provided
        if "duration" in kwargs:
            self.current_batch.metadata["duration"] = kwargs["duration"]
        if "seeds_used" in kwargs:
            self.current_batch.metadata["seeds_used"] = kwargs["seeds_used"]

        batch_path = os.path.join(self.output_dir, f"batch_{batch_id}.json")
        self._atomic_write(batch_path, self.current_batch.to_dict())
        self.current_batch = None
        self.batch_match_ids = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(path)) as tmp_file:
            json.dump(payload, tmp_file, indent=2, default=str)
            tmp_path = tmp_file.name
        os.replace(tmp_path, path)

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
                f"Missing schema_version in {Path(resolved).name}. " f"Expected schema version 1.x"
            )
        if not str(schema_version).startswith("1"):
            raise ValueError(
                f"Unsupported schema version: {schema_version}. "
                f"Expected schema version 1.x (current: {Recorder.SCHEMA_VERSION})"
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
                ["git", "status", "--short"], capture_output=True, text=True, check=True
            )
            dirty = bool(status.stdout.strip())
            return {"commit": commit_hash, "branch": branch, "dirty": dirty}
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Git not available or not a git repository
            return None

    def _get_player_configs(self, players) -> Dict[str, Dict[str, Any]]:
        configs: Dict[str, Dict[str, Any]] = {}
        for player in players:
            config = {
                "type": player.__class__.__name__,
                "module": player.__class__.__module__,
            }
            if hasattr(player, "model"):
                config["model"] = player.model
            if hasattr(player, "temperature"):
                config["temperature"] = player.temperature
            if hasattr(player, "max_tokens"):
                config["max_tokens"] = player.max_tokens
            if hasattr(player, "api_key"):
                key = str(getattr(player, "api_key", ""))
                if key and len(key) > 8:
                    config["api_key_prefix"] = f"***{key[-4:]}"
            configs[player.name] = config
        return configs

    def _get_configuration(self, game, players) -> Dict[str, Any]:
        configuration = {
            "agentdeck_version": self._get_agentdeck_version(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "timestamp": datetime.now().isoformat(),
            "game": {
                "name": game.__class__.__name__,
                "module": game.__class__.__module__,
            },
            "players": [
                {
                    "name": player.name,
                    "type": player.__class__.__name__,
                    "module": player.__class__.__module__,
                }
                for player in players
            ],
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
