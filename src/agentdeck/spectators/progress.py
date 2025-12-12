"""Real-time progress display spectator for AgentDeck."""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Optional

from ..core.base.spectator import Spectator
from ..core.types import EventContext, MatchResult


class ProgressDisplay(Spectator):
    """
    Displays real-time progress during batch execution.

    Per SPEC-SPECTATOR v1.0.0:
    - HC1-HC4: Duck-typed handlers, read-only, quick completion
    - SS1-SS4: Resets state per batch, tolerates missing context
    - EI1-EI3: Error-safe, no execution mutations
    - LO1: Uses logger if provided, else stdout

    Example output:
        [Batch batch_a1b2] Match 3/10 | Alice vs Bob | Winner: Alice | ETA: 1m 45s
    """

    def __init__(
        self, *, logger: Any = None, show_eta: bool = True, use_carriage_return: bool = True
    ) -> None:
        """
        Initialize progress display.

        Args:
            logger: Optional logger for structured output
            show_eta: Calculate and display estimated time remaining
            use_carriage_return: Use \\r for in-place updates (terminal-friendly)
        """
        super().__init__(logger=logger)
        self.show_eta = show_eta
        self.use_carriage_return = use_carriage_return and sys.stdout.isatty()

        # Batch state (reset per batch)
        self.batch_id: Optional[str] = None
        self.total_matches: int = 0
        self.completed_matches: int = 0
        self.batch_start_time: float = 0.0
        self.player_names: List[str] = []

        # Match state
        self.current_match_start: float = 0.0
        self.match_durations: List[float] = []

    def on_batch_start(
        self, batch_id: str, game, players, matches: int, context: Optional[EventContext] = None
    ) -> None:
        """Reset state and display batch start. Per SS3: explicit state reset."""
        self.batch_id = batch_id
        self.total_matches = matches
        self.completed_matches = 0
        self.batch_start_time = time.time()
        self.player_names = [p.name for p in players]
        self.match_durations = []

        msg = f"\n[Batch {batch_id[:8]}] Starting {matches} match{'es' if matches > 1 else ''}"
        self._output(msg, newline=True)

    def on_match_start(
        self,
        game,
        players,
        match_id: Optional[str] = None,
        context: Optional[EventContext] = None,
        **kwargs: Any,  # Accept player ordering fields (seed, player_order, etc.)
    ) -> None:
        """Track match start time."""
        self.current_match_start = time.time()

    def on_match_end(self, result: MatchResult, context: Optional[EventContext] = None) -> None:
        """Update progress after each match. Per HC3: read-only access to result."""
        self.completed_matches += 1

        # Track match duration
        if self.current_match_start > 0:
            duration = time.time() - self.current_match_start
            self.match_durations.append(duration)

        # Calculate ETA
        eta_str = ""
        if self.show_eta and self.match_durations and self.completed_matches < self.total_matches:
            avg_duration = sum(self.match_durations) / len(self.match_durations)
            remaining = self.total_matches - self.completed_matches
            eta_seconds = avg_duration * remaining
            eta_str = f" | ETA: {self._format_duration(eta_seconds)}"

        # Format progress
        winner = result.winner or "Draw"
        turns = result.metadata.get("turns", "?")

        msg = (
            f"[Batch {self.batch_id[:8] if self.batch_id else '?'}] "
            f"Match {self.completed_matches}/{self.total_matches} | "
            f"{' vs '.join(self.player_names)} | "
            f"Winner: {winner} ({turns} turns){eta_str}"
        )

        # Use carriage return for in-place update on final match
        newline = (self.completed_matches == self.total_matches) or not self.use_carriage_return
        self._output(msg, newline=newline)

    def on_batch_end(
        self,
        batch_id: str,
        results: List[MatchResult],
        context: Optional[EventContext] = None,
        **kwargs: Any,  # Per SPEC: accept T3 metadata (matches_completed, duration, seeds_used)
    ) -> None:
        """Display batch summary. Per EI2: avoid raising in cleanup."""
        try:
            duration = kwargs.get("duration") or (time.time() - self.batch_start_time)

            # Calculate win rates
            winners = [r.winner for r in results if r.winner]
            win_counts: Dict[str, int] = {}
            for winner in winners:
                win_counts[winner] = win_counts.get(winner, 0) + 1

            summary_parts = []
            for player in self.player_names:
                wins = win_counts.get(player, 0)
                win_rate = (wins / len(results) * 100) if results else 0
                summary_parts.append(f"{player}: {wins}/{len(results)} ({win_rate:.0f}%)")

            msg = (
                f"\n[Batch {batch_id[:8]}] Complete | "
                f"{len(results)} matches in {self._format_duration(duration)} | "
                f"{' | '.join(summary_parts)}"
            )
            self._output(msg, newline=True)
        except Exception:
            # Per EI2: Log instead of raising in cleanup
            if self.logger:
                self.logger.warning("ProgressDisplay failed to display batch summary")

    def _output(self, msg: str, newline: bool = True) -> None:
        """Output message to logger or stdout. Per LO1: prefer logger."""
        if self.logger and hasattr(self.logger, "info"):
            self.logger.info(msg)
        else:
            if self.use_carriage_return and not newline:
                # In-place update for terminals
                sys.stdout.write(f"\r{msg}")
                sys.stdout.flush()
            else:
                print(msg)

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m"
