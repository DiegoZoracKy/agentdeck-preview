"""
Test auto-attachment of MatchNarrator spectator per SPEC-CONSOLE §5.

Validates that Console auto-attaches MatchNarrator when spectators=None
and respects explicit spectator lists (including empty lists).
"""

import pytest

from agentdeck.core.base import Spectator
from agentdeck.core.console import Console
from agentdeck.core.session import AgentDeckConfig, SessionContext
from agentdeck.spectators import MatchNarrator


class CustomSpectator(Spectator):
    """Test spectator for validation."""


class TestAutoAttachMatchNarrator:
    """Test auto-attachment of MatchNarrator per SPEC-CONSOLE §5."""

    def test_auto_attach_when_spectators_none(self, temp_session_dir):
        """
        When spectators=None (omitted), Console MUST auto-attach MatchNarrator.

        Per SPEC-CONSOLE §5 "Default Session Spectators":
        - Auto-attach MatchNarrator when spectators is None
        - Subscribe it before SESSION_START emission
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        # Call with spectators=None (default)
        console = Console(session=session, spectators=None)

        # Verify MatchNarrator was auto-attached
        assert len(console._base_spectators) == 1
        assert isinstance(console._base_spectators[0], MatchNarrator)

        # Verify it's subscribed to event bus
        assert console._base_spectators[0] in console.event_bus._spectators

        console.close()

    def test_auto_attach_when_spectators_omitted(self, temp_session_dir):
        """
        When spectators parameter omitted, Console MUST auto-attach MatchNarrator.

        Same as spectators=None (Python default parameter semantics).
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        # Call without spectators parameter (defaults to None)
        console = Console(session=session)

        # Verify MatchNarrator was auto-attached
        assert len(console._base_spectators) == 1
        assert isinstance(console._base_spectators[0], MatchNarrator)

        console.close()

    def test_explicit_empty_list_skips_auto_attach(self, temp_session_dir):
        """
        When spectators=[] (explicit empty list), Console MUST NOT auto-attach.

        Per SPEC-CONSOLE §5:
        - Explicit spectator list (even empty) bypasses auto-attachment
        - This is how users opt out of default narrator
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

        # Verify ONLY custom spectator attached (no MatchNarrator)
        assert len(console._base_spectators) == 1
        assert console._base_spectators[0] is custom
        assert not isinstance(console._base_spectators[0], MatchNarrator)

        console.close()

    def test_explicit_match_narrator_allowed(self, temp_session_dir):
        """
        Users can still explicitly attach MatchNarrator if desired.

        This allows customization (e.g., different modes in future).
        """
        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        narrator = MatchNarrator()

        # Call with explicit MatchNarrator
        console = Console(session=session, spectators=[narrator])

        # Verify the explicit narrator is attached
        assert len(console._base_spectators) == 1
        assert console._base_spectators[0] is narrator

        console.close()

    def test_logger_injection_for_auto_attached_narrator(self, temp_session_dir):
        """
        Auto-attached MatchNarrator MUST receive logger injection.

        Per SPEC-CONSOLE §5:
        - Auto-attached spectators follow logger-injection rules (§6.5 P4)
        - Logger allows narrator output to flow through session logger
        """
        from agentdeck.core.logging import AgentDeckLogger

        config = AgentDeckConfig(run_dir=str(temp_session_dir))
        session = SessionContext.create(config)

        # Create a logger instance
        test_logger = AgentDeckLogger(session)

        # Create console with logger
        console = Console(session=session, logger=test_logger)

        # Verify auto-attached narrator received logger injection
        narrator = console._base_spectators[0]
        assert isinstance(narrator, MatchNarrator)
        assert narrator.logger is test_logger
        assert narrator.logger is console.logger

        console.close()


@pytest.fixture
def temp_session_dir(tmp_path):
    """Provide temporary directory for session logs/records."""
    return tmp_path / "test_session"
