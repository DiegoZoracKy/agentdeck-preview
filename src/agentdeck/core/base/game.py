"""
Game base class for AgentDeck v1.0.0 framework.

Implements the canonical contract per:
- SPEC-GAME v0.5.0 §4 (Public API)
- SPEC-GAME v0.5.0 §5 (Invariants & Guarantees)
- SPEC.md §5.5

Key responsibilities:
- Own complete game state machine (setup → update → status)
- Control all narrative/instructional content via get_view()
- Emit domain events through GameEventEmitter
- Provide deterministic outputs using Console-provided RNG
- Expose filtered per-player views without leaking hidden information
- Provide default handshake template for player onboarding

Critical invariants:
- GS1-GS4: State must be JSON-serializable dict
- DT1-DT3: Deterministic behavior (use rng, pure get_view)
- G15-G16: Games own narrative (Console never delivers instructions)
- OB1-OB3: Events JSON-serializable, hide hidden info in views
- V1-V2: Validation side-effect free, raises on violations
- HT1-HT3: Default handshake template mandatory
- IV1-IV5: Optional information_level support
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..types import ActionResult, Event, GameStatus, RandomGenerator

if TYPE_CHECKING:
    from ..event_factory import EventFactory
    from ..game_event_emitter import GameEventEmitter
    from ..types import ActionParseError, HandshakeResult, ParseFailurePolicy


class Game(ABC):
    """
    Abstract base for all games (per SPEC-GAME v0.5.0).

    Games own state machine, rules, and narrative. Console orchestrates
    without interpreting mechanics.

    Lifecycle:
        1. Console → game.setup(players) → canonical game_state
        2. Loop: Console → game.update(state, player, action, rng=fork) → new_state
        3. Console → game.status(state) → GameStatus(is_over, winner)
        4. Console → game.get_view(state, player) → filtered view

    Example minimal game:
        >>> class CoinFlipGame(Game):
        ...     @property
        ...     def instructions(self) -> str:
        ...         return "Guess heads or tails to win."
        ...
        ...     @property
        ...     def allowed_actions(self) -> List[str]:
        ...         return ["HEADS", "TAILS"]
        ...
        ...     @property
        ...     def default_handshake_template(self) -> str:
        ...         return "{game_instructions}\\n\\nRespond 'OK' to begin."
        ...
        ...     def setup(self, players: List[str]) -> Dict[str, Any]:
        ...         return {"round": 0, "coin": None, "winner": None}
        ...
        ...     def update(self, game_state, player, action, *, rng):
        ...         state = dict(game_state)  # Copy for clarity
        ...         state["round"] += 1
        ...         state["coin"] = rng.choice(["heads", "tails"])
        ...         if action.action.lower() == state["coin"]:
        ...             state["winner"] = player
        ...         return state
        ...
        ...     def status(self, game_state) -> GameStatus:
        ...         is_over = game_state["winner"] is not None
        ...         return GameStatus(is_over=is_over, winner=game_state["winner"])
        ...
        ...     def get_view(self, game_state, player):
        ...         return game_state  # Perfect information

    See also:
        - FixedDamageGame: Reference implementation with information_level support
        - SPEC-GAME.md §8: Complete examples
    """

    def __init__(self) -> None:
        """
        Initialize game instance.

        Note: Console will call bind_event_factory() and bind_event_emitter()
              before gameplay starts to enable event creation and emission.
        """
        self.event_factory: Optional[EventFactory] = None
        self.event_emitter: Optional[GameEventEmitter] = None

    # ========================================================================
    # Required Abstract Properties
    # ========================================================================

    @property
    @abstractmethod
    def instructions(self) -> str:
        """
        Reference-only description of rules and objectives.

        Returns:
            Plain string for docs/lobby UIs (may be empty)

        Note: Console never reads or delivers this property.
              Games decide when to surface narrative through state/views.

        Example:
            >>> @property
            >>> def instructions(self) -> str:
            ...     return "Fixed Damage Combat: Attack or use potions to survive."
        """

    @property
    @abstractmethod
    def allowed_actions(self) -> List[str]:
        """
        Canonical list of valid action strings for this game.

        Returns:
            List of action identifiers (e.g., ["ATTACK", "POTION", "FLEE"])

        Usage: Console binds this to action controllers during match setup
               via controller.bind_game(game).

        Example:
            >>> @property
            >>> def allowed_actions(self) -> List[str]:
            ...     return ["ATTACK", "POTION"]
        """

    @property
    @abstractmethod
    def default_handshake_template(self) -> str:
        """
        Template string for player handshake phase (per SPEC-GAME §4 HT1).

        Returns:
            Template containing game instructions, rules, response format

        Rationale: Front-loading instructions in handshake reduces token cost
                   in turn prompts (LLM remembers via conversation history).

        Example:
            >>> @property
            >>> def default_handshake_template(self) -> str:
            ...     return "{game_instructions}\\n\\nRespond 'OK' when ready."

        Placeholders:
            - {game_instructions}: Replaced with self.instructions by PromptBuilder
            - {strategy}: Player-specific strategy hint (if provided)
            - {handshake_controller_format}: Controller's response requirements
        """

    # ========================================================================
    # Required Abstract Methods
    # ========================================================================

    @abstractmethod
    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        """
        Build canonical game_state for match start (per SPEC-GAME §4 GS1, SPEC.md §5.5).

        Args:
            players: Ordered player roster negotiated by Console
            seed: Deterministic seed for reproducibility (per SPEC.md §5.5 line 122)

        Returns:
            JSON-serializable dict containing all data for subsequent turns

        Requirements (GS1, DT2):
            - MUST return JSON-serializable dict (use json.dumps to verify)
            - MUST contain every key required for gameplay and observability
            - MUST use seed for any randomness during initialization (determinism)

        Example:
            >>> def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
            ...     return {
            ...         "health": {p: 100 for p in players},
            ...         "potions": {p: 3 for p in players},
            ...         "turn": 1,
            ...         "seed": seed  # Optional: store for debugging
            ...     }

        Note: Console calls validate_state(state) after setup() completes.
        """

    @abstractmethod
    def update(
        self, game_state: Dict[str, Any], player: str, action: ActionResult, *, rng: RandomGenerator
    ) -> Dict[str, Any]:
        """
        Apply action to evolve game state (per SPEC-GAME §4 GS2, DT1).

        Args:
            game_state: Current canonical state
            player: Acting player name
            action: Parsed action from ActionController
            rng: Deterministic RNG fork (MUST use this for ALL randomness)

        Returns:
            Updated JSON-serializable dict (canonical state after action)

        Requirements (GS2, DT1):
            - MUST return dict representing new canonical game_state
            - In-place mutation allowed, but returned object MUST be authoritative
            - MUST use rng for ALL randomness (not global random module)
            - SHOULD raise ValueError for invalid actions (fail-fast)

        Mutation patterns (both valid per GS2):
            # In-place mutation (efficient):
            >>> def update(self, game_state, player, action, *, rng):
            ...     game_state["health"][player] -= 20
            ...     game_state["turn"] += 1
            ...     return game_state

            # Defensive copy (clearer intent):
            >>> def update(self, game_state, player, action, *, rng):
            ...     state = dict(game_state)  # Shallow copy
            ...     state["health"][player] -= 20
            ...     state["turn"] += 1
            ...     return state

        Error handling:
            >>> if action.action not in self.allowed_actions:
            ...     raise ValueError(f"Invalid action: {action.action}")

        Note: Console calls validate_state(new_state) after update() completes.
        """

    @abstractmethod
    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        """
        Evaluate whether play continues and determine winner.

        Args:
            game_state: Latest canonical state

        Returns:
            GameStatus(is_over: bool, winner: Optional[str])

        Requirements:
            - MUST set winner=None for draws or ongoing games
            - MUST freeze is_over=True once terminal

        Example:
            >>> def status(self, game_state) -> GameStatus:
            ...     alive = [p for p, hp in game_state["health"].items() if hp > 0]
            ...     if len(alive) == 1:
            ...         return GameStatus(is_over=True, winner=alive[0])
            ...     elif len(alive) == 0:
            ...         return GameStatus(is_over=True, winner=None)  # Draw
            ...     else:
            ...         return GameStatus(is_over=False, winner=None)
        """

    @abstractmethod
    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        """
        Produce filtered view for specific player (per SPEC-GAME §4 G15, OB3).

        Args:
            game_state: Canonical state (full truth)
            player: Requesting player identity

        Returns:
            JSON-serializable dict consumed by renderers and prompt builders

        Requirements (G15, OB3, DT3):
            - MUST avoid mutating supplied game_state (use deep copy if enriching)
            - MUST respect information_level configuration (if supported)
            - MUST hide hidden-information content for non-owning players
            - SHOULD include narrative/tutorial content when required
            - MUST be pure projection (repeated calls = identical outputs)

        Example (perfect information):
            >>> def get_view(self, game_state, player):
            ...     return game_state  # No filtering needed

        Example (hidden information with information_level):
            >>> def get_view(self, game_state, player):
            ...     view = {
            ...         "health": {player: game_state["health"][player]},
            ...         "potions": {player: game_state["potions"][player]},
            ...         "turn": game_state["turn"]
            ...     }
            ...     if self.information_level == "full":
            ...         # Show all player stats
            ...         view["health"] = game_state["health"]
            ...         view["potions"] = game_state["potions"]
            ...     return view

        Example (narrative injection):
            >>> def get_view(self, game_state, player):
            ...     view = dict(game_state)
            ...     if game_state["tutorial_phase"] < 3:
            ...         view["tutorial"] = self.tutorial_steps[game_state["tutorial_phase"]]
            ...     return view
        """

    # ========================================================================
    # Optional Hooks (provide defaults)
    # ========================================================================

    def validate_state(self, game_state: Dict[str, Any]) -> None:
        """
        Optional guardrail invoked after setup() and every update() (per V1-V2).

        Args:
            game_state: State to validate

        Raises:
            ValueError: When invariants break (with descriptive message)

        Requirements (V1, V2):
            - MUST raise ValueError for invariant violations
            - MUST NOT mutate provided game_state (side-effect free)

        Default: No-op (games opt in for stronger integrity checks)

        Example:
            >>> def validate_state(self, game_state):
            ...     if "health" not in game_state:
            ...         raise ValueError("Missing required key 'health'")
            ...     for player, hp in game_state["health"].items():
            ...         if hp < 0:
            ...             raise ValueError(f"Invalid health for {player}: {hp}")
        """
        pass  # Default: no validation

    def on_action_parse_failure(
        self,
        player_name: str,
        error: "ActionParseError",  # Forward reference
        turn_context: "TurnContext",  # Forward reference
    ) -> "ParseFailurePolicy":  # Forward reference
        """
        Optional hook to determine policy when action parsing fails (per SPEC-GAME v0.6.0 §4).

        Per SPEC-GAME v0.6.0 PF1-PF4, games return a ParseFailurePolicy value instructing
        Console how to handle the failure. Default implementation returns FORFEIT to allow
        quantifying instruction adherence rates while ensuring matches complete.

        Args:
            player_name: Name of the player whose action failed to parse
            error: ActionParseError with embedded ParseResult (candidates, metadata, reasoning)
            turn_context: Immutable turn context snapshot (turn_number, etc.)

        Returns:
            ParseFailurePolicy enum value:
                - FORFEIT: Declare failing player as loser (default - allows research metrics)
                - SKIP_TURN: Consume failing player's turn and continue
                - ABORT_MATCH: Terminate match immediately
                - RETRY_ONCE: Console re-issues prompt exactly once (deterministic)

        Requirements (PF2-PF4):
            - MUST be deterministic given identical game state/inputs
            - MUST NOT mutate game state (Console applies policy)
            - MAY inspect error.parse_result.metadata for failure context

        Example custom policy:
            >>> def on_action_parse_failure(self, player_name, error, turn_context):
            ...     # Give one retry, then forfeit
            ...     if turn_context.turn_number == 1:
            ...         return ParseFailurePolicy.RETRY_ONCE
            ...     return ParseFailurePolicy.FORFEIT
        """
        from ..types import ParseFailurePolicy

        return ParseFailurePolicy.FORFEIT  # Default: forfeit to enable format adherence metrics

    def get_events(
        self, game_state: Dict[str, Any], player: str, action: ActionResult
    ) -> List[Event]:
        """
        Optional hook to publish additional observability events (per OB1).

        Returns:
            List of domain events (JSON-serializable) to emit via emit_event

        Usage: When game can derive richer analytics after an action
               (e.g., scoring breakdowns, milestones reached)

        Default: Return empty list (no additional events)

        Example:
            >>> def get_events(self, game_state, player, action):
            ...     events = []
            ...     if game_state["health"][player] < 20:
            ...         events.append(Event(
            ...             type="low_health_warning",
            ...             data={"player": player, "health": game_state["health"][player]},
            ...             context={},
            ...             timestamp=time.time()
            ...         ))
            ...     return events
        """
        return []

    def get_player_order(
        self,
        players: List,  # List[Player] - avoiding circular import
        *,
        rng: RandomGenerator,
        match_context: Any,  # MatchContext - avoiding circular import
    ) -> Optional[List]:
        """
        Override to provide custom player ordering logic (per SPEC-GAME §4 PO1-PO4).

        Default: Returns None (Console applies Fisher-Yates shuffle for fairness).

        Args:
            players: Original player list from Console.run()
            rng: Match-specific RandomGenerator for reproducibility
            match_context: MatchContext with seed, match_id, previous_match_result

        Returns:
            - None: Console applies default fair ordering (Fisher-Yates shuffle)
            - List[Player]: Custom ordering (Console validates and uses as-is)

        Requirements (PO2, PO3):
            - If returning custom list, MUST include exact same Player instances
            - MUST use provided rng for any random decisions
            - MUST NOT create own RandomGenerator instance

        When to Override:
            - Auction/bidding systems (highest bidder goes first)
            - Asymmetric roles (attacker vs defender assignment)
            - State-dependent ordering (previous winner advantage, tournament seeding)
            - Fixed role assignments (player order matters for game balance)

        Default: Returns None (recommended for 99% of games)

        Example (auction-based ordering):
            >>> def get_player_order(self, players, *, rng, match_context):
            ...     # Run pre-match auction with provided RNG
            ...     bids = {p: self._auction_bid(p, rng) for p in players}
            ...     # Highest bidder goes first
            ...     return sorted(players, key=lambda p: bids[p], reverse=True)

        Example (state-dependent ordering):
            >>> def get_player_order(self, players, *, rng, match_context):
            ...     # First match or draw: Console randomizes
            ...     if match_context.previous_match_result is None:
            ...         return None  # Let Console randomize
            ...
            ...     prev_result = match_context.previous_match_result
            ...     if prev_result.winner:
            ...         # Winner of previous match goes first
            ...         winner_player = next(p for p in players if p.name == prev_result.winner)
            ...         other_players = [p for p in players if p.name != prev_result.winner]
            ...         return [winner_player] + other_players
            ...
            ...     return None  # Draw: let Console randomize

        Example (fixed asymmetric roles):
            >>> def get_player_order(self, players, *, rng, match_context):
            ...     # Player 0 = Attacker, Player 1 = Defender (roles matter)
            ...     return players  # Use order as provided to Console.run()

        Note: Console validates returned list (same players, no duplicates) and
              raises ValueError on mismatch (H4).
        """
        return None  # Default: no preference, Console applies fairness

    def on_match_forfeited(
        self,
        game_state: Dict[str, Any],
        player_name: str,
        error: "ActionParseError",  # Forward reference
        policy: "ParseFailurePolicy",  # Forward reference
    ) -> Dict[str, Any]:
        """
        Hook invoked after a parse failure is converted into a forfeit decision.

        Games may enrich terminal state (e.g., set resolution_status="invalid_response")
        or emit diagnostic events. Default is a no-op that returns the provided state
        unchanged to preserve backward compatibility.
        """
        return game_state

    def requires_conclusion(self, game_state: Dict[str, Any]) -> Optional[str]:
        """
        Optional hook to request a conclusion phase for a specific player.

        Return the player name that should provide a conclusion, or None to skip.
        Default skips the conclusion phase (no additional LLM calls).
        """
        return None

    def get_conclusion_prompt(self, player: str, game_state: Dict[str, Any]) -> str:
        """
        Build a conclusion prompt for the specified player.

        Default provides a generic reflection prompt; games override to embed
        domain-specific instructions or JSON shapes.
        """
        return "Provide a brief reflection on the match outcome."

    def parse_conclusion(self, player: str, response: Optional[str]) -> Dict[str, Any]:
        """
        Parse the conclusion response into structured data.

        Default attempts JSON parsing; if response is empty/None, returns {}.
        """
        import json

        if response in (None, ""):
            return {}
        return json.loads(response)

    def on_conclusion_received(
        self, game_state: Dict[str, Any], player: str, conclusion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Hook to persist parsed conclusion data into final state.

        Default returns game_state unchanged (backward compatible).
        """
        return game_state

    def on_handshake_complete(
        self, game_state: Dict[str, Any], player: str, handshake_result: "HandshakeResult"
    ) -> Dict[str, Any]:
        """
        Hook invoked after successful handshake validation.

        Games may extract metadata (e.g., personas, strategies) and store it in state.
        Default returns the state unchanged.
        """
        return game_state

    # ========================================================================
    # Infrastructure Hooks (Console integration)
    # ========================================================================

    def bind_event_factory(self, factory: Optional[EventFactory]) -> None:
        """
        Provide the match-scoped event factory to this game instance.

        Called by TurnLoop before gameplay starts. Games can use this to create
        structured events via self.event_factory.custom().

        Args:
            factory: EventFactory wrapper for creating events

        Note: Framework hook - game authors should not call directly.
        """
        self.event_factory = factory

    def bind_event_emitter(self, emitter: Optional[GameEventEmitter]) -> None:
        """
        Attach match-scoped event emitter to this game instance (per OB2).

        Called by Console before gameplay starts. Games MUST NOT emit events
        before this is called.

        Args:
            emitter: GameEventEmitter wrapper around EventBus

        Note: Framework hook - game authors should not call directly.
        """
        self.event_emitter = emitter

    def emit_event(self, event_type: str, **payload: Any) -> None:
        """
        Emit domain event through bound GameEventEmitter.

        Args:
            event_type: Snake_case event name (e.g., "card_drawn", "bid_placed")
            **payload: JSON-serializable event data

        Requirements (OB1, OB2):
            - Payload MUST be JSON-serializable
            - MUST NOT emit structural gameplay events (Console handles those)
            - Only works after bind_event_emitter() called

        Example:
            >>> def update(self, game_state, player, action, *, rng):
            ...     # ... apply action ...
            ...     if game_state["score"][player] > 100:
            ...         self.emit_event("milestone_reached",
            ...                        player=player,
            ...                        score=game_state["score"][player])
            ...     return game_state
        """
        if self.event_emitter is not None:
            self.event_emitter.emit(event_type, **payload)

    # ========================================================================
    # Mechanic Execution (SPEC-GAME v0.6.0 - Game Mechanics Pattern)
    # ========================================================================

    @abstractmethod
    def run(self, runtime, players):
        """
        Execute the mechanic using MatchRuntime infrastructure (per SPEC-GAME v0.6.0 ME1-ME5).

        This is the only entry point Console uses to run a match. Games own execution
        logic (sequential, simultaneous, realtime) while Console remains mechanic-agnostic.

        Args:
            runtime: MatchRuntime - Per-match infrastructure context (created by Console)
            players: List[Player] - Ordered player instances

        Returns:
            TurnResult: Dataclass with (final_state, events, truncated_by_max_turns)
                       Helpers MAY return tuple with same structure for compatibility

        Requirements (ME1-ME5):
            - ME1: Use runtime as exclusive gateway (emit_event, record_turn, handle_parse_failure, fork_rng)
            - ME2: Don't override unless implementing new mechanic (use TurnBasedGame for sequential)
            - ME3: Every decision → runtime.record_turn(), every action → GAMEPLAY event via runtime
            - ME4: Return JSON-serializable final_state, signal truncation boolean
            - ME5: Propagate exceptions with context (runtime attaches match_context)

        Default Implementations:
            - TurnBasedGame: Delegates to TurnLoop helper for sequential turns
            - SimultaneousGame: (future) Collects parallel actions per phase
            - RealtimeGame: (future) Async event loop with timeouts

        Example (custom mechanic skeleton):
            >>> from ..mechanics.turn_based import TurnResult
            >>> def run(self, runtime, players):
            ...     state = self.setup([p.name for p in players])
            ...     while not self.status(state).is_over:
            ...         # Custom execution logic using runtime
            ...         actions = self._collect_actions(runtime, players, state)
            ...         state = self._resolve(state, actions, rng=runtime.fork_rng("round"))
            ...         runtime.validate_state(state)
            ...     return TurnResult(final_state=state, events=[], truncated_by_max_turns=False)

        See:
            - SPEC-GAME.md §4 run() for complete contract
            - SPEC-GAME-MECHANIC-TURN-BASED.md for turn-based implementation
            - SPEC-MATCH-RUNTIME.md for runtime API
        """

    def get_current_player(
        self,
        game_state: Dict[str, Any],
        players: List[str],
        *,
        rng,
        match_context,
    ) -> str:
        """
        Determine which player should act on the current turn (per SPEC-GAME v0.6.0).

        Override for custom turn order logic (auction bidding, phase-based rotation,
        dynamic initiatives).

        Args:
            game_state: Current canonical game state
            players: Ordered list of player names
            rng: Mechanic RNG fork (for deterministic tie-breaking)
            match_context: Match context (match_id, previous results, etc.)

        Returns:
            Name of the player who should act next (MUST be from players list)

        Default Implementation:
            Round-robin based on _first_player_idx and _turn_count from game_state.
            Formula: players[(_first_player_idx + _turn_count - 1) % len(players)]

        Override Examples:
            - Auction: return state["next_bidder"]
            - Phase-based: return state["phase_leader"] if state["phase"] == "bidding" else ...
            - State-dependent: Use rng to break ties deterministically
            - Previous winner: Use match_context.previous_match_result for advantage

        Requirements:
            - MUST return a name from the players list
            - MUST be deterministic (same state → same player)
            - MUST use provided rng for any random decisions (maintains reproducibility)
            - MAY use match_context.previous_match_result for state-based ordering

        Example (custom turn order):
            >>> def get_current_player(self, game_state, players, *, rng, match_context):
            ...     # Auction: highest bidder goes first
            ...     if "next_bidder" in game_state:
            ...         return game_state["next_bidder"]
            ...     # Use rng for deterministic tie-breaking
            ...     if game_state.get("tied_players"):
            ...         return rng.choice(game_state["tied_players"])
            ...     # Otherwise round-robin
            ...     return super().get_current_player(game_state, players, rng=rng, match_context=match_context)

        Note:
            TurnLoop (turn-based helper) validates returned player name and raises
            ValueError if not in players list.
        """
        first_player_idx = game_state.get("_first_player_idx", 0)
        turn_count = game_state.get("_turn_count", 1)
        current_idx = (first_player_idx + turn_count - 1) % len(players)
        return players[current_idx]
