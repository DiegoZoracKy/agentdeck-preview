"""
Unit tests for TurnBasedGame mechanic per SPEC-GAME-MECHANIC-TURN-BASED v2.0.0.

These tests verify:
- TL6: JSON-serializability validation for custom events from get_events()
"""

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

    def update(
        self, game_state: Dict[str, Any], player: str, action, *, rng
    ) -> Dict[str, Any]:
        game_state["turn"] += 1
        if action.action == "END":
            game_state["ended"] = True
        return game_state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        return GameStatus(is_over=game_state["ended"], winner=game_state["players"][0])

    def get_events(
        self, game_state: Dict[str, Any], player: str, action
    ) -> List[Event]:
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

    def update(
        self, game_state: Dict[str, Any], player: str, action, *, rng
    ) -> Dict[str, Any]:
        game_state["turn"] += 1
        if action.action == "END":
            game_state["ended"] = True
        return game_state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        return GameStatus(is_over=game_state["ended"], winner=game_state["players"][0])

    def get_events(
        self, game_state: Dict[str, Any], player: str, action
    ) -> List[Event]:
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

        def get_events(
            self, game_state: Dict[str, Any], player: str, action
        ) -> List[Event]:
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

        def get_events(
            self, game_state: Dict[str, Any], player: str, action
        ) -> List[Event]:
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
