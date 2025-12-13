"""
Core data types for AgentDeck v1.0.0 framework.

This module defines the foundational types used throughout AgentDeck:
- Event system types (Event, EventContext, EventType)
- Player interaction types (HandshakeResult, ActionResult)
- Game state types (GameStatus, MatchResult)
- Prompt composition types (LifecyclePhase, PromptBundle, TemplateError)
- Supporting infrastructure (TurnContext, RandomGenerator)

All types are designed for JSON serialization and replay compatibility.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, TypedDict

# ============================================================================
# Event System Types (SPEC-OBSERVABILITY v1.0.0 §4)
# ============================================================================


class EventType(Enum):
    """
    Standardized event types for the AgentDeck event system.

    Per SPEC-OBSERVABILITY v1.0.0 §3:
    - Lifecycle events: Emitted by Console/AgentDeck
    - Structural gameplay events: Emitted by execution helpers (TurnLoop)
    - Domain events: Custom game-specific events (emitted as strings, not enum)

    Event ordering per SPEC-CONSOLE §6.6 E1:
    SESSION_START → BATCH_START → PLAYER_HANDSHAKE_* → MATCH_START →
    GAMEPLAY → MATCH_END → PLAYER_CONCLUSION → BATCH_END → SESSION_END
    """

    # Session lifecycle events (SPEC-OBSERVABILITY §3.1)
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Batch lifecycle events (SPEC-OBSERVABILITY §3.1)
    BATCH_START = "batch_start"
    BATCH_END = "batch_end"

    # Match lifecycle events (SPEC-OBSERVABILITY §3.1)
    MATCH_START = "match_start"
    MATCH_END = "match_end"

    # Player lifecycle events (SPEC-OBSERVABILITY §3.1.1)
    PLAYER_HANDSHAKE_START = "player_handshake_start"
    PLAYER_HANDSHAKE_COMPLETE = "player_handshake_complete"
    PLAYER_HANDSHAKE_ABORT = "player_handshake_abort"
    PLAYER_ACTION_PARSE_FAILED = "player_action_parse_failed"  # v1.2.0: Parse failure event
    PLAYER_CONCLUSION = "player_conclusion"

    # Structural gameplay events (SPEC-OBSERVABILITY §3.2)
    GAMEPLAY = "gameplay"
    # DIALOGUE_TURN removed in schema v1.3 - prompt metadata embedded in lifecycle events

    # Console events (SPEC-MONITOR v1.0.0 §4.3)
    # Live, immediate events for system-level observation (not replayed)
    CONSOLE_BATCH_START = "console_batch_start"
    CONSOLE_BATCH_PROGRESS = "console_batch_progress"
    CONSOLE_WORKER_START = "console_worker_start"
    CONSOLE_WORKER_COMPLETE = "console_worker_complete"
    CONSOLE_WORKER_FAILED = "console_worker_failed"
    CONSOLE_BATCH_COMPLETE = "console_batch_complete"

    # Logging events
    LOG = "log"


class EventContext(TypedDict, total=False):
    """
    Context metadata envelope for all events.

    Per SPEC-OBSERVABILITY v1.0.0 §4.1, this TypedDict provides structured
    metadata that accompanies every Event object routed through EventBus.

    Field guarantees (SPEC-SPECTATOR §5.5 CA1-CA3):
    - CA1: session_id MUST be present (except early construction events)
    - CA2: match_id MUST be present during match execution (MATCH_START → MATCH_END)
    - CA3: phase_index MUST be present during GAMEPLAY events; MAY be absent for
           handshake/conclusion events

    All fields are optional (total=False) to support partial context in early
    lifecycle events and legacy recordings.

    Time semantics:
    - timestamp: Wall-clock time for logging (time.time())
    - monotonic_time: Monotonic time for duration calculations (time.monotonic())

    Phase semantics:
    - phase_index: Zero-based canonical counter (SPEC-OBSERVABILITY §4.1)
    - turn_index: Alias for phase_index (always same value when present)
    """

    # Core correlation IDs
    session_id: Optional[str]  # Session identifier (may be None before session init)
    batch_id: str  # Batch identifier (present in BATCH_* and below)
    match_id: str  # Match identifier (present in MATCH_* and GAMEPLAY)

    # Phase progression (present in GAMEPLAY events)
    phase_index: int  # Zero-based canonical phase counter
    turn_index: int  # Alias for phase_index (deprecated but supported)

    # Timing metadata (present in all events)
    timestamp: float  # Wall-clock time (time.time())
    monotonic_time: float  # Monotonic clock (time.monotonic())


@dataclass
class Event:
    """
    Unified event object routed through EventBus.

    Per SPEC-OBSERVABILITY v1.0.0 §4, all spectators receive this single Event
    structure regardless of event type. This enables:
    - Consistent replay (same Event objects during live and replay)
    - Type-safe handler signatures
    - JSON serialization for recording

    Fields:
        type: Event identifier (e.g., "match_start", "bid_placed")
              - EventType enum values normalized to strings
              - Custom domain events use snake_case strings
        data: Event-specific payload (must be JSON-serializable)
        context: EventContext envelope with session/match/phase metadata
        timestamp: Event creation time (auto-populated)
        duration: Event duration in seconds (may be updated post-emission)

    Example:
        event = Event(
            type="gameplay",
            data={"player": "Alice", "action": "ATTACK"},
            context={"session_id": "s1", "match_id": "m1", "phase_index": 0},
            timestamp=time.time(),
            duration=0.1
        )
    """

    type: str
    data: Dict[str, Any]
    context: EventContext
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.1


@dataclass
class SpectatorContext:
    """
    Dataclass representation of EventContext for type-safe access.

    Helper for spectators to extract context fields without dict lookups.
    Use via `Spectator.context_from(event.context)` per SPEC-SPECTATOR v1.0.0 §4.

    Example:
        def on_gameplay(self, event: Event):
            ctx = self.context_from(event.context)
            print(f"Match {ctx.match_id}, Phase {ctx.phase_index}")
    """

    session_id: Optional[str]
    batch_id: Optional[str] = None
    match_id: Optional[str] = None
    phase_index: Optional[int] = None
    turn_index: Optional[int] = None  # Alias for phase_index
    timestamp: Optional[float] = None
    monotonic_time: Optional[float] = None

    @classmethod
    def from_event(cls, context: Optional[EventContext]) -> "SpectatorContext":
        """
        Convert EventContext dict to typed SpectatorContext.

        Handles missing fields gracefully (returns None for absent keys).
        Per SPEC-SPECTATOR §5.2 SS4, spectators MUST tolerate missing fields.

        Args:
            context: EventContext dict (may be None or have missing fields)

        Returns:
            SpectatorContext with all fields extracted (None for missing)
        """
        if not context:
            return cls(session_id=None)
        return cls(
            session_id=context.get("session_id"),
            batch_id=context.get("batch_id"),
            match_id=context.get("match_id"),
            phase_index=context.get("phase_index"),
            turn_index=context.get("turn_index"),
            timestamp=context.get("timestamp"),
            monotonic_time=context.get("monotonic_time"),
        )


# ============================================================================
# Player Interaction Types (SPEC-PLAYER v1.0.0, SPEC-CONTROLLER v1.0.0)
# ============================================================================


@dataclass
class HandshakeContext:
    """
    Context provided to Player.handshake() and HandshakeController.parse().

    Per SPEC-PLAYER v1.0.0 §6, console provides this context so players can
    tailor handshake prompts with match-specific information.

    Fields:
        match_id: Match identifier
        player_name: Name of the player being validated
        opponent_names: List of opponent names
        game_name: Game identifier
        seed: Match seed for reproducibility
        handshake_template_id: Template identifier used
        metadata: Optional additional context (game instructions, etc.)

    Example:
        context = HandshakeContext(
            match_id="match-123",
            player_name="Alice",
            opponent_names=["Bob"],
            game_name="FixedDamageGame",
            seed=42,
            handshake_template_id="default",
            metadata={"game_instructions": "Attack or use potions..."}
        )
    """

    match_id: str
    player_name: str
    opponent_names: List[str]
    game_name: str
    seed: Optional[int]
    handshake_template_id: str = "default"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HandshakeResult:
    """
    Result from parsing handshake response (SPEC-CONTROLLER v1.0.0 §4.1).

    The handshake phase is the first of three player lifecycle phases:
    handshake → turn → conclusion. This result indicates whether the player
    acknowledged match conditions and is ready to proceed.

    Fields:
        accepted: True if player acknowledged, False if rejected
        normalized_response: Cleaned/parsed response text
        raw_response: Original LLM output (for prompt metadata)
        reason: Optional explanation for acceptance/rejection
        metadata: Controller-specific parsing metadata

    Example:
        result = HandshakeResult(
            accepted=True,
            normalized_response="OK",
            raw_response="I'm ready to play! OK.",
            reason="Contains acknowledgment keyword",
            metadata={"keywords_found": ["OK", "ready"]}
        )
    """

    accepted: bool
    normalized_response: Optional[str] = None
    raw_response: str = ""
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """
    Result from parsing turn action response (SPEC-CONTROLLER v1.0.0 §4.2).

    Returned by ActionController.parse() during the turn phase of player lifecycle.
    Contains the parsed action plus optional reasoning and controller metadata.

    Fields:
        action: Parsed action string (e.g., "ATTACK", "BID:100")
        reasoning: Optional reasoning extracted by controller
        metadata: Controller-specific metadata (validation, retries, etc.)
        raw_response: Original LLM response (for prompt metadata)

    Example:
        result = ActionResult(
            action="ATTACK",
            reasoning="Opponent is weak, go aggressive",
            raw_response="REASONING: Opponent is weak\nACTION: ATTACK",
            metadata={"validated": True, "allowed_actions": ["ATTACK", "DEFEND"]}
        )
    """

    action: str
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None


@dataclass
class MatchContext:
    """
    Console-managed context for match execution.

    Per SPEC-PLAYER v1.0.0 §6, this extends basic match metadata with
    lifecycle tracking (handshake_completed) and RNG information.

    Per SPEC-CONSOLE §3 M4, includes previous_match_result for batch-local
    state-dependent player ordering (auction games, previous-winner-first, etc.).

    Fields:
        match_id: Match identifier
        players: List of player names
        game_name: Game identifier
        seed: Match seed for reproducibility
        handshake_completed: True after all players complete handshake
        rng_info: Optional RNG state/metadata
        previous_match_result: Previous match result within current batch (None for first match)

    Example:
        context = MatchContext(
            match_id="match-123",
            players=["Alice", "Bob"],
            game_name="FixedDamageGame",
            seed=42,
            handshake_completed=True,
            rng_info={"seed": 42, "state": ...},
            previous_match_result=prev_result  # From previous match in batch
        )
    """

    match_id: str
    players: List[str]
    game_name: str
    seed: Optional[int]
    handshake_completed: bool = False
    rng_info: Optional[Dict[str, Any]] = None
    previous_match_result: Optional["MatchResult"] = None  # Forward reference for type hint
    conclusion_prompt: Optional[str] = None


class ActionParseError(Exception):
    """
    Structured exception raised when action controller fails to parse LLM response.

    Per SPEC-CONTROLLER v1.2.0 §5.7 (APF), this exception carries the originating
    ParseResult to preserve full diagnostic context (candidates, reasoning, metadata)
    for Console, Recorder, and research analysis.

    Attributes:
        parse_result: The ParseResult that triggered the failure
        message: Human-readable error description (reuses ParseResult.error)

    Example:
        try:
            action_result = parse_result.to_action_result()
        except ActionParseError as e:
            print(f"Parsing failed: {e}")
            print(f"Candidates: {e.parse_result.metadata.get('candidates')}")
    """

    def __init__(self, parse_result: "ParseResult"):
        self.parse_result = parse_result
        error_msg = parse_result.error or "Failed to parse action from LLM response"
        super().__init__(f"Action parsing failed: {error_msg}")


class MatchAbortedError(Exception):
    """
    Exception raised when match must be aborted due to parse failure with ABORT_MATCH policy.

    Per SPEC-CONSOLE v0.5.0 §6.11 PF4, this exception signals that the match should terminate
    but Console MUST still emit MATCH_END and record the partial match before propagating.

    Attributes:
        player_name: Name of player who caused abort
        parse_error: Original ActionParseError with ParseResult
        turn_context: Turn context when failure occurred
        policy: The ParseFailurePolicy that was applied (always ABORT_MATCH)

    Usage:
        Raised by Console.get_player_action() when game policy returns ABORT_MATCH.
        Caller (Console._play_match or _MatchWorker) catches this, emits MATCH_END with
        metadata["outcome"] = "aborted", then terminates execution.
    """

    def __init__(
        self,
        player_name: str,
        parse_error: "ActionParseError",
        turn_context: Optional["TurnContext"],
        policy: "ParseFailurePolicy",
    ):
        self.player_name = player_name
        self.parse_error = parse_error
        self.turn_context = turn_context
        self.policy = policy
        self.abort_state: Optional[Dict[str, Any]] = None

        # Codex fix #2: Tolerate None turn_context (for reconstructed exceptions)
        if turn_context is not None:
            turn_info = f"at turn {turn_context.turn_number}"
        else:
            turn_info = "(turn context unavailable)"

        super().__init__(f"Match aborted due to parse failure: {player_name} {turn_info}")


class MatchForfeitedError(Exception):
    """
    Exception raised when match ends due to parse failure with FORFEIT policy.

    Similar to MatchAbortedError, but the failing player loses (other players win).
    Console MUST emit MATCH_END with winner set before propagating.

    Attributes:
        player_name: Name of player who forfeited
        parse_error: Original ActionParseError with ParseResult
        turn_context: Turn context when failure occurred
        policy: The ParseFailurePolicy that was applied (always FORFEIT)
        winner: Name of the winning player (opponent of forfeiter)

    Usage:
        Raised by Console.get_player_action() when game policy returns FORFEIT.
        Caller emits MATCH_END with metadata["outcome"] = "forfeit" and winner set.
    """

    def __init__(
        self,
        player_name: str,
        parse_error: "ActionParseError",
        turn_context: Optional["TurnContext"],
        policy: "ParseFailurePolicy",
        winner: str,
    ):
        self.player_name = player_name
        self.parse_error = parse_error
        self.turn_context = turn_context
        self.policy = policy
        self.winner = winner
        self.forfeit_state: Optional[Dict[str, Any]] = None

        # Tolerate None turn_context (for reconstructed exceptions)
        if turn_context is not None:
            turn_info = f"at turn {turn_context.turn_number}"
        else:
            turn_info = "(turn context unavailable)"

        super().__init__(f"Match forfeited: {player_name} {turn_info}, winner: {winner}")


@dataclass
class ParseResult:
    """
    Structured parsing outcome returned by action controllers.

    Per SPEC-CONTROLLER v1.2.0 §4, action controllers return ParseResult to enable
    stateless parsing. Callers convert to ActionResult via to_action_result() method.

    This two-step pattern (parse → convert) separates parsing logic from error handling,
    allowing controllers to be pure functions. Parsing failures raise ActionParseError
    to ensure they surface for evaluation rather than being hidden by fallback mechanisms.
    """

    success: bool
    action: Optional[str]
    raw_response: str
    reasoning: Optional[str] = None
    error: Optional[str] = None
    normalized_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_action_result(self) -> ActionResult:
        """
        Convert the parse result into an ActionResult.

        Per SPEC-CONTROLLER v1.2.0 §5.4 (VF2-VF4), this method raises ActionParseError
        when success=False instead of applying fallback semantics. This ensures parsing
        failures surface explicitly for research evaluation.

        Returns:
            ActionResult with parsed action and metadata

        Raises:
            ActionParseError: If parsing failed (success=False). The exception exposes
                             the originating ParseResult via error.parse_result.

        Example:
            parse_result = controller.parse(raw_response)
            try:
                action_result = parse_result.to_action_result()
            except ActionParseError as e:
                # Console handles failure via _handle_parse_failure()
                logger.error(f"Parse failed: {e.parse_result.error}")
        """
        if not self.success:
            raise ActionParseError(self)

        if not self.action:
            # Mark as failure before raising so ParseResult in exception is truthful
            self.success = False
            self.error = self.error or "Action parsing succeeded but no action was extracted"
            raise ActionParseError(self)

        metadata = dict(self.metadata)
        metadata.setdefault("parser_success", True)

        result = ActionResult(
            action=self.action,
            reasoning=self.reasoning,
            metadata=metadata,
            raw_response=self.raw_response,
        )
        return result


# ============================================================================
# Game State Types (SPEC-GAME v0.6.0)
# ============================================================================


class ParseFailurePolicy(Enum):
    """
    Policy outcomes for action parsing failures.

    Per SPEC-GAME v0.6.0 §4, games return one of these values from
    on_action_parse_failure() to instruct Console how to handle the failure.

    Values:
        FORFEIT: Failing player loses immediately (default behavior)
        SKIP_TURN: Consume the failing player's turn and continue match
        ABORT_MATCH: Terminate match immediately
        RETRY_ONCE: Console re-issues prompt exactly once (deterministic)

    Example:
        def on_action_parse_failure(self, player_name, error, turn_context):
            # Custom game policy: give one retry, then forfeit
            if turn_context.turn_number == 1:
                return ParseFailurePolicy.RETRY_ONCE
            return ParseFailurePolicy.FORFEIT
    """

    ABORT_MATCH = "abort"  # Terminate match immediately
    SKIP_TURN = "skip"  # Consume the failing player's turn, continue match
    FORFEIT = "forfeit"  # Failing player loses immediately (default)
    RETRY_ONCE = "retry"  # Console re-issues prompt exactly once


@dataclass
class GameStatus:
    """
    Game state status returned by Game.status().

    Per SPEC-GAME v1.0.0 §3.4, games return this to indicate whether the
    match is complete and who won (if applicable).

    Fields:
        is_over: True if match is complete
        winner: Winner's name (or None for draw/ongoing)

    Example:
        status = GameStatus(is_over=True, winner="Alice")
    """

    is_over: bool
    winner: Optional[str] = None


@dataclass
class MatchResult:
    """
    Complete result from a single match execution.

    Returned by Console.run() and stored in recordings. Contains final state,
    event stream, seed for reproducibility, and metadata.

    Fields:
        winner: Winner's name (or None for draw)
        final_state: Final game state dict
        events: Complete event stream (for replay)
        seed: Match seed used (for reproducibility)
        metadata: Additional match metadata (players, dialogue, duration, etc.)

    Example:
        result = MatchResult(
            winner="Alice",
            final_state={"health": {"Alice": 20, "Bob": 0}},
            events=[...],
            seed=42,
            metadata={
                "players": ["Alice", "Bob"],
                "match_id": "match-123",
                "dialogue": [...]
            }
        )
    """

    winner: Optional[str]
    final_state: Dict[str, Any]
    events: List[Event]
    seed: Optional[int]
    metadata: Dict[str, Any]


@dataclass
class MatchArtifact:
    """
    Artifacts from a worker match execution (SPEC-PARALLEL v1.0.0 §4).

    Used internally by Console for parallel execution. Workers capture events
    in an isolated EventBus, then return artifacts for main-thread replay.

    This type enables the event replay pattern that preserves spectator and
    recorder behavior: workers execute matches in parallel on isolated copies,
    then the main thread replays their events in match_index order.

    Fields:
        match_index: Original match index in batch (for ordering results)
        result: MatchResult with final state, winner, metadata
        events: Captured events from worker's isolated EventBus

    Note:
        - match_index ensures deterministic ordering even if matches complete
          out-of-order in parallel execution
        - events include full context (session_id, batch_id, match_id) for replay
        - This type is internal; users never see it (they receive MatchResults)

    Example:
        # Worker returns artifact after isolated execution
        artifact = MatchArtifact(
            match_index=2,
            result=MatchResult(...),
            events=[Event(...), Event(...), ...]
        )

        # Console replays events in order
        for artifact in sorted(artifacts, key=lambda a: a.match_index):
            console._replay_events(artifact.replay_events)
    """

    match_index: int
    result: MatchResult
    events: List[Event]  # Sanitized snapshots for result.events (Player->name conversion)
    replay_events: List[tuple[EventType, Dict[str, Any], Dict[str, Any]]] = field(
        default_factory=list
    )  # Original payloads for spectator replay


@dataclass
class MatchResults:
    """
    Container for multiple match results with analysis helpers.

    Returned by AgentDeck.play() when running multiple matches. Provides
    convenience methods for win rate analysis and summary statistics.

    Example:
        results = deck.play(game, players, matches=10)
        print(results.summary)
        print(f"Alice win rate: {results.win_rates['Alice']:.1%}")
    """

    matches: List[MatchResult]

    def __len__(self) -> int:
        """Number of matches."""
        return len(self.matches)

    def __getitem__(self, index: int) -> MatchResult:
        """Access match by index."""
        return self.matches[index]

    @property
    def single(self) -> MatchResult:
        """
        Convenience accessor for single match.

        Raises:
            ValueError: If not exactly one match in results
        """
        if len(self.matches) != 1:
            raise ValueError(f"Expected 1 match, got {len(self.matches)}")
        return self.matches[0]

    @property
    def win_rates(self) -> Dict[str, float]:
        """
        Calculate win rates for each player.

        Returns:
            Dictionary mapping player name to win rate (0.0-1.0)
        """
        # Collect all unique player names from match metadata
        all_players = set()
        for match in self.matches:
            if match.metadata and "players" in match.metadata:
                all_players.update(match.metadata["players"])

        # Count wins
        wins = {player: 0 for player in all_players}
        total = len(self.matches)

        for match in self.matches:
            if match.winner and match.winner in wins:
                wins[match.winner] += 1

        # Return win rates (including 0.0 for players with no wins)
        return {player: count / total if total > 0 else 0.0 for player, count in wins.items()}

    @property
    def summary(self) -> str:
        """
        Generate human-readable summary.

        Returns:
            Multi-line string with match count and win rates
        """
        rates = self.win_rates
        total = len(self.matches)

        lines = [f"Matches played: {total}"]
        for player, rate in rates.items():
            wins = int(rate * total)
            lines.append(f"{player}: {wins}/{total} ({rate:.1%})")

        return "\n".join(lines)


# ============================================================================
# Supporting Types
# ============================================================================


@dataclass(frozen=True)
class RenderResult:
    """
    Immutable renderer output containing text and metadata (SPEC-RENDERER v0.3.0 §4).

    frozen=True ensures immutability so recorder hashes remain stable.
    This is critical for replay integrity and observability.

    Fields:
        text: Primary rendered output passed to PromptBuilder
        metadata: JSON-serializable dict (sections, format hints, token estimates)

    Example:
        result = RenderResult(
            text="=== Game State ===\nHealth: 100\n...",
            metadata={"format": "text", "sections": ["header", "health"]}
        )

    Note: Cannot modify fields after creation due to frozen=True. Create new
          instance instead of mutating.
    """

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Prompt Composition Types (SPEC-PROMPT-BUILDER v0.4.0)
# ============================================================================


class LifecyclePhase(Enum):
    """
    Player lifecycle phases for prompt composition.

    Per SPEC-PROMPT-BUILDER v0.4.0 §6 and SPEC-PLAYER v1.0.0 §3:
    - HANDSHAKE: Initial acknowledgment phase (player accepts match conditions)
    - TURN: Repeated action selection phase (player chooses action each turn)
    - CONCLUSION: Final reflection phase (player receives match outcome)

    Example:
        bundle = builder.compose(
            phase=LifecyclePhase.TURN,
            render_result=...,
            controller_format=...
        )
    """

    HANDSHAKE = "handshake"
    TURN = "turn"
    CONCLUSION = "conclusion"


@dataclass(frozen=True)
class PromptContext:
    """
    Immutable context passed to custom providers during prompt composition.

    Per SPEC-PROMPT-BUILDER v0.4.0 §6 PS1, this context is frozen to prevent
    providers from mutating state mid-composition. The extras field is wrapped
    in MappingProxyType during construction to ensure true immutability.

    Fields:
        phase: Lifecycle phase (HANDSHAKE/TURN/CONCLUSION)
        turn_number: 1-based turn counter (0 for handshake/conclusion)
        render_result: Renderer output (game view text + metadata)
        controller_format: Action controller format instructions
        handshake_controller_format: Handshake controller format instructions
        turn_context: Optional turn execution metadata
        extras: Additional researcher-provided data (immutable via MappingProxyType)

    Example:
        def hint_provider(ctx: PromptContext) -> str:
            if ctx.turn_number > 5:
                return "Consider defensive strategy"
            return ""

    Note: Cannot modify fields after creation due to frozen=True. The extras
          field is a read-only mapping (MappingProxyType) to prevent providers
          from mutating it via ctx.extras[key] = value.
    """

    phase: LifecyclePhase
    turn_number: int
    render_result: RenderResult
    controller_format: str
    handshake_controller_format: Optional[str]
    turn_context: Optional[TurnContext]
    extras: Mapping[str, Any]  # Immutable via MappingProxyType


@dataclass
class PromptBlock:
    """
    Single content block rendered into a prompt.

    Per SPEC-PROMPT-BUILDER v0.4.0 §6, blocks capture which placeholders
    were substituted during composition for observability and debugging.

    Fields:
        key: Placeholder name (e.g., "game_view", "strategy")
        content: Rendered content for this block
        metadata: Optional block-specific metadata (from renderer, etc.)

    Example:
        block = PromptBlock(
            key="game_view",
            content="Health: 100\n...",
            metadata={"sections": ["header", "health"]}
        )
    """

    key: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PromptBundle:
    """
    Complete prompt composition result with metadata.

    Per SPEC-PROMPT-BUILDER v0.4.0 §6, PromptBuilder.compose() returns this
    bundle containing both the text to send to the LLM and metadata for
    recorder/debugging.

    Fields:
        text: Final rendered prompt string (send to LLM)
        blocks: Ordered list of blocks rendered (observability)
        metadata: Required bundle metadata (template_id, phase, turn_number, blocks_rendered)

    Required metadata keys (SPEC-PROMPT-BUILDER §5.3 MC1):
        - template_id: Identifier for the template used (str)
        - phase: Lifecycle phase (str, e.g., "turn")
        - turn_number: Turn number (int, 0 for handshake/conclusion)
        - blocks_rendered: List of block keys rendered (e.g., ["game_view", "controller_format"])

    Example:
        bundle = builder.compose(phase=LifecyclePhase.TURN, ...)
        prompt_text = bundle.text  # Send to LLM
        template_used = bundle.metadata["template_id"]
        blocks_included = bundle.metadata["blocks_rendered"]
    """

    text: str
    blocks: List[PromptBlock]
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateError(Exception):
    """
    Raised when template rendering fails.

    Per SPEC-PROMPT-BUILDER v0.4.0 §6, template errors include context
    for debugging (placeholder name, template ID, phase).

    Common causes:
        - Undefined placeholder (not in auto-bound sources, extras, or custom providers)
        - Provider exception during evaluation
        - Invalid template syntax

    Example:
        try:
            bundle = builder.compose(...)
        except TemplateError as e:
            print(f"Template error: {e}")
            print(f"Placeholder: {e.placeholder}")
            print(f"Template: {e.template_id}")
            print(f"Phase: {e.phase}")
    """

    def __init__(
        self,
        message: str,
        placeholder: Optional[str] = None,
        template_id: Optional[str] = None,
        phase: Optional[str] = None,
    ):
        """
        Initialize template error with context.

        Args:
            message: Human-readable error description
            placeholder: Placeholder name that triggered error (if applicable)
            template_id: Template identifier (if applicable)
            phase: Lifecycle phase (if applicable)
        """
        self.placeholder = placeholder
        self.template_id = template_id
        self.phase = phase
        super().__init__(message)


# ============================================================================
# Legacy Types (Backward Compatibility)
# ============================================================================


@dataclass
class PromptBlockMetadata:
    """
    Lightweight serialization schema for prompt sections.

    NOTE: Legacy type for backward compatibility. Will be removed when
    PromptBuilder is rewritten per SPEC-PROMPT-BUILDER v1.0.0.
    """

    key: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        stripped = self.content.strip()
        return {
            "key": self.key,
            "content": stripped,
            "length": len(stripped),
        }


@dataclass
class ActionMetadata:
    """
    Structured metadata captured for each player action.

    NOTE: Legacy type for backward compatibility. Will be removed when
    Player is rewritten per SPEC-PLAYER v1.0.0.
    """

    raw_prompt: str
    prompt_blocks: List[PromptBlockMetadata]
    prompt_length: int
    raw_response: Optional[str] = None
    usage_info: Optional[Dict[str, Any]] = None
    retries: int = 0
    retry_durations: List[float] = field(default_factory=list)
    attempt_durations: List[float] = field(default_factory=list)
    turn_context: Optional[Dict[str, Any]] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary for action metadata."""
        payload: Dict[str, Any] = {
            "raw_prompt": self.raw_prompt,
            "prompt_length": self.prompt_length,
            "prompt_blocks": [block.to_dict() for block in self.prompt_blocks],
            "retries": self.retries,
            "retry_durations": list(self.retry_durations),
            "attempt_durations": list(self.attempt_durations),
        }
        if self.raw_response is not None:
            payload["raw_response"] = self.raw_response
        if self.usage_info is not None:
            payload["usage_info"] = self.usage_info
        if self.turn_context is not None:
            payload["turn_context"] = self.turn_context
        if self.extras:
            payload["extras"] = dict(self.extras)
        return payload


@dataclass
class TurnContext:
    """
    Metadata describing a single turn execution.

    Passed to Player.decide() and ActionController.parse() to provide
    turn-specific context beyond the game state.

    Fields:
        match_id: Match identifier
        turn_number: 1-based counter (human-friendly)
        turn_index: 0-based index (array indexing)
        player: Current player's name
        started_at: Turn start timestamp
        duration: Turn duration in seconds
        rng_seed: Optional RNG seed for this turn
        rng_label: Optional RNG label for debugging

    Example:
        ctx = TurnContext(
            match_id="match-123",
            turn_number=5,
            turn_index=4,
            player="Alice",
            started_at=time.time(),
            duration=1.2,
            rng_seed=12345
        )
    """

    match_id: str
    turn_number: int  # 1-based counter for display
    turn_index: int  # 0-based index for arrays
    player: str
    started_at: float
    duration: float
    rng_seed: Optional[int] = None
    rng_label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dictionary.

        Use for:
        - Recording turn data for replay
        - Embedding in ActionResult.metadata
        - Emitting in events to spectators

        Returns:
            Dictionary with all turn context fields (omits None values)
        """
        payload = {
            "match_id": self.match_id,
            "turn_number": self.turn_number,
            "turn_index": self.turn_index,
            "player": self.player,
            "started_at": self.started_at,
            "duration": self.duration,
            "ended_at": self.started_at + self.duration,
        }
        if self.rng_seed is not None:
            payload["rng_seed"] = self.rng_seed
        if self.rng_label:
            payload["rng_label"] = self.rng_label
        return payload


class RandomGenerator:
    """
    Encapsulates random number generation for reproducibility.

    Per SPEC.md §2.4, AgentDeck ensures full reproducibility through
    deterministic seeding. Each game instance receives its own RNG to
    ensure reproducible results independent of global random state.

    Example:
        rng = RandomGenerator(seed=42)
        first_player = rng.choice(["Alice", "Bob"])
        damage = rng.randint(10, 20)
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize with optional seed for reproducibility.

        Args:
            seed: Optional integer seed (None for non-deterministic)
        """
        self._rng = random.Random(seed)
        self.seed = seed

    def randint(self, a: int, b: int) -> int:
        """Return random integer in range [a, b], inclusive."""
        return self._rng.randint(a, b)

    def random(self) -> float:
        """Return random float in range [0.0, 1.0)."""
        return self._rng.random()

    def choice(self, seq):
        """Return random element from non-empty sequence."""
        return self._rng.choice(seq)

    def shuffle(self, seq):
        """Shuffle sequence in-place."""
        self._rng.shuffle(seq)

    def sample(self, population, k):
        """Return k unique random elements from population."""
        return self._rng.sample(population, k)

    def uniform(self, a: float, b: float) -> float:
        """Return random float N such that a <= N <= b."""
        return self._rng.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        """Return random float from Gaussian distribution."""
        return self._rng.gauss(mu, sigma)

    def getstate(self):
        """Return internal state for later restoration."""
        return self._rng.getstate()

    def setstate(self, state):
        """Restore internal state from previous getstate()."""
        self._rng.setstate(state)

    def fork(self, salt: Any = None) -> "RandomGenerator":
        """
        Create a new RNG with a derived seed.

        Useful for creating independent RNGs for sub-components while
        maintaining reproducibility from the parent seed.

        Behavior:
        - Seeded parent: Derives deterministic seed from parent seed + salt
        - Unseeded parent: Derives seed from parent's current RNG state

        Args:
            salt: Optional salt for seed derivation

        Returns:
            New RandomGenerator with derived seed
        """
        import hashlib

        if self.seed is not None:
            # Seeded parent: derive deterministic seed from parent seed + salt
            combined = f"{self.seed}:{salt}".encode()
            hash_bytes = hashlib.sha256(combined).digest()
            # Use first 8 bytes as new seed (max 64-bit int)
            new_seed = int.from_bytes(hash_bytes[:8], "big") % (2**32)
        else:
            # Unseeded parent: derive from current RNG state
            new_seed = self._rng.getrandbits(64) % (2**32)

        return RandomGenerator(new_seed)


# ============================================================================
# Logging Types
# ============================================================================


class LogLevel(Enum):
    """
    Logging levels for AgentDeck framework.

    Simplified to two levels per AGENTS.md philosophy:
    - INFO: Match narrative (turns, actions, reasoning, state changes)
    - DEBUG: System diagnostics (API calls, tokens, retries, errors)
    """

    INFO = "info"
    DEBUG = "debug"


# ============================================================================
# Legacy Types (Backward Compatibility)
# ============================================================================

from typing import Callable

ReplaySpeed = Callable[[float, float], float]
"""Legacy type for replay speed functions. Will be removed in future versions."""
