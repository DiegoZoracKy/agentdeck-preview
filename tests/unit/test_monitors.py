"""
Unit tests for Monitor system (SPEC-MONITOR v1.0.0).

Tests:
- Monitor base class
- Default monitor attachment
- Console event emission
- Event isolation (monitors vs spectators)
- Logger injection
"""

from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.core.types import Event
from agentdeck.games.examples import FixedDamageGame
from agentdeck.monitors import Monitor, ProgressMonitor
from agentdeck.players import MockPlayer
from agentdeck.spectators import MatchReporter


class EventCollector(Monitor):
    """Test monitor that collects all console events."""

    def __init__(self):
        super().__init__()
        self.events = []

    def on_console_batch_start(self, event: Event) -> None:
        self.events.append(("batch_start", event.data))

    def on_console_batch_progress(self, event: Event) -> None:
        self.events.append(("batch_progress", event.data))

    def on_console_worker_start(self, event: Event) -> None:
        self.events.append(("worker_start", event.data))

    def on_console_worker_complete(self, event: Event) -> None:
        self.events.append(("worker_complete", event.data))

    def on_console_worker_failed(self, event: Event) -> None:
        self.events.append(("worker_failed", event.data))

    def on_console_batch_complete(self, event: Event) -> None:
        self.events.append(("batch_complete", event.data))


class SpectatorSpy(MatchReporter):
    """Test spectator that tracks which events it receives."""

    def __init__(self):
        super().__init__()
        self.received_event_types = []

    def on_batch_start(self, event: Event) -> None:
        self.received_event_types.append(event.type)
        super().on_batch_start(event)

    def on_match_start(self, event: Event) -> None:
        self.received_event_types.append(event.type)
        super().on_match_start(event)

    def on_gameplay(self, event: Event) -> None:
        self.received_event_types.append(event.type)
        super().on_gameplay(event)


def test_default_monitor_parallel():
    """Test default ProgressMonitor auto-attached when concurrency > 1."""
    config = AgentDeckConfig(concurrency=5)
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        # Verify console EventBus created
        assert hasattr(deck.console, "console_bus")

        # Verify ProgressMonitor attached
        monitors = deck.console.console_bus._spectators
        progress_monitors = [m for m in monitors if isinstance(m, ProgressMonitor)]
        assert len(progress_monitors) == 1
        assert progress_monitors[0].mode == "normal"


def test_no_default_monitor_sequential():
    """Test no default monitor for sequential execution (concurrency=1)."""
    config = AgentDeckConfig(concurrency=1)
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        # Verify console EventBus created (always present)
        assert hasattr(deck.console, "console_bus")

        # Verify NO ProgressMonitor attached
        monitors = deck.console.console_bus._spectators
        progress_monitors = [m for m in monitors if isinstance(m, ProgressMonitor)]
        assert len(progress_monitors) == 0


def test_explicit_opt_out():
    """Test monitors=[] explicitly opts out of default monitor."""
    config = AgentDeckConfig(concurrency=10, monitors=[])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        # Verify NO monitors attached (explicit opt-out)
        monitors = deck.console.console_bus._spectators
        assert len(monitors) == 0


def test_custom_monitors():
    """Test custom monitors can be attached."""
    collector = EventCollector()
    config = AgentDeckConfig(concurrency=3, monitors=[collector])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        # Verify custom monitor attached (not default)
        monitors = deck.console.console_bus._spectators
        assert len(monitors) == 1
        assert monitors[0] is collector

        # Run matches
        deck.play(players, matches=3)

    # Verify events received
    event_types = [e[0] for e in collector.events]
    assert "batch_start" in event_types
    assert "batch_complete" in event_types
    assert event_types.count("worker_complete") == 3
    assert event_types.count("batch_progress") == 3


def test_console_events_parallel():
    """Test console events emitted during parallel execution."""
    collector = EventCollector()
    config = AgentDeckConfig(concurrency=2, monitors=[collector])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        deck.play(players, matches=4)

    # Verify event sequence
    event_types = [e[0] for e in collector.events]

    # Should have batch_start at beginning
    assert event_types[0] == "batch_start"

    # Should have batch_complete at end
    assert event_types[-1] == "batch_complete"

    # Should have worker_start, worker_complete, and batch_progress for each match
    assert event_types.count("worker_start") == 4
    assert event_types.count("worker_complete") == 4
    assert event_types.count("batch_progress") == 4

    # Verify worker events are paired (each worker_start has matching worker_complete)
    # Per SPEC-MONITOR §6.2 EM5
    worker_starts = [e for e in collector.events if e[0] == "worker_start"]
    worker_completes = [e for e in collector.events if e[0] == "worker_complete"]
    worker_start_ids = {e[1]["worker_id"] for e in worker_starts}
    worker_complete_ids = {e[1]["worker_id"] for e in worker_completes}
    assert worker_start_ids == worker_complete_ids  # Same set of worker IDs

    # Verify batch_start payload
    batch_start = collector.events[0][1]
    assert batch_start["total_matches"] == 4
    assert batch_start["concurrency"] == 2
    assert batch_start["mode"] == "parallel"

    # Verify batch_complete payload
    batch_complete = collector.events[-1][1]
    assert batch_complete["completed"] == 4
    assert batch_complete["total"] == 4
    assert batch_complete["failed"] == 0
    assert "duration" in batch_complete
    assert "avg_match_duration" in batch_complete


def test_console_events_sequential():
    """Test console events emitted during sequential execution."""
    collector = EventCollector()
    config = AgentDeckConfig(concurrency=1, monitors=[collector])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        deck.play(players, matches=3)

    # Verify we got events
    assert len(collector.events) > 0

    # Verify event sequence
    event_types = [e[0] for e in collector.events]

    # Should have batch_start at beginning
    assert "batch_start" in event_types
    assert event_types[0] == "batch_start"

    # Should have batch_complete at end
    assert "batch_complete" in event_types
    assert event_types[-1] == "batch_complete"

    # Should have batch_progress for each match (no worker events in sequential)
    assert event_types.count("batch_progress") == 3
    assert event_types.count("worker_complete") == 0  # No workers in sequential

    # Verify batch_start payload
    batch_start_events = [e for e in collector.events if e[0] == "batch_start"]
    assert len(batch_start_events) > 0
    batch_start = batch_start_events[0][1]
    assert batch_start["total_matches"] == 3
    assert batch_start["concurrency"] == 1
    assert batch_start["mode"] == "sequential"


def test_event_isolation():
    """Test monitors don't receive match events, spectators don't receive console events."""
    collector = EventCollector()
    spectator = SpectatorSpy()

    config = AgentDeckConfig(concurrency=2, monitors=[collector])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, spectators=[spectator], session=config) as deck:
        deck.play(players, matches=2)

    # Monitor should receive only console events
    monitor_event_types = [e[0] for e in collector.events]
    assert all(evt.startswith(("batch_", "worker_")) for evt in monitor_event_types)

    # Spectator should receive only match events (NOT console events)
    spectator_event_types = spectator.received_event_types
    assert any(evt in ("batch_start", "match_start", "gameplay") for evt in spectator_event_types)
    assert not any(evt.startswith("console_") for evt in spectator_event_types)


def test_logger_injection():
    """Test logger injected into monitors before subscription."""

    class LoggerCheckMonitor(Monitor):
        def __init__(self):
            super().__init__()
            self.logger_injected = False

        def on_console_batch_start(self, event: Event) -> None:
            # Check if logger was injected
            self.logger_injected = self.logger is not None

    monitor = LoggerCheckMonitor()
    assert monitor.logger is None  # Not injected yet

    config = AgentDeckConfig(concurrency=2, monitors=[monitor])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        # Logger should be injected during Console.__init__
        assert monitor.logger is not None
        assert monitor.logger is deck.console.logger

        # Run to verify injection works during event handling
        deck.play(players, matches=1)

    assert monitor.logger_injected


def test_progress_reporter_quiet_mode():
    """Test ProgressMonitor quiet mode output."""
    monitor = ProgressMonitor(mode="quiet")
    config = AgentDeckConfig(concurrency=2, monitors=[monitor])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        deck.play(players, matches=5)

    # No assertions on output, just verify it doesn't crash
    # (quiet mode uses carriage returns which are hard to test)


def test_progress_reporter_normal_mode():
    """Test ProgressMonitor normal mode output."""
    monitor = ProgressMonitor(mode="normal")
    config = AgentDeckConfig(concurrency=2, monitors=[monitor])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        deck.play(players, matches=10)

    # No assertions on output, just verify it doesn't crash
    # Normal mode prints milestone progress


def test_progress_reporter_verbose_mode():
    """Test ProgressMonitor verbose mode output."""
    monitor = ProgressMonitor(mode="verbose")
    config = AgentDeckConfig(concurrency=2, monitors=[monitor])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        deck.play(players, matches=5)

    # No assertions on output, just verify it doesn't crash
    # Verbose mode prints worker-level logs


def test_batch_progress_eta_calculation():
    """Test batch progress includes ETA based on average duration."""
    collector = EventCollector()
    config = AgentDeckConfig(concurrency=2, monitors=[collector])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        deck.play(players, matches=5)

    # Find batch_progress events
    progress_events = [e for e in collector.events if e[0] == "batch_progress"]
    assert len(progress_events) > 0

    # First progress event may not have ETA (no completed matches yet)
    # Later events should have ETA
    later_progress = [e[1] for e in progress_events if e[1]["completed"] > 1]
    if later_progress:
        # Should have ETA once we have average duration
        assert any("estimated_remaining" in p for p in later_progress)


def test_monitor_exception_isolation():
    """Test monitor exceptions don't crash execution."""

    class CrashingMonitor(Monitor):
        def on_console_batch_start(self, event: Event) -> None:
            raise RuntimeError("Monitor crashed!")

    class HealthyMonitor(Monitor):
        def __init__(self):
            super().__init__()
            self.events_received = 0

        def on_console_batch_start(self, event: Event) -> None:
            self.events_received += 1

    crashing = CrashingMonitor()
    healthy = HealthyMonitor()

    config = AgentDeckConfig(concurrency=2, monitors=[crashing, healthy])
    game = FixedDamageGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=game, session=config) as deck:
        # Execution should complete despite crashing monitor
        results = deck.play(players, matches=3)

    # Verify execution completed
    assert len(results) == 3

    # Healthy monitor should have received events
    assert healthy.events_received > 0


def test_sequential_fallback_suppresses_worker_events():
    """
    Test that sequential fallback (get_player_order hook) does NOT emit worker events.

    Per SPEC-MONITOR §6.2 EM5: CONSOLE_WORKER_* events only during parallel execution.
    When a game overrides get_player_order(), Console falls back to sequential execution
    via _run_sequential() which uses _MatchWorker but should NOT emit worker events.
    """

    class GameWithHook(FixedDamageGame):
        """Game that forces sequential fallback via get_player_order hook."""

        def get_player_order(self, players, *, rng, match_context):
            # Returning player list forces sequential fallback
            return list(players)

    collector = EventCollector()
    config = AgentDeckConfig(concurrency=4, monitors=[collector])
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    with AgentDeck(game=GameWithHook(), session=config) as deck:
        deck.play(players, matches=3)

    event_types = [e[0] for e in collector.events]

    # Should have batch events
    assert "batch_start" in event_types
    assert "batch_progress" in event_types
    assert "batch_complete" in event_types

    # Should NOT have worker events (sequential fallback)
    assert "worker_start" not in event_types
    assert "worker_complete" not in event_types
    assert "worker_failed" not in event_types
