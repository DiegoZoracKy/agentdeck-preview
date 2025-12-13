"""
MatchRuntime: Per-match infrastructure context for game mechanics.

Implements the canonical contract per:
- SPEC-MATCH-RUNTIME v1.0.0 §4 (Public API)
- SPEC-MATCH-RUNTIME v1.0.0 §5 (Invariants & Guarantees MR1-MR7)

Key responsibilities:
- Encapsulate per-match state (session_id, batch_id, match_id, seed, RNG)
- Emit lifecycle + gameplay events on behalf of mechanics
- Collect prompt/response/action metadata for recorder and cost tracking
- Execute parse-failure policies defined by games
- Provide helpers for validation, logging, and future features (checkpointing)

Critical invariants:
- MR1: Runtime Isolation - one runtime per match, no shared state
- MR2: Event Ordering - lifecycle ordering enforced with mechanic metadata
- MR3: Recorder Consistency - record_turn flushes in order
- MR4: Parse Failure Integrity - emit event, log, update recorder, return policy
- MR5: RNG Traceability - fork labels recorded in debug logs
- MR6: Exception Safety - restore bindings even if mechanics raise
- MR7: Extensibility - new methods remain backward compatible
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .types import (
    ActionParseError,
    ActionResult,
    EventType,
    LogLevel,
    ParseFailurePolicy,
    PromptBlock,
    RandomGenerator,
    TurnContext,
)

if TYPE_CHECKING:
    from .base.game import Game
    from .base.player import Player
    from .console import Console
    from .logging import AgentDeckLogger
    from .recorder import Recorder


class MatchRuntime:
    """
    Per-match infrastructure context that Console passes to game.run(runtime, players).

    Mechanics use this as the exclusive gateway for event emission, recorder writes,
    RNG usage, parse-failure handling, and state validation. This prevents duplication
    of orchestration logic across different mechanics (turn-based, simultaneous, realtime).

    Example usage (from TurnLoop):
        >>> runtime = MatchRuntime(
        ...     console=console,
        ...     game=game,
        ...     match_context=match_ctx,
        ...     recorder=console.recorder,
        ...     logger=console.logger,
        ...     rng=match_ctx.rng,
        ... )
        >>> # Emit events
        >>> runtime.emit_event(EventType.TURN_START, player=player_name, turn=1)
        >>> # Record turn
        >>> runtime.record_turn(
        ...     player=player_name,
        ...     prompt_blocks=prompt_blocks,
        ...     response_text=response,
        ...     action=action_result,
        ...     turn_context=turn_ctx,
        ... )
        >>> # Fork RNG
        >>> turn_rng = runtime.fork_rng(f"turn_{turn_number}")
        >>> # Handle parse failure
        >>> policy = runtime.handle_parse_failure(player, error, turn_context=turn_ctx)

    See SPEC-MATCH-RUNTIME.md §6 for complete usage pattern.
    """

    def __init__(
        self,
        *,
        console: Console,
        game: Game,
        match_id: str,
        session_id: str,
        batch_id: str,
        seed: int,
        max_turns: int,
        recorder: Recorder,
        logger: AgentDeckLogger,
        rng: RandomGenerator,
        previous_match_result: Optional[Any] = None,
        events_list: Optional[List] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a new MatchRuntime instance.

        Args:
            console: Console instance (provides access to EventBus and parse-failure helper)
            game: Game instance (for validation and parse-failure policy hooks)
            match_id: Unique match identifier
            session_id: Session identifier
            batch_id: Batch identifier
            seed: Match seed for reproducibility
            max_turns: Maximum turns before truncation
            recorder: Recorder instance for capturing dialogue
            logger: Logger instance for structured logging
            rng: Match-specific RNG (base for all forks)
            previous_match_result: Previous match result for stateful ordering (optional)
            events_list: MatchExecutionContext.events list for replay parity (TL6)

        Note:
            Console creates one runtime per match. Mechanics never touch EventBus directly -
            runtime forwards everything via console.
        """
        self._console = console
        self._game = game
        self._match_id = match_id
        self._session_id = session_id
        self._batch_id = batch_id
        self._seed = seed
        self._max_turns = max_turns
        self._recorder = recorder
        self._logger = logger
        self._rng = rng
        self._previous_match_result = previous_match_result
        self._events_list = events_list  # For replay parity (TL6)
        self._initial_state = initial_state

    @property
    def match_id(self) -> str:
        """Match identifier."""
        return self._match_id

    @property
    def session_id(self) -> str:
        """Session identifier."""
        return self._session_id

    @property
    def batch_id(self) -> str:
        """Batch identifier."""
        return self._batch_id

    @property
    def seed(self) -> int:
        """Match seed."""
        return self._seed

    @property
    def max_turns(self) -> int:
        """Maximum turns before truncation."""
        return self._max_turns

    @property
    def initial_state(self) -> Optional[Dict[str, Any]]:
        """Optional precomputed game state to seed mechanics."""
        return self._initial_state

    @initial_state.setter
    def initial_state(self, state: Optional[Dict[str, Any]]) -> None:
        self._initial_state = state

    @property
    def events(self) -> List:
        """Events list for replay parity (TL6 - exposes exec_ctx.events)."""
        return self._events_list if self._events_list is not None else []

    @property
    def previous_match_result(self) -> Optional[Any]:
        """Previous match result for stateful ordering."""
        return self._previous_match_result

    def emit_event(self, event_type: str, /, **data: Any) -> None:
        """
        Emit lifecycle or gameplay event with pre-populated context.

        Emits events via console.event_bus with session_id/batch_id/match_id context.
        Mechanics MUST use this for all GAMEPLAY + custom events.

        Args:
            event_type: Event type (EventType enum value or string)
            **data: Additional event payload fields

        Example:
            >>> runtime.emit_event(EventType.TURN_START, player="Alice", turn_number=1)
            >>> runtime.emit_event("card_drawn", player="Bob", card="Ace of Spades")

        Invariants:
            - MR2: Ensures lifecycle ordering (MATCH_START < GAMEPLAY < MATCH_END)
            - Automatically enforces SPEC-OBSERVABILITY payload requirements
        """
        # Convert EventType enum to string if needed
        if hasattr(event_type, "value"):
            event_type = event_type.value

        # Emit via console event bus
        # Note: session_id/batch_id/match_id are added to EventContext by EventBus,
        # not to the event payload. The console/event_bus handles context enrichment.
        self._console.event_bus.emit(event_type, **data)

    def record_turn(
        self,
        *,
        player: str,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        action: ActionResult,
        turn_context: TurnContext,
        prompt_blocks: Optional[List[PromptBlock]] = None,
    ) -> None:
        """
        Emit canonical GAMEPLAY event for turn recording (TL4, MR3, PM1-PM6).

        Per SPEC-GAME-MECHANIC-TURN-BASED v2.0.0 TL4 and SPEC-MATCH-RUNTIME §4.3,
        this builds and emits a GAMEPLAY event containing turn data with complete
        prompt metadata (PM1-PM6), ensuring Recorder and spectators receive the
        full transcript via the event bus.

        Automatically extracts PM metadata from ActionResult:
        - PM1 (response_text): from action.raw_response
        - PM2-PM6 (controller metadata, usage_info): from action.metadata
        - prompt_blocks: from action.metadata if available, or explicit parameter

        Args:
            player: Player name
            state_before: Game state before action applied
            state_after: Game state after action applied
            action: Parsed action result (contains raw_response and metadata)
            turn_context: Turn metadata (turn_number, match_id, timestamps, etc.)
            prompt_blocks: Optional explicit prompt blocks (if not in action.metadata)

        Invariants:
            - MR3: Emits GAMEPLAY event via runtime event bus
            - TL4: Every successful player.decide produces GAMEPLAY event
            - PM1-PM6: Always includes raw_response and available metadata
        """
        import copy

        from .types import EventType

        # Build GAMEPLAY event payload (SPEC-OBSERVABILITY §3.2)
        payload = {
            "mechanic": "turn_based",
            "match_id": turn_context.match_id,
            "player": player,
            "turn_context": turn_context.to_dict(),
            "state_before": copy.deepcopy(state_before),
            "state_after": copy.deepcopy(state_after),
            "action": {
                "action": action.action,
                "reasoning": action.reasoning,
                "metadata": copy.deepcopy(action.metadata) if action.metadata else {},
                "raw_response": action.raw_response,
            },
        }

        # Extract and include PM1-PM6 prompt metadata at top level (TL4 requirement)
        # Per SPEC-RECORDER v1.3.0 §6.7, recorder's _extract_prompt_payload looks for
        # PM fields in event.data (top-level), not nested in event.data["prompt"].
        # The recorder will extract these and embed in event_data["data"]["prompt"].

        # PM1: Prompt text (raw prompt rendered by PromptBuilder)
        if action.metadata and "raw_prompt" in action.metadata:
            payload["prompt_text"] = action.metadata["raw_prompt"]

        # PM3: Raw response text (ActionResult.raw_response)
        if action.raw_response:
            payload["response_text"] = action.raw_response

        # PM2-PM6: Extract from action.metadata if present (deep-copy for immutability)
        if action.metadata:
            # prompt_blocks from metadata (if embedded by controller) - DEEP COPY
            if "prompt_blocks" in action.metadata and not prompt_blocks:
                payload["prompt_blocks"] = copy.deepcopy(action.metadata["prompt_blocks"])

            # Controller format/metadata - deep copy controller_metadata
            if "controller_format" in action.metadata:
                payload["controller_format"] = action.metadata["controller_format"]
            if "controller_metadata" in action.metadata:
                payload["controller_metadata"] = copy.deepcopy(
                    action.metadata["controller_metadata"]
                )

            # Usage info (tokens, cost, latency) - already deep-copied above
            if "usage_info" in action.metadata:
                payload["usage_info"] = copy.deepcopy(action.metadata["usage_info"])

            # Renderer output (if present) - DEEP COPY
            if "renderer_output" in action.metadata:
                payload["renderer_output"] = copy.deepcopy(action.metadata["renderer_output"])

            # Prompt text (if present) - string, no need to copy
            if "prompt_text" in action.metadata:
                payload["prompt_text"] = action.metadata["prompt_text"]

        # Override with explicitly provided prompt_blocks - DEEP COPY
        if prompt_blocks:
            payload["prompt_blocks"] = copy.deepcopy(
                [block.to_dict() if hasattr(block, "to_dict") else block for block in prompt_blocks]
            )

        # Inject phase_index/turn_index for observers (TL6 / SPEC-OBSERVABILITY §3.4)
        phase_index = turn_context.turn_index
        payload["phase_index"] = phase_index
        payload["turn_index"] = phase_index

        # Update Console's phase tracking so MATCH_END/other events get correct context
        if hasattr(self._console, "_current_phase_index"):
            self._console._current_phase_index = phase_index

        # Temporarily update EventBus context so Event.context carries phase indices
        self._console.event_bus.update_context(
            phase_index=phase_index,
            turn_index=phase_index,
        )
        try:
            # Emit via runtime event bus (not directly to recorder)
            self.emit_event(EventType.GAMEPLAY, **payload)

            # TL6: Also append to events_list for replay parity
            # ReplayEngine replays from match_result.events, so we must populate it
            if self._events_list is not None:
                from .types import Event, EventContext

                snapshot_payload = copy.deepcopy(payload)
                context: EventContext = {
                    **self._console.event_bus._base_context,
                    "phase_index": phase_index,
                    "turn_index": phase_index,
                    "timestamp": time.time(),
                    "monotonic_time": time.monotonic(),
                }
                event_snapshot = Event(
                    type=EventType.GAMEPLAY.value,
                    data=snapshot_payload,
                    context=context,
                    timestamp=context["timestamp"],
                    duration=0.1,
                )
                self._events_list.append(event_snapshot)
        finally:
            self._console.event_bus.clear_context("phase_index", "turn_index")

    def handle_parse_failure(
        self,
        player: Player,
        error: ActionParseError,
        *,
        turn_context: TurnContext,
    ) -> ParseFailurePolicy:
        """
        Invoke shared parse-failure policy pipeline.

        Calls console's parse-failure helper which:
        1. Emits PLAYER_ACTION_PARSE_FAILED event
        2. Records failure in recorder
        3. Logs warning
        4. Invokes game.on_action_parse_failure() to get policy
        5. Returns policy outcome

        Args:
            player: Failing player instance
            error: ActionParseError with embedded ParseResult
            turn_context: Immutable turn metadata snapshot

        Returns:
            ParseFailurePolicy enum (ABORT_MATCH, SKIP_TURN, FORFEIT, RETRY_ONCE)

        Invariants:
            - MR4: Parse Failure Integrity - MUST emit event, log, record, return policy
            - Mechanics MUST NOT call console helpers directly

        Example:
            >>> try:
            ...     action = player.decide(...)
            ... except ActionParseError as e:
            ...     policy = runtime.handle_parse_failure(player, e, turn_context=ctx)
            ...     if policy == ParseFailurePolicy.ABORT_MATCH:
            ...         raise MatchTerminationError(...)
            ...     elif policy == ParseFailurePolicy.SKIP_TURN:
            ...         continue  # Skip to next turn
        """
        return self._console._handle_parse_failure(
            player=player,
            error=error,
            turn_context=turn_context,
        )

    def fork_rng(self, label: str) -> RandomGenerator:
        """
        Return deterministic RNG fork tagged by label for debugging.

        Mechanics MUST call fork_rng whenever randomness is required (setup, per-turn,
        tie-breakers). Ensures reproducibility across sequential and parallel runs.

        Args:
            label: Debug label for tracing randomness sources (e.g., "setup", "turn_5")

        Returns:
            RandomGenerator fork (child of match RNG)

        Invariants:
            - MR5: RNG Traceability - fork label recorded in debug logs
            - Ensures reproducibility per SPEC-PARALLEL

        Example:
            >>> setup_rng = runtime.fork_rng("setup")
            >>> state = game.setup(players, rng=setup_rng)
            >>> for turn in range(1, max_turns + 1):
            ...     turn_rng = runtime.fork_rng(f"turn_{turn}")
            ...     state = game.update(state, player, action, rng=turn_rng)
        """
        # Log fork for traceability (MR5)
        if self._logger:
            self._logger.debug(
                f"RNG fork: {label} (match_id={self._match_id}, base_seed={self._seed})"
            )

        # Fork the RNG
        return self._rng.fork(label)

    def validate_state(self, state: Dict[str, Any]) -> None:
        """
        Call game.validate_state if implemented; raise ValueError on failure.

        Mechanics SHOULD call after setup and each update. Runtime may enforce
        periodic validation (configurable via console).

        Args:
            state: Current game state to validate

        Raises:
            ValueError: If game.validate_state() raises or validation fails

        Example:
            >>> state = game.setup(players)
            >>> runtime.validate_state(state)  # Validate initial state
            >>> state = game.update(state, player, action, rng=turn_rng)
            >>> runtime.validate_state(state)  # Validate after update
        """
        try:
            self._game.validate_state(state)
        except Exception as e:
            # Log validation failure with context
            self._logger.error(
                f"State validation failed (match_id={self._match_id}, game={self._game.__class__.__name__}): {e}",
                error=e,
            )
            raise

    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        **extra: Any,
    ) -> None:
        """
        Write structured log entry and emit LOG event.

        Mechanics MAY attach player, turn_number, or custom fields (e.g., phase, outcome).

        Args:
            message: Log message
            level: Log level (INFO or DEBUG)
            **extra: Additional context fields

        Example:
            >>> runtime.log("Turn started", level=LogLevel.DEBUG, player="Alice", turn=1)
            >>> runtime.log("Match truncated", level=LogLevel.INFO, max_turns=100)
        """
        # Add match context to extra
        log_extra = {
            "match_id": self._match_id,
            "session_id": self._session_id,
            "batch_id": self._batch_id,
            **extra,
        }

        # Format extra fields into message (AgentDeckLogger doesn't support extra kwarg)
        if extra:
            extra_str = ", ".join(f"{k}={v}" for k, v in extra.items())
            log_message = f"{message} ({extra_str})"
        else:
            log_message = message

        # Write to logger based on level (LogLevel only has INFO and DEBUG)
        if self._logger:
            if level == LogLevel.DEBUG:
                self._logger.debug(log_message)
            else:
                # Default to info for any other level
                self._logger.info(log_message)

        # Emit LOG event for spectators
        # Note: session_id/batch_id/match_id go in EventContext, not payload
        # Only include the extra fields from caller, not match context
        self.emit_event(
            EventType.LOG,
            message=message,
            level=level.value if hasattr(level, "value") else str(level),
            log_context=extra,  # Pass extra fields as log_context
        )

    def checkpoint(self, state: Dict[str, Any]) -> None:
        """
        Hook for future checkpoint/resume functionality.

        Currently a no-op. Mechanics MAY call without worrying about implementation.
        Console can override to persist state snapshots for long-running experiments.

        Args:
            state: Current game state to checkpoint

        Note:
            Runtime automatically forwards to console helper when implemented.
        """
        # Future: self._console._checkpoint(state, self._match_context)
