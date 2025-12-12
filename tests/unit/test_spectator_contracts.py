"""
Test suite for spectator contracts (StatsTracker, TokenUsageTracker, ProgressDisplay).

Tests verify SPEC-SPECTATOR v1.0.0 invariants:
- HC1-HC4: Duck-typed handlers, read-only, quick completion
- SS1-SS4: State management and reset behavior
- EI1-EI3: Error isolation, no execution mutations
"""

from unittest.mock import MagicMock, Mock

from agentdeck.core.types import (
    ActionResult,
    Event,
    MatchResult,
)
from agentdeck.spectators.stats import StatsTracker
from agentdeck.spectators.token_usage import TokenUsageTracker


def make_event(event_type: str, data: dict) -> Event:
    """Helper to create Event with required context."""
    return Event(
        type=event_type, data=data, context={"session_id": "test-session", "match_id": "test-match"}
    )


def make_match_result(winner=None, final_state=None) -> MatchResult:
    """Helper to create MatchResult with required fields."""
    return MatchResult(
        winner=winner, final_state=final_state or {}, events=[], seed=42, metadata={"turns": 5}
    )


class TestStatsTracker:
    """Tests for StatsTracker spectator."""

    def test_init_default_state(self):
        """StatsTracker initializes with empty state."""
        tracker = StatsTracker()

        assert tracker.total_matches == 0
        assert tracker.draws == 0
        assert len(tracker.wins) == 0
        assert len(tracker.losses) == 0
        assert len(tracker.match_durations) == 0

    def test_init_with_dialogue_tracking(self):
        """StatsTracker can be configured to track dialogue."""
        tracker = StatsTracker(track_dialogue=True)
        assert tracker.track_dialogue is True
        assert tracker.dialogue_log == []

    def test_reset_clears_all_state(self):
        """reset() clears all accumulated statistics."""
        tracker = StatsTracker()

        # Add some state
        tracker.total_matches = 5
        tracker.wins["Alice"] = 3
        tracker.losses["Bob"] = 2
        tracker.draws = 1
        tracker.match_durations.append(10.0)

        # Reset
        tracker.reset()

        # Verify cleared
        assert tracker.total_matches == 0
        assert tracker.draws == 0
        assert len(tracker.wins) == 0
        assert len(tracker.losses) == 0
        assert len(tracker.match_durations) == 0

    def test_on_match_start_records_players(self):
        """on_match_start() records player names and start time."""
        tracker = StatsTracker()

        player1 = Mock()
        player1.name = "Alice"
        player2 = Mock()
        player2.name = "Bob"

        tracker.on_match_start(game=Mock(), players=[player1, player2], match_id="test-123")

        assert tracker.current_players == ["Alice", "Bob"]
        assert tracker.current_match_start is not None

    def test_on_gameplay_tracks_action_result(self):
        """on_gameplay() tracks actions from ActionResult."""
        tracker = StatsTracker()

        action = ActionResult(action="ATTACK", reasoning="Test")
        event = make_event("gameplay", {"player": "Alice", "action": action})

        tracker.on_gameplay(event)

        assert tracker.total_turns["Alice"] == 1
        actions_dict = tracker.actions.as_dict()
        assert "Alice" in actions_dict
        assert actions_dict["Alice"]["ATTACK"] == 1

    def test_on_gameplay_handles_string_action(self):
        """on_gameplay() handles string actions (legacy format)."""
        tracker = StatsTracker()

        event = make_event("gameplay", {"player": "Bob", "action": "DEFEND"})

        tracker.on_gameplay(event)

        assert tracker.total_turns["Bob"] == 1

    def test_on_gameplay_ignores_missing_player(self):
        """on_gameplay() ignores events without player."""
        tracker = StatsTracker()

        event = make_event("gameplay", {"action": "ATTACK"})  # No player

        tracker.on_gameplay(event)

        assert len(tracker.total_turns) == 0

    def test_on_match_end_tracks_winner(self):
        """on_match_end() tracks wins and losses correctly."""
        tracker = StatsTracker()
        tracker.current_players = ["Alice", "Bob"]
        tracker.current_match_start = 0  # Set start time

        result = make_match_result(winner="Alice", final_state={"health": {"Alice": 50, "Bob": 0}})

        tracker.on_match_end(result)

        assert tracker.total_matches == 1
        assert tracker.wins["Alice"] == 1
        assert tracker.losses["Bob"] == 1
        assert tracker.draws == 0

    def test_on_match_end_tracks_draw(self):
        """on_match_end() tracks draws when no winner."""
        tracker = StatsTracker()
        tracker.current_players = ["Alice", "Bob"]
        tracker.current_match_start = 0

        result = make_match_result(winner=None, final_state={})

        tracker.on_match_end(result)

        assert tracker.total_matches == 1
        assert tracker.draws == 1
        assert tracker.wins["Alice"] == 0
        assert tracker.wins["Bob"] == 0

    def test_get_win_rate_calculation(self):
        """get_win_rate() calculates correctly."""
        tracker = StatsTracker()
        tracker.wins["Alice"] = 7
        tracker.losses["Alice"] = 3

        rate = tracker.get_win_rate("Alice")

        assert rate == 0.7

    def test_get_win_rate_zero_games(self):
        """get_win_rate() returns 0.0 for unknown player."""
        tracker = StatsTracker()

        rate = tracker.get_win_rate("Unknown")

        assert rate == 0.0

    def test_get_stats_comprehensive(self):
        """get_stats() returns comprehensive statistics."""
        tracker = StatsTracker()
        tracker.total_matches = 10
        tracker.draws = 2
        tracker.wins["Alice"] = 5
        tracker.losses["Alice"] = 3
        tracker.total_turns["Alice"] = 25
        tracker.match_durations = [1.0, 2.0, 3.0]

        stats = tracker.get_stats()

        assert stats["total_matches"] == 10
        assert stats["draws"] == 2
        assert "Alice" in stats["players"]
        assert stats["players"]["Alice"]["wins"] == 5
        assert stats["players"]["Alice"]["losses"] == 3
        assert stats["players"]["Alice"]["win_rate"] == 0.625
        assert "avg_match_duration" in stats

    def test_summaries_returns_get_stats(self):
        """summaries() returns same data as get_stats()."""
        tracker = StatsTracker()
        tracker.total_matches = 5

        assert tracker.summaries() == tracker.get_stats()

    def test_on_dialogue_turn_when_disabled(self):
        """on_dialogue_turn() does nothing when tracking disabled."""
        tracker = StatsTracker(track_dialogue=False)

        tracker.on_dialogue_turn(player="Alice", prompt="Test prompt", response="Test response")

        assert len(tracker.dialogue_log) == 0

    def test_on_dialogue_turn_when_enabled(self):
        """on_dialogue_turn() logs dialogue when enabled."""
        tracker = StatsTracker(track_dialogue=True)

        tracker.on_dialogue_turn(
            player="Alice",
            prompt="Test prompt",
            response="Test response",
            metadata={"model": "gpt-4"},
        )

        assert len(tracker.dialogue_log) == 1
        assert tracker.dialogue_log[0]["player"] == "Alice"
        assert tracker.dialogue_log[0]["prompt"] == "Test prompt"

    def test_print_summary_with_logger(self):
        """print_summary() uses logger when available."""
        logger = MagicMock()
        tracker = StatsTracker(logger=logger)
        tracker.total_matches = 1
        tracker.wins["Alice"] = 1
        tracker.total_turns["Alice"] = 5

        tracker.print_summary(use_logger=True)

        assert logger.info.called

    def test_log_summary_uses_logger(self):
        """log_summary() is alias for print_summary with logger."""
        logger = MagicMock()
        tracker = StatsTracker(logger=logger)
        tracker.total_matches = 1

        tracker.log_summary()

        assert logger.info.called


class TestTokenUsageTracker:
    """Tests for TokenUsageTracker spectator."""

    def test_init_default_state(self):
        """TokenUsageTracker initializes with zero counters."""
        tracker = TokenUsageTracker()

        assert tracker.total_tokens == 0
        assert tracker.total_cost == 0.0
        assert tracker.total_calls == 0
        assert len(tracker.player_tokens) == 0

    def test_on_batch_start_resets_state(self):
        """on_batch_start() resets all counters (SS3)."""
        tracker = TokenUsageTracker()

        # Add some state
        tracker.total_tokens = 1000
        tracker.total_cost = 0.01
        tracker.total_calls = 5
        tracker.player_tokens["Alice"]["total_tokens"] = 500

        # Reset via batch start
        tracker.on_batch_start(batch_id="test-batch", game=Mock(), players=[], matches=10)

        # Verify reset
        assert tracker.total_tokens == 0
        assert tracker.total_cost == 0.0
        assert tracker.total_calls == 0
        assert len(tracker.player_tokens) == 0

    def test_on_gameplay_extracts_usage_info(self):
        """on_gameplay() extracts tokens from usage_info format."""
        tracker = TokenUsageTracker()

        action = ActionResult(
            action="ATTACK",
            metadata={
                "usage_info": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "tokens": 150,
                    "cost": 0.001,
                    "model": "gpt-4o-mini",
                }
            },
        )
        event = make_event("gameplay", {"player": "Alice", "action": action})

        tracker.on_gameplay(event)

        assert tracker.total_tokens == 150
        assert tracker.total_prompt_tokens == 100
        assert tracker.total_completion_tokens == 50
        assert tracker.total_cost == 0.001
        assert tracker.total_calls == 1
        assert tracker.player_tokens["Alice"]["total_tokens"] == 150
        assert "gpt-4o-mini" in tracker.model_usage

    def test_on_gameplay_extracts_legacy_format(self):
        """on_gameplay() handles legacy direct metadata format."""
        tracker = TokenUsageTracker()

        action = ActionResult(
            action="ATTACK",
            metadata={
                "prompt_tokens": 80,
                "completion_tokens": 40,
                "total_tokens": 120,
                "cost": 0.0005,
                "model": "gpt-3.5-turbo",
            },
        )
        event = make_event("gameplay", {"player": "Bob", "action": action})

        tracker.on_gameplay(event)

        assert tracker.total_tokens == 120
        assert tracker.player_tokens["Bob"]["total_tokens"] == 120

    def test_on_gameplay_handles_dict_action(self):
        """on_gameplay() handles dict action format."""
        tracker = TokenUsageTracker()

        event = make_event(
            "gameplay",
            {
                "player": "Alice",
                "action": {
                    "action": "ATTACK",
                    "metadata": {"usage_info": {"tokens": 100, "cost": 0.001, "model": "test"}},
                },
            },
        )

        tracker.on_gameplay(event)

        assert tracker.total_tokens == 100

    def test_on_gameplay_ignores_zero_tokens(self):
        """on_gameplay() ignores events with no tokens."""
        tracker = TokenUsageTracker()

        action = ActionResult(action="ATTACK", metadata={})
        event = make_event("gameplay", {"player": "Alice", "action": action})

        tracker.on_gameplay(event)

        assert tracker.total_calls == 0

    def test_on_gameplay_ignores_missing_player(self):
        """on_gameplay() ignores events without player."""
        tracker = TokenUsageTracker()

        event = make_event("gameplay", {"action": ActionResult(action="ATTACK")})

        tracker.on_gameplay(event)

        assert tracker.total_calls == 0

    def test_on_gameplay_handles_errors_silently(self):
        """on_gameplay() handles errors without raising (EI1)."""
        tracker = TokenUsageTracker()

        # Malformed event - data is None which will cause error
        event = Event(type="gameplay", data=None, context={"session_id": "test"})

        # Should not raise
        tracker.on_gameplay(event)

        assert tracker.total_calls == 0

    def test_on_batch_end_logs_summary(self):
        """on_batch_end() logs summary when calls exist."""
        logger = MagicMock()
        tracker = TokenUsageTracker(logger=logger)
        tracker.total_calls = 5
        tracker.total_tokens = 1000
        tracker.total_cost = 0.01

        tracker.on_batch_end(batch_id="test-batch-123", results=[])

        assert logger.info.called

    def test_on_batch_end_skips_when_no_calls(self):
        """on_batch_end() skips logging when no calls tracked."""
        logger = MagicMock()
        tracker = TokenUsageTracker(logger=logger)

        tracker.on_batch_end(batch_id="test-batch", results=[])

        assert not logger.info.called

    def test_get_summary_structure(self):
        """get_summary() returns properly structured data."""
        tracker = TokenUsageTracker()
        tracker.total_calls = 10
        tracker.total_prompt_tokens = 800
        tracker.total_completion_tokens = 200
        tracker.total_tokens = 1000
        tracker.total_cost = 0.01

        tracker.player_tokens["Alice"]["calls"] = 5
        tracker.player_tokens["Alice"]["total_tokens"] = 500
        tracker.player_costs["Alice"] = 0.005

        tracker.model_usage["gpt-4"]["calls"] = 10
        tracker.model_usage["gpt-4"]["tokens"] = 1000
        tracker.model_usage["gpt-4"]["cost"] = 0.01

        summary = tracker.get_summary()

        assert summary["total"]["calls"] == 10
        assert summary["total"]["total_tokens"] == 1000
        assert summary["total"]["cost"] == 0.01
        assert "Alice" in summary["per_player"]
        assert "gpt-4" in summary["per_model"]

    def test_get_average_cost_per_match(self):
        """get_average_cost_per_match() calculates correctly."""
        tracker = TokenUsageTracker()
        tracker.total_cost = 0.10

        avg = tracker.get_average_cost_per_match(10)

        assert avg == 0.01

    def test_get_average_cost_per_match_zero_matches(self):
        """get_average_cost_per_match() handles zero matches."""
        tracker = TokenUsageTracker()
        tracker.total_cost = 0.10

        avg = tracker.get_average_cost_per_match(0)

        assert avg == 0.0

    def test_multiple_gameplay_events_accumulate(self):
        """Multiple gameplay events accumulate correctly."""
        tracker = TokenUsageTracker()

        for i in range(3):
            action = ActionResult(
                action="ATTACK",
                metadata={"usage_info": {"tokens": 100, "cost": 0.001, "model": "gpt-4o-mini"}},
            )
            event = make_event("gameplay", {"player": "Alice", "action": action})
            tracker.on_gameplay(event)

        assert tracker.total_calls == 3
        assert tracker.total_tokens == 300
        assert tracker.total_cost == 0.003


class TestSpectatorUtils:
    """Tests for spectator utility classes."""

    def test_counter_map_operations(self):
        """CounterMap increments and retrieves correctly."""
        from agentdeck.spectators.utils import CounterMap

        counter = CounterMap()
        counter.increment("Alice", "ATTACK")
        counter.increment("Alice", "ATTACK")
        counter.increment("Alice", "DEFEND")

        data = counter.as_dict()
        assert data["Alice"]["ATTACK"] == 2
        assert data["Alice"]["DEFEND"] == 1

    def test_duration_tracker_operations(self):
        """DurationTracker records and averages correctly."""
        from agentdeck.spectators.utils import DurationTracker

        tracker = DurationTracker()
        tracker.record("Alice", 1.0)
        tracker.record("Alice", 2.0)
        tracker.record("Alice", 3.0)

        assert tracker.average("Alice") == 2.0
        assert tracker.values("Alice") == [1.0, 2.0, 3.0]

    def test_duration_tracker_unknown_player(self):
        """DurationTracker handles unknown player gracefully."""
        from agentdeck.spectators.utils import DurationTracker

        tracker = DurationTracker()

        assert tracker.average("Unknown") == 0.0
        assert tracker.values("Unknown") == []
