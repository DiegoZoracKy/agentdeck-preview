from __future__ import annotations

import json

from agentdeck import AgentDeck, FixedDamageGame
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
    def get_player_order(self, players, *, rng, match_context):
        # Ensure Alice (with BAD action) goes first to trigger forfeit
        return [p for p in players if p.name == "Alice"] + [p for p in players if p.name != "Alice"]

    def on_match_forfeited(self, game_state: dict, player_name: str, error, policy) -> dict:
        # Hook receives state, should mutate and return
        # Per spec: "Return: Updated JSON-serializable dict (canonical state for recording)"
        state = dict(game_state)  # Defensive copy
        state["resolution_status"] = "invalid_response"
        state["failed_player"] = player_name
        return state


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
    # Verify handshake hook was called and stored metadata
    assert "Alice" in final_state["handshakes"]
    assert "Bob" in final_state["handshakes"]
    # HandshakeResult.metadata is a dict (guaranteed by TC1)
    assert isinstance(final_state["handshakes"]["Alice"], dict)


def test_on_match_forfeited_enriches_final_state():
    deck = AgentDeck(game=ForfeitHookGame())
    # Alice has BAD action which will trigger forfeit, Bob has END
    results = deck.play(
        players=[MockPlayer("Alice", actions=["BAD"]), MockPlayer("Bob", actions=["END"])],
        matches=1,
        seed=100,  # Fixed seed to ensure Alice goes first
    )

    final_state = results[0].final_state
    # Verify forfeit hook was called and enriched state
    assert final_state.get("resolution_status") == "invalid_response"
    assert final_state.get("failed_player") == "Alice"  # Alice went first with BAD action
    # Bob should win since Alice forfeited
    assert results[0].winner == "Bob"


def test_conclusion_phase_persists_conclusion():
    deck = AgentDeck(game=ConclusionGame())
    results = deck.play(
        players=[
            ConclusionPlayer("Alice", actions=["END"], conclusion_response='{"summary": "Alice won"}'),
            ConclusionPlayer("Bob", actions=["END"], conclusion_response='{"summary": "Bob won"}'),
        ],
        matches=1,
        seed=42,  # Fixed seed for deterministic player order
    )

    final_state = results[0].final_state
    winner = results[0].winner
    # Verify conclusion was captured from the winner
    assert final_state.get("conclusion") is not None
    assert "summary" in final_state["conclusion"]
    # Conclusion should match the winner
    assert winner in final_state["conclusion"]["summary"]


def test_fixed_damage_game_behavior_stable_with_hook_defaults():
    players = [MockPlayer("A", actions=["ATTACK"]), MockPlayer("B", actions=["ATTACK"])]

    deck1 = AgentDeck(game=FixedDamageGame())
    result1 = deck1.play(players=players, matches=1, seed=123)[0]

    # Only canonical keys should be present (no hook-added keys)
    expected_keys = {"health", "potions", "last_action", "turn", "_turn_count", "_first_player_idx"}
    assert set(result1.final_state.keys()) == expected_keys
    assert result1.winner in {None, "A", "B"}

    # Deterministic repeat with the same seed yields identical outcome and state
    deck2 = AgentDeck(game=FixedDamageGame())
    result2 = deck2.play(
        players=[MockPlayer("A", actions=["ATTACK"]), MockPlayer("B", actions=["ATTACK"])],
        matches=1,
        seed=123,
    )[0]

    assert result1.winner == result2.winner
    assert result1.final_state == result2.final_state
