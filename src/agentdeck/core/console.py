"""Console orchestrator for AgentDeck v1.0.0."""

from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import Game, Player, Spectator
from .conversation import ConversationManager
from .event_factory import EventFactory
from .event_bus import EventBus
from .game_event_emitter import GameEventEmitter
from .logging import AgentDeckLogger
from .match_runtime import MatchRuntime
from .recorder import Recorder
from .session import AgentDeckConfig, SessionContext
from .types import (
    ActionResult,
    Event,
    EventType,
    GameStatus,
    HandshakeContext,
    MatchArtifact,
)
from .types import MatchContext as PlayerMatchContext
from .types import (
    MatchResult,
    RandomGenerator,
    TurnContext,
)

__all__ = ["Console", "SessionState", "HandshakeRejectedError"]


class HandshakeRejectedError(RuntimeError):
    """Raised when a player rejects the handshake phase."""


class ParallelExecutionError(RuntimeError):
    """
    Raised when parallel execution cannot proceed due to cloning failures.

    Per SPEC-PARALLEL v1.0.0 §8, this occurs when deepcopy fails for game
    or player objects (e.g., non-serializable state like database handles,
    sockets, thread locks).

    Solutions:
    1. Set concurrency=1 to disable parallel execution
    2. Ensure objects avoid non-serializable state
    3. (Future) Implement custom cloning support when available
    """


@dataclass
class SessionState:
    """Resolved session metadata for console lifecycle management."""

    config: AgentDeckConfig
    session_id: str
    seed: int
    started_at: float
    log_directory: str
    record_directory: str
    log_file_levels: List[Any] = field(default_factory=list)
    finished_at: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return self.finished_at - self.started_at


@dataclass
class BatchContext:
    """Runtime metadata tracked for a single batch run."""

    batch_id: str
    seed: Optional[int]
    started_at: float
    match_results: List[MatchResult] = field(default_factory=list)


@dataclass
class MatchExecutionContext:
    """
    Execution metadata for a single match (lightweight tracking).

    Note: This is NOT the same as MatchRuntime (infrastructure context).
    MatchRuntime provides infrastructure API (emit_event, record_turn, etc.).
    MatchExecutionContext just tracks metadata during match execution.
    """

    match_id: str
    seed: Optional[int]
    rng: RandomGenerator
    started_at: float
    events: List[Event] = field(default_factory=list)
    handshake_completed: bool = False
    truncated_by_max_turns: bool = False


def _entropy_seed() -> int:
    """Generate a random seed from system entropy."""
    return RandomGenerator().fork(time.time()).seed or int(
        time.time() * 1000
    )  # pragma: no cover - fallback


class _MatchWorker:
    """
    Internal worker for isolated match execution (SPEC-PARALLEL v1.0.0 §5).

    Deep-copies game and players, executes match with isolated event bus,
    and returns MatchArtifact containing result + captured events for replay.

    Thread-safe: Does NOT mutate parent Console state. Uses extracted helpers
    and own local state for match execution.

    Used by both sequential and parallel execution paths to ensure consistent
    isolation semantics.
    """

    def __init__(
        self,
        game: Game,
        players: List[Player],
        console: "Console",
        match_index: int,
        seed: Optional[int],
        batch_ctx: BatchContext,
        previous_match_result: Optional[MatchResult] = None,
        emit_worker_events: bool = False,
    ):
        """
        Initialize worker with deep-copied game and players.

        Args:
            game: Game instance to clone
            players: Player instances to clone
            console: Parent Console instance (for config + helper access only)
            match_index: Match index within batch (for MatchArtifact)
            seed: Seed for this match (derived by scheduler)
            batch_ctx: Batch context metadata
            previous_match_result: Previous match result (for player ordering hook)
            emit_worker_events: If True, emit CONSOLE_WORKER_START/COMPLETE events
                              (only set by _run_parallel, not _run_sequential)

        Raises:
            ParallelExecutionError: If deep-copy fails for game or players
        """
        self.match_index = match_index
        self.seed = seed
        self.batch_ctx = batch_ctx
        self.previous_match_result = previous_match_result
        self.console = console
        self.emit_worker_events = emit_worker_events

        # Deep-copy game and players for isolation
        try:
            self.game = copy.deepcopy(game)
        except Exception as exc:
            raise ParallelExecutionError(
                f"Failed to clone {game.__class__.__name__} for parallel execution.\n\n"
                f"Error: {exc}\n\n"
                f"Solutions:\n"
                f"  1. Set concurrency=1 to disable parallel execution.\n"
                f"  2. Ensure {game.__class__.__name__} avoids non-serializable state "
                f"(database handles, sockets, thread locks).\n"
                f"  3. (Future) Implement custom cloning support when available."
            ) from exc

        self.players: List[Player] = []
        for player in players:
            try:
                cloned_player = player.clone()
            except Exception as exc:
                player_name = getattr(player, "__class__", type(player)).__name__
                raise ParallelExecutionError(
                    f"Failed to clone {player_name} for parallel execution.\n\n"
                    f"Error: {exc}\n\n"
                    f"Solutions:\n"
                    f"  1. Set concurrency=1 to disable parallel execution.\n"
                    f"  2. Ensure {player_name} avoids non-serializable state "
                    f"(database handles, sockets, thread locks).\n"
                    f"  3. Override Player.clone() to construct a fresh instance with "
                    f"serializable configuration."
                ) from exc

            # Ensure runtime bindings are cleared even if subclass forgot
            if hasattr(cloned_player, "conversation_manager"):
                cloned_player.conversation_manager = None
            if hasattr(cloned_player, "logger"):
                cloned_player.logger = None

            self.players.append(cloned_player)

        # Create isolated EventBus scoped to this worker execution
        self.event_bus = EventBus(session_id=console.session_state.session_id)

        # Capture replay-ready events (with original Player/Game objects + context for spectators)
        self.replay_events: List[tuple[EventType, Dict[str, Any], Dict[str, Any]]] = []

        # MatchRuntime-facing attributes (mirrors Console surface expected by TurnLoop)
        self.logger = console.logger
        self.first_player_info: Optional[Dict[str, Any]] = None
        self._retry_budget: Dict[str, bool] = {}
        self._current_phase_index: Optional[int] = None

    def run(self) -> MatchArtifact:
        """
        Execute match with isolated state and return artifact.

        Returns:
            MatchArtifact: Contains match_index, result, and captured events

        Thread-safe: Fully isolated execution. Does NOT access Console instance
        state. Uses only Console's stateless helper methods.

        Note: CONSOLE_WORKER_START event is emitted only in parallel mode
        (when emit_worker_events=True). Sequential fallback does NOT emit
        worker events per SPEC-MONITOR §6.2 EM5.
        """
        # Emit CONSOLE_WORKER_START if in parallel mode (SPEC-MONITOR §6.2 EM5)
        if self.emit_worker_events:
            self.console._emit_console_event(
                EventType.CONSOLE_WORKER_START,
                {
                    "worker_id": self.match_index,
                    "match_index": self.match_index,
                    "seed": self.seed,
                    "started_at": time.time(),
                },
            )

        # Create isolated match runtime
        runtime = self._create_match_runtime()

        # Determine player order using Console's extracted helper
        ordered_players, player_order, player_order_source, first_player, cost_baseline = (
            self.console._determine_player_order_and_baseline(
                self.game, self.players, runtime, self.previous_match_result
            )
        )

        player_names = [player.name for player in ordered_players]

        # Update isolated event bus context
        self.event_bus.update_context(
            match_id=runtime.match_id, batch_id=self.batch_ctx.batch_id, phase_index=None
        )

        # Prepare players, run setup + handshake, emit MATCH_START
        self._prepare_players(ordered_players)

        infra_runtime = self._create_infrastructure_runtime(runtime)

        temp_emitter = GameEventEmitter(self.event_bus, runtime.match_id)
        temp_factory = EventFactory(runtime.match_id)
        self.game.bind_event_factory(temp_factory)
        self.game.bind_event_emitter(temp_emitter)
        try:
            # Pre-compute initial state (per SPEC-GAME v0.7.0 data flow)
            setup_rng = infra_runtime.fork_rng("setup")
            state = self.game.setup(player_names, seed=setup_rng.seed)
            if not isinstance(state, dict):
                raise TypeError(
                    f"{self.game.__class__.__name__}.setup() must return a dict, got {type(state).__name__}"
                )
            state.setdefault("_turn_count", 1)
            infra_runtime.validate_state(state)

            state = self._run_handshake(ordered_players, runtime, infra_runtime, state)
            infra_runtime.initial_state = state
            infra_runtime.validate_state(state)
        finally:
            self.game.bind_event_factory(None)
            self.game.bind_event_emitter(None)
            temp_emitter.clear_phase_index()

        self._dispatch_event(
            EventType.MATCH_START,
            events=runtime.events,
            game=self.game,
            players=ordered_players,
            match_id=runtime.match_id,
            seed=runtime.seed,
            player_names=player_names,
            player_order=player_order,
            player_order_source=player_order_source,
            first_player=first_player,
        )

        from .types import MatchAbortedError, MatchForfeitedError

        try:
            from .mechanics.turn_based import TurnResult

            result = self.game.run(infra_runtime, ordered_players)
            if isinstance(result, TurnResult):
                final_state = result.final_state
                truncated = result.truncated_by_max_turns
            else:
                final_state, _, truncated = result

            turn_count = final_state.get("_turn_count", 0)
            runtime.truncated_by_max_turns = truncated

            # Compute status and duration (normal completion)
            status = self._safe_status(final_state)
            match_duration = time.time() - runtime.started_at

            metadata = self.console._build_match_metadata(
                self.game,
                player_names,
                player_order,
                player_order_source,
                first_player,
                match_duration,
                runtime,
                truncated,
                turn_count,
                {},
                0.0,
                self.batch_ctx,
            )

            match_result = MatchResult(
                winner=status.winner,
                final_state=copy.deepcopy(final_state),
                events=list(runtime.events),
                seed=runtime.seed,
                metadata=metadata,
            )

            # Run conclusion and emit MATCH_END (normal completion)
            self._run_conclusion(ordered_players, match_result, runtime)

            # Recompute per-player API cost deltas after conclusions to include reflection spend
            final_player_costs, final_total_match_cost = self.console._compute_cost_deltas(
                ordered_players, cost_baseline
            )
            match_result.metadata["player_costs"] = final_player_costs
            match_result.metadata["cost"] = final_total_match_cost

            self._dispatch_event(
                EventType.MATCH_END,
                events=runtime.events,
                result=match_result,
            )

        except MatchAbortedError as abort_error:
            # PF4: Match aborted due to parse failure - emit MATCH_END with aborted metadata
            match_duration = time.time() - runtime.started_at

            # Use actual state at point of abort (attached by mechanic via exception)
            abort_state = getattr(abort_error, "abort_state", {})

            # Get turn number safely (Codex fix #2: tolerate None turn_context)
            abort_turn = abort_error.turn_context.turn_number if abort_error.turn_context else 0

            # Build metadata with abort information
            metadata = self.console._build_match_metadata(
                self.game,
                player_names,
                player_order,
                player_order_source,
                first_player,
                match_duration,
                runtime,
                False,
                abort_turn,
                {},
                0.0,
                self.batch_ctx,
            )

            # Add abort-specific metadata (PF4)
            metadata["outcome"] = "aborted"
            metadata["abort_reason"] = "parse_failure"
            metadata["failing_player"] = abort_error.player_name
            metadata["policy"] = abort_error.policy.value
            metadata["abort_turn"] = abort_turn

            # Serialize turn context for reconstruction (Codex fix #2)
            if abort_error.turn_context is not None:
                metadata["abort_turn_context"] = {
                    "match_id": abort_error.turn_context.match_id,
                    "turn_number": abort_error.turn_context.turn_number,
                    "turn_index": abort_error.turn_context.turn_index,
                    "player": abort_error.turn_context.player,
                    "started_at": abort_error.turn_context.started_at,
                    "duration": abort_error.turn_context.duration,
                    "rng_seed": abort_error.turn_context.rng_seed,
                    "rng_label": abort_error.turn_context.rng_label,
                }

            # Serialize parse error details
            metadata["parse_error"] = {
                "success": abort_error.parse_error.parse_result.success,
                "error": abort_error.parse_error.parse_result.error,
                "raw_response": abort_error.parse_error.parse_result.raw_response,
                "reasoning": abort_error.parse_error.parse_result.reasoning,
                "metadata": copy.deepcopy(abort_error.parse_error.parse_result.metadata),
                "candidates": abort_error.parse_error.parse_result.metadata.get("candidates", []),
            }

            # Compute per-player API costs up to point of abort
            final_player_costs, final_total_match_cost = self.console._compute_cost_deltas(
                ordered_players, cost_baseline
            )
            metadata["player_costs"] = final_player_costs
            metadata["cost"] = final_total_match_cost

            # Create MatchResult with aborted metadata (PF4)
            match_result = MatchResult(
                winner=None,  # No winner for aborted matches
                final_state=copy.deepcopy(abort_state),
                events=list(runtime.events),
                seed=runtime.seed,
                metadata=metadata,
            )

            # Emit MATCH_END event with aborted result (PF4 requirement)
            self._dispatch_event(
                EventType.MATCH_END,
                events=runtime.events,
                result=match_result,
            )

            # Clear context
            self.event_bus.clear_context("match_id", "phase_index")

            # Return artifact with aborted match result (PF4: must record partial match)
            # Caller will check metadata["outcome"]=="aborted" and re-raise MatchAbortedError
            return MatchArtifact(
                match_index=self.match_index,
                result=match_result,
                events=list(runtime.events),  # Sanitized for recording
                replay_events=list(self.replay_events),  # Original objects for spectator replay
            )

        except MatchForfeitedError as forfeit_error:
            # FORFEIT policy: Match ends with winner determined
            match_duration = time.time() - runtime.started_at

            # Use actual state at point of forfeit (attached by mechanic via exception)
            forfeit_state = getattr(forfeit_error, "forfeit_state", {})

            # Get turn number safely (tolerate None turn_context)
            forfeit_turn = (
                forfeit_error.turn_context.turn_number if forfeit_error.turn_context else 0
            )

            # Build metadata with forfeit information
            metadata = self.console._build_match_metadata(
                self.game,
                player_names,
                player_order,
                player_order_source,
                first_player,
                match_duration,
                runtime,
                False,
                forfeit_turn,
                {},
                0.0,
                self.batch_ctx,
            )

            # Add forfeit-specific metadata
            metadata["outcome"] = "forfeit"
            metadata["forfeit_reason"] = "parse_failure"
            metadata["forfeiting_player"] = forfeit_error.player_name
            metadata["policy"] = forfeit_error.policy.value

            # Serialize turn context for reconstruction
            if forfeit_error.turn_context is not None:
                metadata["forfeit_turn"] = forfeit_error.turn_context.turn_number
                metadata["forfeit_turn_context"] = {
                    "match_id": forfeit_error.turn_context.match_id,
                    "turn_number": forfeit_error.turn_context.turn_number,
                    "turn_index": forfeit_error.turn_context.turn_index,
                    "player": forfeit_error.turn_context.player,
                    "started_at": forfeit_error.turn_context.started_at,
                    "duration": forfeit_error.turn_context.duration,
                    "rng_seed": forfeit_error.turn_context.rng_seed,
                    "rng_label": forfeit_error.turn_context.rng_label,
                }
            else:
                metadata["forfeit_turn"] = None

            # Serialize parse error details (Codex fix #2: include reasoning + full metadata)
            metadata["parse_error"] = {
                "success": forfeit_error.parse_error.parse_result.success,
                "error": forfeit_error.parse_error.parse_result.error,
                "raw_response": forfeit_error.parse_error.parse_result.raw_response,
                "reasoning": forfeit_error.parse_error.parse_result.reasoning,
                "metadata": copy.deepcopy(forfeit_error.parse_error.parse_result.metadata),
                "candidates": forfeit_error.parse_error.parse_result.metadata.get("candidates", []),
            }

            # Compute per-player API costs up to point of forfeit
            final_player_costs, final_total_match_cost = self.console._compute_cost_deltas(
                ordered_players, cost_baseline
            )
            metadata["player_costs"] = final_player_costs
            metadata["cost"] = final_total_match_cost

            # Create MatchResult with forfeit metadata and winner
            match_result = MatchResult(
                winner=forfeit_error.winner,  # Opponent wins
                final_state=copy.deepcopy(forfeit_state),
                events=list(runtime.events),
                seed=runtime.seed,
                metadata=metadata,
            )

            # Emit MATCH_END event with forfeit result
            self._dispatch_event(
                EventType.MATCH_END,
                events=runtime.events,
                result=match_result,
            )

            # Clear context
            self.event_bus.clear_context("match_id", "phase_index")

            # Return artifact with forfeited match result
            return MatchArtifact(
                match_index=self.match_index,
                result=match_result,
                events=list(runtime.events),
                replay_events=list(self.replay_events),
            )

        # Clear context
        self.event_bus.clear_context("match_id", "phase_index")

        # Return artifact with both sanitized snapshots and replay-ready events
        return MatchArtifact(
            match_index=self.match_index,
            result=match_result,
            events=list(runtime.events),  # Sanitized for recording
            replay_events=list(self.replay_events),  # Original objects for spectator replay
        )

    def _create_match_runtime(self) -> MatchExecutionContext:
        """Create match runtime (isolated, does not touch Console state)."""
        # Use canonical match ID format: match_{hex8}
        match_id = f"match_{uuid.uuid4().hex[:8]}"

        if self.seed is not None:
            rng = RandomGenerator(self.seed)
        else:
            rng = RandomGenerator(_entropy_seed())

        return MatchExecutionContext(
            match_id=match_id,
            seed=rng.seed,
            rng=rng,
            started_at=time.time(),
        )

    def _create_infrastructure_runtime(self, exec_ctx: MatchExecutionContext) -> MatchRuntime:
        """
        Create MatchRuntime infrastructure context bound to this worker.

        Mirrors Console._create_infrastructure_runtime but routes through the worker's
        isolated event bus so gameplay events remain sandboxed until replay.
        """
        return MatchRuntime(
            console=self,
            game=self.game,
            match_id=exec_ctx.match_id,
            session_id=self.console.session_state.session_id,
            batch_id=self.batch_ctx.batch_id,
            seed=exec_ctx.seed or 0,
            max_turns=self.console.max_turns,
            recorder=self.console.recorder,
            logger=self.logger,
            rng=exec_ctx.rng,
            previous_match_result=self.previous_match_result,
            events_list=exec_ctx.events,  # TL6: for replay parity
        )

    def _prepare_players(self, players: List[Player]) -> None:
        """Prepare players (isolated, mirrors Console._prepare_players fully)."""
        for player in players:
            # Reset conversation history
            if hasattr(player, "reset_conversation"):
                player.reset_conversation()

            # Bind fresh ConversationManager with isolated event bus
            conversation = ConversationManager(player_name=player.name, event_bus=self.event_bus)
            if hasattr(player, "bind_conversation_manager"):
                player.bind_conversation_manager(conversation)

            # Inject logger (use parent console's logger)
            if hasattr(player, "logger"):
                player.logger = self.console.logger

    def _run_handshake(
        self,
        players: List[Player],
        runtime: MatchExecutionContext,
        infra_runtime: MatchRuntime,
        game_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run handshake phase (isolated implementation)."""
        state = copy.deepcopy(game_state)
        player_names = [p.name for p in players]
        for player in players:
            context = HandshakeContext(
                match_id=runtime.match_id,
                player_name=player.name,
                opponent_names=[name for name in player_names if name != player.name],
                game_name=self.game.__class__.__name__,
                seed=runtime.seed,
                handshake_template_id="default",
                metadata={
                    "game_instructions": getattr(self.game, "instructions", ""),
                    "allowed_actions": getattr(self.game, "allowed_actions", []),
                },
            )
            self._dispatch_event(
                EventType.PLAYER_HANDSHAKE_START,
                events=runtime.events,
                player=player.name,
                match_id=runtime.match_id,
            )

            # Bind controller to game before handshake (GB1)
            # This allows controller to provide game-specific format instructions with allowed_actions
            if hasattr(player, "controller") and hasattr(player.controller, "bind_game"):
                player.controller.bind_game(self.game)

            raw = player.handshake(context)

            # Capture handshake prompt from conversation history (if available)
            prompt_text: Optional[str] = None
            conversation_manager = getattr(player, "conversation_manager", None)
            if conversation_manager is not None:
                history = conversation_manager.history()
                if len(history) >= 2:
                    prompt_text = history[-2]["content"]

            result = player.controller.validate_handshake(raw, context=context)
            result.metadata = result.metadata or {}
            if result.normalized_response is None:
                result.normalized_response = result.raw_response
            if result.normalized_response is None:
                result.normalized_response = result.raw_response
            result.metadata = result.metadata or {}
            if not result.accepted:
                self._dispatch_event(
                    EventType.PLAYER_HANDSHAKE_ABORT,
                    events=runtime.events,
                    player=player.name,
                    reason=result.reason,
                    prompt_text=prompt_text,
                )
                raise HandshakeRejectedError(
                    f"Player {player.name} rejected handshake: {result.reason}"
                )

            try:
                state = self.game.on_handshake_complete(state, player.name, result) or state
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError(
                    f"{self.game.__class__.__name__}.on_handshake_complete() failed for player {player.name}"
                ) from exc

            runtime.handshake_completed = True
            infra_runtime.initial_state = state
            self._dispatch_event(
                EventType.PLAYER_HANDSHAKE_COMPLETE,
                events=runtime.events,
                player=player.name,
                response=result.normalized_response,
                metadata=result.metadata,
                prompt_text=prompt_text,
            )

        return state

    def get_player_action(
        self,
        player_view: Dict[str, Any],
        player: Player,
        game: Game,
        *,
        turn_context: TurnContext,
        extras: Optional[Dict[str, Any]] = None,
    ) -> ActionResult:
        """
        Worker-scoped version of Console.get_player_action().

        TurnLoop obtains this via runtime._console to keep legacy behaviour while the
        worker isolates side effects from the parent console/event bus.
        """
        from .types import ActionParseError, MatchAbortedError, ParseFailurePolicy

        try:
            action_result = player.decide(player_view, turn_context=turn_context, extras=extras)
        except ActionParseError as parse_error:
            # Handle parse failure via game policy (PF1-PF3)
            policy = self._handle_parse_failure(player, parse_error, turn_context)

            if policy == ParseFailurePolicy.ABORT_MATCH:
                # PF4: Raise MatchAbortedError (caller emits MATCH_END before propagating)
                raise MatchAbortedError(
                    player_name=player.name,
                    parse_error=parse_error,
                    turn_context=turn_context,
                    policy=policy,
                )
            elif policy == ParseFailurePolicy.SKIP_TURN:
                # Return sentinel ActionResult preserving original ParseResult metadata
                # Codex fix: Must include parser_success=False to maintain contract
                sentinel_metadata = (
                    dict(parse_error.parse_result.metadata)
                    if parse_error.parse_result.metadata
                    else {}
                )
                sentinel_metadata.update(
                    {
                        "parser_success": False,  # Truthful parse status
                        "_skip_turn": True,
                        "parse_error": parse_error.parse_result.error,
                        "policy": "skip_turn",
                    }
                )
                return ActionResult(
                    action="__SKIP_TURN__",
                    raw_response=parse_error.parse_result.raw_response,
                    reasoning=parse_error.parse_result.reasoning,
                    metadata=sentinel_metadata,
                )
            elif policy == ParseFailurePolicy.FORFEIT:
                # Failing player forfeits - opponent wins
                # For 2-player games, winner is the other player
                # For multiplayer (>2), use first opponent (game-specific logic may vary)
                from .types import MatchForfeitedError

                # Get all player names from worker's player list
                all_players = [p.name for p in self.players]
                opponents = [name for name in all_players if name != player.name]
                winner = opponents[0] if opponents else None

                if not winner:
                    raise RuntimeError(
                        f"FORFEIT policy requires at least 2 players, found only {player.name}"
                    )

                raise MatchForfeitedError(
                    player_name=player.name,
                    parse_error=parse_error,
                    turn_context=turn_context,
                    policy=policy,
                    winner=winner,
                )
            elif policy == ParseFailurePolicy.RETRY_ONCE:
                # Track retry budget: only retry once per player per turn
                # Use turn context to check if we've already retried
                retry_key = f"{turn_context.match_id}_{turn_context.turn_number}_{player.name}"

                # Check if we have a retry budget tracker (create if needed)
                if retry_key in self._retry_budget:
                    # Already retried once - fall back to ABORT_MATCH
                    raise MatchAbortedError(
                        player_name=player.name,
                        parse_error=parse_error,
                        turn_context=turn_context,
                        policy=ParseFailurePolicy.ABORT_MATCH,
                    )

                # Mark this turn as retried
                self._retry_budget[retry_key] = True

                # Retry: call player.decide() again with same inputs
                try:
                    action_result = player.decide(
                        player_view, turn_context=turn_context, extras=None
                    )
                    # Retry succeeded - clear retry budget and return result
                    del self._retry_budget[retry_key]
                    return action_result
                except ActionParseError as retry_error:
                    # Retry failed - clear budget and fall back to ABORT_MATCH
                    del self._retry_budget[retry_key]

                    # PF1/PF2 compliance: Emit parse failure event for retry failure
                    # Even though we're forcing ABORT_MATCH, we must record the second parse failure
                    retry_policy = self._handle_parse_failure(player, retry_error, turn_context)
                    # Policy should be ABORT_MATCH (we force it), but respect hook decision
                    if retry_policy != ParseFailurePolicy.ABORT_MATCH:
                        # Game hook tried to override - log warning and force ABORT
                        # (retry budget exhausted, no other option)
                        pass  # TODO: Consider logging this edge case

                    raise MatchAbortedError(
                        player_name=player.name,
                        parse_error=retry_error,
                        turn_context=turn_context,
                        policy=ParseFailurePolicy.ABORT_MATCH,
                    )
            else:
                raise RuntimeError(f"Unknown ParseFailurePolicy: {policy}")
        except Exception as exc:
            raise RuntimeError(
                f"Player {player.name} failed during decide() in match {turn_context.match_id} "
                f"turn {turn_context.turn_number}"
            ) from exc

        if not isinstance(action_result, ActionResult):
            raise TypeError(
                f"Player {player.name}.decide() must return ActionResult, "
                f"got {type(action_result).__name__}"
            )
        if not action_result.action or not str(action_result.action).strip():
            raise ValueError(
                f"Player {player.name}.decide() returned empty action. "
                f"Action must be non-empty string."
            )
        return action_result

    def _handle_parse_failure(
        self,
        player: Player,
        error: "ActionParseError",
        turn_context: TurnContext,
    ) -> "ParseFailurePolicy":
        """
        Delegate parse-failure handling to the parent console while preserving isolation.
        """
        from .types import ActionParseError

        if not isinstance(error, ActionParseError):  # Defensive - should never happen
            raise TypeError(f"Expected ActionParseError, got {type(error).__name__}")

        return self.console._handle_parse_failure(player, error, turn_context, self.game)

    def emit_turn(
        self,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        player: str,
        action: ActionResult,
        *,
        turn_context: Any,
        events: Optional[List[Event]] = None,
    ) -> None:
        """Worker-scoped gameplay emission that mirrors Console.emit_turn()."""
        if isinstance(turn_context, dict):
            ctx_dict = dict(turn_context)
            turn_index = ctx_dict.get("turn_index", 0)
            match_id = ctx_dict.get("match_id", state_before.get("match_id"))
        else:
            ctx_dict = turn_context.to_dict()
            turn_index = turn_context.turn_index
            match_id = turn_context.match_id

        # Update event bus context for turn_index (E3)
        self.event_bus.update_context(phase_index=turn_index, turn_index=turn_index)

        # Build payload matching Console.emit_turn format
        payload = {
            "mechanic": "turn_based",  # SPEC-OBSERVABILITY §3.2: mechanic field required
            "match_id": match_id,
            "player": player,
            "turn_context": ctx_dict,
            "state_before": copy.deepcopy(state_before),
            "state_after": copy.deepcopy(state_after),
            "action": {
                "action": action.action,
                "reasoning": action.reasoning,
                "metadata": copy.deepcopy(action.metadata) if action.metadata else {},
                "raw_response": action.raw_response,
            },
        }

        self._dispatch_event(EventType.GAMEPLAY, events=events, **payload)

        # Clear turn_index from context after emission
        self.event_bus.clear_context("phase_index", "turn_index")

    def _safe_status(self, state: Any) -> GameStatus:
        """Get game status (isolated)."""
        try:
            return self.game.status(state)
        except Exception as exc:
            raise RuntimeError(f"{self.game.__class__.__name__}.status() failed") from exc

    def _run_conclusion(
        self, players: List[Player], result: MatchResult, runtime: MatchExecutionContext
    ) -> None:
        """Run conclusion phase (isolated implementation)."""
        match_ctx = PlayerMatchContext(
            match_id=runtime.match_id,
            players=[player.name for player in players],
            game_name=result.metadata.get("game", ""),
            seed=runtime.seed,
            handshake_completed=runtime.handshake_completed,
            rng_info={"seed": runtime.seed},
        )
        concluding_player = None
        conclusion_reflection: Optional[str] = None

        try:
            concluding_player = self.game.requires_conclusion(result.final_state)
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"{self.game.__class__.__name__}.requires_conclusion() failed"
            ) from exc

        if concluding_player:
            target = next((p for p in players if p.name == concluding_player), None)
            if target is None:
                raise ValueError(
                    f"{self.game.__class__.__name__}.requires_conclusion returned unknown player '{concluding_player}'"
                )

            prompt = self.game.get_conclusion_prompt(concluding_player, result.final_state)
            match_ctx.conclusion_prompt = prompt
            conclusion_reflection = target.conclude(result, match_context=match_ctx)
            parsed = self.game.parse_conclusion(concluding_player, conclusion_reflection)
            try:
                result.final_state = self.game.on_conclusion_received(
                    result.final_state, concluding_player, parsed
                )
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError(
                    f"{self.game.__class__.__name__}.on_conclusion_received() failed"
                ) from exc

        for player in players:
            if player.name == concluding_player:
                reflection = conclusion_reflection
            else:
                match_ctx.conclusion_prompt = None
                reflection = player.conclude(result, match_context=match_ctx)

            self._dispatch_event(
                EventType.PLAYER_CONCLUSION,
                events=runtime.events,
                player=player.name,
                reflection=reflection,
            )

    def _dispatch_event(
        self, event_type: EventType, events: Optional[List[Event]], **payload
    ) -> None:
        """
        Dispatch event to isolated event bus and capture snapshot.

        Mirrors Console._dispatch_event behavior:
        1. Emit to spectators via event_bus.emit()
        2. Capture Event snapshot for runtime.events list
        """
        # Selectively deepcopy payload, excluding objects that may contain unpicklable elements
        event_payload: Dict[str, Any] = {}
        for key, value in payload.items():
            # Don't deepcopy Player, Game, or Spectator objects
            if isinstance(value, (Player, Game, Spectator)):
                event_payload[key] = value
            # Don't deepcopy lists of Player/Game/Spectator objects
            elif (
                isinstance(value, list)
                and value
                and isinstance(value[0], (Player, Game, Spectator))
            ):
                event_payload[key] = value
            else:
                event_payload[key] = copy.deepcopy(value)

        # Emit to spectators on isolated bus
        self.event_bus.emit(event_type, **event_payload)

        # Capture replay-ready event (with original Player/Game objects + context for spectator replay)
        # Capture current event bus context (match_id, phase_index, etc.)
        event_context = dict(self.event_bus._base_context)
        self.replay_events.append((event_type, event_payload, event_context))

        # Capture snapshot for runtime.events list (with sanitized data for recording)
        if events is not None:
            snapshot = self._make_event_snapshot(event_type, payload)
            events.append(snapshot)

    def _make_event_snapshot(self, event_type: EventType, payload: Dict[str, Any]) -> Event:
        """
        Create Event snapshot for runtime.events list.

        Mirrors Console._make_event_snapshot, capturing current event bus context.
        """
        context: Dict[str, Any] = {
            **self.event_bus._base_context,
            "session_id": self.console.session_state.session_id,
            "timestamp": time.time(),
            "monotonic_time": time.monotonic(),
        }

        # Selectively deepcopy payload for snapshot, converting player/game objects to names
        snapshot_data: Dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, (Player, Game, Spectator)):
                snapshot_data[key] = getattr(value, "name", value.__class__.__name__)
            elif (
                isinstance(value, list)
                and value
                and isinstance(value[0], (Player, Game, Spectator))
            ):
                snapshot_data[key] = [
                    getattr(item, "name", item.__class__.__name__) for item in value
                ]
            else:
                snapshot_data[key] = copy.deepcopy(value)

        return Event(
            type=event_type.value if isinstance(event_type, EventType) else event_type,
            data=snapshot_data,
            context=context,
        )


class Console:
    """Execution engine coordinating session/batch/match lifecycles."""

    def __init__(
        self,
        *,
        config: Optional[AgentDeckConfig] = None,
        session: Optional[SessionContext] = None,
        seed: Optional[int] = None,
        recorder: Optional[Recorder] = None,
        spectators: Optional[List[Spectator]] = None,
        logger: Optional[AgentDeckLogger] = None,
        session_factory: Optional[
            Callable[[AgentDeckConfig, SessionContext, int], SessionState]
        ] = None,
    ) -> None:
        """
        Construct a new console instance.

        Args:
            config: Session configuration (defaults to AgentDeckConfig()).
            session: Legacy SessionContext. When provided it will be adapted to SessionState.
            seed: Optional seed override (takes precedence over config/session seeds).
            recorder: Recorder instance to capture match dialogue (optional).
            spectators: Spectators that observe every batch/match (optional).
            logger: Structured logger instance (optional).
            session_factory: Custom factory producing SessionState from config.
        """
        if session is not None:
            base_config = session.config
            session.ensure_directories()
        else:
            base_config = config or AgentDeckConfig()
            session = SessionContext.create(base_config)
            session.ensure_directories()

        resolved_seed = seed
        if resolved_seed is None:
            resolved_seed = session.seed if session.seed is not None else _entropy_seed()
        if base_config.seed is None:
            base_config.seed = resolved_seed

        factory = session_factory or self._default_session_factory
        self.session_state = factory(base_config, session, resolved_seed)

        self.logger = logger
        self.recorder = recorder
        self.max_turns = base_config.max_turns

        # Match EventBus (buffered, replayed in order)
        self.event_bus = EventBus(session_id=self.session_state.session_id)

        # Console EventBus (live, immediate) - SPEC-MONITOR v1.0.0 §6.1 ML1
        # Inject session logger for proper exception context (§6.3 EI4 / §8.1)
        self.console_bus = EventBus(session_id=self.session_state.session_id, logger=self.logger)

        # SPEC-CONSOLE §5: Auto-attach MatchNarrator when spectators=None
        if spectators is None:
            from agentdeck.spectators import MatchNarrator

            self._base_spectators: List[Spectator] = [MatchNarrator()]
        else:
            self._base_spectators: List[Spectator] = spectators
        self._temp_spectators: List[Spectator] = []
        self._session_started = False
        self._session_closed = False
        self._current_batch_id: Optional[str] = None
        self._current_match_id: Optional[str] = None
        self._current_phase_index: Optional[int] = None
        self._match_counter: int = 0
        self._rng = RandomGenerator(self.session_state.seed)
        self.game: Optional[Game] = None
        self.players: List[Player] = []

        # Subscribe recorder and base spectators to match EventBus
        if self.recorder is not None:
            self.event_bus.subscribe(self.recorder)
            self.recorder.bind_session(session)

        # LI1 & LI4: Inject logger into session spectators before subscription
        for spectator in self._base_spectators:
            if getattr(spectator, "logger", None) is None:
                spectator.logger = self.logger
            self.event_bus.subscribe(spectator)

        # Setup monitors for console EventBus - SPEC-MONITOR v1.0.0 §6.1 ML2-ML5
        self._setup_monitors(base_config)

        # Emit SESSION_START immediately
        self._emit_session_start()

    @property
    def spectators(self) -> List[Spectator]:
        """Return the session-scoped spectator set (copy)."""
        return list(self._base_spectators)

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def run(
        self,
        game: Game,
        players: List[Player],
        *,
        matches: int = 1,
        seed: Optional[int] = None,
        spectators: Optional[List[Spectator]] = None,
    ) -> List[MatchResult]:
        """Execute a batch of matches and return MatchResult instances."""
        if self._session_closed:
            raise RuntimeError("Console session already closed")
        if matches <= 0:
            raise ValueError("matches must be >= 1")

        batch_id = self._next_batch_id()
        base_seed = seed if seed is not None else self.session_state.seed
        batch_ctx = BatchContext(batch_id=batch_id, seed=base_seed, started_at=time.time())

        # LI1 & LI4: Attach temporary spectators for this run and inject logger
        temp_spectators = spectators or []
        for spectator in temp_spectators:
            if getattr(spectator, "logger", None) is None:
                spectator.logger = self.logger
            self.event_bus.subscribe(spectator)
            self._temp_spectators.append(spectator)

        self._current_batch_id = batch_id
        self.event_bus.update_context(batch_id=batch_id)
        self._dispatch_event(
            EventType.BATCH_START,
            events=None,
            batch_id=batch_id,
            game=game,  # Pass game object (Recorder expects this)
            players=players,  # Pass player objects (Recorder expects this, not names)
            matches=matches,  # Use 'matches' keyword per Recorder signature
        )

        # Track all match seeds for BATCH_END (T3/R3)
        seeds_used = []

        try:
            # Route based on concurrency setting (SPEC-PARALLEL v1.0.0 §6-8)
            # concurrency == 1: Use legacy direct path (byte-for-byte compatible)
            # concurrency > 1: Use parallel path UNLESS game uses previous_match_result

            if self.session_state.config.concurrency == 1:
                # Legacy path: Direct play_match calls (no deep-copy isolation)
                batch_start_time = time.time()
                match_durations = []

                # Emit CONSOLE_BATCH_START - SPEC-MONITOR v1.0.0 §6.2 EM3
                self._emit_console_event(
                    EventType.CONSOLE_BATCH_START,
                    {
                        "batch_id": batch_ctx.batch_id,
                        "total_matches": matches,
                        "concurrency": 1,
                        "mode": "sequential",
                        "base_seed": base_seed,
                    },
                )

                for index in range(matches):
                    match_seed = self._derive_match_seed(base_seed, index)

                    # Determine previous match result for stateful ordering (batch-local scope)
                    previous_match_result = (
                        batch_ctx.match_results[-1] if batch_ctx.match_results else None
                    )

                    result = self.play_match(
                        game,
                        players,
                        batch_ctx,
                        match_index=index,
                        seed=match_seed,
                        previous_match_result=previous_match_result,
                    )
                    batch_ctx.match_results.append(result)
                    # Capture actual runtime seed (may differ from match_seed when entropy-derived)
                    seeds_used.append(result.seed)

                    # Track metrics
                    duration = result.metadata.get("duration", 0)
                    match_durations.append(duration)

                    # Emit CONSOLE_BATCH_PROGRESS - SPEC-MONITOR v1.0.0 §6.2 EM6
                    completed = index + 1
                    elapsed = time.time() - batch_start_time
                    avg_duration = (
                        sum(match_durations) / len(match_durations) if match_durations else 0
                    )
                    remaining = matches - completed
                    eta = avg_duration * remaining if avg_duration > 0 and remaining > 0 else None

                    self._emit_console_event(
                        EventType.CONSOLE_BATCH_PROGRESS,
                        {
                            "batch_id": batch_ctx.batch_id,
                            "completed": completed,
                            "total": matches,
                            "in_progress": 0,
                            "failed": 0,
                            "elapsed_time": elapsed,
                            "estimated_remaining": eta,
                        },
                    )

                # Emit CONSOLE_BATCH_COMPLETE - SPEC-MONITOR v1.0.0 §6.2 EM4
                total_duration = time.time() - batch_start_time
                avg_match_duration = (
                    sum(match_durations) / len(match_durations) if match_durations else 0
                )

                self._emit_console_event(
                    EventType.CONSOLE_BATCH_COMPLETE,
                    {
                        "batch_id": batch_ctx.batch_id,
                        "completed": len(seeds_used),
                        "total": matches,
                        "failed": 0,
                        "duration": total_duration,
                        "avg_match_duration": avg_match_duration,
                        "seeds_used": seeds_used,
                    },
                )
            else:
                # Check if game OVERRIDES get_player_order (not just inherits default)
                # Base Game class defines get_player_order() returning None, so we check
                # if the game's class actually implements it (not inherited from base)
                game_overrides_player_order = "get_player_order" in type(game).__dict__

                if game_overrides_player_order:
                    # Fallback: Sequential execution with isolation
                    if self.logger:
                        self.logger.debug(
                            f"Falling back to sequential execution: game.get_player_order() "
                            f"may use previous_match_result (not supported in parallel mode)"
                        )
                    _, seeds_used = self._run_sequential(
                        game=game,
                        players=players,
                        batch_ctx=batch_ctx,
                        base_seed=base_seed,
                        matches=matches,
                    )
                else:
                    # Parallel execution: matches run concurrently
                    _, seeds_used = self._run_parallel(
                        game=game,
                        players=players,
                        batch_ctx=batch_ctx,
                        base_seed=base_seed,
                        matches=matches,
                    )
        except Exception as exc:
            # BATCH_END with T3-required metadata even on failure
            self._dispatch_event(
                EventType.BATCH_END,
                events=None,
                batch_id=batch_id,
                results=list(batch_ctx.match_results),
                matches_completed=len(batch_ctx.match_results),  # T3
                duration=time.time() - batch_ctx.started_at,  # T3
                seeds_used=seeds_used,  # T3: seed list for deterministic reconstruction
                error=str(exc),
            )
            raise
        else:
            # BATCH_END with complete T3 metadata
            self._dispatch_event(
                EventType.BATCH_END,
                events=None,
                batch_id=batch_id,
                results=list(batch_ctx.match_results),
                matches_completed=len(batch_ctx.match_results),  # T3
                duration=time.time() - batch_ctx.started_at,  # T3
                seeds_used=seeds_used,  # T3: seed list for deterministic reconstruction
            )
        finally:
            self.event_bus.clear_context("batch_id")
            self._current_batch_id = None
            for spectator in self._temp_spectators:
                self.event_bus.unsubscribe(spectator)
            self._temp_spectators.clear()

        return list(batch_ctx.match_results)

    def _run_sequential(
        self,
        game: Game,
        players: List[Player],
        batch_ctx: BatchContext,
        base_seed: Optional[int],
        matches: int,
    ) -> tuple[List[MatchResult], List[Optional[int]]]:
        """
        Execute matches sequentially using _MatchWorker (SPEC-PARALLEL v1.0.0 §7).

        Uses workers even in sequential mode to ensure consistent isolation semantics
        with parallel execution. Events are replayed in order to preserve spectator
        experience.

        Args:
            game: Game instance (will be cloned per worker)
            players: Player instances (will be cloned per worker)
            batch_ctx: Batch context metadata
            base_seed: Base seed for deterministic seeding
            matches: Number of matches to execute

        Returns:
            Tuple of (match_results, seeds_used)
        """
        batch_start_time = time.time()
        match_durations = []

        # Emit CONSOLE_BATCH_START - SPEC-MONITOR v1.0.0 §6.2 EM3
        self._emit_console_event(
            EventType.CONSOLE_BATCH_START,
            {
                "batch_id": batch_ctx.batch_id,
                "total_matches": matches,
                "concurrency": 1,
                "mode": "sequential",
                "base_seed": base_seed,
            },
        )

        seeds_used = []

        for index in range(matches):
            match_seed = self._derive_match_seed(base_seed, index)
            effective_seed = match_seed
            if effective_seed is None:
                self._match_counter += 1
                effective_seed = self._rng.fork(f"match-{self._match_counter}").seed

            # Determine previous match result for stateful ordering
            previous_match_result = batch_ctx.match_results[-1] if batch_ctx.match_results else None

            # Create worker with cloned game/players
            worker = _MatchWorker(
                game=game,
                players=players,
                console=self,
                match_index=index,
                seed=effective_seed,
                batch_ctx=batch_ctx,
                previous_match_result=previous_match_result,
            )

            # Execute match and get artifact
            artifact = worker.run()

            # Replay events to main event bus (preserves spectator ordering)
            self._replay_events(artifact.replay_events)

            # Store result
            batch_ctx.match_results.append(artifact.result)
            seeds_used.append(artifact.result.seed)

            # Track metrics
            duration = artifact.result.metadata.get("duration", 0)
            match_durations.append(duration)

            # Sync clone metrics back to original players
            self._sync_player_metrics(players, worker.players)

            # PF4: Check if match was aborted and raise to stop batch
            # Worker emitted MATCH_END and returned artifact, now we raise to halt execution
            from .types import (
                ActionParseError,
                MatchAbortedError,
                ParseFailurePolicy,
                ParseResult,
                TurnContext,
            )

            if artifact.result.metadata.get("outcome") == "aborted":
                # Reconstruct MatchAbortedError from metadata to propagate abort
                parse_error_data = artifact.result.metadata.get("parse_error", {})
                parse_result = ParseResult(
                    success=parse_error_data.get("success", False),
                    action=None,
                    raw_response=parse_error_data.get("raw_response", ""),
                    reasoning=parse_error_data.get("reasoning"),
                    error=parse_error_data.get("error", "Unknown parse error"),
                    metadata=parse_error_data.get("metadata", {}),
                )
                abort_ctx_data = artifact.result.metadata.get("abort_turn_context")
                abort_turn_context = TurnContext(**abort_ctx_data) if abort_ctx_data else None
                abort_error = MatchAbortedError(
                    player_name=artifact.result.metadata.get("failing_player", "unknown"),
                    parse_error=ActionParseError(parse_result),
                    turn_context=abort_turn_context,
                    policy=ParseFailurePolicy.ABORT_MATCH,
                )
                # Preserve abort state for callers
                abort_error.abort_state = copy.deepcopy(artifact.result.final_state)
                raise abort_error

            # Emit CONSOLE_BATCH_PROGRESS - SPEC-MONITOR v1.0.0 §6.2 EM6
            # (Even in sequential mode, allows monitors to track progress if attached)
            completed = index + 1
            elapsed = time.time() - batch_start_time
            avg_duration = sum(match_durations) / len(match_durations) if match_durations else 0
            remaining = matches - completed
            eta = avg_duration * remaining if avg_duration > 0 and remaining > 0 else None

            self._emit_console_event(
                EventType.CONSOLE_BATCH_PROGRESS,
                {
                    "batch_id": batch_ctx.batch_id,
                    "completed": completed,
                    "total": matches,
                    "in_progress": 0,  # Sequential has no concurrent workers
                    "failed": 0,  # Sequential aborts on first failure
                    "elapsed_time": elapsed,
                    "estimated_remaining": eta,
                },
            )

        # Emit CONSOLE_BATCH_COMPLETE - SPEC-MONITOR v1.0.0 §6.2 EM4
        total_duration = time.time() - batch_start_time
        avg_match_duration = sum(match_durations) / len(match_durations) if match_durations else 0

        self._emit_console_event(
            EventType.CONSOLE_BATCH_COMPLETE,
            {
                "batch_id": batch_ctx.batch_id,
                "completed": len(seeds_used),
                "total": matches,
                "failed": 0,
                "duration": total_duration,
                "avg_match_duration": avg_match_duration,
                "seeds_used": seeds_used,
            },
        )

        return list(batch_ctx.match_results), seeds_used

    def _run_parallel(
        self,
        game: Game,
        players: List[Player],
        batch_ctx: BatchContext,
        base_seed: Optional[int],
        matches: int,
    ) -> tuple[List[MatchResult], List[Optional[int]]]:
        """
        Execute matches in parallel using ThreadPoolExecutor (SPEC-PARALLEL v1.0.0 §7).

        Workers execute concurrently with deep-copy isolation. Events are replayed
        in match_index order to preserve spectator/recorder experience.

        Args:
            game: Game instance (will be cloned per worker)
            players: Player instances (will be cloned per worker)
            batch_ctx: Batch context metadata
            base_seed: Base seed for deterministic seeding
            matches: Number of matches to execute

        Returns:
            Tuple of (match_results, seeds_used)

        Note: Uses ThreadPoolExecutor (not ProcessPoolExecutor) because:
              - LLM I/O is network-bound, releases GIL
              - Deep-copy is simpler than pickle/unpickle
              - Shared Console reference for helpers works naturally
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        concurrency = self.session_state.config.concurrency
        batch_start_time = time.time()

        # Emit CONSOLE_BATCH_START - SPEC-MONITOR v1.0.0 §6.2 EM3
        self._emit_console_event(
            EventType.CONSOLE_BATCH_START,
            {
                "batch_id": batch_ctx.batch_id,
                "total_matches": matches,
                "concurrency": concurrency,
                "mode": "parallel",
                "base_seed": base_seed,
            },
        )

        # Pre-create all workers with deterministic seeds
        workers = []
        for index in range(matches):
            match_seed = self._derive_match_seed(base_seed, index)
            effective_seed = match_seed
            if effective_seed is None:
                self._match_counter += 1
                effective_seed = self._rng.fork(f"match-{self._match_counter}").seed

            # Note: previous_match_result is None for all matches in parallel execution
            # (per SPEC-PARALLEL §8 limitation)
            worker = _MatchWorker(
                game=game,
                players=players,
                console=self,
                match_index=index,
                seed=effective_seed,
                batch_ctx=batch_ctx,
                previous_match_result=None,
                emit_worker_events=True,  # Emit CONSOLE_WORKER_START/COMPLETE (SPEC-MONITOR §6.2 EM5)
            )
            workers.append(worker)

        # Execute workers in parallel
        artifacts: List[Optional[tuple[MatchArtifact, _MatchWorker]]] = [None] * matches
        completed_count = 0
        failed_count = 0
        match_durations = []

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit all workers
            future_to_worker = {executor.submit(worker.run): worker for worker in workers}

            # Collect results as they complete
            for future in as_completed(future_to_worker):
                worker = future_to_worker[future]

                try:
                    artifact = future.result()
                    artifacts[artifact.match_index] = (artifact, worker)

                    # Track metrics
                    duration = artifact.result.metadata.get("duration", 0)
                    match_durations.append(duration)
                    completed_count += 1

                    # Emit CONSOLE_WORKER_COMPLETE - SPEC-MONITOR v1.0.0 §6.2 EM5
                    self._emit_console_event(
                        EventType.CONSOLE_WORKER_COMPLETE,
                        {
                            "worker_id": worker.match_index,
                            "match_index": worker.match_index,
                            "duration": duration,
                            "winner": artifact.result.winner,
                            "turns": artifact.result.metadata.get("turns", 0),
                            "completed_at": time.time(),
                        },
                    )

                    # Calculate actual in_progress: min(concurrency, remaining matches)
                    remaining = matches - completed_count - failed_count
                    in_progress = min(concurrency, remaining)

                    # Emit CONSOLE_BATCH_PROGRESS - SPEC-MONITOR v1.0.0 §6.2 EM6
                    elapsed = time.time() - batch_start_time
                    avg_duration = (
                        sum(match_durations) / len(match_durations) if match_durations else 0
                    )
                    eta = avg_duration * remaining if avg_duration > 0 and remaining > 0 else None

                    self._emit_console_event(
                        EventType.CONSOLE_BATCH_PROGRESS,
                        {
                            "batch_id": batch_ctx.batch_id,
                            "completed": completed_count,
                            "total": matches,
                            "in_progress": in_progress,
                            "failed": failed_count,
                            "elapsed_time": elapsed,
                            "estimated_remaining": eta,
                        },
                    )

                except Exception as exc:
                    # Worker failed
                    failed_count += 1

                    # Emit CONSOLE_WORKER_FAILED - SPEC-MONITOR v1.0.0 §6.2 EM5
                    self._emit_console_event(
                        EventType.CONSOLE_WORKER_FAILED,
                        {
                            "worker_id": worker.match_index,
                            "match_index": worker.match_index,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                            "failed_at": time.time(),
                        },
                    )

                    # Propagate exception
                    raise RuntimeError(
                        f"Match {worker.match_index} failed during parallel execution"
                    ) from exc

        # Replay events in match_index order (preserves spectator observation semantics)
        seeds_used = []
        for item in artifacts:
            assert item is not None
            artifact, worker = item

            self._replay_events(artifact.replay_events)
            batch_ctx.match_results.append(artifact.result)
            seeds_used.append(artifact.result.seed)

            # Sync clone metrics back to original players
            self._sync_player_metrics(players, worker.players)

            # Note: Aborted matches (outcome="aborted") are already handled gracefully.
            # The match is recorded with full metadata, and the batch continues.
            # No need to re-raise MatchAbortedError - parse failures are policy-driven now.

        # Emit CONSOLE_BATCH_COMPLETE - SPEC-MONITOR v1.0.0 §6.2 EM4
        total_duration = time.time() - batch_start_time
        avg_match_duration = sum(match_durations) / len(match_durations) if match_durations else 0

        self._emit_console_event(
            EventType.CONSOLE_BATCH_COMPLETE,
            {
                "batch_id": batch_ctx.batch_id,
                "completed": completed_count,
                "total": matches,
                "failed": failed_count,
                "duration": total_duration,
                "avg_match_duration": avg_match_duration,
                "seeds_used": seeds_used,
            },
        )

        return list(batch_ctx.match_results), seeds_used

    def _replay_events(
        self, replay_events: List[tuple[EventType, Dict[str, Any], Dict[str, Any]]]
    ) -> None:
        """
        Replay captured events to main EventBus (SPEC-PARALLEL v1.0.0 §6-7).

        Events captured from worker are replayed in order to main EventBus,
        preserving spectator observation semantics. Events contain original
        Player/Game objects (not sanitized), so spectators receive the same
        payload structure as in sequential execution.

        CRITICAL: Temporarily restores worker's event bus context (match_id,
        phase_index, etc.) before each emission to ensure spectators see
        correct context metadata.

        Args:
            replay_events: List of (event_type, payload, context) tuples from worker
        """
        # Save current main bus context
        saved_context = dict(self.event_bus._base_context)

        try:
            for event_type, payload, context in replay_events:
                # Temporarily restore worker's context (match_id, phase_index, etc.)
                self.event_bus._base_context.clear()
                # Exclude timestamps - EventBus.emit will add fresh ones
                replay_context = {
                    k: v for k, v in context.items() if k not in ("timestamp", "monotonic_time")
                }
                self.event_bus._base_context.update(replay_context)

                # Emit with original payload (spectators get Player/Game objects, not names)
                self.event_bus.emit(event_type, **payload)

        finally:
            # Always restore main bus context
            self.event_bus._base_context.clear()
            self.event_bus._base_context.update(saved_context)

    def _sync_player_metrics(self, originals: List[Player], clones: List[Player]) -> None:
        """Propagate aggregate metrics (e.g., total_cost) from clones back to originals."""
        original_map = {player.name: player for player in originals}

        for clone in clones:
            original = original_map.get(clone.name)
            if original is None:
                continue

            for attr in ("total_cost", "total_tokens"):
                if hasattr(clone, attr) and hasattr(original, attr):
                    setattr(original, attr, getattr(clone, attr))

            if hasattr(clone, "response_times") and hasattr(original, "response_times"):
                setattr(original, "response_times", copy.deepcopy(getattr(clone, "response_times")))

    def _determine_player_order_and_baseline(
        self,
        game: Game,
        players: List[Player],
        runtime: MatchExecutionContext,
        previous_match_result: Optional[MatchResult],
    ) -> tuple[List[Player], List[int], str, Dict[str, Any], Dict[str, float]]:
        """
        Determine player order and capture cost baseline.

        Extracted from play_match() to enable reuse in worker path.

        Returns:
            Tuple of (ordered_players, player_order, player_order_source, first_player, cost_baseline)
        """
        # Call game hook with match context (allows state-dependent ordering)
        match_context_for_hook = PlayerMatchContext(
            match_id=runtime.match_id,
            players=[p.name for p in players],
            game_name=game.__class__.__name__,
            seed=runtime.seed,
            handshake_completed=False,  # Not started yet
            rng_info={"seed": runtime.seed},
            previous_match_result=previous_match_result,  # Batch-local (M4)
        )

        # Check if game has get_player_order hook
        if hasattr(game, "get_player_order"):
            game_ordered = game.get_player_order(
                players, rng=runtime.rng, match_context=match_context_for_hook
            )
        else:
            game_ordered = None

        # Determine ordered players and source
        original_players = list(players)  # Keep original for metadata
        if game_ordered is not None:
            # Game overrode ordering - validate (H4)
            self._validate_player_list(players, game_ordered)
            ordered_players = game_ordered
            player_order_source = "game"
        else:
            # Console applies Fisher-Yates shuffle (PO4)
            ordered_players = self._shuffle_players(players, runtime.rng)
            player_order_source = "console"

        # Calculate player_order indices and first_player metadata
        player_order = [original_players.index(p) for p in ordered_players]
        first_player = {"name": ordered_players[0].name, "index": player_order[0]}

        # Track per-player API cost baseline prior to handshake/turns
        cost_baseline = {
            player.name: float(getattr(player, "total_cost", 0.0)) for player in ordered_players
        }

        # Log at DEBUG level (M4)
        if self.logger:
            self.logger.debug(
                f"Player order determined: {[p.name for p in ordered_players]} (source: {player_order_source})"
            )

        return ordered_players, player_order, player_order_source, first_player, cost_baseline

    def _compute_cost_deltas(
        self,
        ordered_players: List[Player],
        cost_baseline: Dict[str, float],
    ) -> tuple[Dict[str, float], float]:
        """
        Compute per-player API cost deltas.

        Extracted from play_match() to enable reuse in worker path.

        Returns:
            Tuple of (player_costs, total_match_cost)
        """
        player_costs: Dict[str, float] = {}
        total_match_cost = 0.0
        for player in ordered_players:
            before_cost = cost_baseline.get(player.name, 0.0)
            after_cost = float(getattr(player, "total_cost", 0.0))
            delta = after_cost - before_cost
            if delta < 0:
                delta = 0.0
            player_costs[player.name] = delta
            total_match_cost += delta
        return player_costs, total_match_cost

    def _build_match_metadata(
        self,
        game: Game,
        player_names: List[str],
        player_order: List[int],
        player_order_source: str,
        first_player: Dict[str, Any],
        match_duration: float,
        runtime: MatchExecutionContext,
        truncated: bool,
        turn_count: int,
        player_costs: Dict[str, float],
        total_match_cost: float,
        batch_ctx: BatchContext,
    ) -> Dict[str, Any]:
        """
        Build match metadata dictionary.

        Extracted from play_match() to enable reuse in worker path.

        Returns:
            Match metadata dict
        """
        return {
            "game": game.__class__.__name__,
            "players": player_names,  # Recorder expects this (ordered list post-ordering)
            "player_names": player_names,  # Ordered list post-ordering
            "player_order": player_order,  # Original indices (M4)
            "player_order_source": player_order_source,  # "console" or "game" (M4)
            "first_player": first_player,  # {"name": str, "index": int} (M4)
            "duration": match_duration,
            "handshake_completed": runtime.handshake_completed,
            "seed": runtime.seed,
            "batch_id": batch_ctx.batch_id,
            "truncated_by_max_turns": truncated,
            "turns": turn_count,  # M1: Include turn count
            "player_costs": player_costs,
            "cost": total_match_cost,
            "schema_version": Recorder.SCHEMA_VERSION,
        }

    def play_match(
        self,
        game: Game,
        players: List[Player],
        batch_ctx: BatchContext,
        *,
        match_index: int,
        seed: Optional[int],
        previous_match_result: Optional[MatchResult] = None,
    ) -> MatchResult:
        """Execute a single match."""
        runtime = self._create_match_runtime(seed)

        # Determine player order using extracted helper
        ordered_players, player_order, player_order_source, first_player, cost_baseline = (
            self._determine_player_order_and_baseline(game, players, runtime, previous_match_result)
        )

        player_names = [player.name for player in ordered_players]

        self.game = game
        self.players = list(ordered_players)
        self._current_match_id = runtime.match_id
        self.event_bus.update_context(match_id=runtime.match_id, phase_index=None)

        self._prepare_players(ordered_players)

        infra_runtime = self._create_infrastructure_runtime(game, runtime, previous_match_result)

        temp_emitter = GameEventEmitter(self.event_bus, runtime.match_id)
        temp_factory = EventFactory(runtime.match_id)
        game.bind_event_factory(temp_factory)
        game.bind_event_emitter(temp_emitter)
        try:
            setup_rng = infra_runtime.fork_rng("setup")
            state = game.setup(player_names, seed=setup_rng.seed)
            if not isinstance(state, dict):
                raise TypeError(
                    f"{game.__class__.__name__}.setup() must return a dict, got {type(state).__name__}"
                )
            state.setdefault("_turn_count", 1)
            infra_runtime.validate_state(state)

            state = self._run_handshake(game, ordered_players, runtime, infra_runtime, state)
            infra_runtime.initial_state = state
            infra_runtime.validate_state(state)
        finally:
            game.bind_event_factory(None)
            game.bind_event_emitter(None)
            temp_emitter.clear_phase_index()

        self._dispatch_event(
            EventType.MATCH_START,
            events=runtime.events,
            game=game,  # Recorder expects game object
            players=ordered_players,  # Recorder expects player objects (ordered)
            match_id=runtime.match_id,
            seed=runtime.seed,  # Per SPEC-OBSERVABILITY §9.1
            player_names=player_names,  # Ordered list post-ordering
            player_order=player_order,  # Original indices
            player_order_source=player_order_source,  # "console" or "game"
            first_player=first_player,  # {"name": str, "index": int}
        )

        from .types import MatchAbortedError, MatchForfeitedError

        try:
            # Call game.run(runtime, players) - mechanic-agnostic delegation (SPEC-GAME v0.6.0)
            from .mechanics.turn_based import TurnResult

            result = game.run(infra_runtime, ordered_players)

            # Extract result (TurnResult or compatible tuple)
            if isinstance(result, TurnResult):
                final_state = result.final_state
                truncated = result.truncated_by_max_turns
            else:
                # Backward compat: game returned tuple (final_state, events, truncated)
                final_state, _, truncated = result

            # Count turns from final state
            turn_count = final_state.get("_turn_count", 0)
            runtime.truncated_by_max_turns = truncated
        except MatchAbortedError as abort_error:
            match_duration = time.time() - runtime.started_at

            abort_state = copy.deepcopy(getattr(abort_error, "abort_state", {}))
            abort_turn = abort_error.turn_context.turn_number if abort_error.turn_context else 0

            metadata = self._build_match_metadata(
                game,
                player_names,
                player_order,
                player_order_source,
                first_player,
                match_duration,
                runtime,
                False,
                abort_turn,
                {},
                0.0,
                batch_ctx,
            )

            metadata["outcome"] = "aborted"
            metadata["abort_reason"] = "parse_failure"
            metadata["failing_player"] = abort_error.player_name
            metadata["policy"] = abort_error.policy.value
            metadata["abort_turn"] = abort_turn

            if abort_error.turn_context is not None:
                metadata["abort_turn_context"] = {
                    "match_id": abort_error.turn_context.match_id,
                    "turn_number": abort_error.turn_context.turn_number,
                    "turn_index": abort_error.turn_context.turn_index,
                    "player": abort_error.turn_context.player,
                    "started_at": abort_error.turn_context.started_at,
                    "duration": abort_error.turn_context.duration,
                    "rng_seed": abort_error.turn_context.rng_seed,
                    "rng_label": abort_error.turn_context.rng_label,
                }

            metadata["parse_error"] = {
                "success": abort_error.parse_error.parse_result.success,
                "error": abort_error.parse_error.parse_result.error,
                "raw_response": abort_error.parse_error.parse_result.raw_response,
                "reasoning": abort_error.parse_error.parse_result.reasoning,
                "metadata": copy.deepcopy(abort_error.parse_error.parse_result.metadata),
                "candidates": abort_error.parse_error.parse_result.metadata.get("candidates", []),
            }

            final_player_costs, final_total_match_cost = self._compute_cost_deltas(
                ordered_players, cost_baseline
            )
            metadata["player_costs"] = final_player_costs
            metadata["cost"] = final_total_match_cost

            match_result = MatchResult(
                winner=None,
                final_state=copy.deepcopy(abort_state),
                events=list(runtime.events),
                seed=runtime.seed,
                metadata=metadata,
            )

            self._dispatch_event(
                EventType.MATCH_END,
                events=runtime.events,
                result=match_result,
            )

            # Preserve abort state for callers and clear console context before propagating
            abort_error.abort_state = copy.deepcopy(abort_state)
            self.event_bus.clear_context("match_id", "phase_index")
            self._current_match_id = None
            self._current_phase_index = None
            self.game = None
            self.players = []
            raise

        except MatchForfeitedError as forfeit_error:
            # FORFEIT policy: Match ends with winner determined (Codex fix: add sequential path handler)
            match_duration = time.time() - runtime.started_at

            forfeit_state = copy.deepcopy(getattr(forfeit_error, "forfeit_state", {}))
            forfeit_turn = (
                forfeit_error.turn_context.turn_number if forfeit_error.turn_context else 0
            )

            metadata = self._build_match_metadata(
                game,
                player_names,
                player_order,
                player_order_source,
                first_player,
                match_duration,
                runtime,
                False,
                forfeit_turn,
                {},
                0.0,
                batch_ctx,
            )

            metadata["outcome"] = "forfeit"
            metadata["forfeit_reason"] = "parse_failure"
            metadata["forfeiting_player"] = forfeit_error.player_name
            metadata["policy"] = forfeit_error.policy.value
            metadata["forfeit_turn"] = forfeit_turn

            if forfeit_error.turn_context is not None:
                metadata["forfeit_turn_context"] = {
                    "match_id": forfeit_error.turn_context.match_id,
                    "turn_number": forfeit_error.turn_context.turn_number,
                    "turn_index": forfeit_error.turn_context.turn_index,
                    "player": forfeit_error.turn_context.player,
                    "started_at": forfeit_error.turn_context.started_at,
                    "duration": forfeit_error.turn_context.duration,
                    "rng_seed": forfeit_error.turn_context.rng_seed,
                    "rng_label": forfeit_error.turn_context.rng_label,
                }

            # Codex fix #2: Include full parse_result metadata (reasoning + deep copy)
            metadata["parse_error"] = {
                "success": forfeit_error.parse_error.parse_result.success,
                "error": forfeit_error.parse_error.parse_result.error,
                "raw_response": forfeit_error.parse_error.parse_result.raw_response,
                "reasoning": forfeit_error.parse_error.parse_result.reasoning,
                "metadata": copy.deepcopy(forfeit_error.parse_error.parse_result.metadata),
                "candidates": forfeit_error.parse_error.parse_result.metadata.get("candidates", []),
            }

            final_player_costs, final_total_match_cost = self._compute_cost_deltas(
                ordered_players, cost_baseline
            )
            metadata["player_costs"] = final_player_costs
            metadata["cost"] = final_total_match_cost

            match_result = MatchResult(
                winner=forfeit_error.winner,  # Opponent wins
                final_state=copy.deepcopy(forfeit_state),
                events=list(runtime.events),
                seed=runtime.seed,
                metadata=metadata,
            )

            self._dispatch_event(
                EventType.MATCH_END,
                events=runtime.events,
                result=match_result,
            )

            # Clear console context and return normally (match completed with winner)
            self.event_bus.clear_context("match_id", "phase_index")
            self._current_match_id = None
            self._current_phase_index = None
            self.game = None
            self.players = []

            return match_result

        status = self._safe_status(game, final_state)
        match_duration = time.time() - runtime.started_at

        # Build metadata using extracted helper (costs filled after conclusions)
        metadata = self._build_match_metadata(
            game,
            player_names,
            player_order,
            player_order_source,
            first_player,
            match_duration,
            runtime,
            truncated,
            turn_count,
            {},
            0.0,
            batch_ctx,
        )

        match_result = MatchResult(
            winner=status.winner,
            final_state=copy.deepcopy(final_state),
            events=list(runtime.events),
            seed=runtime.seed,
            metadata=metadata,
        )

        # Run conclusion phase BEFORE MATCH_END so spectators see reflections
        self._run_conclusion(ordered_players, match_result, runtime)

        # Recompute per-player API cost deltas after conclusions to include reflection spend
        final_player_costs, final_total_match_cost = self._compute_cost_deltas(
            ordered_players, cost_baseline
        )
        match_result.metadata["player_costs"] = final_player_costs
        match_result.metadata["cost"] = final_total_match_cost

        # Emit MATCH_END after conclusions
        self._dispatch_event(
            EventType.MATCH_END,
            events=runtime.events,
            result=match_result,  # Recorder expects result: MatchResult
        )

        self.event_bus.clear_context("match_id", "phase_index")
        self._current_match_id = None
        self._current_phase_index = None
        self.game = None
        self.players = []
        return match_result

    def _handle_parse_failure(
        self,
        player: "Player",
        error: "ActionParseError",
        turn_context: "TurnContext",
        game: "Game",
    ) -> "ParseFailurePolicy":
        """
        Handle action parsing failure per SPEC-CONSOLE v0.5.0 §6.11 PF2.

        Steps:
        1. Extract ParseResult from error.parse_result
        2. Emit PLAYER_ACTION_PARSE_FAILED event
        3. Append failure to Recorder (via event subscription)
        4. Call game.on_action_parse_failure() to determine policy
        5. Return policy outcome to caller

        Args:
            player: Player who failed to produce valid action
            error: ActionParseError with embedded ParseResult
            turn_context: Immutable turn context snapshot
            game: Game instance for policy hook

        Returns:
            ParseFailurePolicy enum value (ABORT_MATCH, SKIP_TURN, FORFEIT, RETRY_ONCE)

        Per SPEC-CONSOLE PF2-PF5.
        """

        parse_result = error.parse_result

        # Step 1: Call game hook to determine policy (PF2 step 4)
        policy = game.on_action_parse_failure(player.name, error, turn_context)

        # Step 2: Emit PLAYER_ACTION_PARSE_FAILED event with policy (PF2 step 2)
        # IMPORTANT: Emit AFTER hook so policy_outcome is included
        # Schema v1.3: Include prompt metadata (PM1-PM6) in parse failure events
        # Note: Full prompt capture requires player/LLM cooperation - using raw_response as fallback
        self.event_bus.emit(
            EventType.PLAYER_ACTION_PARSE_FAILED,
            player=player.name,
            match_id=turn_context.match_id,
            turn_number=turn_context.turn_number,
            parse_result={
                "success": parse_result.success,
                "error": parse_result.error,
                "raw_response": parse_result.raw_response,
                "reasoning": parse_result.reasoning,
                "metadata": parse_result.metadata,
                "candidates": parse_result.metadata.get("candidates", []),
            },
            raw_response=parse_result.raw_response,
            policy_outcome=policy.value,  # Include policy chosen by game
            # PM1-PM6: Prompt metadata (schema v1.3)
            prompt_text=getattr(parse_result, "prompt_text", ""),  # PM1: Full prompt text
            prompt_blocks=getattr(parse_result, "prompt_blocks", []),  # PM2: PromptBuilder blocks
            response_text=parse_result.raw_response,  # PM3: LLM response (use raw_response)
            # PM4-PM6 are optional and currently not available in parse context
        )

        # Step 3: Recorder handles via on_player_action_parse_failed() subscription
        # (Event bus delivers to all subscribers including Recorder)

        # Step 4: Log policy decision (PF5)
        if self.logger:
            self.logger.warning(
                f"Parse failure for {player.name} at turn {turn_context.turn_number}. "
                f"Error: {parse_result.error}. Policy: {policy.value}"
            )

        return policy

    def get_player_action(
        self,
        player_view: Dict[str, Any],
        player: Player,
        game: Game,
        *,
        turn_context: TurnContext,
        extras: Optional[Dict[str, Any]] = None,
    ) -> ActionResult:
        """
        Broker a player decision without inspecting game semantics.

        Per SPEC-CONSOLE v0.5.0 §6.11 PF1-PF4, catches ActionParseError and delegates
        to _handle_parse_failure() for policy-based resolution.

        Raises:
            MatchAbortedError: When policy is ABORT_MATCH. Caller MUST emit MATCH_END
                              with metadata["outcome"]="aborted" before propagating (PF4).
        """
        from .types import ActionParseError, MatchAbortedError, ParseFailurePolicy

        try:
            action_result = player.decide(player_view, turn_context=turn_context, extras=extras)
        except ActionParseError as parse_error:
            # Handle parse failure via game policy (PF1-PF3)
            policy = self._handle_parse_failure(player, parse_error, turn_context, game)

            if policy == ParseFailurePolicy.ABORT_MATCH:
                # PF4: Raise MatchAbortedError (caller emits MATCH_END before propagating)
                raise MatchAbortedError(
                    player_name=player.name,
                    parse_error=parse_error,
                    turn_context=turn_context,
                    policy=policy,
                )
            elif policy == ParseFailurePolicy.SKIP_TURN:
                # Return sentinel ActionResult preserving original ParseResult metadata
                # Codex fix: Must include parser_success=False to maintain contract
                sentinel_metadata = (
                    dict(parse_error.parse_result.metadata)
                    if parse_error.parse_result.metadata
                    else {}
                )
                sentinel_metadata.update(
                    {
                        "parser_success": False,  # Truthful parse status
                        "_skip_turn": True,
                        "parse_error": parse_error.parse_result.error,
                        "policy": "skip_turn",
                    }
                )
                return ActionResult(
                    action="__SKIP_TURN__",
                    raw_response=parse_error.parse_result.raw_response,
                    reasoning=parse_error.parse_result.reasoning,
                    metadata=sentinel_metadata,
                )
            elif policy == ParseFailurePolicy.FORFEIT:
                # Failing player forfeits - opponent wins
                # For 2-player games, winner is the other player
                # For multiplayer (>2), use first opponent (game-specific logic may vary)
                from .types import MatchForfeitedError

                # Get all player names from Console's player list
                all_players = [p.name for p in self.players]
                opponents = [name for name in all_players if name != player.name]
                winner = opponents[0] if opponents else None

                if not winner:
                    raise RuntimeError(
                        f"FORFEIT policy requires at least 2 players, found only {player.name}"
                    )

                raise MatchForfeitedError(
                    player_name=player.name,
                    parse_error=parse_error,
                    turn_context=turn_context,
                    policy=policy,
                    winner=winner,
                )
            elif policy == ParseFailurePolicy.RETRY_ONCE:
                # Track retry budget: only retry once per player per turn
                retry_key = f"{turn_context.match_id}_{turn_context.turn_number}_{player.name}"

                # Check if we have a retry budget tracker (create if needed)
                if not hasattr(self, "_retry_budget"):
                    self._retry_budget = {}

                if retry_key in self._retry_budget:
                    # Already retried once - fall back to ABORT_MATCH
                    raise MatchAbortedError(
                        player_name=player.name,
                        parse_error=parse_error,
                        turn_context=turn_context,
                        policy=ParseFailurePolicy.ABORT_MATCH,
                    )

                # Mark this turn as retried
                self._retry_budget[retry_key] = True

                # Retry: call player.decide() again with same inputs
                try:
                    action_result = player.decide(
                        player_view, turn_context=turn_context, extras=extras
                    )
                    # Retry succeeded - clear retry budget and return result
                    del self._retry_budget[retry_key]
                    return action_result
                except ActionParseError as retry_error:
                    # Retry failed - clear budget and fall back to ABORT_MATCH
                    del self._retry_budget[retry_key]

                    # PF1/PF2 compliance: Emit parse failure event for retry failure
                    # Even though we're forcing ABORT_MATCH, we must record the second parse failure
                    retry_policy = self._handle_parse_failure(
                        player, retry_error, turn_context, game
                    )
                    # Policy should be ABORT_MATCH (we force it), but respect hook decision
                    if retry_policy != ParseFailurePolicy.ABORT_MATCH:
                        # Game hook tried to override - log warning and force ABORT
                        # (retry budget exhausted, no other option)
                        pass  # TODO: Consider logging this edge case

                    raise MatchAbortedError(
                        player_name=player.name,
                        parse_error=retry_error,
                        turn_context=turn_context,
                        policy=ParseFailurePolicy.ABORT_MATCH,
                    )
            else:
                raise ValueError(f"Unknown ParseFailurePolicy: {policy}")

        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Player {player.name} failed during decide() in match {turn_context.match_id} "
                f"turn {turn_context.turn_number}"
            ) from exc

        if not isinstance(action_result, ActionResult):
            raise TypeError(
                f"Player {player.name}.decide() must return ActionResult, "
                f"got {type(action_result).__name__}"
            )
        if not action_result.action or not str(action_result.action).strip():
            raise ValueError(
                f"Player {player.name}.decide() returned empty action. "
                f"ActionResult.action must be non-empty."
            )

        return action_result

    def emit_turn(
        self,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        player: str,
        action: ActionResult,
        *,
        turn_context: Any,
        events: Optional[List[Event]] = None,
    ) -> None:
        """Emit turn gameplay event with deep-copied states."""
        if isinstance(turn_context, dict):
            ctx_dict = dict(turn_context)
            turn_index = ctx_dict.get("turn_index", 0)
            match_id = ctx_dict.get("match_id")
        else:
            ctx_dict = turn_context.to_dict()
            turn_index = turn_context.turn_index
            match_id = turn_context.match_id

        self._current_phase_index = turn_index

        # Update EventBus context so GAMEPLAY events include turn_index (E3)
        self.event_bus.update_context(phase_index=turn_index, turn_index=turn_index)

        payload = {
            "mechanic": "turn_based",  # SPEC-OBSERVABILITY §3.2: mechanic field required
            "match_id": match_id,
            "player": player,
            "turn_context": ctx_dict,
            "state_before": copy.deepcopy(state_before),
            "state_after": copy.deepcopy(state_after),
            "action": {
                "action": action.action,
                "reasoning": action.reasoning,
                "metadata": copy.deepcopy(action.metadata) if action.metadata else {},
                "raw_response": action.raw_response,
            },
        }
        self._dispatch_event(EventType.GAMEPLAY, events=events, **payload)

        # Clear turn_index from EventBus context after emission
        self.event_bus.clear_context("phase_index", "turn_index")
        self._current_phase_index = None

    def emit_event(self, event: Event) -> None:
        """Forward custom game event via the EventBus."""
        payload = copy.deepcopy(event.data)
        self.event_bus.emit(event.type, **payload)

    def log(
        self,
        message: str,
        *,
        level: str = "info",
        player: Optional[str] = None,
        match_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log structured diagnostic information and emit LOG event."""
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message, extra=extra)

        self._dispatch_event(
            EventType.LOG,
            events=None,
            message=message,
            level=level,
            player=player,
            match_id=match_id,
            turn_number=turn_number,
            extra=extra or {},
        )

    def close(self) -> None:
        """Cleanup console resources and emit SESSION_END."""
        if self._session_closed:
            return

        try:
            self._dispatch_event(
                EventType.SESSION_END,
                events=None,
                session_id=self.session_state.session_id,
            )
        finally:
            self.session_state.finished_at = time.time()
            for spectator in self._base_spectators:
                self.event_bus.unsubscribe(spectator)
            if self.recorder is not None:
                self.event_bus.unsubscribe(self.recorder)
            self._session_closed = True

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _setup_monitors(self, config: AgentDeckConfig) -> None:
        """
        Setup console monitors per SPEC-MONITOR v1.0.0 §6.1.

        Invariants:
        - ML2: Auto-attach ProgressMonitor when concurrency > 1 and monitors=None
        - ML3: No default monitor when concurrency == 1
        - ML4: Respect explicit monitors=[] (opt-out)
        - ML5: Inject logger into monitors before subscription
        """
        from ..monitors import ProgressMonitor

        monitors = config.monitors

        # ML2 & ML3: Auto-attach default ProgressMonitor for parallel execution
        if monitors is None:
            if config.concurrency > 1:
                monitors = [ProgressMonitor(mode="normal")]
            else:
                monitors = []

        # ML5: Inject logger into monitors and subscribe to console EventBus
        for monitor in monitors:
            if getattr(monitor, "logger", None) is None:
                monitor.logger = self.logger
            self.console_bus.subscribe(monitor)

    def _default_session_factory(
        self,
        config: AgentDeckConfig,
        session: SessionContext,
        seed: int,
    ) -> SessionState:
        return SessionState(
            config=config,
            session_id=session.session_id,
            seed=seed,
            started_at=session.started_at,
            log_directory=session.log_directory,
            record_directory=session.record_directory,
            log_file_levels=list(session.log_file_levels),
        )

    def _emit_session_start(self) -> None:
        if self._session_started:
            return
        self.event_bus.update_context(session_id=self.session_state.session_id)
        self._dispatch_event(
            EventType.SESSION_START,
            events=None,
            session_id=self.session_state.session_id,
            seed=self.session_state.seed,
            log_directory=self.session_state.log_directory,
            record_directory=self.session_state.record_directory,
        )
        self._session_started = True

    def _next_batch_id(self) -> str:
        return f"batch_{uuid.uuid4().hex[:8]}"

    def _derive_match_seed(self, base_seed: Optional[int], index: int) -> Optional[int]:
        if base_seed is None:
            return None
        return base_seed + index

    def _validate_player_list(self, original: List[Player], game_returned: List[Player]) -> None:
        """
        Validate that game.get_player_order() returned a valid player list (H4).

        Args:
            original: Original player list passed to game
            game_returned: Player list returned by game.get_player_order()

        Raises:
            ValueError: If returned list is invalid
        """
        # Check length
        if len(game_returned) != len(original):
            raise ValueError(
                f"Game returned player list with {len(game_returned)} players but expected {len(original)}"
            )

        # Check for duplicates FIRST (before instance check)
        returned_set = set(id(p) for p in game_returned)
        if len(returned_set) != len(game_returned):
            # Find the duplicate
            seen = set()
            for p in game_returned:
                if p.name in seen:
                    raise ValueError(f"Game returned duplicate player: {p.name}")
                seen.add(p.name)

        # Check for same player instances (not just names)
        original_set = set(id(p) for p in original)
        if original_set != returned_set:
            raise ValueError(
                "Game returned different Player instances than provided. "
                "Must return same instances in possibly different order."
            )

    def _shuffle_players(self, players: List[Player], rng: RandomGenerator) -> List[Player]:
        """
        Shuffle player list using Fisher-Yates algorithm with provided RNG.

        Args:
            players: Original player list
            rng: RandomGenerator for deterministic shuffling

        Returns:
            New list with shuffled players (original list unchanged)
        """
        shuffled = list(players)  # Copy to avoid mutating input
        for i in range(len(shuffled) - 1, 0, -1):
            j = rng.randint(0, i)  # RandomGenerator.randint(a, b) inclusive
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
        return shuffled

    def _create_match_runtime(self, seed: Optional[int]) -> MatchExecutionContext:
        """Create lightweight execution context for tracking match metadata."""
        if seed is not None:
            rng = RandomGenerator(seed)
        else:
            self._match_counter += 1
            rng = self._rng.fork(f"match-{self._match_counter}")
        match_id = f"match_{uuid.uuid4().hex[:8]}"
        return MatchExecutionContext(
            match_id=match_id,
            seed=seed if seed is not None else rng.seed,
            rng=rng,
            started_at=time.time(),
        )

    def _create_infrastructure_runtime(
        self,
        game: Game,
        exec_ctx: MatchExecutionContext,
        previous_match_result: Optional[MatchResult] = None,
    ) -> MatchRuntime:
        """
        Create MatchRuntime infrastructure context for game.run().

        Bundles all infrastructure (events, recorder, RNG, logging) into single
        object that games/mechanics use as exclusive gateway (per SPEC-MATCH-RUNTIME).

        Args:
            game: Game instance (for validation hooks)
            exec_ctx: Execution metadata (match_id, seed, rng, etc.)
            previous_match_result: Previous match result for stateful ordering

        Returns:
            MatchRuntime instance ready for game.run(runtime, players)
        """
        # Create MatchRuntime (infrastructure context) with all required fields
        return MatchRuntime(
            console=self,
            game=game,
            match_id=exec_ctx.match_id,
            session_id=self.session_state.session_id,
            batch_id=self._current_batch_id or "unknown",
            seed=exec_ctx.seed or 0,
            max_turns=self.max_turns,
            recorder=self.recorder,
            logger=self.logger,
            rng=exec_ctx.rng,
            previous_match_result=previous_match_result,
            events_list=exec_ctx.events,  # TL6: for replay parity
        )

    def _prepare_players(self, players: List[Player]) -> None:
        for player in players:
            if hasattr(player, "reset_conversation"):
                player.reset_conversation()
            conversation = ConversationManager(player_name=player.name, event_bus=self.event_bus)
            if hasattr(player, "bind_conversation_manager"):
                player.bind_conversation_manager(conversation)
            if hasattr(player, "logger"):
                player.logger = self.logger

    def _run_handshake(
        self,
        game: Game,
        players: List[Player],
        runtime: MatchExecutionContext,
        infra_runtime: MatchRuntime,
        game_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = copy.deepcopy(game_state)
        player_names = [p.name for p in players]
        for player in players:
            context = HandshakeContext(
                match_id=runtime.match_id,
                player_name=player.name,
                opponent_names=[name for name in player_names if name != player.name],
                game_name=game.__class__.__name__,
                seed=runtime.seed,
                handshake_template_id="default",
                metadata={
                    "game_instructions": getattr(game, "instructions", ""),
                    "allowed_actions": getattr(game, "allowed_actions", []),
                },
            )
            self._dispatch_event(
                EventType.PLAYER_HANDSHAKE_START,
                events=runtime.events,
                player=player.name,
                match_id=runtime.match_id,
            )

            # Bind controller to game before handshake (GB1)
            # This allows controller to provide game-specific format instructions with allowed_actions
            if hasattr(player, "controller") and hasattr(player.controller, "bind_game"):
                player.controller.bind_game(self.game)

            raw = player.handshake(context)

            # Capture handshake prompt from conversation history (if available)
            prompt_text: Optional[str] = None
            conversation_manager = getattr(player, "conversation_manager", None)
            if conversation_manager is not None:
                history = conversation_manager.history()
                if len(history) >= 2:
                    # Handshake adds user prompt followed by assistant response
                    prompt_text = history[-2]["content"]

            result = player.controller.validate_handshake(raw, context=context)
            if not result.accepted:
                self._dispatch_event(
                    EventType.PLAYER_HANDSHAKE_ABORT,
                    events=runtime.events,
                    player=player.name,
                    reason=result.reason,
                    prompt_text=prompt_text,
                )
                raise HandshakeRejectedError(
                    f"Player {player.name} rejected handshake: {result.reason}"
                )

            try:
                state = game.on_handshake_complete(state, player.name, result) or state
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError(
                    f"{game.__class__.__name__}.on_handshake_complete() failed for player {player.name}"
                ) from exc

            runtime.handshake_completed = True
            infra_runtime.initial_state = state
            self._dispatch_event(
                EventType.PLAYER_HANDSHAKE_COMPLETE,
                events=runtime.events,
                player=player.name,
                response=result.normalized_response,
                metadata=result.metadata,
                prompt_text=prompt_text,
            )

        return state

    def _run_conclusion(
        self,
        players: List[Player],
        match_result: MatchResult,
        runtime: MatchExecutionContext,
    ) -> None:
        match_ctx = PlayerMatchContext(
            match_id=runtime.match_id,
            players=[player.name for player in players],
            game_name=match_result.metadata.get("game", ""),
            seed=runtime.seed,
            handshake_completed=runtime.handshake_completed,
            rng_info={"seed": runtime.seed},
        )
        concluding_player = None
        conclusion_reflection: Optional[str] = None

        try:
            concluding_player = self.game.requires_conclusion(match_result.final_state)
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"{self.game.__class__.__name__}.requires_conclusion() failed"
            ) from exc

        if concluding_player:
            target = next((p for p in players if p.name == concluding_player), None)
            if target is None:
                raise ValueError(
                    f"{self.game.__class__.__name__}.requires_conclusion returned unknown player '{concluding_player}'"
                )

            prompt = self.game.get_conclusion_prompt(concluding_player, match_result.final_state)
            match_ctx.conclusion_prompt = prompt
            conclusion_reflection = target.conclude(match_result, match_context=match_ctx)
            parsed = self.game.parse_conclusion(concluding_player, conclusion_reflection)
            match_result.final_state = self.game.on_conclusion_received(
                match_result.final_state, concluding_player, parsed
            )

        for player in players:
            if player.name == concluding_player:
                reflection = conclusion_reflection
            else:
                match_ctx.conclusion_prompt = None
                reflection = player.conclude(match_result, match_context=match_ctx)
            self._dispatch_event(
                EventType.PLAYER_CONCLUSION,
                events=runtime.events,
                player=player.name,
                reflection=reflection,
            )

    def _safe_status(self, game: Game, state: Dict[str, Any]) -> GameStatus:
        try:
            return game.status(state)
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"{game.__class__.__name__}.status() failed") from exc

    def _dispatch_event(
        self,
        event_type: EventType,
        *,
        events: Optional[List[Event]],
        **payload: Any,
    ) -> None:
        """Send event through EventBus and optionally capture snapshot."""
        # Selectively deepcopy payload, excluding objects that may contain unpicklable elements
        # (e.g., Player objects with OpenAI clients containing thread locks)
        event_payload = {}
        for key, value in payload.items():
            # Don't deepcopy Player, Game, or Spectator objects - they're read-only in events
            if isinstance(value, (Player, Game, Spectator)):
                event_payload[key] = value
            # Don't deepcopy lists of Player/Game/Spectator objects
            elif (
                isinstance(value, list)
                and value
                and isinstance(value[0], (Player, Game, Spectator))
            ):
                event_payload[key] = value
            else:
                event_payload[key] = copy.deepcopy(value)

        self.event_bus.emit(event_type, **event_payload)
        if events is not None:
            snapshot = self._make_event_snapshot(event_type, payload)
            events.append(snapshot)

    def _make_event_snapshot(self, event_type: EventType, payload: Dict[str, Any]) -> Event:
        context: Dict[str, Any] = {
            "session_id": self.session_state.session_id,
            "timestamp": time.time(),
            "monotonic_time": time.monotonic(),
        }
        if self._current_batch_id:
            context["batch_id"] = self._current_batch_id
        if self._current_match_id:
            context["match_id"] = self._current_match_id
        if self._current_phase_index is not None:
            context["phase_index"] = self._current_phase_index
            context["turn_index"] = self._current_phase_index

        # Selectively deepcopy payload for snapshot, excluding unpicklable objects
        snapshot_data = {}
        for key, value in payload.items():
            if isinstance(value, (Player, Game, Spectator)):
                # For Player/Game/Spectator objects, just store the name/class
                if hasattr(value, "name"):
                    snapshot_data[key] = value.name
                else:
                    snapshot_data[key] = value.__class__.__name__
            elif (
                isinstance(value, list)
                and value
                and isinstance(value[0], (Player, Game, Spectator))
            ):
                # For lists of Player/Game/Spectator, store their names
                snapshot_data[key] = [
                    getattr(item, "name", item.__class__.__name__) for item in value
                ]
            else:
                snapshot_data[key] = copy.deepcopy(value)

        return Event(
            type=event_type.value,
            data=snapshot_data,
            context=context,
        )

    def _emit_console_event(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        """
        Emit console event to console EventBus (SPEC-MONITOR v1.0.0 §6.2).

        Console events are:
        - Live (emitted immediately, not buffered)
        - Not replayed (monitors see them once, during execution)
        - Isolated from match EventBus (spectators don't receive them)

        Per SPEC-MONITOR §6.3 EI4 / §8.1, monitor exceptions are routed through
        the session logger (AgentDeckLogger) which was injected into console_bus
        during Console.__init__ to provide proper session/batch context.

        Args:
            event_type: Console event type (CONSOLE_*)
            payload: Event data payload
        """
        self.console_bus.emit(event_type, **payload)
