"""A tiny Game authored outside the AgentDeck source package."""

from __future__ import annotations

from typing import Any, Dict, List

from agentdeck import ActionResult, GameStatus, TurnBasedGame
from agentdeck.core.types import RandomGenerator


class NumberDuelGame(TurnBasedGame):
    """First player to reach the configured target wins."""

    def __init__(self, target: int = 3) -> None:
        super().__init__()
        if target < 1:
            raise ValueError("target must be positive")
        self.target = target

    @property
    def instructions(self) -> str:
        return f"Choose GAIN or HOLD. The first player to reach {self.target} points wins."

    @property
    def allowed_actions(self) -> List[str]:
        return ["GAIN", "HOLD"]

    @property
    def default_handshake_template(self) -> str:
        return "{game_instructions}\n{controller_format}\n{handshake_controller_format}"

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        if len(players) != 2:
            raise ValueError("NumberDuelGame requires two players")
        return {"scores": {player: 0 for player in players}, "turn": 1, "seed": seed}

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        if player not in game_state["scores"]:
            raise ValueError("unknown player")
        return {
            "scores": dict(game_state["scores"]),
            "turn": game_state["turn"],
            "target": self.target,
        }

    def update(
        self,
        game_state: Dict[str, Any],
        player: str,
        action: ActionResult,
        *,
        rng: RandomGenerator,
    ) -> Dict[str, Any]:
        del rng
        value = action.action.upper()
        if value not in self.allowed_actions:
            raise ValueError(f"unsupported action: {value}")
        state = {
            "scores": dict(game_state["scores"]),
            "turn": int(game_state["turn"]) + 1,
            "seed": game_state["seed"],
        }
        if value == "GAIN":
            state["scores"][player] += 1
        return state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        for player, score in game_state["scores"].items():
            if score >= self.target:
                return GameStatus(is_over=True, winner=player)
        return GameStatus(is_over=False, winner=None)

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "allowed_actions": self.allowed_actions,
            "config": {"target": self.target},
        }
