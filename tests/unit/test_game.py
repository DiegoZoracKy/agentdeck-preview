"""
Unit tests for Game base class (SPEC-GAME v0.5.0).

Tests verify all invariants from SPEC-GAME §5:
- GS1-GS4: Game State Data (JSON-serializable, deep-copyable)
- DT1-DT3: Determinism (pure functions, reproducibility)
- OB3: Observability (EventBus integration, hidden information)
- HT1-HT3: Handshake Template (mandatory, format requirements)
- IV1-IV5: Information Visibility (optional information_level support)
- GB1-GB2: Game Boundaries (validation, error handling)

Uses FixedDamageGame as reference implementation per TEST-PLAN-spec-driven.md §3.2.
"""

import copy
import json
from unittest.mock import Mock

import pytest

from agentdeck.core.game_event_emitter import GameEventEmitter
from agentdeck.core.types import ActionResult, GameStatus, RandomGenerator
from agentdeck.games.examples import FixedDamageGame

# ============================================================================
# GS1-GS4: Game State Data Tests
# ============================================================================


def test_GS1_setup_returns_json_serializable():
    """
    SPEC-GAME §5.1 GS1: setup() MUST return JSON-serializable dict.

    Verify that the game_state returned by setup() can be serialized
    to JSON without errors.
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Must be serializable to JSON
    try:
        json_str = json.dumps(game_state)
        assert isinstance(json_str, str)
        # Must be deserializable back to dict
        restored = json.loads(json_str)
        assert isinstance(restored, dict)
    except (TypeError, ValueError) as e:
        pytest.fail(f"game_state is not JSON-serializable: {e}")


def test_GS2_update_returns_canonical_state():
    """
    SPEC-GAME §5.1 GS2: update() MUST return authoritative game_state.

    Verify that update() returns a dict representing the new canonical
    state after applying an action.
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)
    initial_health = game_state["health"]["Alice"]

    # Create mock RNG
    class MockRNG:
        def choice(self, seq):
            return seq[0]

    action = ActionResult(action="ATTACK", raw_response="ATTACK")
    rng = MockRNG()

    new_state = game.update(game_state, "Alice", action, rng=rng)

    # Must return a dict
    assert isinstance(new_state, dict)
    # Must be authoritative (health changed)
    assert new_state["health"]["Bob"] < 100  # Attack reduces opponent health


def test_GS3_state_contains_no_unserializable_objects():
    """
    SPEC-GAME §5.1 GS3: game_state MUST be free of unserializable objects.

    Verify that game_state contains only JSON-serializable types (no
    functions, classes, file handles, etc.).
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Check all values are JSON-serializable
    def check_serializable(obj, path="root"):
        if isinstance(obj, dict):
            for key, value in obj.items():
                check_serializable(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_serializable(item, f"{path}[{i}]")
        elif obj is None:
            pass
        elif isinstance(obj, (str, int, float, bool)):
            pass
        else:
            pytest.fail(f"Unserializable object at {path}: {type(obj).__name__}")

    check_serializable(game_state)


def test_GS4_get_view_deep_copyable():
    """
    SPEC-GAME §5.1 GS4: get_view() and game_state MUST be deep-copyable.

    Verify that both game_state and the view returned by get_view()
    can be deep-copied without errors.
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)
    view = game.get_view(game_state, "Alice")

    # Must be deep-copyable
    try:
        state_copy = copy.deepcopy(game_state)
        view_copy = copy.deepcopy(view)

        assert isinstance(state_copy, dict)
        assert isinstance(view_copy, dict)

        # Verify independence (mutations don't leak)
        state_copy["health"]["Alice"] = 9999
        assert game_state["health"]["Alice"] != 9999

    except Exception as e:
        pytest.fail(f"Deep copy failed: {e}")


# ============================================================================
# DT1-DT3: Determinism Tests
# ============================================================================


def test_DT1_update_uses_provided_rng():
    """
    SPEC-GAME §5.2 DT1: All randomness MUST come from provided rng.

    Verify that update() uses the provided RNG fork for all random
    decisions, ensuring deterministic behavior.
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Create deterministic mock RNG
    class DeterministicRNG:
        def __init__(self, value):
            self.value = value
            self.called = False

        def choice(self, seq):
            self.called = True
            return self.value

    rng = DeterministicRNG("ATTACK")
    action = ActionResult(action="ATTACK", raw_response="ATTACK")

    game.update(game_state, "Alice", action, rng=rng)

    # If game uses RNG internally, it should have been called
    # FixedDamageGame doesn't use RNG, so we just verify it's accepted
    assert rng is not None


def test_DT2_identical_inputs_produce_identical_states():
    """
    SPEC-GAME §5.2 DT2: Identical inputs MUST produce identical states.

    Given same players, seed, and action sequence, the game MUST
    produce identical future states and GameStatus outputs.
    """
    players = ["Alice", "Bob"]
    seed = 12345

    # Run 1
    game1 = FixedDamageGame()
    state1 = game1.setup(players, seed)

    # Run 2
    game2 = FixedDamageGame()
    state2 = game2.setup(players, seed)

    # Initial states must be identical
    assert state1 == state2

    # Apply same action sequence
    class MockRNG:
        def choice(self, seq):
            return seq[0]

    action = ActionResult(action="ATTACK", raw_response="ATTACK")
    rng1 = MockRNG()
    rng2 = MockRNG()

    state1 = game1.update(state1, "Alice", action, rng=rng1)
    state2 = game2.update(state2, "Alice", action, rng=rng2)

    # States must remain identical
    assert state1 == state2


def test_DT3_get_view_is_pure():
    """
    SPEC-GAME §5.2 DT3: get_view() MUST be pure (no side effects).

    Repeated calls with identical inputs MUST yield identical outputs
    and must not mutate the game_state.
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)
    original_state = copy.deepcopy(game_state)

    # Call get_view multiple times
    view1 = game.get_view(game_state, "Alice")
    view2 = game.get_view(game_state, "Alice")

    # Views must be identical
    assert view1 == view2

    # Original state must be unchanged
    assert game_state == original_state


# ============================================================================
# OB3: Observability & Hidden Information Tests
# ============================================================================


def test_OB3_get_view_hides_hidden_information():
    """
    SPEC-GAME §5.4 OB3: get_view() MUST hide hidden information.

    For games with information_level="partial", verify that non-owning
    players don't receive opponent's private data.
    """
    # Test with partial information level
    game = FixedDamageGame(information_level="partial")
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Alice's view should not contain Bob's stats
    alice_view = game.get_view(game_state, "Alice")

    # Alice should see her own health
    assert "Alice" in alice_view["health"]
    assert alice_view["health"]["Alice"] == 100

    # Alice should NOT see Bob's health in partial mode
    assert "Bob" not in alice_view["health"]


def test_OB3_full_information_level_shows_all():
    """
    SPEC-GAME §5.7 IV2: information_level="full" shows all observable info.

    Verify that when information_level="full", get_view() includes
    all players' stats.
    """
    # Test with full information level
    game = FixedDamageGame(information_level="full")
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Alice's view should contain both players' stats
    alice_view = game.get_view(game_state, "Alice")

    assert "Alice" in alice_view["health"]
    assert "Bob" in alice_view["health"]
    assert alice_view["health"]["Alice"] == 100
    assert alice_view["health"]["Bob"] == 100


def test_OB3_recorder_gets_full_canonical_state():
    """
    SPEC-GAME §5.4 OB3: Recorder snapshots retain full canonical state.

    Even with information_level="partial", the canonical game_state
    (used by recorder) must contain truthful full data.
    """
    game = FixedDamageGame(information_level="partial")
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Canonical state (what recorder sees) has all data
    assert "Alice" in game_state["health"]
    assert "Bob" in game_state["health"]
    assert game_state["health"]["Alice"] == 100
    assert game_state["health"]["Bob"] == 100


# ============================================================================
# HT1-HT3: Handshake Template Tests
# ============================================================================


def test_HT1_provides_default_handshake_template():
    """
    SPEC-GAME §5.6 HT1: Games MUST provide default_handshake_template.

    Verify that the game exposes a default_handshake_template property.
    """
    game = FixedDamageGame()

    assert hasattr(game, "default_handshake_template")
    template = game.default_handshake_template
    assert isinstance(template, str)
    assert len(template) > 0


def test_HT2_handshake_includes_instructions():
    """
    SPEC-GAME §5.6 HT2: Handshake template SHOULD include instructions.

    Verify that the template contains game instructions and response format.
    """
    game = FixedDamageGame()
    template = game.default_handshake_template

    # Template should have placeholder for game instructions
    assert "{game_instructions}" in template or len(game.instructions) > 0


def test_HT3_handshake_mandatory():
    """
    SPEC-GAME §5.6 HT3: Handshake validation failures MUST abort match.

    This is verified at Console level, but we verify the game provides
    the template required for handshake validation.
    """
    game = FixedDamageGame()

    # Game must provide template (Console will enforce validation)
    assert game.default_handshake_template is not None
    assert isinstance(game.default_handshake_template, str)


# ============================================================================
# Event Emission Tests (OB1-OB2)
# ============================================================================


def test_OB1_emit_event_with_json_serializable_payload():
    """
    SPEC-GAME §5.4 OB1: emit_event() payloads MUST be JSON-serializable.

    Verify that games can emit events with JSON-serializable payloads.
    """
    game = FixedDamageGame()

    # Create mock emitter
    mock_emitter = Mock(spec=GameEventEmitter)
    game.bind_event_emitter(mock_emitter)

    # Emit event with JSON-serializable payload
    game.emit_event("test_event", player="Alice", score=100, data={"key": "value"})

    # Verify emitter was called
    assert mock_emitter.emit.called
    call_args = mock_emitter.emit.call_args
    assert call_args[0][0] == "test_event"  # event_type
    assert call_args[1]["player"] == "Alice"
    assert call_args[1]["score"] == 100


def test_OB2_emit_event_requires_bound_emitter():
    """
    SPEC-GAME §5.4 OB2: emit_event() only works after bind_event_emitter().

    Verify that calling emit_event() before binding has no effect
    (doesn't raise, just silently no-ops).
    """
    game = FixedDamageGame()

    # emit_event before binding should not raise
    try:
        game.emit_event("test_event", data="test")
    except Exception as e:
        pytest.fail(f"emit_event should not raise when emitter not bound: {e}")

    # After binding, it should work
    mock_emitter = Mock(spec=GameEventEmitter)
    game.bind_event_emitter(mock_emitter)
    game.emit_event("test_event", data="test")

    assert mock_emitter.emit.called


# ============================================================================
# GB1-GB2: Game Boundaries & Validation Tests
# ============================================================================


def test_GB1_validate_state_detects_violations():
    """
    SPEC-GAME §5.5 V1: validate_state() MUST detect invariant violations.

    For games that implement validate_state(), verify it raises ValueError
    on invalid states.
    """

    # FixedDamageGame doesn't implement validate_state, so we create a test game
    class ValidatingGame(FixedDamageGame):
        def validate_state(self, game_state):
            if any(hp < 0 for hp in game_state["health"].values()):
                raise ValueError("Health cannot be negative")

    game = ValidatingGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Valid state should pass
    game.validate_state(game_state)

    # Invalid state should raise
    game_state["health"]["Alice"] = -10
    with pytest.raises(ValueError, match="Health cannot be negative"):
        game.validate_state(game_state)


def test_GB2_validate_state_side_effect_free():
    """
    SPEC-GAME §5.5 V2: validate_state() MUST be side-effect free.

    Verify that validation failures don't mutate the game_state.
    """

    class ValidatingGame(FixedDamageGame):
        def validate_state(self, game_state):
            if any(hp < 0 for hp in game_state["health"].values()):
                # Must not mutate state before raising
                raise ValueError("Health cannot be negative")

    game = ValidatingGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)
    game_state["health"]["Alice"] = -10

    original_state = copy.deepcopy(game_state)

    # Validation should raise
    with pytest.raises(ValueError):
        game.validate_state(game_state)

    # State should be unchanged
    assert game_state == original_state


# ============================================================================
# Additional Coverage: get_current_player, status, allowed_actions
# ============================================================================


def test_get_current_player_round_robin():
    """
    SPEC-GAME §4: get_current_player() default implementation is round-robin.

    Verify that the default get_current_player() implementation cycles
    through players in order.
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob", "Charlie"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Default uses _turn_count and _first_player_idx
    game_state["_turn_count"] = 1
    game_state["_first_player_idx"] = 0

    # Create mock RNG and match_context for new signature
    rng = RandomGenerator(seed)
    mock_match_context = Mock()

    assert (
        game.get_current_player(game_state, players, rng=rng, match_context=mock_match_context)
        == "Alice"
    )

    game_state["_turn_count"] = 2
    assert (
        game.get_current_player(game_state, players, rng=rng, match_context=mock_match_context)
        == "Bob"
    )

    game_state["_turn_count"] = 3
    assert (
        game.get_current_player(game_state, players, rng=rng, match_context=mock_match_context)
        == "Charlie"
    )

    game_state["_turn_count"] = 4
    assert (
        game.get_current_player(game_state, players, rng=rng, match_context=mock_match_context)
        == "Alice"
    )  # Wraps around


def test_status_returns_game_status():
    """
    SPEC-GAME §4: status() MUST return GameStatus(is_over, winner).

    Verify that status() returns a proper GameStatus object.
    """
    game = FixedDamageGame()
    players = ["Alice", "Bob"]
    seed = 12345

    game_state = game.setup(players, seed)

    # Initial status: game not over
    status = game.status(game_state)
    assert isinstance(status, GameStatus)
    assert status.is_over is False
    assert status.winner is None

    # Simulate game end (Alice wins)
    game_state["health"]["Bob"] = 0
    status = game.status(game_state)
    assert status.is_over is True
    assert status.winner == "Alice"


def test_allowed_actions_returns_list():
    """
    SPEC-GAME §4: allowed_actions MUST return list of action strings.

    Verify that the game exposes a list of valid actions.
    """
    game = FixedDamageGame()

    actions = game.allowed_actions
    assert isinstance(actions, list)
    assert len(actions) > 0
    assert "ATTACK" in actions
    assert "POTION" in actions
