"""Base spectator class for AgentDeck framework."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..types import Event, EventContext, LogLevel, MatchResult, SpectatorContext


class Spectator:
    """Base class for match observers.

    Spectators should treat all incoming state as read-only and prefer logging
    over stdout unless explicitly emitting structured summaries.
    """

    def __init__(self, *, logger: Any = None) -> None:
        self.logger = logger

    def on_session_start(self, context: Optional[EventContext] = None, **kwargs: Any):
        """Console initialized.

        Context includes: session_id, timestamp

        Note: Per SPEC-SPECTATOR v1.0.0, uses **kwargs for forward compatibility.
        Console may emit additional fields (session_id, seed, log_directory, etc.)
        """

    def on_session_end(self, context: Optional[EventContext] = None, **kwargs: Any):
        """Console closing.

        Context includes: session_id, timestamp

        Note: Per SPEC-SPECTATOR v1.0.0, uses **kwargs for forward compatibility.
        Console may emit additional fields (session_id, etc.)
        """

    def on_batch_start(
        self,
        batch_id: str,
        game: "Game",
        players: List["Player"],
        matches: int,
        context: Optional[EventContext] = None,
    ):
        """Batch of matches starting.

        Context includes: session_id, timestamp, batch_id
        """

    def on_batch_end(
        self,
        batch_id: str,
        results: List[MatchResult],
        context: Optional[EventContext] = None,
        **kwargs: Any,  # Accept T3 metadata (matches_completed, duration, seeds_used)
    ):
        """Batch completed.

        Context includes: session_id, timestamp, batch_id

        Note: Per SPEC-CONSOLE T3, receives matches_completed, duration, seeds_used metadata.
        """

    def on_match_start(
        self,
        game: "Game",
        players: List["Player"],
        match_id: str = None,
        context: Optional[EventContext] = None,
        **kwargs: Any,
    ):
        """Match beginning.

        Context includes: session_id, timestamp, batch_id (if in batch), match_id

        Note: Per player ordering implementation, accepts additional fields:
        seed, player_names, player_order, player_order_source, first_player
        """

    def on_player_instructed(
        self, player: str, instructions: str, context: Optional[EventContext] = None
    ):
        """Player received game instructions.

        Context includes: session_id, timestamp, batch_id (if in batch), match_id
        """

    def on_gameplay(self, event: Event) -> None:
        """Gameplay event emitted each phase."""

    def on_event(self, event: Event, context: Optional[EventContext] = None):
        """Custom game event.

        Context includes: session_id, timestamp, and other fields as available
        """

    # on_dialogue_turn removed in schema v1.3
    # Prompt metadata now in lifecycle events (PLAYER_HANDSHAKE_COMPLETE, GAMEPLAY, etc.)
    # Access via event.data["prompt"] in recordings

    def on_match_end(self, result: MatchResult, context: Optional[EventContext] = None):
        """Match ended.

        Context includes: session_id, timestamp, batch_id (if in batch), match_id
        """

    def on_log(
        self,
        message: str,
        level: LogLevel,
        log_context: Dict,
        context: Optional[EventContext] = None,
    ):
        """Log event.

        Args:
            message: Log message
            level: Log level (INFO or DEBUG)
            log_context: Log-specific context (game state, etc.)
            context: Event context with session_id, timestamp, and other fields as available
        """

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def context_from(self, context: Optional[EventContext]) -> SpectatorContext:
        """Convert raw EventContext dictionaries into a SpectatorContext."""
        return SpectatorContext.from_event(context)
