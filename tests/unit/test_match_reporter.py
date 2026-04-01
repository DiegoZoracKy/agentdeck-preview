"""
Unit tests for MatchReporter spectator.

Tests verify that MatchReporter:
- Uses injected logger for all output (LI1-LI5)
- Displays match start banner
- Reports turn-by-turn gameplay
- Shows state changes and token usage
- Displays match completion summary
- Resets state between matches
"""

from agentdeck.core.types import ActionResult, Event, MatchResult
from agentdeck.spectators.reporter import MatchReporter


class MockLogger:
    """Test logger that captures log calls."""

    def __init__(self):
        self.info_calls = []
        self.debug_calls = []

    def info(self, msg: str):
        self.info_calls.append(msg)

    def debug(self, msg: str):
        self.debug_calls.append(msg)


class MockGame:
    """Mock game for testing."""


class MockPlayer:
    """Mock player for testing."""

    def __init__(self, name: str):
        self.name = name


def test_reporter_uses_injected_logger():
    """Verify LI1: MatchReporter uses injected logger for output."""
    reporter = MatchReporter()
    test_logger = MockLogger()

    # Logger should be None initially
    assert reporter.logger is None

    # Inject logger (simulates Console injection)
    reporter.logger = test_logger

    # Trigger match start
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="test-match-1"
    )

    # Verify logger was used
    assert len(test_logger.info_calls) > 0
    assert any("test-match-1" in call for call in test_logger.info_calls)


def test_reporter_match_start_banner():
    """Verify reporter displays match start information."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Trigger match start
    game = MockGame()
    players = [MockPlayer("Alice"), MockPlayer("Bob")]
    reporter.on_match_start(game=game, players=players, match_id="match-abc")

    # Check output
    output = "\n".join(test_logger.info_calls)
    assert "match-abc starting" in output
    assert "MockGame" in output
    assert "Alice" in output
    assert "Bob" in output


def test_reporter_turn_reporting():
    """Verify reporter shows turn-by-turn gameplay."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match context
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    # Clear initial calls
    test_logger.info_calls.clear()

    # Simulate turn event
    turn_event = Event(
        type="gameplay",
        data={
            "mechanic": "turn_based",
            "phase_index": 0,
            "player": "Alice",
            "action": "ATTACK",
            "state_before": {"health": {"Alice": 100, "Bob": 100}},
            "state_after": {"health": {"Alice": 100, "Bob": 80}},
            "metadata": {
                "usage_info": {"prompt_tokens": 153, "completion_tokens": 2, "total_tokens": 155}
            },
            "turn_context": {"turn_number": 1, "duration": 1.04},
        },
        context={"match_id": "match-1", "turn_index": 0},
    )

    reporter.on_gameplay(turn_event)

    # Check output
    output = "\n".join(test_logger.info_calls)
    assert "Turn 1: Alice" in output
    assert "Action: ATTACK" in output
    assert "tokens=155" in output
    assert "prompt=153" in output
    assert "completion=2" in output
    assert "health.Bob:100->80" in output
    assert "1.04s" in output


def test_reporter_first_player_selection():
    """Verify reporter logs first player selection on turn 0."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # First turn (turn_index = 0)
    first_turn = Event(
        type="gameplay",
        data={
            "mechanic": "turn_based",
            "phase_index": 0,
            "player": "Bob",
            "action": "DEFEND",
            "state_before": {},
            "state_after": {},
            "metadata": {},
            "turn_context": {"turn_number": 1},
        },
        context={"turn_index": 0},
    )

    reporter.on_gameplay(first_turn)

    output = "\n".join(test_logger.info_calls)
    assert "First player selected: Bob (index 1)" in output


def test_reporter_state_delta_computation():
    """Verify reporter computes state changes correctly."""
    reporter = MatchReporter(show_state_changes=True)
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # Turn with multiple state changes
    turn_event = Event(
        type="gameplay",
        data={
            "mechanic": "turn_based",
            "phase_index": 5,
            "player": "Alice",
            "action": "POTION",
            "state_before": {
                "health": {"Alice": 80, "Bob": 100},
                "potions": {"Alice": 3, "Bob": 3},
                "last_action": {"Alice": "ATTACK", "Bob": None},
            },
            "state_after": {
                "health": {"Alice": 100, "Bob": 100},
                "potions": {"Alice": 2, "Bob": 3},
                "last_action": {"Alice": "POTION", "Bob": None},
            },
            "metadata": {},
            "turn_context": {"turn_number": 6},
        },
        context={"turn_index": 5},
    )

    reporter.on_gameplay(turn_event)

    output = "\n".join(test_logger.info_calls)
    assert "health.Alice:80->100" in output
    assert "last_action.Alice:ATTACK->POTION" in output
    assert "potions.Alice:3->2" in output


def test_reporter_match_end_summary():
    """Verify reporter displays match completion summary."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-123"
    )

    test_logger.info_calls.clear()

    # Trigger match end
    result = MatchResult(
        winner="Alice",
        final_state={"health": {"Alice": 20, "Bob": 0}},
        events=[],
        seed=42,
        metadata={"turns": 21, "duration": 18.0},
    )

    reporter.on_match_end(result)

    # Check output
    output = "\n".join(test_logger.info_calls)
    assert "match-123 complete" in output
    assert "Winner: Alice" in output
    assert "Turns: 21" in output
    assert "Duration:" in output


def test_reporter_without_logger_silent():
    """Verify reporter does nothing without logger (before injection)."""
    reporter = MatchReporter()

    # No logger injected yet
    assert reporter.logger is None

    # These should not raise errors
    reporter.on_match_start(game=MockGame(), players=[MockPlayer("Alice")], match_id="test")

    reporter.on_gameplay(
        Event(
            type="gameplay",
            data={"mechanic": "turn_based", "player": "Alice", "action": "MOVE"},
            context={},
        )
    )

    reporter.on_match_end(
        MatchResult(winner="Alice", final_state={}, events=[], seed=1, metadata={})
    )

    # No errors = success


def test_reporter_state_reset_between_matches():
    """Verify reporter resets state per SS3 between matches."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # First match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    assert reporter.match_id == "match-1"
    assert reporter.game_name == "MockGame"
    assert reporter.player_names == ["Alice", "Bob"]

    # Second match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Charlie"), MockPlayer("Dave")], match_id="match-2"
    )

    # State should be reset
    assert reporter.match_id == "match-2"
    assert reporter.player_names == ["Charlie", "Dave"]
    assert reporter.first_player_selected is False  # Reset


def test_reporter_disable_state_changes():
    """Verify state changes can be disabled."""
    reporter = MatchReporter(show_state_changes=False)
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(game=MockGame(), players=[MockPlayer("Alice")], match_id="match-1")

    test_logger.info_calls.clear()

    # Turn with state changes
    turn_event = Event(
        type="gameplay",
        data={
            "mechanic": "turn_based",
            "phase_index": 0,
            "player": "Alice",
            "action": "MOVE",
            "state_before": {"x": 0},
            "state_after": {"x": 1},
            "metadata": {},
            "turn_context": {"turn_number": 1},
        },
        context={"turn_index": 0},
    )

    reporter.on_gameplay(turn_event)

    output = "\n".join(test_logger.info_calls)
    # Should show turn info but not state delta
    assert "Turn 1" in output
    assert "Action: MOVE" in output
    assert "x:0->1" not in output  # State changes disabled


def test_reporter_non_turn_based_mechanic_ignored():
    """Verify reporter only processes turn-based mechanics."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    reporter.on_match_start(game=MockGame(), players=[MockPlayer("Alice")], match_id="match-1")

    test_logger.info_calls.clear()

    # Simultaneous mechanic event (not supported yet)
    simul_event = Event(
        type="gameplay",
        data={
            "mechanic": "simultaneous",
            "phase_index": 0,
            "actions": {"Alice": "MOVE", "Bob": "ATTACK"},
        },
        context={},
    )

    reporter.on_gameplay(simul_event)

    # Should not log anything for non-turn-based
    assert len(test_logger.info_calls) == 0


def test_reporter_with_action_result_dataclass():
    """
    Verify reporter handles real ActionResult dataclass from live engine.

    This tests Codex's finding: GAMEPLAY events carry ActionResult dataclass
    with nested metadata, not plain strings. The reporter must extract:
    - action text from action_result.action
    - reasoning from action_result.reasoning (Phase 2.8)
    - usage_info from action_result.metadata["usage_info"]
    """
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # Create real ActionResult as the engine would
    action_result = ActionResult(
        action="ATTACK",
        reasoning="Opponent is weak, go aggressive",
        metadata={
            "usage_info": {"prompt_tokens": 200, "completion_tokens": 5, "total_tokens": 205},
            "validated": True,
            "allowed_actions": ["ATTACK", "DEFEND", "POTION"],
        },
        raw_response="REASONING: Opponent is weak\nACTION: ATTACK",
    )

    # Simulate GAMEPLAY event with ActionResult (as live engine does)
    turn_event = Event(
        type="gameplay",
        data={
            "mechanic": "turn_based",
            "phase_index": 3,
            "player": "Alice",
            "action": action_result,  # ActionResult dataclass, not string
            "state_before": {"health": {"Alice": 100, "Bob": 100}},
            "state_after": {"health": {"Alice": 100, "Bob": 80}},
            "turn_context": {"turn_number": 4, "duration": 1.2},
        },
        context={"match_id": "match-1", "turn_index": 3},
    )

    reporter.on_gameplay(turn_event)

    # Verify reporter extracted action text and reasoning correctly
    output = "\n".join(test_logger.info_calls)
    assert (
        "Reasoning: Opponent is weak, go aggressive" in output
    ), "Should display reasoning from ActionResult"
    assert "Action: ATTACK" in output, "Should extract action text from ActionResult.action"

    # Verify reporter found usage_info in ActionResult.metadata
    assert "tokens=205" in output, "Should find usage_info in ActionResult.metadata"
    assert "prompt=200" in output
    assert "completion=5" in output

    # Verify state changes shown
    assert "health.Bob:100->80" in output

    # Should NOT see repr of ActionResult object
    assert "ActionResult" not in output, "Should not log repr of ActionResult"


def test_reporter_with_reasoning_from_dict():
    """
    Verify reporter displays reasoning when action is dict format from Console.

    Console emits action as dict: {"action": "...", "reasoning": "...", "metadata": {...}}
    This test ensures reasoning is properly extracted and displayed (Phase 2.8).
    """
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # Console emits action as dict with reasoning field
    turn_event = Event(
        type="gameplay",
        data={
            "mechanic": "turn_based",
            "phase_index": 0,
            "player": "Alice",
            "action": {
                "action": "DEFEND",
                "reasoning": "My health is low, I need to be defensive",
                "metadata": {
                    "usage_info": {
                        "prompt_tokens": 150,
                        "completion_tokens": 10,
                        "total_tokens": 160,
                    }
                },
            },
            "state_before": {"health": {"Alice": 30, "Bob": 100}},
            "state_after": {"health": {"Alice": 30, "Bob": 100}},
            "turn_context": {"turn_number": 5, "duration": 0.8},
        },
        context={"match_id": "match-1", "turn_index": 4},
    )

    reporter.on_gameplay(turn_event)

    # Verify reasoning and action displayed
    output = "\n".join(test_logger.info_calls)
    assert "Turn 5: Alice" in output
    assert (
        "Reasoning: My health is low, I need to be defensive" in output
    ), "Should display reasoning from dict"
    assert "Action: DEFEND" in output
    assert "tokens=160" in output


def test_reporter_handshake_complete():
    """Verify reporter displays handshake completion."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # Handshake events
    handshake_event = Event(
        type="player_handshake_complete",
        data={
            "player": "Alice",
            "accepted": True,
            "normalized_response": "OK",
            "response_text": "OK",
            "controller_metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_player_handshake_complete(handshake_event)

    output = "\n".join(test_logger.info_calls)
    assert "✓ Alice handshake: OK" in output


def test_reporter_handshake_abort():
    """Verify reporter displays handshake rejection."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # Handshake rejection event
    abort_event = Event(
        type="player_handshake_abort",
        data={
            "player": "Bob",
            "accepted": False,
            "normalized_response": None,
            "response_text": "maybe",
            "controller_metadata": {},
            "reason": "I don't understand the rules",
        },
        context={"match_id": "match-1"},
    )

    reporter.on_player_handshake_abort(abort_event)

    output = "\n".join(test_logger.info_calls)
    assert "✗ Bob rejected handshake: I don't understand the rules" in output


def test_reporter_player_conclusion():
    """Verify reporter displays player conclusions/reflections."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # Conclusion events
    conclusion_event = Event(
        type="player_conclusion",
        data={
            "player": "Alice",
            "reflection_text": "Great match! I should have used more potions.",
            "metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_player_conclusion(conclusion_event)

    output = "\n".join(test_logger.info_calls)
    assert "💭 Alice reflection: Great match! I should have used more potions." in output


def test_reporter_conclusion_without_reflection():
    """Verify reporter handles missing reflections gracefully."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # Conclusion event without reflection (player returned None)
    conclusion_event = Event(
        type="player_conclusion",
        data={"player": "Bob", "reflection_text": None, "metadata": {}},
        context={"match_id": "match-1"},
    )

    reporter.on_player_conclusion(conclusion_event)

    # Should not log anything if reflection is None
    output = "\n".join(test_logger.info_calls)
    assert len(test_logger.info_calls) == 0


def test_reporter_handshake_complete_with_instructions():
    """Verify reporter displays handshake instructions alongside completion."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # First, emit dialogue_turn with handshake prompt
    dialogue_event = Event(
        type="dialogue_turn",
        data={
            "phase": "handshake",
            "player": "Alice",
            "prompt_text": "You are playing FixedDamageGame.\n\nGame rules:\n- ATTACK deals 20 damage\n- First to 0 HP loses\n\nPlease respond with OK to begin.",
            "response_text": "OK",
            "metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_dialogue_turn(dialogue_event)

    # Then emit handshake_complete
    handshake_event = Event(
        type="player_handshake_complete",
        data={
            "player": "Alice",
            "accepted": True,
            "normalized_response": "OK",
            "response_text": "OK",
            "controller_metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_player_handshake_complete(handshake_event)

    # Verify output includes both completion and instructions
    output = "\n".join(test_logger.info_calls)
    assert "Alice handshake instructions:" in output
    assert "You are playing FixedDamageGame" in output
    assert "ATTACK deals 20 damage" in output
    assert "Please respond with OK to begin" in output
    assert "✓ Alice handshake: OK" in output


def test_reporter_handshake_instructions_cached_from_prompt_field():
    """Ensure reporter handles live dialogue_turn payloads using 'prompt' key."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    live_dialogue_event = Event(
        type="dialogue_turn",
        data={
            "phase": "handshake",
            "player": "Alice",
            "prompt": "Live handshake prompt\nLine 2\nLine 3",
            "response": "OK",
        },
        context={"match_id": "match-1"},
    )

    reporter.on_dialogue_turn(live_dialogue_event)

    handshake_event = Event(
        type="player_handshake_complete",
        data={
            "player": "Alice",
            "accepted": True,
            "normalized_response": "OK",
            "response_text": "OK",
            "controller_metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_player_handshake_complete(handshake_event)

    output = "\n".join(test_logger.info_calls)
    assert "Alice handshake instructions:" in output
    assert "Live handshake prompt" in output
    assert "Line 2" in output


def test_reporter_handshake_abort_with_instructions():
    """Verify reporter displays handshake instructions alongside rejection."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(
        game=MockGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")], match_id="match-1"
    )

    test_logger.info_calls.clear()

    # First, emit dialogue_turn with handshake prompt
    dialogue_event = Event(
        type="dialogue_turn",
        data={
            "phase": "handshake",
            "player": "Bob",
            "prompt_text": "You are playing ComplexGame.\n\nInstructions:\nLine 1\nLine 2\nLine 3",
            "response_text": "I don't understand",
            "metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_dialogue_turn(dialogue_event)

    # Then emit handshake_abort
    abort_event = Event(
        type="player_handshake_abort",
        data={
            "player": "Bob",
            "accepted": False,
            "normalized_response": None,
            "response_text": "I don't understand",
            "controller_metadata": {},
            "reason": "Unclear instructions",
        },
        context={"match_id": "match-1"},
    )

    reporter.on_player_handshake_abort(abort_event)

    # Verify output includes both rejection and instructions
    output = "\n".join(test_logger.info_calls)
    assert "Bob handshake instructions:" in output
    assert "You are playing ComplexGame" in output
    assert "Line 1" in output
    assert "✗ Bob rejected handshake: Unclear instructions" in output


def test_reporter_handshake_instructions_display_full_prompt():
    """Verify long handshake instructions are displayed without truncation."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # Set up match
    reporter.on_match_start(game=MockGame(), players=[MockPlayer("Alice")], match_id="match-1")

    test_logger.info_calls.clear()

    # Create a long prompt (15 lines)
    long_prompt = "\n".join([f"Line {i}" for i in range(1, 16)])

    # Emit dialogue_turn with long prompt
    dialogue_event = Event(
        type="dialogue_turn",
        data={
            "phase": "handshake",
            "player": "Alice",
            "prompt_text": long_prompt,
            "response_text": "OK",
            "metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_dialogue_turn(dialogue_event)

    # Emit handshake_complete
    handshake_event = Event(
        type="player_handshake_complete",
        data={
            "player": "Alice",
            "accepted": True,
            "normalized_response": "OK",
            "response_text": "OK",
            "controller_metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_player_handshake_complete(handshake_event)

    # Verify full prompt is displayed without truncation
    output = "\n".join(test_logger.info_calls)
    assert "Alice handshake instructions:" in output
    for i in range(1, 16):
        assert f"Line {i}" in output
    assert "... (" not in output
    assert "✓ Alice handshake: OK" in output


def test_reporter_handshake_cache_cleared_between_matches():
    """Verify handshake prompt cache is cleared between matches (SS3)."""
    reporter = MatchReporter()
    test_logger = MockLogger()
    reporter.logger = test_logger

    # First match - cache a handshake prompt
    reporter.on_match_start(game=MockGame(), players=[MockPlayer("Alice")], match_id="match-1")

    dialogue_event = Event(
        type="dialogue_turn",
        data={
            "phase": "handshake",
            "player": "Alice",
            "prompt_text": "First match instructions",
            "response_text": "OK",
            "metadata": {},
        },
        context={"match_id": "match-1"},
    )

    reporter.on_dialogue_turn(dialogue_event)

    # Verify cache has Alice's prompt
    assert "Alice" in reporter._handshake_prompts
    assert reporter._handshake_prompts["Alice"] == "First match instructions"

    # Second match - cache should be cleared
    reporter.on_match_start(game=MockGame(), players=[MockPlayer("Bob")], match_id="match-2")

    # Cache should be empty after match start
    assert len(reporter._handshake_prompts) == 0
    assert "Alice" not in reporter._handshake_prompts
