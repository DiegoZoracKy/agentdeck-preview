"""Progress monitoring for batch execution.

Per SPEC-MONITOR v1.0.0 §5.3:
- Provides three output modes: quiet, normal, verbose
- Tracks completed/total, elapsed time, ETA
- Auto-attached when concurrency > 1 (unless monitors explicitly provided)
- Displays real-time feedback during parallel execution
"""

from __future__ import annotations

import sys
import time
from typing import Literal, Optional

from ..core.types import Event
from .base import Monitor


class ProgressMonitor(Monitor):
    """
    Default console monitor for tracking batch execution progress.

    Displays real-time progress during batch execution with three output modes:

    - **quiet**: Minimal single-line progress bar
      ```
      [████████████░░░░░░░░] 60/100 (60%)
      ```

    - **normal**: Status updates at completion milestones (default)
      ```
      🚀 Starting batch: 100 matches (concurrency=10)
        ✓ 10/100 (10%) | ETA: 4m 30s
        ✓ 20/100 (20%) | ETA: 3m 45s
        ...
      🎉 Batch complete: 100/100 matches | Duration: 5m 12s | Avg: 3.1s/match
      ```

    - **verbose**: Detailed worker-level logs
      ```
      🚀 Starting batch: 100 matches (concurrency=10)
        ▶ Worker 0: Starting match 0
        ▶ Worker 1: Starting match 1
        ...
        ✓ Worker 0: Complete | Winner: Alice | 42 turns | 3.2s
        ✓ Worker 1: Complete | Winner: Bob | 38 turns | 2.9s
        ...
      🎉 Batch complete: 100/100 matches | Duration: 5m 12s | Avg: 3.1s/match
      ```

    Usage:
        # Default (auto-attached when concurrency > 1)
        config = AgentDeckConfig(concurrency=10)
        deck = AgentDeck(game=game, session=config)

        # Explicit mode
        config = AgentDeckConfig(
            concurrency=10,
            monitors=[ProgressMonitor(mode="verbose")]
        )

        # Opt-out (silent execution)
        config = AgentDeckConfig(concurrency=10, monitors=[])

    Per SPEC-MONITOR v1.0.0 §6:
    - PA1-PA4: Progress reporting accuracy invariants
    - ML2: Auto-attached when concurrency > 1 and monitors=None
    """

    def __init__(self, mode: Literal["quiet", "normal", "verbose"] = "normal"):
        """
        Initialize progress monitor with output mode.

        Args:
            mode: Output verbosity level
                - quiet: Single-line progress bar only
                - normal: Milestone updates with ETA (default)
                - verbose: Detailed worker start/complete/fail logs
        """
        super().__init__()
        self.mode = mode

        # Batch state
        self._batch_id: Optional[str] = None
        self._batch_start_time: Optional[float] = None
        self._total: int = 0
        self._completed: int = 0
        self._failed: int = 0
        self._match_durations: list[float] = []
        self._workers_started: int = 0  # Track worker starts for initial feedback

        # Terminal detection (for carriage return support)
        self._use_carriage_return = sys.stdout.isatty() and self.mode == "quiet"

    def on_console_batch_start(self, event: Event) -> None:
        """Display batch start message and reset state."""
        data = event.data
        self._batch_id = data["batch_id"]
        self._batch_start_time = time.time()
        self._total = data["total_matches"]
        self._completed = 0
        self._failed = 0
        self._match_durations = []
        self._workers_started = 0

        if self.mode in ("normal", "verbose"):
            mode = data.get("mode", "sequential")
            concurrency = data.get("concurrency", 1)

            msg = f"🚀 Starting batch: {self._total} match"
            if self._total != 1:
                msg += "es"

            if mode == "parallel":
                msg += f" (concurrency={concurrency})"

            print(msg, flush=True)  # Flush immediately for real-time output

    def on_console_batch_progress(self, event: Event) -> None:
        """
        Update progress display.

        Called at least once per completed match.
        """
        data = event.data
        self._completed = data["completed"]

        if self.mode == "quiet":
            # Progress bar: [████████░░░░░░░░░░░░] 42/100 (42%)
            self._display_progress_bar()

    def on_console_worker_start(self, event: Event) -> None:
        """Log worker start. Verbose mode shows per-worker details, normal mode shows initial progress."""
        self._workers_started += 1

        if self.mode == "verbose":
            # Verbose: Show each worker starting
            data = event.data
            match_index = data["match_index"]
            worker_id = data.get("worker_id", match_index)
            print(f"  ▶ Worker {worker_id}: Starting match {match_index}", flush=True)
        elif self.mode == "normal" and self._workers_started == 1:
            # Normal: Show "Executing..." message once when first worker starts
            print(f"  ⏳ Executing matches...", flush=True)

    def on_console_worker_complete(self, event: Event) -> None:
        """Log worker completion and update progress."""
        data = event.data
        duration = data.get("duration", 0)
        self._match_durations.append(duration)

        if self.mode == "normal":
            # Update every 10% milestone or final match
            self._display_milestone_progress()

        elif self.mode == "verbose":
            # Detailed worker completion log
            worker_id = data.get("worker_id", data.get("match_index", "?"))
            winner = data.get("winner") or "Draw"
            turns = data.get("turns", "?")
            print(
                f"  ✓ Worker {worker_id}: Complete | "
                f"Winner: {winner} | {turns} turns | {duration:.2f}s",
                flush=True,
            )

    def on_console_worker_failed(self, event: Event) -> None:
        """Log worker failure."""
        data = event.data
        self._failed += 1

        if self.mode != "quiet":
            worker_id = data.get("worker_id", data.get("match_index", "?"))
            error_type = data.get("error_type", "Error")
            error_msg = data.get("error_message", "Unknown error")
            print(f"  ✗ Worker {worker_id}: FAILED | {error_type}: {error_msg}", flush=True)

    def on_console_batch_complete(self, event: Event) -> None:
        """Display batch completion summary."""
        data = event.data
        duration = data.get("duration", 0)
        avg_duration = data.get("avg_match_duration", 0)
        completed = data.get("completed", self._completed)
        total = data.get("total", self._total)
        failed = data.get("failed", self._failed)

        if self.mode == "quiet":
            # Newline after progress bar
            print(flush=True)

        # Completion message
        print(
            f"🎉 Batch complete: {completed}/{total} match"
            + ("es" if total != 1 else "")
            + f" | Duration: {self._format_duration(duration)} | "
            + f"Avg: {avg_duration:.2f}s/match",
            flush=True,
        )

        # Failure warning
        if failed > 0:
            print(f"⚠️  {failed} match" + ("es" if failed != 1 else "") + " failed", flush=True)

    def _display_progress_bar(self) -> None:
        """Display single-line progress bar (quiet mode)."""
        if self._total == 0:
            return

        pct = (self._completed / self._total) * 100
        bar_width = 20
        filled = int((self._completed / self._total) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        msg = f"[{bar}] {self._completed}/{self._total} ({pct:.0f}%)"

        if self._use_carriage_return and self._completed < self._total:
            # In-place update for terminals
            sys.stdout.write(f"\r{msg}")
            sys.stdout.flush()
        else:
            # Newline for non-terminal or final update
            print(msg, flush=True)

    def _display_milestone_progress(self) -> None:
        """Display progress at milestones (normal mode)."""
        if self._total == 0:
            return

        # Calculate milestone (10% or every match if < 10 matches)
        milestone = max(1, self._total // 10)

        # Display at milestones or final match
        if self._completed % milestone == 0 or self._completed == self._total:
            pct = (self._completed / self._total) * 100

            # Calculate ETA from average duration
            eta_str = ""
            if self._match_durations and self._completed < self._total:
                avg_duration = sum(self._match_durations) / len(self._match_durations)
                remaining = self._total - self._completed
                eta_seconds = avg_duration * remaining
                eta_str = f" | ETA: {self._format_duration(eta_seconds)}"

            print(f"  ✓ {self._completed}/{self._total} ({pct:.0f}%){eta_str}", flush=True)

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration as human-readable string.

        Examples:
            45 seconds → "45s"
            125 seconds → "2m 5s"
            3725 seconds → "1h 2m"
        """
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
