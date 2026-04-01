"""
Test auto-attachment of MatchReporter spectator per SPEC-CONSOLE §5.

Validates that Console auto-attaches MatchReporter when spectators=None
and respects explicit spectator lists (including empty lists).
"""

import pytest

from agentdeck.core.base import Spectator
from agentdeck.core.console import Console
from agentdeck.core.session import AgentDeckConfig, SessionContext
from agentdeck.spectators import MatchReporter


class CustomSpectator(Spectator):
    """Test spectator for validation."""


class TestAutoAttachMatchReporter:
    """Test auto-attachment of MatchReporter per SPEC-CONSOLE §5."""

    def test_auto_attach_when_spectators_none(self, temp_session_dir):
        """
        When spectators=None (omitted), Console MUST auto-attach MatchReporter.

        Per SPEC-CONSOLE §5 "Default Session Spectators":
        - Auto-attach MatchReporter when spectators is None
        - Subscribe it before SESSION_START emission
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        # Call with spectators=None (default)
        console = Console(session=session, spectators=None)

        # Verify MatchReporter was auto-attached
        assert len(console._base_spectators) == 1
        assert isinstance(console._base_spectators[0], MatchReporter)

        # Verify it's subscribed to event bus
        assert console._base_spectators[0] in console.event_bus._spectators

        console.close()

    def test_auto_attach_when_spectators_omitted(self, temp_session_dir):
        """
        When spectators parameter omitted, Console MUST auto-attach MatchReporter.

        Same as spectators=None (Python default parameter semantics).
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        # Call without spectators parameter (defaults to None)
        console = Console(session=session)

        # Verify MatchReporter was auto-attached
        assert len(console._base_spectators) == 1
        assert isinstance(console._base_spectators[0], MatchReporter)

        console.close()

    def test_explicit_empty_list_skips_auto_attach(self, temp_session_dir):
        """
        When spectators=[] (explicit empty list), Console MUST NOT auto-attach.

        Per SPEC-CONSOLE §5:
        - Explicit spectator list (even empty) bypasses auto-attachment
        - This is how users opt out of default reporter
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        # Call with explicit empty list
        console = Console(session=session, spectators=[])

        # Verify NO spectators attached
        assert len(console._base_spectators) == 0

        console.close()

    def test_explicit_spectators_skips_auto_attach(self, temp_session_dir):
        """
        When spectators=[...] (explicit list), Console MUST NOT auto-attach.

        User-provided spectators completely replace the default.
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        custom = CustomSpectator()

        # Call with explicit spectator list
        console = Console(session=session, spectators=[custom])

        # Verify ONLY custom spectator attached (no MatchReporter)
        assert len(console._base_spectators) == 1
        assert console._base_spectators[0] is custom
        assert not isinstance(console._base_spectators[0], MatchReporter)

        console.close()

    def test_explicit_match_reporter_allowed(self, temp_session_dir):
        """
        Users can still explicitly attach MatchReporter if desired.

        This allows customization (e.g., different modes in future).
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        reporter = MatchReporter()

        # Call with explicit MatchReporter
        console = Console(session=session, spectators=[reporter])

        # Verify the explicit reporter is attached
        assert len(console._base_spectators) == 1
        assert console._base_spectators[0] is reporter

        console.close()

    def test_logger_injection_for_auto_attached_reporter(self, temp_session_dir):
        """
        Auto-attached MatchReporter MUST receive logger injection.

        Per SPEC-CONSOLE §5:
        - Auto-attached spectators follow logger-injection rules (§6.5 P4)
        - Logger allows reporter output to flow through session logger
        """
        from agentdeck.core.logging import AgentDeckLogger

        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        # Create a logger instance
        test_logger = AgentDeckLogger(session)

        # Create console with logger
        console = Console(session=session, logger=test_logger)

        # Verify auto-attached reporter received logger injection
        reporter = console._base_spectators[0]
        assert isinstance(reporter, MatchReporter)
        assert reporter.logger is test_logger
        assert reporter.logger is console.logger

        console.close()


@pytest.fixture
def temp_session_dir(tmp_path):
    """Provide temporary directory for session logs/records."""
    return tmp_path / "test_session"
