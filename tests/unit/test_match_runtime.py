"""
Unit tests for MatchRuntime per SPEC-MATCH-RUNTIME v1.0.0.

These tests focus on the runtime-specific invariants and API surface:
- MR1: runtime instances remain isolated per match
- MR2: record_turn emits canonical gameplay events in order
- MR3: handle_parse_failure delegates through the shared policy pipeline
- MR4: RNG forks are deterministic and traceable in logs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from agentdeck.core.event_bus import EventBus
from agentdeck.core.match_runtime import MatchRuntime
from agentdeck.core.types import (
    ActionParseError,
    ActionResult,
    EventType,
    LogLevel,
    ParseFailurePolicy,
    ParseResult,
    RandomGenerator,
    TurnContext,
)


class DummyLogger:
    def __init__(self) -> None:
        self.debug_calls: List[str] = []
        self.info_calls: List[str] = []
        self.warning_calls: List[str] = []
        self.error_calls: List[tuple[str, Exception]] = []

    def debug(self, message: str) -> None:
        self.debug_calls.append(message)

    def info(self, message: str) -> None:
        self.info_calls.append(message)

    def warning(self, message: str) -> None:
        self.warning_calls.append(message)

    def error(self, message: str, *, error: Exception) -> None:
        self.error_calls.append((message, error))


class DummyGame:
    def __init__(self, *, validation_error: Optional[Exception] = None) -> None:
        self.validation_error = validation_error

    def validate_state(self, state: Dict[str, Any]) -> None:
        if self.validation_error:
            raise self.validation_error


@dataclass
class DummyPlayer:
    name: str


class DummyConsole:
    def __init__(self, *, session_id: str, batch_id: str, match_id: str) -> None:
        self.event_bus = EventBus(session_id=session_id)
        self.event_bus.update_context(batch_id=batch_id, match_id=match_id)
        self._current_phase_index: Optional[int] = None
        self.dispatched_events = []
        self.parse_failure_calls = []
        self.parse_failure_events = []

    def _dispatch_event(self, event_type: str, events=None, **data: Any) -> None:
        event = self.event_bus.emit(event_type, **data)
        self.dispatched_events.append(event)
        if events is not None:
            events.append(event)

    def _handle_parse_failure(
        self,
        *,
        player: DummyPlayer,
        error: ActionParseError,
        turn_context: TurnContext,
        game: DummyGame,
    ) -> ParseFailurePolicy:
        self.parse_failure_calls.append(
            {
                "player": player,
                "error": error,
                "turn_context": turn_context,
                "game": game,
            }
        )
        event = self.event_bus.emit(
            EventType.PLAYER_ACTION_PARSE_FAILED,
            player=player.name,
            match_id=turn_context.match_id,
            turn_number=turn_context.turn_number,
            parse_result={"error": error.parse_result.error},
            policy_outcome=ParseFailurePolicy.SKIP_TURN.value,
        )
        self.parse_failure_events.append(event)
        return ParseFailurePolicy.SKIP_TURN


def _make_runtime(
    *,
    match_id: str = "match-1",
    seed: int = 42,
    events_list: Optional[List] = None,
    initial_state: Optional[Dict[str, Any]] = None,
    game: Optional[DummyGame] = None,
    logger: Optional[DummyLogger] = None,
) -> tuple[MatchRuntime, DummyConsole, DummyLogger, DummyGame]:
    console = DummyConsole(session_id="session-1", batch_id="batch-1", match_id=match_id)
    game = game or DummyGame()
    logger = logger or DummyLogger()
    runtime = MatchRuntime(
        console=console,
        game=game,
        match_id=match_id,
        session_id="session-1",
        batch_id="batch-1",
        seed=seed,
        max_turns=50,
        recorder=None,
        logger=logger,
        rng=RandomGenerator(seed),
        previous_match_result=None,
        events_list=events_list,
        initial_state=initial_state,
    )
    return runtime, console, logger, game


def _turn_context(
    match_id: str = "match-1", player: str = "Alice", turn_number: int = 1
) -> TurnContext:
    return TurnContext(
        match_id=match_id,
        turn_number=turn_number,
        turn_index=turn_number - 1,
        player=player,
        started_at=100.0,
        duration=0.25,
        rng_seed=777,
        rng_label=f"turn_{turn_number}",
    )


def test_mr1_match_runtime_instances_are_isolated():
    """SPEC-MATCH-RUNTIME MR1: one runtime per match with isolated mutable state."""
    events_a: List[Any] = []
    events_b: List[Any] = []
    runtime_a, console_a, _, _ = _make_runtime(
        match_id="match-a",
        seed=101,
        events_list=events_a,
        initial_state={"hp": {"Alice": 100, "Bob": 100}},
    )
    runtime_b, console_b, _, _ = _make_runtime(
        match_id="match-b",
        seed=202,
        events_list=events_b,
        initial_state={"hp": {"Alice": 80, "Bob": 90}},
    )

    runtime_a.initial_state = {"hp": {"Alice": 50, "Bob": 75}}
    runtime_a.log("runtime-a-only", level=LogLevel.INFO)

    assert runtime_a.match_id == "match-a"
    assert runtime_b.match_id == "match-b"
    assert runtime_a.seed == 101
    assert runtime_b.seed == 202
    assert runtime_a.initial_state == {"hp": {"Alice": 50, "Bob": 75}}
    assert runtime_b.initial_state == {"hp": {"Alice": 80, "Bob": 90}}
    assert len(console_a.dispatched_events) == 1
    assert console_b.dispatched_events == []
    assert events_a == []
    assert events_b == []


def test_mr2_record_turn_emits_gameplay_and_preserves_snapshots():
    """SPEC-MATCH-RUNTIME MR2: record_turn emits ordered GAMEPLAY events and snapshots."""
    events: List[Any] = []
    runtime, console, _, _ = _make_runtime(events_list=events)
    state_before = {"hp": {"Alice": 55, "Bob": 25}}
    state_after = {"hp": {"Alice": 55, "Bob": 5}}
    action = ActionResult(
        action="ATTACK",
        reasoning="Finish the opponent.",
        raw_response="REASONING: Finish the opponent\nACTION: ATTACK",
        metadata={
            "raw_prompt": "Take your turn.",
            "usage_info": {"input_tokens": 10, "output_tokens": 5},
            "controller_metadata": {"parser": "action_only"},
            "renderer_output": {"template_id": "default"},
        },
    )

    runtime.record_turn(
        player="Alice",
        state_before=state_before,
        state_after=state_after,
        action=action,
        turn_context=_turn_context(),
        prompt_blocks=[{"role": "system", "content": "Take your turn."}],
    )

    state_before["hp"]["Bob"] = 999
    state_after["hp"]["Bob"] = 999
    action.metadata["usage_info"]["input_tokens"] = 999

    assert len(console.dispatched_events) == 1
    emitted = console.dispatched_events[0]
    assert emitted.type == EventType.GAMEPLAY.value
    assert emitted.data["player"] == "Alice"
    assert emitted.data["phase_index"] == 0
    assert emitted.data["turn_index"] == 0
    assert emitted.data["state_before"]["hp"]["Bob"] == 25
    assert emitted.data["state_after"]["hp"]["Bob"] == 5
    assert emitted.data["usage_info"]["input_tokens"] == 10
    assert emitted.data["prompt_blocks"] == [{"role": "system", "content": "Take your turn."}]
    assert console._current_phase_index == 0
    assert "phase_index" not in console.event_bus._base_context
    assert "turn_index" not in console.event_bus._base_context

    assert len(events) == 1
    snapshot = events[0]
    assert snapshot.type == EventType.GAMEPLAY.value
    assert snapshot.data["state_before"]["hp"]["Bob"] == 25
    assert snapshot.data["usage_info"]["input_tokens"] == 10


def test_mr3_handle_parse_failure_delegates_shared_pipeline_and_returns_policy():
    """
    SPEC-MATCH-RUNTIME MR3: runtime routes parse failures through the shared policy helper.

    Side effects of the shared helper are exercised in parse-failure integration tests;
    this unit test verifies MatchRuntime delegates the correct objects and returns policy.
    """
    runtime, console, _, game = _make_runtime()
    player = DummyPlayer("Alice")
    parse_error = ActionParseError(
        ParseResult(
            success=False,
            action=None,
            raw_response="???",
            error="Could not parse action",
            metadata={"candidates": []},
        )
    )
    turn_context = _turn_context()

    policy = runtime.handle_parse_failure(player, parse_error, turn_context=turn_context)

    assert policy == ParseFailurePolicy.SKIP_TURN
    assert len(console.parse_failure_calls) == 1
    call = console.parse_failure_calls[0]
    assert call["player"] is player
    assert call["error"] is parse_error
    assert call["turn_context"] is turn_context
    assert call["game"] is game
    assert console.dispatched_events == []
    assert len(console.parse_failure_events) == 1
    assert console.parse_failure_events[0].type == EventType.PLAYER_ACTION_PARSE_FAILED.value
    assert (
        console.parse_failure_events[0].data["policy_outcome"] == ParseFailurePolicy.SKIP_TURN.value
    )


def test_mr4_fork_rng_logs_label_and_is_deterministic():
    """SPEC-MATCH-RUNTIME MR4: fork_rng records labels and preserves deterministic seeds."""
    runtime_a, _, logger_a, _ = _make_runtime(seed=12345, match_id="match-rng")
    runtime_b, _, logger_b, _ = _make_runtime(seed=12345, match_id="match-rng")

    fork_a = runtime_a.fork_rng("turn_7")
    fork_b = runtime_b.fork_rng("turn_7")
    other_fork = runtime_a.fork_rng("setup")

    assert fork_a.seed == fork_b.seed
    assert fork_a.seed != other_fork.seed
    assert fork_a.randint(1, 1000) == fork_b.randint(1, 1000)
    assert logger_a.debug_calls == [
        "RNG fork: turn_7 (match_id=match-rng, base_seed=12345)",
        "RNG fork: setup (match_id=match-rng, base_seed=12345)",
    ]
    assert logger_b.debug_calls == ["RNG fork: turn_7 (match_id=match-rng, base_seed=12345)"]


def test_validate_state_logs_and_reraises_failures():
    """SPEC-MATCH-RUNTIME §4.6: validate_state logs context and re-raises validation failures."""
    validation_error = ValueError("state invalid")
    logger = DummyLogger()
    runtime, _, _, _ = _make_runtime(
        game=DummyGame(validation_error=validation_error), logger=logger
    )

    with pytest.raises(ValueError, match="state invalid"):
        runtime.validate_state({"hp": {"Alice": -1}})

    assert len(logger.error_calls) == 1
    message, error = logger.error_calls[0]
    assert "State validation failed" in message
    assert "match_id=match-1" in message
    assert error is validation_error


def test_log_writes_logger_and_emits_log_event():
    """SPEC-MATCH-RUNTIME §4.7: runtime.log writes via logger and emits LOG events."""
    runtime, console, logger, _ = _make_runtime()

    runtime.log("Turn started", level=LogLevel.DEBUG, player="Alice", turn_number=3)
    runtime.log("Match continuing", level=LogLevel.INFO, reason="midgame")

    assert logger.debug_calls == ["Turn started (player=Alice, turn_number=3)"]
    assert logger.info_calls == ["Match continuing (reason=midgame)"]
    assert [event.type for event in console.dispatched_events] == [
        EventType.LOG.value,
        EventType.LOG.value,
    ]
    assert console.dispatched_events[0].data == {
        "message": "Turn started",
        "level": "debug",
        "log_context": {"player": "Alice", "turn_number": 3},
    }
    assert console.dispatched_events[1].data == {
        "message": "Match continuing",
        "level": "info",
        "log_context": {"reason": "midgame"},
    }
