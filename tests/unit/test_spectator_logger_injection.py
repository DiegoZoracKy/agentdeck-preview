"""
Unit tests for SPEC-SPECTATOR v1.2.0 Logger Injection (LI1-LI5).

Tests verify that Console and ReplayEngine inject logger into spectators
before event subscription, enabling spectators to write to core log streams.

Test Coverage:
- LI1: Console/ReplayEngine inject logger if spectator.logger is None
- LI2: Injected logger is the same AgentDeckLogger instance
- LI3: Spectators with constructor logger bypass injection
- LI4: Injection occurs for both session and execution spectators
- LI5: Spectator logger writes to core log streams
"""

from agentdeck import AgentDeck
from agentdeck.core.base.spectator import Spectator
from agentdeck.core.logging import InMemoryLogHandler, NullLogger
from agentdeck.core.replay import ReplayEngine
from agentdeck.core.session import AgentDeckConfig
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players.mock import MockPlayer


class LoggingSpectator(Spectator):
    """Test spectator that tracks logger injection and usage."""

    def __init__(self):
        super().__init__()
        self.logger_injected = False
        self.log_calls = []

    def on_batch_start(self, batch_id, game, players, matches, context=None, **kwargs):
        """Verify logger was injected."""
        self.logger_injected = self.logger is not None
        if self.logger:
            self.logger.info(f"Batch {batch_id} starting")
            self.log_calls.append(f"batch_start:{batch_id}")

    def on_match_start(self, game, players, match_id=None, context=None, **kwargs):
        """Log match start."""
        if self.logger:
            self.logger.info(f"Match {match_id} starting")
            self.log_calls.append(f"match_start:{match_id}")


class PreConfiguredSpectator(Spectator):
    """Test spectator with logger provided in constructor."""

    def __init__(self, logger):
        super().__init__(logger=logger)
        self.original_logger = logger
        self.logger_changed = False

    def on_batch_start(self, batch_id, game, players, matches, context=None, **kwargs):
        """Check if logger was replaced."""
        self.logger_changed = self.logger != self.original_logger


class InfoLoggingSpectator(Spectator):
    """Test spectator that writes to INFO log stream."""

    def on_batch_start(self, batch_id, game, players, matches, context=None, **kwargs):
        if self.logger:
            self.logger.info(f"[SPECTATOR] Batch {batch_id} starting")


# ============================================================================
# LI1 & LI2: Console injects logger (same instance)
# ============================================================================


def test_console_injects_logger_into_session_spectators():
    """
    Verify LI1 & LI2: Console injects logger into session spectators.

    SPEC-SPECTATOR v1.2.0 §5.5 LI1:
    Console MUST inject logger into spectators if spectator.logger is None.

    SPEC-SPECTATOR v1.2.0 §5.5 LI2:
    Injected logger MUST be the same AgentDeckLogger instance.
    """
    # Session spectator (no logger in constructor)
    session_spec = LoggingSpectator()
    assert session_spec.logger is None  # Not injected yet

    # Create AgentDeck (which creates Console internally)
    game = FixedDamageGame()
    with AgentDeck(game=game, spectators=[session_spec]) as deck:
        # LI1: Console MUST inject logger during construction
        assert session_spec.logger is not None

        # LI2: Injected logger MUST be AgentDeckLogger instance
        assert session_spec.logger is deck.logger


def test_console_injects_logger_into_execution_spectators(mock_player_pair):
    """
    Verify LI1 & LI4: Console injects logger into execution spectators.

    SPEC-SPECTATOR v1.2.0 §5.5 LI4:
    Logger injection MUST occur for execution spectators (attached during play()).
    """
    # Execution spectator (no logger in constructor)
    exec_spec = LoggingSpectator()
    assert exec_spec.logger is None

    game = FixedDamageGame()

    with AgentDeck(game=game) as deck:
        # Execute with execution spectator
        deck.play(players=mock_player_pair, matches=1, spectators=[exec_spec])

        # LI1/LI4: Console MUST inject logger for execution spectators
        assert exec_spec.logger is not None
        assert exec_spec.logger is deck.logger


def test_console_injects_same_logger_for_session_and_execution_spectators():
    """
    Verify LI2: Both session and execution spectators receive same logger instance.
    """
    session_spec = LoggingSpectator()
    exec_spec = LoggingSpectator()

    game = FixedDamageGame()
    players = [
        MockPlayer(name="Player-1"),
        MockPlayer(name="Player-2"),
    ]

    with AgentDeck(game=game, spectators=[session_spec]) as deck:
        deck.play(players=players, matches=1, spectators=[exec_spec])

        # LI2: Both spectators MUST receive the same logger instance
        assert session_spec.logger is deck.logger
        assert exec_spec.logger is deck.logger
        assert session_spec.logger is exec_spec.logger


# ============================================================================
# LI3: Spectators with constructor logger bypass injection
# ============================================================================


def test_spectator_with_constructor_logger_bypasses_injection():
    """
    Verify LI3: Spectator with logger in constructor bypasses injection.

    SPEC-SPECTATOR v1.2.0 §5.5 LI3:
    Spectators MAY receive logger via constructor, bypassing late-binding injection.
    """
    custom_logger = NullLogger()
    spectator = PreConfiguredSpectator(logger=custom_logger)

    game = FixedDamageGame()

    with AgentDeck(game=game, spectators=[spectator]) as deck:
        deck.play(players=[MockPlayer(name="P1"), MockPlayer(name="P2")], matches=1)

        # LI3: Spectator with logger MUST NOT have it replaced
        assert spectator.logger is custom_logger
        assert not spectator.logger_changed


# ============================================================================
# LI4: Injection for both session and execution spectators
# ============================================================================


def test_logger_injection_for_both_session_and_execution_scopes():
    """
    Verify LI4: Logger injection occurs for both session and execution spectators.

    SPEC-SPECTATOR v1.2.0 §5.5 LI4:
    Logger injection MUST occur for BOTH session spectators (attached at Console
    construction) AND execution spectators (attached during play() call).
    """
    session_spec = LoggingSpectator()
    exec_spec_1 = LoggingSpectator()
    exec_spec_2 = LoggingSpectator()

    game = FixedDamageGame()
    players = [
        MockPlayer(name="Player-1"),
        MockPlayer(name="Player-2"),
    ]

    with AgentDeck(game=game, spectators=[session_spec]) as deck:
        # First execution
        deck.play(players=players, matches=1, spectators=[exec_spec_1])

        # Second execution
        deck.play(players=players, matches=1, spectators=[exec_spec_2])

        # LI4: All spectators MUST have logger injected
        assert session_spec.logger is deck.logger
        assert exec_spec_1.logger is deck.logger
        assert exec_spec_2.logger is deck.logger

        # Verify spectators could use logger
        assert session_spec.logger_injected
        assert exec_spec_1.logger_injected
        assert exec_spec_2.logger_injected


# ============================================================================
# LI5: Spectator logger writes to core log streams
# ============================================================================


def test_spectator_logger_writes_to_core_streams():
    """
    Verify LI5: Spectator logger writes to core log streams.

    SPEC-SPECTATOR v1.2.0 §5.5 LI5:
    When spectator uses logger, it WRITES to core log streams (info.log, debug.log,
    console) via logger.info(), logger.debug(), etc.
    """
    spectator = InfoLoggingSpectator()

    game = FixedDamageGame()
    players = [
        MockPlayer(name="Player-1"),
        MockPlayer(name="Player-2"),
    ]

    # Create deck with in-memory handler
    handler = InMemoryLogHandler()
    from agentdeck.core.logging import LogLevel

    # Enable logging at INFO level so logger exists
    session_config = AgentDeckConfig(
        log_level=LogLevel.INFO,  # Enable console logging at INFO
        log_file_levels=[],  # Disable file logging
    )

    with AgentDeck(game=game, session=session_config, spectators=[spectator]) as deck:
        # Add handler to capture all logs
        if deck.logger and hasattr(deck.logger, "logger"):
            deck.logger.logger.addHandler(handler)

        deck.play(players=players, matches=1)

        # LI5: Spectator log calls MUST appear in core log stream
        log_messages = [record.getMessage() for record in handler.records]
        spectator_logs = [msg for msg in log_messages if "[SPECTATOR]" in msg]
        assert (
            len(spectator_logs) > 0
        ), f"Spectator logs should appear in core log stream. Got {len(handler.records)} total logs, spectator called logger: {spectator.logger is not None}"


# ============================================================================
# ReplayEngine Logger Injection
# ============================================================================


def test_replay_engine_injects_logger_into_spectators():
    """
    Verify LI1 & LI2: ReplayEngine injects logger into spectators.

    SPEC-SPECTATOR v1.2.0 §5.5 LI1:
    ReplayEngine MUST inject logger into spectators if spectator.logger is None.

    SPEC-SPECTATOR v1.2.0 §5.5 LI2:
    Injected logger MUST be the same instance as ReplayEngine.logger.
    """
    from agentdeck.core.types import MatchResult

    # Create minimal MatchResult for replay
    match_result = MatchResult(
        winner="Player-1",
        final_state={"winner": "Player-1"},
        events=[],
        seed=42,
        metadata={
            "match_id": "test-match-1",
            "game": "TestGame",
            "players": ["Player-1", "Player-2"],
            "schema_version": "1.3",  # Required for v1.3.0 schema validation
        },
    )

    # Create ReplayEngine and assign a logger (any logger instance works)
    replay_engine = ReplayEngine(match_result)
    test_logger = NullLogger()
    replay_engine.logger = test_logger

    # Create spectator without logger
    spectator = LoggingSpectator()
    assert spectator.logger is None  # Not injected yet

    # Replay with spectator
    replay_engine.replay(spectators=[spectator])

    # LI1: ReplayEngine MUST inject logger during replay()
    assert spectator.logger is not None

    # LI2: Injected logger MUST be the same instance as ReplayEngine.logger
    assert spectator.logger is test_logger
    assert spectator.logger is replay_engine.logger


# ============================================================================
# Edge Cases
# ============================================================================


def test_spectator_without_logger_attribute_doesnt_crash():
    """
    Verify framework handles spectators without logger attribute gracefully.

    Per LI1, framework checks getattr(spectator, 'logger', None) before injection.
    """

    class MinimalSpectator:
        """Spectator without inheriting from base Spectator class."""

        def on_batch_start(self, batch_id, game, players, matches, context=None, **kwargs):
            pass

    spectator = MinimalSpectator()

    game = FixedDamageGame()
    players = [
        MockPlayer(name="Player-1"),
        MockPlayer(name="Player-2"),
    ]

    # Should not crash even though spectator has no logger attribute
    with AgentDeck(game=game, spectators=[spectator]) as deck:
        deck.play(players=players, matches=1)


def test_multiple_spectators_all_receive_logger():
    """Verify all spectators in list receive logger injection."""
    spec_1 = LoggingSpectator()
    spec_2 = LoggingSpectator()
    spec_3 = LoggingSpectator()

    game = FixedDamageGame()
    players = [
        MockPlayer(name="Player-1"),
        MockPlayer(name="Player-2"),
    ]

    with AgentDeck(game=game, spectators=[spec_1, spec_2, spec_3]) as deck:
        deck.play(players=players, matches=1)

        # All spectators MUST receive logger
        assert spec_1.logger is deck.logger
        assert spec_2.logger is deck.logger
        assert spec_3.logger is deck.logger

        assert spec_1.logger_injected
        assert spec_2.logger_injected
        assert spec_3.logger_injected
