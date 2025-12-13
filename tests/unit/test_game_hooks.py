from __future__ import annotations

import json

from agentdeck import AgentDeck
from agentdeck.core.base.game import GameStatus
from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.players.mock import MockPlayer


class BaseHookGame(TurnBasedGame):
    @property
    def instructions(self) -> str:
        return "Test hook game."

    @property
    def allowed_actions(self) -> list[str]:
        return ["END"]

    @property
    def default_handshake_template(self) -> str:
        return "Respond with OK to start."

    def setup(self, players: list[str], seed: int) -> dict:
        return {
            "players": players,
            "winner": None,
            "ended": False,
            "handshakes": {},
            "conclusion": None,
        }

    def get_view(self, game_state: dict, player: str) -> dict:
        return {
            "player": player,
            "ended": game_state["ended"],
        }

    def update(self, game_state: dict, player: str, action, *, rng) -> dict:
        if action.action == "END":
            game_state["ended"] = True
            game_state["winner"] = player
        return game_state

    def status(self, game_state: dict) -> GameStatus:
        return GameStatus(is_over=game_state["ended"], winner=game_state["winner"])


class HandshakeHookGame(BaseHookGame):
    def on_handshake_complete(self, game_state: dict, player: str, handshake_result) -> dict:
        game_state["handshakes"][player] = handshake_result.metadata
        return game_state


class ForfeitHookGame(BaseHookGame):
    def on_match_forfeited(self, game_state: dict, player_name: str, error, policy) -> dict:
        game_state["resolution_status"] = "invalid_response"
        game_state["failed_player"] = player_name
        return game_state


class ConclusionGame(BaseHookGame):
    def requires_conclusion(self, game_state: dict) -> str | None:
        return game_state["winner"]

    def get_conclusion_prompt(self, player: str, game_state: dict) -> str:
        return "Respond with JSON: {\"summary\": \"...\"}"

    def parse_conclusion(self, player: str, response: str | None) -> dict:
        return {} if not response else json.loads(response)

    def on_conclusion_received(self, game_state: dict, player: str, conclusion: dict) -> dict:
        game_state["conclusion"] = conclusion
        return game_state


class ConclusionPlayer(MockPlayer):
    def __init__(self, name: str, *, conclusion_response: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self._conclusion_response = conclusion_response

    def conclude(self, result, *, match_context):
        return self._conclusion_response


def test_on_handshake_complete_updates_state():
    deck = AgentDeck(game=HandshakeHookGame())
    results = deck.play(
        players=[MockPlayer("Alice", actions=["END"]), MockPlayer("Bob", actions=["END"])],
        matches=1,
    )

    final_state = results[0].final_state
    assert "Alice" in final_state["handshakes"]
    assert final_state["handshakes"]["Alice"]["allowed_actions"] == ["END"]


def test_on_match_forfeited_enriches_final_state():
    deck = AgentDeck(game=ForfeitHookGame())
    # First player will fail parsing because "BAD" is not an allowed action
    results = deck.play(
        players=[MockPlayer("Alice", actions=["BAD"]), MockPlayer("Bob", actions=["END"])],
        matches=1,
    )

    final_state = results[0].final_state
    assert final_state.get("resolution_status") == "invalid_response"
    assert final_state.get("failed_player") == "Alice"
    assert results[0].winner == "Bob"


def test_conclusion_phase_persists_conclusion():
    deck = AgentDeck(game=ConclusionGame())
    results = deck.play(
        players=[
            ConclusionPlayer("Alice", actions=["END"], conclusion_response='{"summary": "done"}'),
            ConclusionPlayer("Bob", actions=["END"], conclusion_response='{"summary": "skip"}'),
        ],
        matches=1,
    )

    final_state = results[0].final_state
    assert final_state.get("conclusion") == {"summary": "done"}
