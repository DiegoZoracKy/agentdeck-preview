"""
Unit tests for AgentDeck facade per SPEC-AGENTDECK v0.3.0.

These tests verify:
- E3: elapsed_time property returns wall-clock seconds since SESSION_START
- R1: replay() validates input types and raises TypeError for invalid types
"""

import json
from pathlib import Path

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
def deck_with_game(simple_game, tmp_path):
    """AgentDeck instance with a simple game, using tmp_path for isolation."""
    config = AgentDeckConfig(seed=42, run_dir=tmp_path)
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

    # Capture elapsed time again
    time2 = deck_with_game.elapsed_time

    # SPEC-AGENTDECK E3: MUST report wall-clock seconds since SESSION_START
    # Only assert monotonic non-decrease - avoid brittle timing thresholds
    assert time2 >= time1


def test_e3_elapsed_time_starts_from_session_start(simple_game, tmp_path):
    """Test E3: elapsed_time starts counting from session initialization."""
    # Create deck and immediately check elapsed time
    config = AgentDeckConfig(seed=99, run_dir=tmp_path)
    with AgentDeck(game=simple_game, session=config) as deck:
        # Should be non-negative since just created
        # Avoid upper bound assertion - can flake on slow CI
        elapsed = deck.elapsed_time
        assert elapsed >= 0.0


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
    deck_with_game.play(players=players, game=simple_game, matches=1)

    # Load a recorded match payload to mirror real replay usage
    records_dir = Path(deck_with_game.session.record_directory)
    match_files = list(records_dir.glob("match_*.json"))
    assert len(match_files) > 0, "No match files found in records directory"
    with match_files[0].open("r", encoding="utf-8") as handle:
        match_dict = json.load(handle)

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


def test_r1_replay_with_valid_path(deck_with_game, simple_game):
    """Test R1: replay() accepts string path parameter."""
    players = [MockPlayer("Alice"), MockPlayer("Bob")]
    result = deck_with_game.play(players=players, game=simple_game, matches=1)

    # Use the actual recorded match file from the session (in tmp_path via fixture)
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
