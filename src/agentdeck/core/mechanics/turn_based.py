"""
Turn-based game mechanic implementation.

Implements the canonical contract per:
- SPEC-GAME-MECHANIC-TURN-BASED v2.0.0 §4 (Public API)
- SPEC-GAME-MECHANIC-TURN-BASED v2.0.0 §5 (Invariants TL1-TL6)

Key components:
- TurnResult: Dataclass returned by game.run()
- TurnBasedGame: Base class for sequential turn games
- TurnLoop: Helper that executes deterministic turns using MatchRuntime

Critical invariants:
- TL1: Deterministic Setup - fork RNG before game.setup()
- TL2: Single Acting Player - get_current_player must return valid player
- TL3: Runtime Usage - MUST use runtime for all infrastructure
- TL4: Prompt/Response Capture - every decide() → record_turn()
- TL5: Error Propagation - annotate exceptions with context
- TL6: Replay Fidelity - attach phase_index/turn_number to events
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..base.game import Game
from ..event_factory import EventFactory
from ..game_event_emitter import GameEventEmitter
from ..state_adapter import StateAdapter
from ..types import ActionResult, Event, TurnContext

if TYPE_CHECKING:
    from ..base.player import Player
    from ..match_runtime import MatchRuntime
    from ..session import MatchContext
    from ..types import RandomGenerator


@dataclass
class TurnResult:
    """
    Solid return type used by TurnBasedGame.run().

    Lives in agentdeck.core.mechanics.turn_based per SPEC-GAME-MECHANIC-TURN-BASED.

    Attributes:
        final_state: JSON-serializable game state dict
        events: List of gameplay events emitted during match
        truncated_by_max_turns: True if match ended due to turn limit

    Example:
        >>> result = TurnResult(
        ...     final_state={"winner": "Alice", "health": {"Alice": 100, "Bob": 0}},
        ...     events=[...],
        ...     truncated_by_max_turns=False,
        ... )
    """

    final_state: Dict[str, Any]
    events: List[Event]
    truncated_by_max_turns: bool = False


class TurnBasedGame(Game):
    """
    Default base class for sequential turn games.

    Provides run() implementation that delegates to TurnLoop helper. Game authors
    SHOULD inherit from this class and MUST NOT override run() unless implementing
    a brand-new sequential mechanic.

    Hooks available for customization:
        - get_current_player(state, players, *, rng, match_context) → str
          Override for asymmetric turn order or dynamic scheduling
        - on_turn_start(turn_context) → None
          Optional hook invoked before each turn (default no-op)
        - on_turn_end(turn_context, mechanic_events) → None
          Optional hook invoked after each turn (default no-op)
        - on_action_parse_failure(...) → ParseFailurePolicy
          Defined in Game base class, used by runtime

    Example:
        >>> class MyGame(TurnBasedGame):
        ...     def setup(self, players):
        ...         return {"health": {p: 100 for p in players}}
        ...
        ...     def update(self, state, player, action, *, rng):
        ...         # Apply action
        ...         return state
        ...
        ...     def status(self, state):
        ...         # Check win condition
        ...         return GameStatus(...)
        ...
        ...     def get_view(self, state, player):
        ...         return state

    See SPEC-GAME-MECHANIC-TURN-BASED.md §4.1 for complete contract.
    """

    def run(
        self,
        runtime: MatchRuntime,
        players: List[Player],
    ) -> TurnResult:
        """
        Execute the turn-based mechanic using TurnLoop helper.

        This default implementation delegates to TurnLoop which handles:
        - Setup phase with RNG fork
        - Turn-by-turn execution with state management
        - Event emission via runtime
        - Parse failure handling via runtime
        - Validation via runtime

        Args:
            runtime: Per-match infrastructure context (created by Console)
            players: Ordered list of Player instances

        Returns:
            TurnResult with final_state, events, truncated_by_max_turns

        Note:
            Game authors MUST NOT override this method unless implementing a
            fundamentally new sequential mechanic. Use hooks (get_current_player,
            on_turn_start, on_turn_end) for customization.

        Example:
            >>> # Console creates runtime and calls game.run()
            >>> runtime = MatchRuntime(console=console, game=game, ...)
            >>> result = game.run(runtime, players)
            >>> assert isinstance(result, TurnResult)
            >>> assert result.final_state["winner"] in [p.name for p in players]
        """
        return TurnLoop(self, runtime, players).run()

    def get_current_player(
        self,
        state: Dict[str, Any],
        player_names: List[str],
        *,
        rng: RandomGenerator,
        match_context: MatchContext,
    ) -> str:
        """
        Return acting player name for the next turn (defaults to round-robin).

        Override for custom turn order logic (auction bidding, phase-based rotation,
        dynamic initiatives).

        Args:
            state: Current canonical game state
            player_names: Ordered list of player names
            rng: Mechanic RNG fork (for deterministic tie-breaking)
            match_context: Match context (match_id, previous results, etc.)

        Returns:
            Player name who should act next (MUST be from player_names list)

        Raises:
            ValueError: If returned name not in player_names (TurnLoop validates)

        Default Implementation:
            Round-robin: players[(first_player_idx + turn_number - 1) % len(players)]

        Override Examples:
            - Auction: return state["next_bidder"]
            - Phase-based: return state["phase_leader"] if state["phase"] == "bidding" else ...
            - State-dependent: Use rng to break ties deterministically

        See SPEC-GAME.md §4 get_current_player for complete contract.
        """
        # Default round-robin implementation
        turn_number = state.get("_turn_count", 1)
        first_player_idx = state.get("_first_player_idx", 0)
        current_idx = (first_player_idx + turn_number - 1) % len(player_names)
        return player_names[current_idx]

    def on_turn_start(self, turn_context: TurnContext) -> None:
        """
        Optional hook invoked before each turn (default no-op).

        Games MAY override to perform custom logic before turn execution
        (e.g., phase transitions, resource generation, event triggers).

        Args:
            turn_context: Immutable turn metadata (turn_number, player, timestamps, etc.)

        Example:
            >>> def on_turn_start(self, turn_context):
            ...     if turn_context.turn_number % 5 == 0:
            ...         self.emit_event("resource_generation", player=turn_context.player_name)
        """
        pass  # Default no-op

    def on_turn_end(
        self,
        turn_context: TurnContext,
        mechanic_events: List[Event],
    ) -> None:
        """
        Optional hook invoked after each turn (default no-op).

        Games MAY override to perform custom logic after turn execution
        (e.g., end-of-turn effects, cleanup, state transitions).

        Args:
            turn_context: Immutable turn metadata
            mechanic_events: Events emitted during this turn

        Example:
            >>> def on_turn_end(self, turn_context, mechanic_events):
            ...     # Trigger end-of-turn damage
            ...     if turn_context.turn_number > 10:
            ...         self.emit_event("poison_damage", player=turn_context.player_name)
        """
        pass  # Default no-op


class TurnLoop:
    """
    Execute the canonical turn-based game flow using MatchRuntime.

    This helper is used by TurnBasedGame.run() to execute sequential turns.
    It uses MatchRuntime as the exclusive gateway for all infrastructure
    interactions (events, recorder, RNG, parse failures, validation, logging).

    Example usage (from TurnBasedGame.run):
        >>> from .mechanics.turn_based import TurnLoop, TurnResult
        >>> def run(self, runtime, players):
        ...     return TurnLoop(self, runtime, players).run()

    See SPEC-GAME-MECHANIC-TURN-BASED.md §4.2 for complete contract.
    """

    def __init__(
        self,
        game: Game,
        runtime: MatchRuntime,
        players: List[Player],
    ) -> None:
        """
        Initialize TurnLoop with game, runtime, and players.

        Args:
            game: Game instance (provides setup, update, status, get_view, get_current_player)
            runtime: MatchRuntime instance (provides infrastructure: events, recorder, RNG, etc.)
            players: Ordered list of Player instances

        Note:
            TurnLoop uses runtime as exclusive gateway per TL3 invariant.
        """
        self.game = game
        self.runtime = runtime
        self.players = players
        self.player_names = [p.name for p in players]
        self.event_factory = EventFactory(runtime.match_id)

    def run(self) -> TurnResult:
        """
        Execute turn-based game flow with MatchRuntime infrastructure.

        Steps (per SPEC-GAME-MECHANIC-TURN-BASED §4.2):
            1. Fork RNG and call game.setup() (TL1)
            2. Validate initial state via runtime
            3. Select first player and emit event
            4. Loop until game.status().is_over or max_turns:
                a. Get current player via game.get_current_player()
                b. Build TurnContext
                c. Get player view and call player.decide()
                d. Apply action via game.update()
                e. Emit GAMEPLAY event via runtime
                f. Record turn via runtime
                g. Emit custom events from game.get_events()
                h. Validate state via runtime
                i. Check game status
            5. Return TurnResult

        Returns:
            TurnResult with (final_state, events, truncated_by_max_turns)

        Invariants Enforced:
            - TL1: Fork RNG before setup
            - TL2: Validate get_current_player returns valid player
            - TL3: Use runtime for all infrastructure
            - TL4: Record every turn via runtime.record_turn()
            - TL5: Annotate exceptions with match_context
            - TL6: Attach phase_index/turn_number to events
        """
        from ..types import MatchForfeitedError

        # Make factory and emitter available for custom game hooks
        # Note: This maintains backward compatibility with games using emit_event()
        emitter = GameEventEmitter(
            self.runtime._console.event_bus,  # Access via runtime's console
            self.runtime.match_id,
        )
        self.game.bind_event_factory(self.event_factory)
        self.game.bind_event_emitter(emitter)

        state: Dict[str, Any] = {}
        try:
            state = (
                copy.deepcopy(self.runtime.initial_state)
                if getattr(self.runtime, "initial_state", None) is not None
                else None
            ) or {}

            if not state:
                # TL1: Deterministic Setup - fork RNG before game.setup()
                setup_rng = self.runtime.fork_rng("setup")
                state = self.game.setup(self.player_names, seed=setup_rng.seed)

                # Type check: setup() must return a dict
                if not isinstance(state, dict):
                    raise TypeError(
                        f"{self.game.__class__.__name__}.setup() must return a dict, "
                        f"got {type(state).__name__}"
                    )

            state.setdefault("_turn_count", 1)
            events: List[Event] = []

            # Validate initial state via runtime (TL3)
            self.runtime.validate_state(state)

            # Select first player (emits event via runtime)
            self._select_first_player(state)

            # Main turn loop
            truncated = False
            while state["_turn_count"] <= self.runtime.max_turns:
                # Check if game is over
                try:
                    status = self.game.status(state)
                except Exception as e:
                    turn_num = state.get("_turn_count", "unknown")
                    raise RuntimeError(
                        f"Error in {self.game.__class__.__name__}.status() at turn {turn_num}"
                    ) from e

                if status.is_over:
                    break

                # Execute turn and collect events
                turn_state = self._execute_turn(state)
                state = turn_state.final_state
                events.extend(turn_state.events)
            else:
                # Loop exited because we hit max_turns (not via break)
                truncated = True
                if state["_turn_count"] > self.runtime.max_turns:
                    state["_turn_count"] = self.runtime.max_turns

            return TurnResult(
                final_state=state,
                events=events,
                truncated_by_max_turns=truncated,
            )
        except MatchForfeitedError as forfeit_error:
            # Allow game to enrich terminal state before Console emits MATCH_END
            forfeit_state = getattr(forfeit_error, "forfeit_state", copy.deepcopy(state))
            updated_state = self.game.on_match_forfeited(
                forfeit_state,
                forfeit_error.player_name,
                forfeit_error.parse_error,
                forfeit_error.policy,
            )
            forfeit_error.forfeit_state = updated_state
            raise
        finally:
            # TL6: Restore bindings even if mechanics raise (MR6)
            self.game.bind_event_factory(None)
            self.game.bind_event_emitter(None)
            emitter.clear_phase_index()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_first_player(self, state: Dict[str, Any]) -> None:
        """
        Select first player using RNG fork and emit event via runtime.

        Updates state with _first_player_idx for round-robin sequencing.
        Emits FIRST_PLAYER_SELECTED event via runtime.
        """
        # Fork RNG for first player selection (TL1)
        first_player_rng = self.runtime.fork_rng("first_player_selection")
        first_idx = first_player_rng.randint(0, len(self.players) - 1)
        state["_first_player_idx"] = first_idx

        # Store in console for metadata (accessed via runtime's console reference)
        self.runtime._console.first_player_info = {
            "name": self.players[first_idx].name,
            "index": first_idx,
        }

        # Log via runtime (TL3)
        from ..types import LogLevel

        self.runtime.log(
            f"First player selected: {self.players[first_idx].name} (index {first_idx})",
            level=LogLevel.INFO,
        )

    def _execute_turn(self, state: Dict[str, Any]) -> TurnResult:
        """
        Execute a single turn using runtime infrastructure.

        Steps:
            1. Get current player via game.get_current_player() with RNG
            2. Build TurnContext
            3. Get player view and call player.decide()
            4. Apply action via game.update() with RNG fork
            5. Emit GAMEPLAY event via runtime
            6. Record turn via runtime.record_turn()
            7. Emit custom game events via runtime
            8. Validate state via runtime
            9. Check status and increment turn counter

        Returns:
            TurnResult with (final_state, events, truncated=False)
        """
        adapter = StateAdapter(state)

        turn_number = adapter.before.get("_turn_count", 1)
        turn_index = turn_number - 1

        # Fork RNG for this turn (TL1, TL3)
        turn_rng = self.runtime.fork_rng(f"turn_{turn_number}")

        # TL2: Get current player and validate
        current_player_name = self.game.get_current_player(
            state,
            self.player_names,
            rng=turn_rng,
            match_context=self.runtime,
        )

        # Set phase index for event emitter
        if self.game.event_emitter is not None:
            self.game.event_emitter.set_phase_index(turn_index)

        # Find player object (TL2: validate player name)
        player_obj = None
        for p in self.players:
            if p.name == current_player_name:
                player_obj = p
                break

        if player_obj is None:
            raise RuntimeError(
                f"Game {self.game.__class__.__name__}.get_current_player() returned "
                f"'{current_player_name}' which is not in the player list: {self.player_names}"
            )

        turn_start = time.time()

        # Get player view (pass copy to prevent get_view from mutating snapshot)
        state_copy_for_view = copy.deepcopy(adapter.before)
        try:
            player_view = self.game.get_view(state_copy_for_view, current_player_name)
        except Exception as e:
            raise RuntimeError(
                f"Error in {self.game.__class__.__name__}.get_view() for player {current_player_name} "
                f"during turn {turn_number}"
            ) from e

        # Build TurnContext (TL6)
        turn_rng_label = f"turn-{turn_number}-{current_player_name}"
        turn_ctx = TurnContext(
            match_id=self.runtime.match_id,
            turn_number=turn_number,
            turn_index=turn_index,
            player=current_player_name,
            started_at=turn_start,
            duration=0.0,
            rng_seed=turn_rng.seed,
            rng_label=turn_rng_label,
        )

        # Get player action (via console helper - maintains existing interface)
        # Wrap in try/except to capture state before abort/forfeit (PF4)
        from ..types import MatchAbortedError, MatchForfeitedError

        try:
            action = self.runtime._console.get_player_action(
                player_view,
                player_obj,
                self.game,
                turn_context=turn_ctx,
            )
        except (MatchAbortedError, MatchForfeitedError) as e:
            # Copy current state into error before re-raising (PF4 compliance)
            # This ensures Console can emit MATCH_END with real final_state
            if isinstance(e, MatchAbortedError):
                e.abort_state = copy.deepcopy(state)
            else:  # MatchForfeitedError
                e.forfeit_state = copy.deepcopy(state)
            raise

        # Apply action via game.update with RNG fork
        updated_state = self._apply_action(adapter, current_player_name, action, turn_rng)
        final_state = adapter.commit(updated_state)

        # Update turn context duration
        turn_duration = time.time() - turn_start
        turn_ctx.duration = turn_duration

        # Log turn via console logger (maintains existing interface)
        if self.runtime._console.logger:
            self.runtime._console.logger.turn(
                turn_number=turn_number,
                player=current_player_name,
                action=action.action,
                reasoning=action.reasoning,
                state_before=adapter.before,
                state_after=final_state,
                duration=turn_duration,
                usage_info=action.metadata.get("usage_info") if action.metadata else None,
            )

        # Attach turn context to action metadata
        action.metadata = action.metadata or {}
        action.metadata["turn_context"] = turn_ctx.to_dict()

        # TL4: Record turn via runtime - emit GAMEPLAY event with PM1-PM6 metadata
        # Per SPEC-GAME-MECHANIC-TURN-BASED v2.0.0 TL4 and SPEC-MATCH-RUNTIME §4.3,
        # runtime.record_turn() automatically extracts PM metadata from ActionResult
        # (raw_response, controller metadata, usage_info) and emits complete GAMEPLAY event.
        self.runtime.record_turn(
            player=current_player_name,
            state_before=adapter.before,
            state_after=final_state,
            action=action,
            turn_context=turn_ctx,
        )

        # Get custom events from game (TL6)
        custom_events = self.game.get_events(adapter.before, current_player_name, action)
        turn_events: List[Event] = []
        if custom_events:
            turn_events.extend(custom_events)

        # Emit custom events via runtime (TL3)
        for event in custom_events or []:
            self.runtime.emit_event(event.event_type, **event.data)

        # Check game status
        try:
            status = self.game.status(final_state)
        except Exception as e:
            raise RuntimeError(
                f"Error in {self.game.__class__.__name__}.status() after turn {turn_number}"
            ) from e

        # Increment turn counter if game not over
        if not status.is_over:
            final_state["_turn_count"] = adapter.before.get("_turn_count", 1) + 1

        # Clear phase index
        if self.game.event_emitter is not None:
            self.game.event_emitter.clear_phase_index()

        return TurnResult(final_state=final_state, events=turn_events)

    def _apply_action(
        self,
        adapter: StateAdapter,
        player: str,
        action: ActionResult,
        turn_rng,
    ) -> Optional[Dict[str, Any]]:
        """
        Apply action via game.update() and validate state via runtime.

        Args:
            adapter: StateAdapter tracking before/working/after states
            player: Acting player name
            action: Parsed action result
            turn_rng: Deterministic RNG fork for this turn

        Returns:
            Updated state dict (or None if game mutated in-place)

        Raises:
            RuntimeError: If game.update() fails
            TypeError: If game.update() returns wrong type
            ValueError: If game.validate_state() fails
        """
        turn_num = adapter.before.get("_turn_count", "unknown")

        # Call game.update() with error context
        try:
            updated_state = self.game.update(
                adapter.working,
                player,
                action,
                rng=turn_rng,
            )
        except Exception as e:
            raise RuntimeError(
                f"Error in {self.game.__class__.__name__}.update() during turn {turn_num}. "
                f"Player: {player}, Action: {action.action}"
            ) from e

        # Type check: update() must return dict or None (in-place mutation)
        if updated_state is not None and not isinstance(updated_state, dict):
            raise TypeError(
                f"{self.game.__class__.__name__}.update() must return a dict or None, "
                f"got {type(updated_state).__name__}"
            )

        # TL3: Validate state via runtime
        state_to_validate = updated_state if updated_state is not None else adapter.working
        self.runtime.validate_state(state_to_validate)

        return updated_state


__all__ = ["TurnResult", "TurnBasedGame", "TurnLoop"]
