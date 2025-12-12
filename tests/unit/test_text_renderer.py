"""
Unit tests for TextRenderer per SPEC-RENDERER v0.3.0.

These tests verify:
- Generic text rendering for arbitrary game states
- Deterministic key ordering per MB1 invariant
- Turn context handling (from turn_context or state["turn"])
- Nested dict/list rendering
- Player-specific "You:" labeling
- 2D grid rendering
- Empty value handling (show_empty flag)
- Metadata capture (DS2 invariant)
- describe() method (MO2 invariant)
"""

import pytest

from agentdeck.core.types import TurnContext
from agentdeck.renderers.text_renderer import TextRenderer

# Fixtures


@pytest.fixture
def turn_context():
    """Turn context for testing."""
    return TurnContext(
        match_id="match-123",
        turn_number=5,
        turn_index=4,
        player="Alice",
        started_at=1234567890.0,
        duration=1.5,
    )


@pytest.fixture
def basic_renderer():
    """TextRenderer with default settings."""
    return TextRenderer()


@pytest.fixture
def show_empty_renderer():
    """TextRenderer that shows empty values."""
    return TextRenderer(show_empty=True)


# Test: Basic rendering with turn_context


def test_render_with_turn_context(basic_renderer, turn_context):
    """Test basic rendering with turn_context provided."""
    state = {
        "health": {"Alice": 100, "Bob": 80},
        "scores": [10, 20, 30],
    }

    result = basic_renderer.render(state, player="Alice", turn_context=turn_context)

    # Check header
    assert "=== Current Game State ===" in result.text
    assert "You are: Alice" in result.text
    assert "Turn: 5" in result.text

    # Check content
    assert "Health:" in result.text
    assert "You: 100" in result.text  # Alice should be labeled "You"
    assert "Bob: 80" in result.text

    # Check metadata
    assert result.metadata["player"] == "Alice"
    assert result.metadata["turn_number"] == 5
    assert "health" in result.metadata["sections"]
    assert "scores" in result.metadata["sections"]


def test_render_with_state_turn(basic_renderer):
    """Test rendering with turn from state dict (covers line 78)."""
    state = {
        "turn": 7,
        "health": {"Alice": 90},
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    # Turn should come from state
    assert "Turn: 7" in result.text

    # Turn should be in sections (turn_context path adds it)
    # But state path doesn't skip it in sections
    assert "health" in result.metadata["sections"]


# Test: Nested dict rendering


def test_render_nested_dict(basic_renderer):
    """Test rendering of nested dictionaries (covers lines 145-149)."""
    state = {
        "inventory": {
            "weapons": {
                "sword": 1,
                "bow": 2,
            },
            "potions": {
                "health": 5,
                "mana": 3,
            },
        },
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    # Check nested rendering (nested keys are not title-cased, only top-level)
    assert "Inventory:" in result.text
    assert "  weapons:" in result.text
    assert "    sword: 1" in result.text
    assert "    bow: 2" in result.text
    assert "  potions:" in result.text
    assert "    health: 5" in result.text
    assert "    mana: 3" in result.text


def test_render_dict_with_player_key(basic_renderer):
    """Test dict rendering with player's own key labeled 'You' (covers line 141)."""
    state = {
        "scores": {
            "Alice": 100,
            "Bob": 50,
        },
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    # Alice's score should be labeled "You"
    assert "You: 100" in result.text
    assert "Bob: 50" in result.text


# Test: List rendering


def test_render_1d_list(basic_renderer):
    """Test rendering of 1D lists (covers lines 165-167)."""
    state = {
        "available_actions": ["ATTACK", "DEFEND", "HEAL"],
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    # Check bullet points
    assert "Available Actions:" in result.text
    assert "  - ATTACK" in result.text
    assert "  - DEFEND" in result.text
    assert "  - HEAL" in result.text


def test_render_2d_grid(basic_renderer):
    """Test rendering of 2D grids (covers lines 160-163)."""
    state = {
        "board": [
            ["X", "O", "."],
            ["O", "X", "."],
            [".", ".", "X"],
        ],
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    # Check grid rendering (space-separated rows)
    assert "Board:" in result.text
    assert "  X O ." in result.text
    assert "  O X ." in result.text
    assert "  . . X" in result.text


def test_render_nested_list_in_dict(basic_renderer):
    """Test nested list within dict (covers lines 147-149)."""
    state = {
        "player_data": {
            "Alice": {
                "cards": ["A", "K", "Q"],
            },
        },
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    assert "Player Data:" in result.text
    assert "  You:" in result.text
    assert "    cards:" in result.text  # Nested keys not title-cased
    assert "      - A" in result.text
    assert "      - K" in result.text
    assert "      - Q" in result.text


# Test: Scalar values


def test_render_scalar_values(basic_renderer):
    """Test rendering of scalar values (covers line 107)."""
    state = {
        "round": 3,
        "phase": "combat",
        "active_player": "Alice",
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    assert "Round: 3" in result.text
    assert "Phase: combat" in result.text
    assert "Active Player: Alice" in result.text


# Test: Mixed types


def test_render_mixed_types(basic_renderer):
    """Test rendering state with mixed value types (covers lines 102-107)."""
    state = {
        "turn": 10,
        "health": {"Alice": 100, "Bob": 80},  # Dict
        "actions": ["MOVE", "SHOOT"],  # List
        "phase": "action",  # Scalar
    }

    result = basic_renderer.render(state, player="Alice", turn_context=None)

    # All types should render
    assert "Turn: 10" in result.text
    assert "Health:" in result.text
    assert "Actions:" in result.text
    assert "Phase: action" in result.text


# Test: Empty value handling


def test_is_empty_none(basic_renderer):
    """Test _is_empty() with None (covers line 124-125)."""
    assert basic_renderer._is_empty(None) is True


def test_is_empty_empty_list(basic_renderer):
    """Test _is_empty() with empty list (covers line 126-127)."""
    assert basic_renderer._is_empty([]) is True


def test_is_empty_empty_dict(basic_renderer):
    """Test _is_empty() with empty dict (covers line 126-127)."""
    assert basic_renderer._is_empty({}) is True


def test_is_empty_empty_string(basic_renderer):
    """Test _is_empty() with empty string (covers line 126-127)."""
    assert basic_renderer._is_empty("") is True


def test_is_empty_non_empty_values(basic_renderer):
    """Test _is_empty() with non-empty values (covers line 128)."""
    assert basic_renderer._is_empty([1, 2, 3]) is False
    assert basic_renderer._is_empty({"a": 1}) is False
    assert basic_renderer._is_empty("text") is False
    assert basic_renderer._is_empty(42) is False


# Test: Show_empty flag


def test_show_empty_flag_default():
    """Test show_empty defaults to False."""
    renderer = TextRenderer()
    assert renderer.show_empty is False


def test_show_empty_flag_explicit():
    """Test show_empty can be set to True."""
    renderer = TextRenderer(show_empty=True)
    assert renderer.show_empty is True


# Test: describe() method


def test_describe_method(basic_renderer):
    """Test describe() method returns renderer identity (covers line 178)."""
    desc = basic_renderer.describe()

    assert desc["name"] == "TextRenderer"
    assert desc["version"] == "1.0.0"
    assert desc["metadata"]["show_empty"] is False
    assert desc["metadata"]["style"] == "generic"


def test_describe_with_show_empty(show_empty_renderer):
    """Test describe() reflects show_empty setting."""
    desc = show_empty_renderer.describe()

    assert desc["metadata"]["show_empty"] is True


# Test: Metadata capture (DS2 invariant)


def test_metadata_includes_player(basic_renderer):
    """Test metadata includes player per DS2."""
    state = {"health": 100}
    result = basic_renderer.render(state, player="Alice")

    assert result.metadata["player"] == "Alice"


def test_metadata_includes_sections(basic_renderer):
    """Test metadata includes sections list per DS2."""
    state = {
        "health": 100,
        "mana": 50,
        "inventory": {},
    }
    result = basic_renderer.render(state, player="Alice")

    # All keys should be in sections (MB1: no filtering)
    assert result.metadata["sections"] == ["health", "mana", "inventory"]


def test_metadata_includes_turn_number(basic_renderer, turn_context):
    """Test metadata includes turn_number when turn_context provided."""
    state = {"health": 100}
    result = basic_renderer.render(state, player="Alice", turn_context=turn_context)

    assert result.metadata["turn_number"] == 5


def test_metadata_no_turn_number_without_context(basic_renderer):
    """Test metadata doesn't include turn_number without turn_context."""
    state = {"health": 100}
    result = basic_renderer.render(state, player="Alice", turn_context=None)

    assert "turn_number" not in result.metadata


# Test: Insertion order preservation (MB1 invariant)


def test_preserves_insertion_order(basic_renderer):
    """Test renderer preserves dict insertion order per MB1."""
    state = {
        "z_field": 1,
        "a_field": 2,
        "m_field": 3,
    }
    result = basic_renderer.render(state, player="Alice")

    # Check sections maintain order (not alphabetical)
    assert result.metadata["sections"] == ["z_field", "a_field", "m_field"]

    # Check text rendering order
    lines = result.text.split("\n")
    z_index = next(i for i, line in enumerate(lines) if "Z Field" in line)
    a_index = next(i for i, line in enumerate(lines) if "A Field" in line)
    m_index = next(i for i, line in enumerate(lines) if "M Field" in line)

    assert z_index < a_index < m_index


# Test: Edge cases


def test_empty_state(basic_renderer):
    """Test rendering empty state dict."""
    state = {}
    result = basic_renderer.render(state, player="Alice")

    # Should have header and footer, but no content
    assert "=== Current Game State ===" in result.text
    assert "You are: Alice" in result.text
    assert "=" * 25 in result.text
    assert result.metadata["sections"] == []


def test_state_with_none_values(basic_renderer):
    """Test state with None values renders without error."""
    state = {
        "health": None,
        "mana": 50,
    }
    result = basic_renderer.render(state, player="Alice")

    # Should render None as string
    assert "Health: None" in result.text
    assert "Mana: 50" in result.text


def test_state_with_empty_list(basic_renderer):
    """Test state with empty list renders correctly."""
    state = {
        "inventory": [],
    }
    result = basic_renderer.render(state, player="Alice")

    assert "Inventory:" in result.text
    # Empty list should render without items


def test_state_with_empty_dict(basic_renderer):
    """Test state with empty dict renders correctly."""
    state = {
        "scores": {},
    }
    result = basic_renderer.render(state, player="Alice")

    assert "Scores:" in result.text
    # Empty dict should render without entries


def test_key_formatting(basic_renderer):
    """Test underscores in keys are replaced with spaces and title-cased."""
    state = {
        "player_health": 100,
        "enemy_count": 5,
    }
    result = basic_renderer.render(state, player="Alice")

    assert "Player Health: 100" in result.text
    assert "Enemy Count: 5" in result.text


def test_no_turn_in_state_or_context(basic_renderer):
    """Test rendering when no turn info available."""
    state = {"health": 100}
    result = basic_renderer.render(state, player="Alice", turn_context=None)

    # Should not crash, just omit turn info
    assert "You are: Alice" in result.text
    assert "Health: 100" in result.text
    # Turn line should not appear
    assert "Turn:" not in result.text


def test_turn_context_takes_precedence_over_state_turn(basic_renderer, turn_context):
    """Test turn_context.turn_number takes precedence over state['turn']."""
    state = {
        "turn": 99,  # Wrong turn number
        "health": 100,
    }

    result = basic_renderer.render(state, player="Alice", turn_context=turn_context)

    # Should use turn_context.turn_number (5), not state["turn"] (99)
    assert "Turn: 5" in result.text
    assert "Turn: 99" not in result.text


# Test: Complex nested structures


def test_deeply_nested_structure(basic_renderer):
    """Test rendering deeply nested dicts and lists."""
    state = {
        "world": {
            "regions": {
                "north": {
                    "cities": ["CityA", "CityB"],
                    "population": 1000,
                },
                "south": {
                    "cities": ["CityC"],
                    "population": 500,
                },
            },
        },
    }

    result = basic_renderer.render(state, player="Alice")

    assert "World:" in result.text
    assert "  regions:" in result.text  # Nested keys not title-cased
    assert "    north:" in result.text
    assert "      cities:" in result.text
    assert "        - CityA" in result.text
    assert "      population: 1000" in result.text
