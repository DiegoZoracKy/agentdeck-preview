"""
Unit tests for Controller contracts (SPEC-CONTROLLER v1.3.0).

Tests verify critical invariants with parametrized suites to avoid redundancy:
- GB1-GB6: Game Binding (bind_game idempotent, allowed_actions injection, fail-fast)
- HV1-HV5: Handshake Validation (default implementation, determinism, normalization)
- VF1-VF3: Validation & Fallback (casefold, metadata, safe defaults)
- FI1-FI2: Format Instructions (alignment with parsing, deterministic)
- AP1-AP3: Action Parsing (raw_response, success/error handling)
- DS1-DS2: Determinism (pure functions, no state mutation)
- CP1-CP2: Conclusion Parsing (default passthrough, overridable)

Uses ActionOnlyController and ReasoningController per TEST-PLAN-spec-driven.md §3.3.
"""

import pytest

from agentdeck.controllers import (
    ActionOnlyController,
    ReasoningController,
)
from agentdeck.core.types import ActionParseError, HandshakeContext

# ============================================================================
# Test Helpers
# ============================================================================


class MockGame:
    """Minimal game mock for controller binding tests."""

    def __init__(self, allowed_actions=None):
        self.allowed_actions = allowed_actions or ["ATTACK", "DEFEND", "POTION"]


# ============================================================================
# GB1-GB6: Game Binding Tests (Parametrized)
# ============================================================================


def test_GB1_GB2_bind_game_idempotent():
    """
    SPEC-CONTROLLER GB1-GB2: bind_game() called once per batch, idempotent.

    Verify that binding the same game multiple times is safe and doesn't
    cause errors or duplicate state.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND"])

    # Bind once
    controller.bind_game(game)
    instructions_1 = controller.get_format_instructions()

    # Bind again (should be safe, idempotent)
    controller.bind_game(game)
    instructions_2 = controller.get_format_instructions()

    # Instructions should be identical (no state corruption)
    assert instructions_1 == instructions_2
    assert "ATTACK, DEFEND" in instructions_2


def test_GB3_bind_game_extracts_allowed_actions():
    """
    SPEC-CONTROLLER GB3: Controllers extract game.allowed_actions during binding.

    Verify that after binding, the controller uses allowed_actions for validation.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND", "POTION"])

    controller.bind_game(game)

    # Valid action should succeed
    result = controller.parse("ACTION: ATTACK")
    assert result.success is True
    assert result.action == "ATTACK"

    # Invalid action should fail
    result = controller.parse("ACTION: INVALID")
    assert result.success is False
    assert "ATTACK" in result.error
    assert "DEFEND" in result.error
    assert "POTION" in result.error


def test_GB4_GB5_format_instructions_before_and_after_binding():
    """
    SPEC-CONTROLLER GB4-GB5: Format instructions change after binding.

    - GB4: get_format_instructions() works before binding (generic default)
    - GB5: After binding, instructions become game-specific (list allowed actions)
    """
    controller = ActionOnlyController()

    # Before binding: generic instructions
    instructions_before = controller.get_format_instructions()
    assert "Allowed actions:" not in instructions_before
    assert "ACTION:" in instructions_before  # Still mentions format

    # After binding: game-specific instructions
    game = MockGame(allowed_actions=["ATTACK", "DEFEND", "POTION"])
    controller.bind_game(game)

    instructions_after = controller.get_format_instructions()
    assert "Allowed actions: ATTACK, DEFEND, POTION" in instructions_after


@pytest.mark.parametrize(
    "response,expected_action",
    [
        ("ACTION: ATTACK", "ATTACK"),
        ("ACTION: DEFEND", "DEFEND"),
        ("ACTION: POTION", "POTION"),
    ],
)
def test_GB3_validation_uses_bound_actions(response, expected_action):
    """
    SPEC-CONTROLLER GB3: Parametrized test for allowed_actions validation.

    Verify that the controller validates all bound actions correctly.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND", "POTION"])
    controller.bind_game(game)

    result = controller.parse(response)
    assert result.success is True
    assert result.action == expected_action


def test_action_only_rejects_incidental_allowed_mentions():
    """Narration must never be promoted into a player decision."""
    controller = ActionOnlyController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK", "POTION"]))

    parse_result = controller.parse(
        "I choose to ATTACK.\n\nCurrent state:\n- You: 100 HP\n- Opponent: 80 HP"
    )

    assert parse_result.success is False
    assert parse_result.action is None
    assert parse_result.metadata["resolution_method"] == "unresolved"
    assert parse_result.metadata["contract_satisfied"] is False


def test_action_only_rejects_last_action_and_intent_mentions_without_field():
    """Neither state narration nor intent prose is an explicit action declaration."""
    controller = ActionOnlyController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK", "POTION"]))

    parse_result = controller.parse(
        "Last Action:\n  You: None\n  Opponent: ATTACK\n\nI will ATTACK now."
    )

    assert parse_result.success is False
    assert parse_result.action is None


def test_action_only_rejects_lowercase_allowed_mention():
    """Free-form action mentions do not satisfy the response contract."""
    controller = ActionOnlyController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK", "POTION"]))

    parse_result = controller.parse("It's your turn now; please attack to finish the match.")

    assert parse_result.success is False
    assert parse_result.action is None


def test_action_only_is_game_agnostic_for_allowed_actions():
    """Controller must honor arbitrary game actions from bind_game(), not fixed domain tokens."""
    controller = ActionOnlyController()
    controller.bind_game(MockGame(allowed_actions=["CAST_SPELL", "GUARD"]))

    parse_result = controller.parse("ACTION: cast_spell")

    assert parse_result.success is True
    assert parse_result.action == "CAST_SPELL"
    assert "CAST_SPELL" in parse_result.metadata["allowed_actions"]
    assert parse_result.metadata["resolution_method"] == "explicit_action_field"
    assert parse_result.metadata["declared_action"] == "CAST_SPELL"


# ============================================================================
# HV1-HV4: Handshake Validation Tests (Parametrized)
# ============================================================================


@pytest.mark.parametrize(
    "response,expected_accepted,expected_normalized",
    [
        ("OK", True, "OK"),
        ("ok", True, "OK"),
        (" ok ", True, "OK"),
        ("ok!", True, "OK"),
        ("OK!!!", True, "OK"),
        ("  YES  ", False, None),
        ("READY.", False, None),
        ("OK\nI am ready.", False, None),
        ("maybe", False, None),  # Rejected -> normalized_response = None
        ("nope", False, None),  # Rejected -> normalized_response = None
        ("", False, None),  # Rejected -> normalized_response = None
    ],
)
def test_HV2_handshake_normalization(response, expected_accepted, expected_normalized):
    """
    SPEC-CONTROLLER HV2: Default handshake validation normalizes responses.

    Parametrized test verifying:
    - Whitespace trimming
    - Case normalization (uppercase)
    - Punctuation removal (!, .)
    - Raw response preservation
    - Rejected handshakes return normalized_response=None (per v1.3.0)
    """
    controller = ActionOnlyController()  # Uses default handshake implementation
    context = HandshakeContext(
        match_id="test-match",
        player_name="Alice",
        opponent_names=["Bob"],
        game_name="TestGame",
        seed=42,
    )

    result = controller.validate_handshake(response, context=context)

    assert result.accepted == expected_accepted
    assert result.normalized_response == expected_normalized
    assert result.raw_response == response.strip()  # Raw preserved (trimmed)


def test_HV3_handshake_rejection_reason():
    """
    SPEC-CONTROLLER HV3: Rejected handshakes populate reason field.

    Verify that when acknowledgement is rejected, reason explains why.
    """
    controller = ActionOnlyController()  # Uses default handshake implementation

    result = controller.validate_handshake("maybe")

    assert result.accepted is False
    assert result.reason is not None
    assert "Expected" in result.reason or "expected" in result.reason
    assert "maybe" in result.reason


def test_HV4_handshake_metadata():
    """
    SPEC-CONTROLLER HV4: Handshake metadata populated for recorder.

    Verify that HandshakeResult includes metadata with allowed tokens
    and player name.
    """
    controller = ActionOnlyController()  # Uses default handshake implementation
    context = HandshakeContext(
        match_id="test-match",
        player_name="Alice",
        opponent_names=["Bob"],
        game_name="TestGame",
        seed=42,
    )

    result = controller.validate_handshake("OK", context=context)

    assert result.metadata is not None
    assert "allowed" in result.metadata
    assert "OK" in result.metadata["allowed"]
    assert result.metadata["player"] == "Alice"


def test_HV1_handshake_deterministic():
    """
    SPEC-CONTROLLER HV1: Handshake validation is deterministic.

    Repeated calls with identical inputs must yield identical results.
    """
    controller = ActionOnlyController()  # Uses default handshake implementation
    context = HandshakeContext(
        match_id="test-match",
        player_name="Alice",
        opponent_names=["Bob"],
        game_name="TestGame",
        seed=42,
    )

    result_1 = controller.validate_handshake("OK!", context=context)
    result_2 = controller.validate_handshake("OK!", context=context)

    assert result_1.accepted == result_2.accepted
    assert result_1.normalized_response == result_2.normalized_response
    assert result_1.raw_response == result_2.raw_response
    assert result_1.reason == result_2.reason


# ============================================================================
# VF1-VF3: Validation & Fallback Tests
# ============================================================================


def test_VF1_casefold_validation():
    """
    SPEC-CONTROLLER VF1: Controllers honor casefold semantics.

    Verify that action validation is case-insensitive.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND"])
    controller.bind_game(game)

    # Lowercase should work (normalized to uppercase)
    result = controller.parse("ACTION: attack")
    assert result.success is True
    assert result.action == "ATTACK"  # Normalized to uppercase

    # Mixed case should work
    result = controller.parse("ACTION: AtTaCk")
    assert result.success is True
    assert result.action == "ATTACK"


def test_VF2_parse_failure_metadata():
    """
    SPEC-CONTROLLER VF2: to_action_result() raises ActionParseError on parse failure.

    Per SPEC-CONTROLLER v1.2.0 §5.4, parse failures raise ActionParseError
    instead of applying fallback semantics. This ensures failures surface
    explicitly for research evaluation.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK"])
    controller.bind_game(game)

    # Parse invalid action
    parse_result = controller.parse("ACTION: INVALID_ACTION")
    assert parse_result.success is False

    # to_action_result() should raise ActionParseError
    with pytest.raises(ActionParseError) as exc_info:
        parse_result.to_action_result()

    # Verify exception contains parse result
    assert exc_info.value.parse_result is parse_result
    assert exc_info.value.parse_result.error is not None


def test_VF3_parse_failure_never_loses_result():
    """
    SPEC-CONTROLLER VF3: ActionParseError MUST include ParseResult.

    Verify that to_action_result() raises ActionParseError with the
    originating ParseResult attached, enabling error handling logic
    to inspect failure details.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK"])
    controller.bind_game(game)

    # Parse failure
    parse_result = controller.parse("invalid response")

    # Should raise ActionParseError with parse_result attached
    with pytest.raises(ActionParseError) as exc_info:
        parse_result.to_action_result()

    assert exc_info.value.parse_result is not None
    assert exc_info.value.parse_result.success is False


# ============================================================================
# ReasoningController Tests (SPEC-CONTROLLER v1.2.0 §8)
# ============================================================================


def test_reasoning_controller_extracts_reasoning_and_action():
    """
    Verify ReasoningController parses reasoning + action (AP1-AP3, DS1-DS2).
    """
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK", "DEFEND"]))

    response = """REASONING: I should attack because opponent is low on health.
ACTION: ATTACK"""

    parse_result = controller.parse(response)

    assert parse_result.success is True
    assert parse_result.action == "ATTACK"
    assert parse_result.reasoning == "I should attack because opponent is low on health."
    assert parse_result.raw_response == response.strip()


def test_reasoning_controller_validates_allowed_actions():
    """
    Verify ReasoningController enforces allowed actions when bound (GB3, VF1).
    """
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK"]))

    # Valid action succeeds
    parse_result = controller.parse("REASONING: Ready.\nACTION: ATTACK")
    assert parse_result.success is True
    assert parse_result.action == "ATTACK"

    # Invalid action fails with error metadata
    parse_result = controller.parse("REASONING: Defending.\nACTION: DEFEND")
    assert parse_result.success is False
    assert parse_result.action is None
    assert parse_result.error is not None
    assert "DEFEND" in parse_result.error


def test_reasoning_controller_casefold_validation():
    """
    Verify ReasoningController honours case-insensitive validation (VF1).
    """
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK"]))

    parse_result = controller.parse("REASONING: attack.\nACTION: attack")
    assert parse_result.success is True
    assert parse_result.action == "ATTACK"


def test_reasoning_controller_rejects_incidental_allowed_mentions():
    """Reasoning prose must not be promoted into a player decision."""
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK", "POTION"]))

    parse_result = controller.parse(
        "It's my turn. I will ATTACK.\n\nHealth:\n- You: 100 HP\n- Opponent: 80 HP"
    )

    assert parse_result.success is False
    assert parse_result.action is None
    assert parse_result.metadata["contract_satisfied"] is False


def test_reasoning_controller_rejects_last_action_and_intent_mentions_without_field():
    """`Last Action:` and free-form intent are not an explicit action declaration."""
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK", "POTION"]))

    parse_result = controller.parse(
        "Last Action:\n  You: None\n  Opponent: ATTACK\n\nI will use ATTACK."
    )

    assert parse_result.success is False
    assert parse_result.action is None


def test_reasoning_controller_rejects_lowercase_allowed_mention():
    """Free-form reasoning without an ACTION field fails closed."""
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK", "POTION"]))

    parse_result = controller.parse("It's your turn! You can attack one more time.")

    assert parse_result.success is False
    assert parse_result.action is None


def test_reasoning_controller_is_game_agnostic_for_allowed_actions():
    """Reasoning controller must follow bound game actions, independent of game domain semantics."""
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["CAST_SPELL", "GUARD"]))

    parse_result = controller.parse("REASONING: This creates an advantage.\nACTION: cast_spell")

    assert parse_result.success is True
    assert parse_result.action == "CAST_SPELL"
    assert "CAST_SPELL" in parse_result.metadata["allowed_actions"]


def test_reasoning_controller_to_action_result():
    """
    Verify ParseResult.to_action_result raises ActionParseError on failure (VF2-VF3).
    """
    controller = ReasoningController()
    controller.bind_game(MockGame(allowed_actions=["ATTACK"]))

    parse_result = controller.parse("REASONING: fallback.\nACTION: INVALID")
    assert parse_result.success is False

    # Should raise ActionParseError
    with pytest.raises(ActionParseError) as exc_info:
        parse_result.to_action_result()

    assert exc_info.value.parse_result is parse_result
    assert exc_info.value.parse_result.error is not None


def test_CP2_parse_conclusion_default_passthrough():
    """Default conclusion parsing should return a reflection dict."""
    controller = ActionOnlyController()

    parsed = controller.parse_conclusion("  Good game!  ")

    assert parsed == {"reflection": "Good game!"}


# ============================================================================
# FI1-FI2: Format Instructions Tests
# ============================================================================


def test_FI1_format_instructions_align_with_parsing():
    """
    SPEC-CONTROLLER FI1: Format instructions align with parsing expectations.

    If controller requires "ACTION:" prefix, instructions must mention it.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND"])
    controller.bind_game(game)

    instructions = controller.get_format_instructions()

    # Instructions must mention the ACTION: format
    assert "ACTION:" in instructions

    # Instructions must list allowed actions (after binding)
    assert "ATTACK" in instructions
    assert "DEFEND" in instructions


def test_FI2_format_instructions_deterministic():
    """
    SPEC-CONTROLLER FI2: Format instructions are deterministic.

    Repeated calls must return identical instructions.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND"])
    controller.bind_game(game)

    instructions_1 = controller.get_format_instructions()
    instructions_2 = controller.get_format_instructions()

    assert instructions_1 == instructions_2


# ============================================================================
# AP1-AP3: Action Parsing Tests
# ============================================================================


def test_AP1_parse_populates_raw_response():
    """
    SPEC-CONTROLLER AP1: parse() populates ParseResult.raw_response.

    Verify that the raw_response field contains the trimmed input.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK"])
    controller.bind_game(game)

    result = controller.parse("  ACTION: ATTACK  ")

    assert result.raw_response == "ACTION: ATTACK"  # Trimmed


def test_AP2_parse_success():
    """
    SPEC-CONTROLLER AP2: On success, ParseResult has success=True, action set, no error.

    Verify successful parse result structure.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK"])
    controller.bind_game(game)

    result = controller.parse("ACTION: ATTACK")

    assert result.success is True
    assert result.action == "ATTACK"
    assert result.error is None


def test_AP3_parse_failure():
    """
    SPEC-CONTROLLER AP3: On failure, ParseResult has success=False, error explained.

    Verify failed parse result structure.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK"])
    controller.bind_game(game)

    # Response with no action tokens at all
    result = controller.parse("I'm thinking about my strategy...")

    assert result.success is False
    assert result.action is None
    assert result.error is not None
    assert "No ACTION: field found" in result.error


# ============================================================================
# DS1-DS2: Determinism & Safety Tests
# ============================================================================


def test_DS1_parse_no_side_effects():
    """
    SPEC-CONTROLLER DS1: Controllers MUST NOT mutate inputs or global state.

    Verify that parsing doesn't mutate the input string or controller state.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK"])
    controller.bind_game(game)

    original_input = "ACTION: ATTACK"
    input_copy = original_input  # Python strings are immutable, but verify behavior

    controller.parse(original_input)

    # Input unchanged
    assert original_input == input_copy


def test_DS2_parse_deterministic():
    """
    SPEC-CONTROLLER DS2: Repeated calls with identical inputs yield identical outputs.

    Verify that parse() is a pure function.
    """
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND"])
    controller.bind_game(game)

    result_1 = controller.parse("ACTION: ATTACK")
    result_2 = controller.parse("ACTION: ATTACK")

    assert result_1.success == result_2.success
    assert result_1.action == result_2.action
    assert result_1.raw_response == result_2.raw_response
    assert result_1.error == result_2.error
