"""Statistics tracker spectator for AgentDeck."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..core.base.spectator import Spectator
from ..core.types import ActionResult, Event, EventContext, MatchResult
from .utils import CounterMap, DurationTracker


class StatsTracker(Spectator):
    """Tracks match, turn, and dialogue statistics for experiments."""

    def __init__(self, *, logger: Any = None, track_dialogue: bool = False) -> None:
        super().__init__(logger=logger)
        self.track_dialogue = track_dialogue
        self.actions = CounterMap()
        self.turn_durations = DurationTracker()
        self.reset()

    def reset(self):
        """Reset all statistics."""
        self.total_matches = 0
        self.wins = defaultdict(int)
        self.losses = defaultdict(int)
        self.draws = 0

        self.total_turns = defaultdict(int)

        self.match_durations = []

        self.current_match_start = None
        self.current_turn_start = None
        self.current_players = []
        self.dialogue_log: List[Dict[str, Any]] = []
        self.actions.clear()
        self.turn_durations.clear()

    def on_match_start(
        self, game, players, match_id=None, context: Optional[EventContext] = None, **kwargs
    ):
        """Track match start."""
        self.current_match_start = time.time()
        self.current_turn_start = None  # Reset turn timing for new match
        self.current_players = [p.name for p in players]

    def on_gameplay(self, event: Event) -> None:
        """Track gameplay statistics."""
        data = event.data
        player = data.get("player")
        if player is None:
            return

        action_obj = data.get("action")
        if isinstance(action_obj, ActionResult):
            action_record = action_obj.action
        else:
            action_record = str(action_obj)

        self.actions.increment(player, action_record)
        self.total_turns[player] += 1

        if self.current_turn_start:
            turn_time = time.time() - self.current_turn_start
            self.turn_durations.record(player, turn_time)

        self.current_turn_start = time.time()

    def on_match_end(self, result: MatchResult, context: Optional[EventContext] = None):
        """Track match end statistics."""
        self.total_matches += 1

        # Track winner/loser
        if result.winner:
            self.wins[result.winner] += 1
            for player in self.current_players:
                if player != result.winner:
                    self.losses[player] += 1
        else:
            self.draws += 1

        # Track match duration
        if self.current_match_start:
            duration = time.time() - self.current_match_start
            self.match_durations.append(duration)

    def on_dialogue_turn(
        self,
        player: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
        turn_context: Optional[Dict[str, Any]] = None,
        context: Optional[EventContext] = None,
        **_: Any,
    ):
        if not self.track_dialogue:
            return

        spectator_context = self.context_from(context)
        self.dialogue_log.append(
            {
                "player": player,
                "prompt": prompt,
                "response": response,
                "metadata": metadata or {},
                "context": spectator_context,
                "turn_context": turn_context,
            }
        )

    def get_win_rate(self, player: str) -> float:
        """Get win rate for a player."""
        total = self.wins[player] + self.losses[player]
        if total == 0:
            return 0.0
        return self.wins[player] / total

    def get_stats(self) -> Dict[str, Any]:
        """Get all statistics as a dictionary."""
        stats = {"total_matches": self.total_matches, "draws": self.draws, "players": {}}

        # Compile per-player statistics
        # Include total_turns to capture players from drawn matches
        all_players = set(self.wins.keys()) | set(self.losses.keys()) | set(self.total_turns.keys())

        for player in all_players:
            player_stats = {
                "wins": self.wins[player],
                "losses": self.losses[player],
                "win_rate": self.get_win_rate(player),
                "total_turns": self.total_turns[player],
                "actions": self.actions.as_dict().get(player, {}),
                "avg_turn_time": self.turn_durations.average(player),
                "turn_durations": self.turn_durations.values(player),
            }
            stats["players"][player] = player_stats

        # Add timing statistics
        if self.match_durations:
            stats["avg_match_duration"] = sum(self.match_durations) / len(self.match_durations)
            stats["total_time"] = sum(self.match_durations)

        if self.track_dialogue:
            stats["dialogue_turns"] = len(self.dialogue_log)

        return stats

    def summaries(self) -> Dict[str, Any]:
        """Structured summary hook used by automation and tests."""
        return self.get_stats()

    def print_summary(self, use_logger: bool = True):
        """
        Print a formatted summary of statistics.

        Args:
            use_logger: If True, use logger. If False, print to stdout.
                       Allows explicit choice for when output is desired.
        """
        stats = self.get_stats()

        # Choose output method
        output = (
            self.logger.info
            if (use_logger and self.logger and hasattr(self.logger, "info"))
            else print
        )

        output("\n" + "=" * 50)
        output("MATCH STATISTICS")
        output("=" * 50)
        output(f"Total Matches: {stats['total_matches']}")
        output(f"Draws: {stats['draws']}")

        if stats.get("avg_match_duration"):
            output(f"Avg Match Duration: {stats['avg_match_duration']:.2f}s")

        output("\n" + "-" * 50)
        output("PLAYER STATISTICS")
        output("-" * 50)

        for player, player_stats in stats["players"].items():
            output(f"\n{player}:")
            output(f"  Wins: {player_stats['wins']}")
            output(f"  Losses: {player_stats['losses']}")
            output(f"  Win Rate: {player_stats['win_rate']:.1%}")
            output(f"  Total Turns: {player_stats['total_turns']}")

            if player_stats["avg_turn_time"]:
                output(f"  Avg Turn Time: {player_stats['avg_turn_time']:.3f}s")

            if player_stats["actions"]:
                output("  Actions Taken:")
                for action, count in player_stats["actions"].items():
                    output(f"    {action}: {count}")

        output("=" * 50)

    def log_summary(self):
        """Log summary using the logger (Rule of Silence compliant)."""
        self.print_summary(use_logger=True)

    def display_summary(self):
        """Explicitly display summary to stdout (when user wants output)."""
        self.print_summary(use_logger=False)
