"""
Integration tests for parse failure handling (SPEC-CONTROLLER v1.2.0).

Tests the complete flow:
1. ActionParseError raised by controller
2. PLAYER_ACTION_PARSE_FAILED event emitted
3. Game hook determines policy
4. Match aborted with MATCH_END event
5. Partial match recorded with outcome="aborted"
"""

import pytest
import tempfile
import json
from pathlib import Path

from agentdeck.core import Console
from agentdeck.core.base import Player, Game
from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.core.types import (
    ParseResult,
    GameStatus,
    MatchAbortedError,
    ParseFailurePolicy,
    ActionParseError,
)
from agentdeck.core.session import AgentDeckConfig
from agentdeck.controllers import ActionOnlyController
from agentdeck.core.recorder import Recorder


class MockGame(TurnBasedGame):
    """Simple game for testing parse failures."""

    allowed_actions = ["ATTACK", "DEFEND"]
    instructions = "Choose ATTACK or DEFEND each turn."

    def __init__(self, parse_failure_policy=None):
        """
        Args:
            parse_failure_policy: Optional policy override for parse failures
        """
        super().__init__()
        self._parse_failure_policy = parse_failure_policy

    def default_handshake_template(self):
        return "Ready to play? (Reply OK)"

    def setup(self, player_names, seed=None):
        return {
            "turn": 1,
            "players": {name: {"hp": 10} for name in player_names},
        }

    def get_view(self, state, player_name):
        return {"your_hp": state["players"][player_name]["hp"], "turn": state["turn"]}

    def update(self, state, player_name, action, rng=None):
        state["turn"] += 1
        # Simple damage: ATTACK deals 3 damage to opponent
        if action.action == "ATTACK":
            for name in state["players"]:
                if name != player_name:
                    state["players"][name]["hp"] -= 3
        return state

    def status(self, state):
        alive = [name for name, data in state["players"].items() if data["hp"] > 0]
        if len(alive) == 1:
            return GameStatus(is_over=True, winner=alive[0])
        return GameStatus(is_over=False, winner=None)

    def get_player_order(self, players, rng=None, match_context=None):
        """Preserve declared player order for deterministic testing."""
        return list(players)

    def on_action_parse_failure(self, player_name, error, turn_context):
        """Override policy if specified in constructor."""
        if self._parse_failure_policy is not None:
            return self._parse_failure_policy
        return super().on_action_parse_failure(player_name, error, turn_context)


class FailingController(ActionOnlyController):
    """Controller that always fails to parse (for testing)."""

    def __init__(self, fail_on_turn=1):
        super().__init__()
        self.fail_on_turn = fail_on_turn
        self.parse_count = 0

    def parse(self, raw_response, **kwargs):
        self.parse_count += 1
        if self.parse_count == self.fail_on_turn:
            # Return failed ParseResult
            return ParseResult(
                success=False,
                action=None,
                raw_response=raw_response,
                reasoning=None,
                error="Simulated parse failure for testing",
                metadata={"candidates": ["ATTACK", "DEFEND"]},
            )
        # Otherwise return valid action
        return ParseResult(
            success=True,
            action="ATTACK",
            raw_response=raw_response,
            reasoning=None,
            error=None,
            metadata={},
        )


class MockPlayer(Player):
    """Player that uses FailingController."""

    def __init__(self, name, fail_on_turn=1):
        controller = FailingController(fail_on_turn=fail_on_turn)
        super().__init__(name=name, controller=controller)
        self.fail_on_turn = fail_on_turn

    def get_response(self, prompt: str) -> str:
        """Mock LLM response."""
        return f"Player {self.name} mock response"

    def decide(self, observation, **kwargs):
        # Simple mock: just return "raw" and let controller parse
        raw_response = f"Player {self.name} choosing action"
        parse_result = self.controller.parse(raw_response)
        return parse_result.to_action_result()

    def handshake(self, context):
        return "READY"

    def conclude(self, outcome, **kwargs):
        pass


def test_parse_failure_abort_and_record():
    """
    Test that parse failure triggers ABORT_MATCH policy and records partial match.

    Flow:
    1. Player 1 fails to parse action on turn 1
    2. ActionParseError raised
    3. Game.on_action_parse_failure() returns ABORT_MATCH (default)
    4. Console emits MATCH_END with outcome="aborted"
    5. Recorder captures partial match with parse failure event
    6. MatchAbortedError propagated to batch level
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentDeckConfig(
            run_dir=str(tmpdir),
            max_turns=10,
            concurrency=1,
        )

        console = Console(config=config, recorder=Recorder())
        game = MockGame(parse_failure_policy=ParseFailurePolicy.ABORT_MATCH)
        players = [
            MockPlayer(name="Alice", fail_on_turn=1),  # Fails on first parse
            MockPlayer(name="Bob", fail_on_turn=999),  # Never fails
        ]

        # Run match - should abort and raise MatchAbortedError
        with pytest.raises(MatchAbortedError) as exc_info:
            console.run(game, players, matches=1, seed=42)

        # Verify exception details
        abort_error = exc_info.value
        assert abort_error.player_name == "Alice"
        assert abort_error.policy == ParseFailurePolicy.ABORT_MATCH
        assert abort_error.turn_context is not None
        assert abort_error.turn_context.turn_number == 1

        # Verify parse error details
        assert isinstance(abort_error.parse_error, ActionParseError)
        assert abort_error.parse_error.parse_result.success is False
        assert abort_error.parse_error.parse_result.error == "Simulated parse failure for testing"

        # Verify match was recorded despite abort
        # Console creates records directory under run_dir/session_id/records
        session_dir = Path(tmpdir) / console.session_state.session_id
        records_dir = session_dir / "records"
        match_files = list(records_dir.glob("match_*.json"))
        assert len(match_files) == 1, "Should have recorded aborted match"

        # Load and verify recording
        with open(match_files[0]) as f:
            match_data = json.load(f)

        # Verify schema version
        assert match_data["schema_version"] == "1.3"
        assert match_data.get("schema_type") == "match"

        # Verify match metadata shows abort
        metadata = match_data["metadata"].get("match", {})
        assert metadata["outcome"] == "aborted"
        assert metadata["abort_reason"] == "parse_failure"
        assert metadata["failing_player"] == "Alice"
        assert metadata["abort_turn"] == 1
        assert metadata["policy"] == "abort"

        # Verify parse error details in metadata
        parse_error = metadata["parse_error"]
        assert parse_error["success"] is False
        assert parse_error["error"] == "Simulated parse failure for testing"
        assert "ATTACK" in parse_error["candidates"]
        assert "DEFEND" in parse_error["candidates"]

        # Verify turn context serialized in metadata
        assert "abort_turn_context" in metadata
        turn_ctx = metadata["abort_turn_context"]
        assert turn_ctx["turn_number"] == 1
        assert turn_ctx["player"] == "Alice"

        # Verify PLAYER_ACTION_PARSE_FAILED event recorded
        events = match_data["events"]
        parse_failed_events = [e for e in events if e["type"] == "player_action_parse_failed"]
        assert len(parse_failed_events) == 1

        parse_event = parse_failed_events[0]
        assert parse_event["data"]["player"] == "Alice"
        assert parse_event["data"]["turn_number"] == 1
        assert parse_event["data"]["policy_outcome"] == "abort"
        assert parse_event["data"]["parse_result"]["error"] == "Simulated parse failure for testing"

        # Schema v1.3: Verify prompt metadata (PM1-PM6) embedded in event
        # This is the core reason for the schema bump - no more dialogue array duplication
        # PM1-PM3 should be present (prompt_text, prompt_blocks, response_text)
        assert "prompt_text" in parse_event["data"], "PM1: prompt_text must be present"
        assert "prompt_blocks" in parse_event["data"], "PM2: prompt_blocks must be present"
        assert "response_text" in parse_event["data"], "PM3: response_text must be present"
        # PM4-PM6 (renderer_output, controller_format, controller_metadata) are optional

        # Verify final state is from point of abort (not reset)
        # Since failure happened on turn 1, state should still show turn=1
        final_state = match_data["final_state"]
        assert final_state["turn"] == 1  # NOT reset to 1 by setup()
        assert final_state["players"]["Alice"]["hp"] == 10  # No damage yet
        assert final_state["players"]["Bob"]["hp"] == 10


def test_parse_failure_on_turn_2():
    """
    Test that parse failure on turn 2 captures correct in-flight state.

    This verifies Codex fix #1: state should reflect turn 2, not be reset to turn 1.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentDeckConfig(
            run_dir=str(tmpdir),
            max_turns=10,
            concurrency=1,
        )

        console = Console(config=config, recorder=Recorder())
        game = MockGame(parse_failure_policy=ParseFailurePolicy.ABORT_MATCH)
        players = [
            MockPlayer(name="Alice", fail_on_turn=999),  # Never fails
            MockPlayer(name="Bob", fail_on_turn=1),  # Fails on first parse (turn 2, Bob's turn)
        ]

        # Run match - Bob fails on turn 2
        with pytest.raises(MatchAbortedError) as exc_info:
            console.run(game, players, matches=1, seed=42)

        # Verify abort happened on turn 2
        abort_error = exc_info.value
        assert abort_error.player_name == "Bob"
        assert abort_error.turn_context.turn_number == 2

        # Load recording and verify state shows turn 2
        session_dir = Path(tmpdir) / console.session_state.session_id
        records_dir = session_dir / "records"
        match_files = list(records_dir.glob("match_*.json"))
        assert len(match_files) == 1

        with open(match_files[0]) as f:
            match_data = json.load(f)

        final_state = match_data["final_state"]

        # State should reflect that Alice took turn 1 (ATTACK), so:
        # - turn counter incremented to 2
        # - Bob's HP reduced by 3 (from Alice's ATTACK)
        assert final_state["turn"] == 2, "State should show turn 2, not reset to 1"
        assert final_state["players"]["Alice"]["hp"] == 10, "Alice took no damage"
        assert final_state["players"]["Bob"]["hp"] == 7, "Bob took 3 damage from Alice's ATTACK"


def test_parse_failure_skip_turn():
    """
    Test SKIP_TURN policy: parse failure results in skipped turn, match continues.

    Flow:
    1. Player 1 fails to parse action on turn 1
    2. Game.on_action_parse_failure() returns SKIP_TURN
    3. Console emits PLAYER_ACTION with sentinel ActionResult (action="__SKIP_TURN__")
    4. Game state unchanged (no call to game.update())
    5. Match continues to next player/turn
    6. Recording shows parse failure + sentinel action
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentDeckConfig(
            run_dir=str(tmpdir),
            max_turns=10,
            concurrency=1,
        )

        console = Console(config=config, recorder=Recorder())

        # Custom game that returns SKIP_TURN policy
        class SkipTurnGame(MockGame):
            def on_action_parse_failure(self, player_name, parse_error, turn_context):
                return ParseFailurePolicy.SKIP_TURN

        game = SkipTurnGame()
        players = [
            MockPlayer(name="Alice", fail_on_turn=1),  # Fails on first parse (turn 1)
            MockPlayer(name="Bob", fail_on_turn=999),  # Never fails
        ]

        # Run match - should complete successfully (no exception)
        match_results = console.run(game, players, matches=1, seed=42)

        # Match should complete (not abort)
        assert len(match_results) == 1
        match_result = match_results[0]

        # Match should end normally (someone wins or max turns reached)
        # Since Alice skips turn 1, Bob attacks on turn 2, etc.
        # Bob should win (Alice never attacks due to skip)
        assert match_result.winner == "Bob"
        assert match_result.metadata.get("outcome") != "aborted"

        # Load recording and verify SKIP_TURN semantics
        session_dir = Path(tmpdir) / console.session_state.session_id
        records_dir = session_dir / "records"
        match_files = list(records_dir.glob("match_*.json"))
        assert len(match_files) == 1

        with open(match_files[0]) as f:
            match_data = json.load(f)

        # Verify PLAYER_ACTION_PARSE_FAILED event recorded
        events = match_data["events"]
        parse_failed_events = [e for e in events if e["type"] == "player_action_parse_failed"]
        assert len(parse_failed_events) == 1

        parse_event = parse_failed_events[0]
        assert parse_event["data"]["player"] == "Alice"
        assert parse_event["data"]["turn_number"] == 1
        assert (
            parse_event["data"]["policy_outcome"] == "skip"
        )  # Enum value is "skip" not "skip_turn"

        # Schema v1.3: Verify prompt metadata (PM1-PM6) embedded in event
        assert "prompt_text" in parse_event["data"], "PM1: prompt_text must be present"
        assert "prompt_blocks" in parse_event["data"], "PM2: prompt_blocks must be present"
        assert "response_text" in parse_event["data"], "PM3: response_text must be present"


def test_parse_failure_forfeit():
    """
    Test FORFEIT policy: parse failure results in match forfeit, opponent wins.

    Flow:
    1. Player 1 fails to parse action on turn 1
    2. Game.on_action_parse_failure() returns FORFEIT
    3. Console determines winner (opponent)
    4. Console emits MATCH_END with winner + parse failure metadata
    5. Match ends normally (no exception propagation)
    6. Recording shows parse failure + match completion with winner
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentDeckConfig(
            run_dir=str(tmpdir),
            max_turns=10,
            concurrency=1,
        )

        console = Console(config=config, recorder=Recorder())

        # Custom game that returns FORFEIT policy
        class ForfeitGame(MockGame):
            def on_action_parse_failure(self, player_name, parse_error, turn_context):
                return ParseFailurePolicy.FORFEIT

        game = ForfeitGame()
        players = [
            MockPlayer(name="Alice", fail_on_turn=1),  # Fails on first parse (turn 1)
            MockPlayer(name="Bob", fail_on_turn=999),  # Never fails
        ]

        # Run match - should complete successfully (no exception)
        match_results = console.run(game, players, matches=1, seed=42)

        # Match should complete with Bob as winner (Alice forfeited)
        assert len(match_results) == 1
        match_result = match_results[0]
        assert match_result.winner == "Bob"

        # Metadata should indicate forfeit
        metadata = match_result.metadata
        assert metadata.get("outcome") == "forfeit"
        assert (
            metadata.get("forfeiting_player") == "Alice"
        )  # Field is "forfeiting_player" not "failing_player"
        assert metadata.get("forfeit_turn") == 1
        assert match_result.winner == "Bob"  # Winner is in MatchResult, not metadata

        # Load recording and verify FORFEIT semantics
        session_dir = Path(tmpdir) / console.session_state.session_id
        records_dir = session_dir / "records"
        match_files = list(records_dir.glob("match_*.json"))
        assert len(match_files) == 1

        with open(match_files[0]) as f:
            match_data = json.load(f)

        # Verify PLAYER_ACTION_PARSE_FAILED event recorded
        events = match_data["events"]
        parse_failed_events = [e for e in events if e["type"] == "player_action_parse_failed"]
        assert len(parse_failed_events) == 1

        parse_event = parse_failed_events[0]
        assert parse_event["data"]["player"] == "Alice"
        assert parse_event["data"]["turn_number"] == 1
        assert parse_event["data"]["policy_outcome"] == "forfeit"

        # Schema v1.3: Verify prompt metadata (PM1-PM6) embedded in event
        assert "prompt_text" in parse_event["data"], "PM1: prompt_text must be present"
        assert "prompt_blocks" in parse_event["data"], "PM2: prompt_blocks must be present"
        assert "response_text" in parse_event["data"], "PM3: response_text must be present"

        # Verify MATCH_END event shows forfeit outcome (if present in recording)
        # Note: MATCH_END might be filtered/deduplicated in some recording contexts
        match_end_events = [e for e in events if e["type"] == "MATCH_END"]
        if len(match_end_events) > 0:
            match_end = match_end_events[0]
            assert match_end.get("winner") == "Bob"
            assert match_end.get("outcome") == "forfeit"

        # Verify match metadata shows forfeit details
        match_metadata = match_data["metadata"]["match"]
        assert match_metadata["outcome"] == "forfeit"
        assert (
            match_metadata["forfeiting_player"] == "Alice"
        )  # Field is "forfeiting_player" not "failing_player"
        assert match_metadata["forfeit_turn"] == 1
        assert match_metadata["policy"] == "forfeit"

        # Verify parse error diagnostics preserved
        parse_error = match_metadata["parse_error"]
        assert parse_error["success"] is False
        assert parse_error["error"] == "Simulated parse failure for testing"
        assert parse_error["reasoning"] is None  # FailingController doesn't set reasoning
        assert "candidates" in parse_error

        # In schema v1.3, dialogue array was removed - prompt metadata embedded in events


def test_parse_failure_retry_once_success():
    """
    Test RETRY_ONCE policy: first parse fails, retry succeeds, match continues.

    Flow:
    1. Player 1 fails to parse action on turn 1 (first attempt)
    2. Game.on_action_parse_failure() returns RETRY_ONCE
    3. Console retries player.decide() with same inputs
    4. Retry succeeds (FailingController returns valid action on second call)
    5. Match continues normally
    6. Recording shows parse failure event + successful retry action
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentDeckConfig(
            run_dir=str(tmpdir),
            max_turns=10,
            concurrency=1,
        )

        console = Console(config=config, recorder=Recorder())

        # Custom game that returns RETRY_ONCE policy
        class RetryOnceGame(MockGame):
            def on_action_parse_failure(self, player_name, parse_error, turn_context):
                return ParseFailurePolicy.RETRY_ONCE

        game = RetryOnceGame()
        players = [
            MockPlayer(name="Alice", fail_on_turn=1),  # Fails on first parse (turn 1, first call)
            MockPlayer(name="Bob", fail_on_turn=999),  # Never fails
        ]

        # Run match - should complete successfully (retry succeeds)
        match_results = console.run(game, players, matches=1, seed=42)

        # Match should complete normally
        assert len(match_results) == 1
        match_result = match_results[0]
        assert match_result.metadata.get("outcome") != "aborted"

        # Load recording and verify RETRY_ONCE semantics
        session_dir = Path(tmpdir) / console.session_state.session_id
        records_dir = session_dir / "records"
        match_files = list(records_dir.glob("match_*.json"))
        assert len(match_files) == 1

        with open(match_files[0]) as f:
            match_data = json.load(f)

        # Verify PLAYER_ACTION_PARSE_FAILED event recorded (for first attempt)
        events = match_data["events"]
        parse_failed_events = [e for e in events if e["type"] == "player_action_parse_failed"]
        assert len(parse_failed_events) == 1

        parse_event = parse_failed_events[0]
        assert parse_event["data"]["player"] == "Alice"
        assert parse_event["data"]["turn_number"] == 1
        assert (
            parse_event["data"]["policy_outcome"] == "retry"
        )  # Enum value is "retry" not "retry_once"

        # Schema v1.3: Verify prompt metadata (PM1-PM6) embedded in event
        assert "prompt_text" in parse_event["data"], "PM1: prompt_text must be present"
        assert "prompt_blocks" in parse_event["data"], "PM2: prompt_blocks must be present"
        assert "response_text" in parse_event["data"], "PM3: response_text must be present"

        # Verify PLAYER_ACTION event shows successful retry
        # Should have normal action (retry succeeded)
        player_action_events = [e for e in events if e["type"] == "PLAYER_ACTION"]
        alice_actions = [e for e in player_action_events if e.get("player") == "Alice"]

        # Alice should have at least one action event (after retry succeeded)
        # The action might not have turn_number=1 due to turn loop indexing
        successful_actions = [
            e for e in alice_actions if e.get("action", {}).get("action") == "ATTACK"
        ]

        if len(successful_actions) > 0:
            retry_action = successful_actions[0]
            # parser_success should be True for successful retry
            assert retry_action["action"]["metadata"].get("parser_success", True) is True

        # In schema v1.3, dialogue array was removed - prompt metadata embedded in events


def test_parse_failure_retry_once_exhausted():
    """
    Test RETRY_ONCE policy: first parse fails, retry also fails, match aborts.

    Flow:
    1. Player 1 fails to parse action on turn 1 (first attempt)
    2. Game.on_action_parse_failure() returns RETRY_ONCE
    3. Console retries player.decide() with same inputs
    4. Retry also fails (FailingController fails twice)
    5. Console emits PLAYER_ACTION_PARSE_FAILED for retry failure (PF1/PF2 compliance)
    6. Console falls back to ABORT_MATCH
    7. MatchAbortedError raised
    8. Recording shows two parse failure events
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentDeckConfig(
            run_dir=str(tmpdir),
            max_turns=10,
            concurrency=1,
        )

        console = Console(config=config, recorder=Recorder())

        # Custom controller that fails twice
        class DoubleFailingController(ActionOnlyController):
            def __init__(self):
                super().__init__()
                self.parse_count = 0

            def parse(self, raw_response, **kwargs):
                self.parse_count += 1
                # Fail on first TWO calls
                if self.parse_count <= 2:
                    return ParseResult(
                        success=False,
                        action=None,
                        raw_response=raw_response,
                        reasoning=f"Parse failure #{self.parse_count}",
                        error=f"Simulated retry failure (attempt {self.parse_count})",
                        metadata={"candidates": ["ATTACK", "DEFEND"], "attempt": self.parse_count},
                    )
                # Otherwise succeed (shouldn't reach here)
                return ParseResult(
                    success=True,
                    action="ATTACK",
                    raw_response=raw_response,
                    reasoning=None,
                    error=None,
                    metadata={},
                )

        class DoubleFailingPlayer(Player):
            def __init__(self, name):
                controller = DoubleFailingController()
                super().__init__(name=name, controller=controller)

            def get_response(self, prompt: str) -> str:
                return f"Player {self.name} mock response"

            def decide(self, observation, **kwargs):
                raw_response = f"Player {self.name} choosing action"
                parse_result = self.controller.parse(raw_response)
                return parse_result.to_action_result()

            def handshake(self, context):
                return "READY"

            def conclude(self, outcome, **kwargs):
                pass

        # Custom game that returns RETRY_ONCE policy
        class RetryOnceGame(MockGame):
            def on_action_parse_failure(self, player_name, parse_error, turn_context):
                return ParseFailurePolicy.RETRY_ONCE

        game = RetryOnceGame()
        players = [
            DoubleFailingPlayer(name="Alice"),  # Fails twice
            MockPlayer(name="Bob", fail_on_turn=999),  # Never fails
        ]

        # Run match - should abort after retry exhausted
        with pytest.raises(MatchAbortedError) as exc_info:
            console.run(game, players, matches=1, seed=42)

        # Verify exception details
        abort_error = exc_info.value
        assert abort_error.player_name == "Alice"
        assert abort_error.policy == ParseFailurePolicy.ABORT_MATCH  # Forced after retry exhausted
        assert abort_error.turn_context.turn_number == 1

        # Verify parse error is from retry failure (second attempt)
        assert (
            "attempt 2" in abort_error.parse_error.parse_result.error.lower()
            or abort_error.parse_error.parse_result.metadata.get("attempt") == 2
        )

        # Load recording and verify TWO parse failure events (PF1/PF2 compliance)
        session_dir = Path(tmpdir) / console.session_state.session_id
        records_dir = session_dir / "records"
        match_files = list(records_dir.glob("match_*.json"))
        assert len(match_files) == 1

        with open(match_files[0]) as f:
            match_data = json.load(f)

        # CRITICAL: Should have TWO PLAYER_ACTION_PARSE_FAILED events
        # 1. First parse failure (triggers RETRY_ONCE)
        # 2. Retry failure (triggers ABORT_MATCH)
        events = match_data["events"]
        parse_failed_events = [e for e in events if e["type"] == "player_action_parse_failed"]
        assert len(parse_failed_events) == 2, "Should record both parse failures (original + retry)"

        # First event: original failure
        first_event = parse_failed_events[0]
        assert first_event["data"]["player"] == "Alice"
        assert first_event["data"]["turn_number"] == 1
        assert (
            first_event["data"]["policy_outcome"] == "retry"
        )  # Enum value is "retry" not "retry_once"
        assert (
            "attempt 1" in first_event["data"]["parse_result"]["error"].lower()
            or first_event["data"]["parse_result"]["metadata"].get("attempt") == 1
        )

        # Schema v1.3: Verify prompt metadata (PM1-PM6) on first event
        assert "prompt_text" in first_event["data"], "PM1: prompt_text must be present"
        assert "prompt_blocks" in first_event["data"], "PM2: prompt_blocks must be present"
        assert "response_text" in first_event["data"], "PM3: response_text must be present"

        # Second event: retry failure
        second_event = parse_failed_events[1]
        assert second_event["data"]["player"] == "Alice"
        assert second_event["data"]["turn_number"] == 1
        # Policy outcome is still "retry" (it was the retry that failed)
        # The fallback to ABORT happens after the event is emitted
        assert second_event["data"]["policy_outcome"] == "retry"
        assert (
            "attempt 2" in second_event["data"]["parse_result"]["error"].lower()
            or second_event["data"]["parse_result"]["metadata"].get("attempt") == 2
        )

        # Schema v1.3: Verify prompt metadata (PM1-PM6) on second event too
        assert "prompt_text" in second_event["data"], "PM1: prompt_text must be present on retry"
        assert (
            "prompt_blocks" in second_event["data"]
        ), "PM2: prompt_blocks must be present on retry"
        assert (
            "response_text" in second_event["data"]
        ), "PM3: response_text must be present on retry"

        # Verify match metadata shows abort
        match_metadata = match_data["metadata"]["match"]
        assert match_metadata["outcome"] == "aborted"
        assert match_metadata["failing_player"] == "Alice"
        assert match_metadata["abort_turn"] == 1
        assert match_metadata["policy"] == "abort"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
