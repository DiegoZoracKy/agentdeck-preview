"""AgentDeck public API facade."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from .base import Game, Player, Spectator
from .console import Console
from .logging import create_logger
from .recorder import Recorder
from .replay import ReplayEngine
from .session import AgentDeckConfig, SessionContext
from .types import LogLevel, MatchResult, MatchResults


class AgentDeck:
    """Public API facade for the AgentDeck framework."""

    def __init__(
        self,
        game: Optional[Game] = None,
        spectators: Optional[List[Spectator]] = None,
        recorder: Optional[Recorder] = None,
        session: Optional[AgentDeckConfig] = None,
    ) -> None:
        """Construct a new :class:`AgentDeck` instance.

        Args:
            game: Optional default game used when ``play`` is called without explicit override.
            spectators: Spectators attached to every match (statistics, logging, etc.).
            recorder: Optional pre-configured recorder. When omitted a default recorder is
                created automatically using the session's recording directory.
            session: Configuration describing seed, logging, and persistence preferences.
        """
        self.default_game = game
        self.total_matches = 0
        self._closed = False  # Idempotence guard for cleanup

        config = session or AgentDeckConfig()
        self.session = SessionContext.create(config)
        self.session_start_time = self.session.started_at
        self.config = self.session.config
        self.seed = self.session.seed

        self.session.ensure_directories()

        self.logger = create_logger(self.session)

        # Prepare recorder
        if recorder is None:
            recorder = Recorder(session=self.session)
        else:
            recorder.bind_session(self.session)
        self.recorder = recorder

        # Console orchestrator with injected session settings
        # Pass spectators=None through to enable Console auto-attachment (SPEC-CONSOLE §5)
        self.console = Console(
            recorder=recorder,
            spectators=spectators,  # Don't convert None to [] - let Console handle auto-attachment
            session=self.session,
            logger=self.logger,
        )

        if self.logger:
            self._log_session_banner(game, spectators)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _log_session_banner(
        self, game: Optional[Game], spectators: Optional[List[Spectator]]
    ) -> None:
        """Emit a descriptive session header to the logger."""
        assert self.logger is not None  # for type checkers
        self.logger.info("=" * 70)
        self.logger.info("AgentDeck Initialized")
        self.logger.info("=" * 70)
        self.logger.info("Configuration:")
        if game:
            self.logger.info(f"  Default Game: {game.__class__.__name__}")
        self.logger.info(f"  Seed: {self.session.seed}")
        self.logger.info(f"  Max Turns: {self.session.max_turns}")
        self.logger.info(f"  Session ID: {self.session.session_id}")

        rel_log_dir = os.path.relpath(self.session.log_directory, os.getcwd())
        self.logger.info(f"  Log Directory: {rel_log_dir}")

        rel_record_dir = os.path.relpath(self.session.record_directory, os.getcwd())
        self.logger.info(f"  Recorder Directory: {rel_record_dir}")

        log_level = self.session.log_level
        self.logger.info(
            f"  Console Logging: {log_level.value if isinstance(log_level, LogLevel) else 'disabled'}"
        )
        file_levels = [level.value for level in self.session.log_file_levels]
        self.logger.info(f"  File Logging: {file_levels if file_levels else 'disabled'}")
        self.logger.info(f"  Log Format: {self.session.log_format}")
        if spectators:
            self.logger.info(f"  Spectators: {[s.__class__.__name__ for s in spectators]}")
        self.logger.info("=" * 70)

    def _prepare_batch(
        self,
        game: Optional[Game],
        players: List[Player],
        matches: int,
        seed: Optional[int],
    ) -> tuple:
        """Resolve batch configuration before execution."""
        resolved_game = game or self.default_game
        if resolved_game is None:
            raise ValueError("No game specified and no default game configured")

        base_seed = seed if seed is not None else self.session.seed
        batch_id = str(uuid.uuid4())[:8]
        return resolved_game, batch_id, base_seed

    def _log_player_details(self, players: List[Player]) -> None:
        """Log detailed player information on first batch using get_summary() protocol."""
        if not self.logger:
            return
        if self.total_matches > 0:
            return
        self.logger.info("")
        self.logger.info("Player Details:")
        for player in players:
            # Use the centralized get_summary() protocol
            summary = player.get_summary()
            self.logger.info(f"  {summary.get('name', player.name)}:")

            # Log all fields from summary except 'name' and 'type' (already shown)
            for key, value in summary.items():
                if key in ("name", "type"):
                    continue
                # Format key as human-readable (e.g., 'max_tokens' -> 'Max Tokens')
                display_key = key.replace("_", " ").title()
                self.logger.info(f"    {display_key}: {value}")

    def _run_batch(
        self,
        game: Game,
        players: List[Player],
        matches: int,
        base_seed: Optional[int],
        execution_spectators: Optional[List[Spectator]] = None,
    ) -> List[MatchResult]:
        """Delegate execution to the console orchestrator.

        Args:
            game: Game instance to run
            players: List of players
            matches: Number of matches
            base_seed: Base seed for determinism
            execution_spectators: Optional execution-scoped spectators (additive with session spectators)
        """
        # Pass execution spectators directly to Console.run()
        # Console handles subscription/unsubscription and combines with session spectators
        return self.console.run(
            game,
            players,
            matches=matches,
            seed=base_seed,
            spectators=execution_spectators,
        )

    def _calculate_costs(self, results: List[MatchResult]) -> tuple:
        """
        Calculate API costs from match results.

        Aggregates costs from match metadata (per-match deltas) rather than
        reading player.total_cost directly (which only reflects last match).

        Args:
            results: List of MatchResult objects containing metadata with player_costs

        Returns:
            Tuple of (total_cost, player_costs_dict)
        """
        total_cost = 0.0
        player_costs: Dict[str, float] = {}
        matches_missing_costs = 0

        for match in results:
            match_player_costs = match.metadata.get("player_costs")
            if not isinstance(match_player_costs, dict):
                matches_missing_costs += 1
                continue

            for player_name, cost in match_player_costs.items():
                amount = float(cost or 0.0)
                player_costs[player_name] = player_costs.get(player_name, 0.0) + amount
                total_cost += amount

        if matches_missing_costs and self.logger:
            self.logger.warning(
                "Cost metadata missing for %d match(es); batch totals may be incomplete.",
                matches_missing_costs,
            )

        return total_cost, player_costs

    def _log_batch_summary(
        self,
        results: List[MatchResult],
        batch_results: MatchResults,
        players: List[Player],
    ) -> None:
        """Log comprehensive batch summary including costs."""
        if not self.logger:
            return

        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("Batch Summary:")

        if len(results) == 1:
            match = results[0]
            self.logger.info(f"  Winner: {match.winner if match.winner else 'Draw'}")
            self.logger.info(f"  Total Turns: {match.metadata.get('turns', 'N/A')}")
            self.logger.info(f"  Duration: {match.metadata.get('duration', 0):.2f}s")
        else:
            self.logger.info(f"  Matches Completed: {len(results)}")
            self.logger.info(f"  Win Rates: {batch_results.win_rates}")
            for line in batch_results.summary.split("\n"):
                if line.strip():
                    self.logger.info(f"    {line}")

        total_cost, player_costs = self._calculate_costs(results)
        if player_costs:
            self.logger.info("")
            self.logger.info("API Costs:")
            for player_name, cost in player_costs.items():
                self.logger.info(f"  {player_name}: ${cost:.4f}")
            self.logger.info(f"  Total: ${total_cost:.4f}")
            if results:
                self.logger.info(f"  Average per match: ${total_cost / len(results):.4f}")

        self.logger.info("=" * 70)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def play(
        self,
        players: List[Player],
        game: Optional[Game] = None,
        matches: int = 1,
        seed: Optional[int] = None,
        spectators: Optional[List[Spectator]] = None,
    ) -> MatchResults:
        """Run the specified number of matches and return the aggregated results.

        Args:
            players: List of players participating in the matches
            game: Game to play (uses default_game if not specified)
            matches: Number of matches to run
            seed: Seed for reproducible randomness
            spectators: Optional execution-scoped spectators (additive with session spectators)

        Reproducibility:
            If the session (or ``seed`` argument) provides a seed, each match in the
            batch is executed with a deterministic seed derived from ``seed`` plus the
            match index. Omitting both values results in stochastic behaviour based on
            process randomness.

        Raises:
            ValueError: If players list is empty, has duplicate names, or if matches < 1.
            TypeError: If seed is provided but not an integer.
        """
        # Validate inputs
        if not players:
            raise ValueError("'players' cannot be empty. Provide at least one player.")

        # Check for duplicate player names
        player_names = [p.name for p in players]
        if len(player_names) != len(set(player_names)):
            duplicates = [name for name in set(player_names) if player_names.count(name) > 1]
            raise ValueError(
                f"Player names must be unique. "
                f"Found duplicate{'s' if len(duplicates) > 1 else ''}: {', '.join(sorted(duplicates))}"
            )

        # Validate matches count
        if matches < 1:
            raise ValueError(f"'matches' must be >= 1, got {matches}")

        # Validate seed type if provided
        if seed is not None and not isinstance(seed, int):
            raise TypeError(f"'seed' must be an integer or None, got {type(seed).__name__}")

        resolved_game, batch_id, base_seed = self._prepare_batch(game, players, matches, seed)
        self._log_player_details(players)

        if self.logger:
            self.logger.batch_start(
                batch_id=batch_id,
                game=resolved_game.__class__.__name__,
                players=[p.name for p in players],
                matches=matches,
            )

        results = self._run_batch(resolved_game, players, matches, base_seed, spectators)
        self.total_matches += len(results)
        batch_results = MatchResults(results)

        if self.logger:
            self.logger.batch_end(
                batch_id=batch_id,
                results={
                    "matches_completed": len(results),
                    "win_rates": batch_results.win_rates,
                },
            )

        self._log_batch_summary(results, batch_results, players)

        return batch_results

    def replay(
        self,
        match: Optional[Union[MatchResult, Dict[str, Any]]] = None,
        *,
        path: Optional[Union[str, os.PathLike[str]]] = None,
        spectators: Optional[List[Spectator]] = None,
        speed: float = 1.0,
    ) -> None:
        """Replay a recorded match either from memory or from disk.

        Args:
            match: MatchResult or dict to replay (mutually exclusive with path)
            path: File path to load match from (mutually exclusive with match)
            spectators: Optional spectators for replay (defaults to session spectators)
            speed: Playback speed multiplier (0.5 = slow, 2.0 = fast)

        Raises:
            ValueError: If both or neither of match/path are provided
        """
        provided = (match is not None) + (path is not None)
        if provided != 1:
            raise ValueError("Provide exactly one of 'match' or 'path'.")

        if path is not None:
            match_data = Recorder.load_match(os.fspath(path))
        else:
            match_data = match  # type: ignore[assignment]

        engine = ReplayEngine(match_data)
        spectator_list = spectators if spectators is not None else self.console.spectators
        engine.replay(spectator_list, speed)

    def replay_batch(
        self,
        matches: List[Union[MatchResult, Dict[str, Any]]],
        spectators: Optional[List[Spectator]] = None,
        speed: float = 1.0,
    ) -> None:
        """Replay multiple matches in sequence.

        Args:
            matches: List of MatchResult objects or dicts to replay
            spectators: Optional spectators for replay (defaults to session spectators)
            speed: Playback speed multiplier applied to all matches

        Example:
            >>> results = deck.play(players, matches=10)
            >>> # Replay first 3 matches
            >>> deck.replay_batch(results.matches[:3])
        """
        for match in matches:
            self.replay(match=match, spectators=spectators, speed=speed)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics without triggering cleanup.

        Useful for checking progress during long-running experiments without
        ending the session.

        Returns:
            Dictionary containing session metadata, match count, elapsed time,
            and output directory paths.

        Example:
            >>> deck = AgentDeck(game=CombatGame(), seed=42)
            >>> for i in range(10):
            ...     deck.play(players, matches=100)
            ...     stats = deck.get_session_stats()
            ...     print(f"Completed {stats['total_matches']} matches in {stats['elapsed_time']:.1f}s")
        """
        return {
            "session_id": self.session.session_id,
            "total_matches": self.total_matches,
            "elapsed_time": time.time() - self.session_start_time,
            "log_directory": self.session.log_directory,
            "record_directory": self.session.record_directory,
            "seed": self.session.seed,
            "max_turns": self.session.max_turns,
        }

    # ------------------------------------------------------------------
    # Context Manager Protocol
    # ------------------------------------------------------------------
    def __enter__(self) -> "AgentDeck":
        """Enter context manager - returns self for use in with statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager - guaranteed cleanup on context exit."""
        self._cleanup()
        # Return None (or False) to propagate exceptions
        return None

    def _cleanup(self) -> None:
        """Cleanup logic extracted for reuse by both __exit__ and __del__.

        Idempotent - safe to call multiple times, only runs once.
        """
        # Guard against double cleanup
        if self._closed:
            return

        if not hasattr(self, "console"):
            return

        try:
            # Mark as closed before any I/O to ensure idempotence even if cleanup fails
            self._closed = True

            if hasattr(self, "console") and self.console:
                try:
                    self.console.close()
                except Exception:
                    pass

            # Log summary only if logger is available
            if hasattr(self, "logger") and self.logger:
                session_duration = time.time() - self.session_start_time

                self.logger.info("")
                self.logger.info("=" * 70)
                self.logger.info("Session Complete")
                self.logger.info("=" * 70)
                self.logger.info("Session Statistics:")
                self.logger.info(f"  Total Matches: {self.total_matches}")
                self.logger.info(f"  Total Duration: {session_duration:.2f}s")
                self.logger.info("")
                self.logger.info("Output Directories:")
                log_path = str(self.session.log_directory)
                rel_log_path = os.path.relpath(log_path, os.getcwd())
                self.logger.info(f"  Logs: {rel_log_path}/")
                if hasattr(self, "recorder") and self.recorder:
                    rel_recorder_path = os.path.relpath(self.session.record_directory, os.getcwd())
                    self.logger.info(f"  Recordings: {rel_recorder_path}/")
                self.logger.info("=" * 70)
        except Exception:
            # Best-effort cleanup - suppress exceptions
            pass

    def __del__(self) -> None:
        """Best-effort session summary on destruction (fallback for non-context-manager usage)."""
        try:
            self._cleanup()
        except Exception:
            # Suppress all exceptions in __del__
            pass
