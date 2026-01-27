"""
Unit tests for AgentDeck facade per SPEC-AGENTDECK v0.3.0.

These tests verify:
- E3: elapsed_time property returns wall-clock seconds since SESSION_START
- R1: replay() validates input types and raises TypeError for invalid types
"""

import time
from pathlib import Path
from typing import Any, Dict

import pytest

from agentdeck import AgentDeck, FixedDamageGame, MockPlayer
from agentdeck.core.session import AgentDeckConfig
from agentdeck.core.types import MatchResult


# Fixtures


@pytest.fixture
def simple_game():
    """Simple game for testing."""
    return FixedDamageGame()


@pytest.fixture
def deck_with_game(simple_game):
    """AgentDeck instance with a simple game."""
    config = AgentDeckConfig(seed=42)
    with AgentDeck(game=simple_game, session=config) as deck:
        yield deck


# Test: E3 - elapsed_time property


def test_e3_elapsed_time_property_exists(deck_with_game):
    """Test E3: elapsed_time property exists and is accessible."""
    # SPEC-AGENTDECK E3: MUST expose elapsed_time property
    assert hasattr(deck_with_game, "elapsed_time")
    assert isinstance(deck_with_game.elapsed_time, float)


def test_e3_elapsed_time_increases(deck_with_game):
    """Test E3: elapsed_time increases over wall-clock time."""
    # Capture initial elapsed time
    time1 = deck_with_game.elapsed_time

    # Wait a small amount
    time.sleep(0.05)

    # Capture elapsed time again
    time2 = deck_with_game.elapsed_time

    # SPEC-AGENTDECK E3: MUST report wall-clock seconds since SESSION_START
    assert time2 > time1
    assert time2 - time1 >= 0.04  # Allow for some timing variance


def test_e3_elapsed_time_starts_from_session_start(simple_game):
    """Test E3: elapsed_time starts counting from session initialization."""
    # Create deck and immediately check elapsed time
    config = AgentDeckConfig(seed=99)
    with AgentDeck(game=simple_game, session=config) as deck:
        # Should be very small (milliseconds) since just created
        elapsed = deck.elapsed_time
        assert 0.0 <= elapsed < 1.0  # Should be less than 1 second


def test_e3_elapsed_time_reflects_session_duration(deck_with_game, simple_game):
    """Test E3: elapsed_time reflects total session duration."""
    players = [MockPlayer("Alice"), MockPlayer("Bob")]

    # Run a match (this takes time)
    result = deck_with_game.play(players=players, game=simple_game, matches=1)

    # elapsed_time should include match execution time
    elapsed = deck_with_game.elapsed_time
    assert elapsed > 0.0


# Test: R1 - replay() type validation


def test_r1_replay_with_match_result(deck_with_game, simple_game):
    """Test R1: replay() accepts MatchResult objects."""
    players = [MockPlayer("Alice"), MockPlayer("Bob")]
    result = deck_with_game.play(players=players, game=simple_game, matches=1)

    # SPEC-AGENTDECK R1: MUST accept MatchResult
    # Should not raise any exception
    deck_with_game.replay(match=result.single, spectators=[])


def test_r1_replay_with_dict(deck_with_game, simple_game):
    """Test R1: replay() accepts dict objects."""
    # First play a match to get a valid structure, then convert to dict
    players = [MockPlayer("Alice"), MockPlayer("Bob")]
    result = deck_with_game.play(players=players, game=simple_game, matches=1)

    # Convert to dict (this is what users might do after loading from JSON)
    match_dict = {
        "events": [e.to_dict() if hasattr(e, "to_dict") else {"type": e.type, "data": e.data} for e in result.single.events],
        "final_state": result.single.final_state,
        "winner": result.single.winner,
        "metadata": result.single.metadata,
        "schema_version": "1.3.0",  # Required by ReplayEngine
    }

    # SPEC-AGENTDECK R1: MUST accept dict
    # Should not raise any exception
    deck_with_game.replay(match=match_dict, spectators=[])


def test_r1_replay_rejects_string(deck_with_game):
    """Test R1: replay() raises TypeError for string match parameter."""
    # SPEC-AGENTDECK R1: MUST raise TypeError for unsupported types
    with pytest.raises(TypeError) as exc_info:
        deck_with_game.replay(match="invalid_string", spectators=[])

    # Error message should mention the type
    assert "match" in str(exc_info.value).lower()
    assert "str" in str(exc_info.value)


def test_r1_replay_rejects_integer(deck_with_game):
    """Test R1: replay() raises TypeError for integer match parameter."""
    # SPEC-AGENTDECK R1: MUST raise TypeError for unsupported types
    with pytest.raises(TypeError) as exc_info:
        deck_with_game.replay(match=12345, spectators=[])

    # Error message should mention the type
    assert "match" in str(exc_info.value).lower()
    assert "int" in str(exc_info.value)


def test_r1_replay_rejects_list(deck_with_game):
    """Test R1: replay() raises TypeError for list match parameter."""
    # SPEC-AGENTDECK R1: MUST raise TypeError for unsupported types
    with pytest.raises(TypeError) as exc_info:
        deck_with_game.replay(match=[{"events": []}], spectators=[])

    # Error message should mention the type
    assert "match" in str(exc_info.value).lower()
    assert "list" in str(exc_info.value)


def test_r1_replay_with_valid_path(deck_with_game, simple_game, tmp_path):
    """Test R1: replay() accepts string path parameter."""
    players = [MockPlayer("Alice"), MockPlayer("Bob")]
    result = deck_with_game.play(players=players, game=simple_game, matches=1)

    # Use the actual recorded match file from the session
    # AgentDeck automatically records matches
    import os
    from pathlib import Path

    records_dir = Path(deck_with_game.session.record_directory)
    match_files = list(records_dir.glob("match_*.json"))

    # Should have at least one recorded match
    assert len(match_files) > 0, "No match files found in records directory"

    # SPEC-AGENTDECK R1: MUST accept str path
    # Should not raise any exception
    deck_with_game.replay(path=str(match_files[0]), spectators=[])


def test_r1_replay_rejects_invalid_path_type(deck_with_game):
    """Test R1: replay() raises TypeError for invalid path type (integer)."""
    # SPEC-AGENTDECK R1: MUST raise TypeError for unsupported path types
    with pytest.raises(TypeError) as exc_info:
        deck_with_game.replay(path=12345, spectators=[])

    # Error message should mention path and type
    assert "path" in str(exc_info.value).lower()


def test_r1_replay_requires_exactly_one_source(deck_with_game):
    """Test R1: replay() requires exactly one of match or path."""
    # SPEC-AGENTDECK R1: MUST require exactly one source

    # Neither match nor path
    with pytest.raises(ValueError) as exc_info:
        deck_with_game.replay(spectators=[])
    assert "exactly one" in str(exc_info.value).lower()

    # Both match and path
    with pytest.raises(ValueError) as exc_info:
        deck_with_game.replay(match={"events": []}, path="/some/path", spectators=[])
    assert "exactly one" in str(exc_info.value).lower()
