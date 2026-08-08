"""
Unit tests for TurnBasedGame mechanic per SPEC-GAME-MECHANIC-TURN-BASED v2.0.0.

These tests verify:
- TL6: JSON-serializability validation for custom events from get_events()
"""

import logging
from typing import Any, Dict, List

import pytest

from agentdeck import AgentDeck
from agentdeck.core.base.game import GameStatus
from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.core.session import AgentDeckConfig
from agentdeck.core.types import Event
from agentdeck.players.mock import MockPlayer


class GameWithJSONSerializableEvents(TurnBasedGame):
    """Game that emits JSON-serializable custom events."""

    @property
    def instructions(self) -> str:
        return "Game with valid custom events."

    @property
    def allowed_actions(self) -> List[str]:
        return ["MOVE", "END"]

    @property
    def default_handshake_template(self) -> str:
        return "Respond with OK."

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        return {
            "players": players,
            "turn": 0,
            "ended": False,
        }

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        return {
            "player": player,
            "turn": game_state["turn"],
        }

    def update(self, game_state: Dict[str, Any], player: str, action, *, rng) -> Dict[str, Any]:
        game_state["turn"] += 1
        if action.action == "END":
            game_state["ended"] = True
        return game_state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        return GameStatus(is_over=game_state["ended"], winner=game_state["players"][0])

    def get_events(self, game_state: Dict[str, Any], player: str, action) -> List[Event]:
        """Return custom events with JSON-serializable data."""
        # TL6: This should work - all data is JSON-serializable
        return [
            Event(
                type="CUSTOM_ACTION",
                data={
                    "player": player,
                    "action": action.action,
                    "turn": game_state["turn"],
                    "metadata": {"score": 100, "items": ["sword", "shield"]},
                },
                context={},
            )
        ]


class GameWithNonJSONSerializableEvents(TurnBasedGame):
    """Game that emits non-JSON-serializable custom events (should fail)."""

    @property
    def instructions(self) -> str:
        return "Game with invalid custom events."

    @property
    def allowed_actions(self) -> List[str]:
        return ["MOVE", "END"]

    @property
    def default_handshake_template(self) -> str:
        return "Respond with OK."

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        return {
            "players": players,
            "turn": 0,
            "ended": False,
        }

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        return {
            "player": player,
            "turn": game_state["turn"],
        }

    def update(self, game_state: Dict[str, Any], player: str, action, *, rng) -> Dict[str, Any]:
        game_state["turn"] += 1
        if action.action == "END":
            game_state["ended"] = True
        return game_state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        return GameStatus(is_over=game_state["ended"], winner=game_state["players"][0])

    def get_events(self, game_state: Dict[str, Any], player: str, action) -> List[Event]:
        """Return custom events with non-JSON-serializable data (lambda function)."""
        # TL6: This should FAIL - lambda is not JSON-serializable
        return [
            Event(
                type="INVALID_EVENT",
                data={
                    "player": player,
                    "callback": lambda x: x * 2,  # Not JSON-serializable!
                },
                context={},
            )
        ]


class GameWithNonJSONView(GameWithJSONSerializableEvents):
    """Game whose player-visible projection cannot round-trip through JSON."""

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        return {"player": player, "hidden_bug": {"not", "json"}}


# Test: TL6 - JSON-serializability validation


def test_tl6_json_serializable_events_accepted(tmp_path):
    """Test TL6: Custom events with JSON-serializable data are accepted."""
    # SPEC-GAME-MECHANIC-TURN-BASED TL6: JSON-serializable events should work
    config = AgentDeckConfig(seed=42, run_dir=tmp_path)
    with AgentDeck(game=GameWithJSONSerializableEvents(), session=config) as deck:
        players = [MockPlayer("Alice", actions=["MOVE", "END"]), MockPlayer("Bob")]

        # Should complete without errors
        results = deck.play(players=players, matches=1)
        assert results.single.winner == "Alice"


def test_mr6_stock_turn_loop_rejects_non_json_view(tmp_path):
    """MR6: TurnLoop validates the Game view before invoking a Player."""
    config = AgentDeckConfig(seed=42, run_dir=tmp_path)
    with AgentDeck(game=GameWithNonJSONView(), session=config) as deck:
        players = [MockPlayer("Alice", actions=["END"]), MockPlayer("Bob")]

        with pytest.raises(RuntimeError, match="get_view"):
            deck.play(players=players, matches=1)


def test_tl6_non_json_serializable_events_raise_typeerror(tmp_path):
    """Test TL6: Custom events with non-JSON-serializable data raise TypeError."""
    # SPEC-GAME-MECHANIC-TURN-BASED TL6: Non-JSON-serializable data must raise TypeError
    config = AgentDeckConfig(seed=42, run_dir=tmp_path)
    with AgentDeck(game=GameWithNonJSONSerializableEvents(), session=config) as deck:
        # Use valid actions so game actually runs and triggers get_events()
        players = [MockPlayer("Alice", actions=["MOVE"]), MockPlayer("Bob", actions=["MOVE"])]

        # Should raise TypeError when trying to validate the custom event
        with pytest.raises(TypeError) as exc_info:
            deck.play(players=players, matches=1)

        # TL6: Error message must include event type and match_id
        error_msg = str(exc_info.value)
        assert "INVALID_EVENT" in error_msg
        assert "non-JSON-serializable" in error_msg
        assert "match_id" in error_msg


def test_tl6_error_includes_turn_number(tmp_path):
    """Test TL6: TypeError for non-JSON-serializable events includes turn number."""
    # SPEC-GAME-MECHANIC-TURN-BASED TL6: Error must include turn number
    config = AgentDeckConfig(seed=99, run_dir=tmp_path)
    with AgentDeck(game=GameWithNonJSONSerializableEvents(), session=config) as deck:
        players = [MockPlayer("Alice", actions=["MOVE"]), MockPlayer("Bob", actions=["MOVE"])]

        with pytest.raises(TypeError) as exc_info:
            deck.play(players=players, matches=1)

        # Should mention turn number in error message
        error_msg = str(exc_info.value)
        assert "turn" in error_msg.lower()


def test_tl6_complex_json_serializable_data(tmp_path):
    """Test TL6: Complex but JSON-serializable structures work fine."""

    class ComplexEventGame(GameWithJSONSerializableEvents):
        """Game with complex but valid JSON data."""

        def get_events(self, game_state: Dict[str, Any], player: str, action) -> List[Event]:
            """Return event with complex JSON-serializable data."""
            return [
                Event(
                    type="COMPLEX_EVENT",
                    context={},
                    data={
                        "player": player,
                        "stats": {
                            "health": 100,
                            "mana": 50,
                            "inventory": ["sword", "shield", "potion"],
                        },
                        "history": [
                            {"turn": 1, "action": "MOVE", "damage": 0},
                            {"turn": 2, "action": "ATTACK", "damage": 10},
                        ],
                        "flags": {"is_alive": True, "has_treasure": False},
                    },
                )
            ]

    config = AgentDeckConfig(seed=77, run_dir=tmp_path)
    with AgentDeck(game=ComplexEventGame(), session=config) as deck:
        players = [MockPlayer("Alice", actions=["MOVE", "END"]), MockPlayer("Bob")]

        # Complex but JSON-serializable data should work
        results = deck.play(players=players, matches=1)
        assert results.single.winner == "Alice"


def test_tl6_multiple_events_one_invalid(tmp_path):
    """Test TL6: If one event in list is invalid, TypeError is raised."""

    class MixedEventsGame(GameWithJSONSerializableEvents):
        """Game that returns both valid and invalid events."""

        def get_events(self, game_state: Dict[str, Any], player: str, action) -> List[Event]:
            """Return mix of valid and invalid events."""
            return [
                Event(type="VALID_EVENT", data={"player": player, "score": 100}, context={}),
                Event(
                    type="INVALID_EVENT",
                    data={"player": player, "obj": object()},  # object() not serializable
                    context={},
                ),
            ]

    config = AgentDeckConfig(seed=55, run_dir=tmp_path)
    with AgentDeck(game=MixedEventsGame(), session=config) as deck:
        players = [MockPlayer("Alice", actions=["MOVE"]), MockPlayer("Bob", actions=["MOVE"])]

        # Should raise TypeError for the invalid event
        with pytest.raises(TypeError) as exc_info:
            deck.play(players=players, matches=1)

        # Error should mention the invalid event
        error_msg = str(exc_info.value)
        assert "INVALID_EVENT" in error_msg


# ---------------------------------------------------------------------------
# TL0 – Mechanic-owned state keys: fail-soft re-inject
#
# Regression for the trap surfaced repeatedly in agent-QA rounds 4/7/8/9,
# where an authored game's update() rebuilt state from scratch and dropped
# the mechanic-owned bookkeeping keys (_turn_count, _first_player_idx).
# Previously this produced a KeyError on the next turn. TurnLoop now
# re-injects the dropped keys from the pre-turn snapshot and emits a
# one-time per-match warning naming the responsible game class.
# ---------------------------------------------------------------------------


class GameDroppingMechanicKeys(TurnBasedGame):
    """
    Hostile game that rebuilds state from scratch on every update(),
    reproducing the Round 7/9 failure mode (dropped _turn_count /
    _first_player_idx).
    """

    MAX_TURNS = 6

    @property
    def instructions(self) -> str:
        return "Drop mechanic keys on every update."

    @property
    def allowed_actions(self) -> List[str]:
        return ["MOVE"]

    @property
    def default_handshake_template(self) -> str:
        return "Respond with OK."

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        return {"players": list(players), "moves": 0, "ended": False}

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        return {"player": player, "moves": game_state["moves"]}

    def update(
        self,
        game_state: Dict[str, Any],
        player: str,
        action,
        *,
        rng,
    ) -> Dict[str, Any]:
        # Deliberately rebuild state from scratch — drops _turn_count
        # and _first_player_idx. This is the Round 7/9 authoring trap.
        next_moves = game_state["moves"] + 1
        return {
            "players": list(game_state["players"]),
            "moves": next_moves,
            "ended": next_moves >= self.MAX_TURNS,
        }

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        winner = game_state["players"][0] if game_state["ended"] else None
        return GameStatus(is_over=game_state["ended"], winner=winner)


class _ListLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_tl0_update_dropping_mechanic_keys_is_fail_soft(tmp_path):
    """
    TL0 regression: update() returning a fresh dict without mechanic keys
    must not crash. TurnLoop re-injects _turn_count / _first_player_idx
    and the match completes normally.
    """
    config = AgentDeckConfig(seed=42, run_dir=tmp_path)
    handler = _ListLogHandler()

    with AgentDeck(game=GameDroppingMechanicKeys(), session=config) as deck:
        deck.console.logger.logger.addHandler(handler)
        try:
            players = [
                MockPlayer("Alice", actions=["MOVE"] * GameDroppingMechanicKeys.MAX_TURNS),
                MockPlayer("Bob", actions=["MOVE"] * GameDroppingMechanicKeys.MAX_TURNS),
            ]

            # Before the fix, the second turn raised KeyError inside
            # TurnBasedGame.get_current_player() (_first_player_idx missing).
            results = deck.play(players=players, matches=1)
        finally:
            deck.console.logger.logger.removeHandler(handler)

    # Match completed without KeyError.
    assert results.single is not None
    final_state = results.single.final_state
    assert "_turn_count" in final_state
    assert "_first_player_idx" in final_state

    # Exactly one warning per dropped key, naming the game class.
    warnings_for_keys = {"_turn_count": 0, "_first_player_idx": 0}
    for record in handler.records:
        if record.levelno != logging.WARNING:
            continue
        msg = record.getMessage()
        if "GameDroppingMechanicKeys" not in msg:
            continue
        if "dropped mechanic key" not in msg:
            continue
        for key in warnings_for_keys:
            if repr(key) in msg:
                warnings_for_keys[key] += 1

    assert (
        warnings_for_keys["_turn_count"] == 1
    ), f"expected 1 warning for _turn_count, got {warnings_for_keys['_turn_count']}"
    assert warnings_for_keys["_first_player_idx"] == 1, (
        f"expected 1 warning for _first_player_idx, got "
        f"{warnings_for_keys['_first_player_idx']}"
    )


def test_tl0_mechanic_key_warning_does_not_repeat_per_turn(tmp_path):
    """
    TL0: the fail-soft warning must fire once per key per match, not on
    every turn. A long match that drops keys on every turn should still
    produce exactly one warning per dropped key.
    """

    class LongMatchDropper(GameDroppingMechanicKeys):
        MAX_TURNS = 10  # longer match to prove warning doesn't repeat

    config = AgentDeckConfig(seed=7, run_dir=tmp_path)
    handler = _ListLogHandler()

    with AgentDeck(game=LongMatchDropper(), session=config) as deck:
        deck.console.logger.logger.addHandler(handler)
        try:
            players = [
                MockPlayer("Alice", actions=["MOVE"] * LongMatchDropper.MAX_TURNS),
                MockPlayer("Bob", actions=["MOVE"] * LongMatchDropper.MAX_TURNS),
            ]
            deck.play(players=players, matches=1)
        finally:
            deck.console.logger.logger.removeHandler(handler)

    total_warnings = sum(
        1
        for record in handler.records
        if record.levelno == logging.WARNING
        and "LongMatchDropper" in record.getMessage()
        and "dropped mechanic key" in record.getMessage()
    )
    # One warning per mechanic key (_turn_count, _first_player_idx).
    assert total_warnings == 2, f"expected exactly 2 warnings (one per key), got {total_warnings}"
