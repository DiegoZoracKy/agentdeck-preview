"""Base Monitor class for console-level observation.

Monitors observe console EventBus (live, immediate events).
Spectators observe match EventBus (buffered, replayed events).

Per SPEC-MONITOR v1.0.0:
- ML1-ML5: Monitor lifecycle (EventBus creation, attachment, logger injection)
- EM1-EM6: Event emission (console events only, live not buffered)
- EI1-EI4: Event isolation (monitors don't receive match events)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..core.logging import AgentDeckLogger
    from ..core.types import Event


class Monitor:
    """
    Base class for console/system-level observers.

    Monitors observe console-level events:
    - Batch execution progress
    - Worker lifecycle (start, complete, fail)
    - System metrics (hardware, checkpoints, etc.)

    Monitors do NOT observe match narrative events:
    - Match events (MATCH_START, MATCH_END)
    - Turn events (TURN_START, GAMEPLAY)
    - Player events (PLAYER_HANDSHAKE_*, PLAYER_CONCLUSION)

    Usage:
        class CustomMonitor(Monitor):
            def on_console_batch_start(self, event: Event) -> None:
                print(f"Batch starting: {event.data['total_matches']} matches")

            def on_console_worker_complete(self, event: Event) -> None:
                print(f"Match {event.data['match_index']} complete")

        config = AgentDeckConfig(concurrency=10, monitors=[CustomMonitor()])
        deck = AgentDeck(game=game, session=config)

    Event Handlers (all optional, duck-typed):
        - on_console_batch_start(event: Event) -> None
        - on_console_batch_progress(event: Event) -> None
        - on_console_worker_start(event: Event) -> None
        - on_console_worker_complete(event: Event) -> None
        - on_console_worker_failed(event: Event) -> None
        - on_console_batch_complete(event: Event) -> None

    Logger Injection:
        Console automatically injects logger before subscription if monitor.logger is None.
        Same pattern as Spectator (SPEC-SPECTATOR §5.5 LI1-LI5).
    """

    def __init__(self, *, logger: Optional[AgentDeckLogger] = None):
        """
        Initialize monitor with optional logger.

        Args:
            logger: Optional logger for structured output.
                    Console will inject logger if None (late-binding pattern).
        """
        self.logger = logger

    # All handlers optional (duck-typed by EventBus)

    def on_console_batch_start(self, event: Event) -> None:
        """
        Called when batch execution begins (sequential or parallel).

        Event payload:
            - batch_id: str
            - total_matches: int
            - concurrency: int
            - mode: Literal["sequential", "parallel"]
            - base_seed: Optional[int]
        """

    def on_console_batch_progress(self, event: Event) -> None:
        """
        Called periodically with batch progress updates.

        Fired at least once per completed match.

        Event payload:
            - batch_id: str
            - completed: int
            - total: int
            - in_progress: int (workers currently executing)
            - failed: int
            - elapsed_time: float
            - estimated_remaining: Optional[float] (None until first match completes)
        """

    def on_console_worker_start(self, event: Event) -> None:
        """
        Called when a parallel worker begins executing a match.

        Only fired during parallel execution (concurrency > 1).

        Event payload:
            - worker_id: int (match_index)
            - match_index: int
            - seed: Optional[int]
            - started_at: float
        """

    def on_console_worker_complete(self, event: Event) -> None:
        """
        Called when a parallel worker completes successfully.

        Only fired during parallel execution (concurrency > 1).

        Event payload:
            - worker_id: int
            - match_index: int
            - duration: float
            - winner: Optional[str]
            - turns: int
            - completed_at: float
        """

    def on_console_worker_failed(self, event: Event) -> None:
        """
        Called when a parallel worker encounters an error.

        Only fired during parallel execution (concurrency > 1).

        Event payload:
            - worker_id: int
            - match_index: int
            - error_type: str (exception class name)
            - error_message: str
            - failed_at: float
        """

    def on_console_batch_complete(self, event: Event) -> None:
        """
        Called when batch execution completes (all matches done).

        Event payload:
            - batch_id: str
            - completed: int
            - total: int
            - failed: int
            - duration: float
            - avg_match_duration: float
            - seeds_used: List[Optional[int]]
        """
