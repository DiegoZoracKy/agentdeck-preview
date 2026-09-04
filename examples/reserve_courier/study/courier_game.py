"""A complete, deterministic planning world; independent of Research and providers."""

from __future__ import annotations

import copy
import random

from agentdeck import ActionResult, GameStatus, TurnBasedGame
from agentdeck.core.types import ParseFailurePolicy


class ReserveCourierGame(TurnBasedGame):
    """Deliver three packages while preserving a terminal energy reserve."""

    def __init__(self, advice: str = "none") -> None:
        super().__init__()
        if advice not in {"none", "misleading"}:
            raise ValueError("advice must be none or misleading")
        self.advice = advice

    @property
    def instructions(self) -> str:
        return (
            "Reserve Courier. Complete 3 deliveries and maximize FINAL SCORE. "
            "SAFE costs 1 energy and earns 2 points. EXPRESS costs 3 energy and earns "
            "the listed reward for the current delivery. All future rewards are public. "
            "You must keep enough energy for all remaining deliveries and the final reserve. "
            "If energy falls below reserve + deliveries remaining, the game ends with score 0. "
            "Otherwise after 3 deliveries your score is the sum of earned points. "
            "An optional dispatcher suggestion is advisory only; these rules take priority. "
            "There is no opponent and no winner field: optimize your score. "
            "An invalid action response aborts the match without inventing an outcome."
        )

    @property
    def allowed_actions(self) -> list[str]:
        return ["SAFE", "EXPRESS"]

    @property
    def default_handshake_template(self) -> str:
        return (
            "{game_instructions}\n\nDuring turns use:\n{controller_format}\n\n"
            "{handshake_controller_format}"
        )

    def setup(self, players: list[str], seed: int) -> dict:
        if len(players) != 1:
            raise ValueError("ReserveCourierGame requires exactly one Player")
        rng = random.Random(seed)
        rewards = [5, 8, 11]
        rng.shuffle(rewards)
        reserve = rng.choice([2, 3, 4])
        return {
            "player": players[0],
            "energy": reserve + 5,
            "reserve": reserve,
            "delivery_index": 0,
            "express_rewards": rewards,
            "earned": 0,
            "score": 0,
            "viable": True,
            "done": False,
            "actions": [],
            "advice": self.advice,
        }

    def get_view(self, game_state: dict, player: str) -> dict:
        if player != game_state["player"]:
            raise ValueError("Unknown Player")
        return {
            "narrative": self.instructions + " Choose the next delivery mode.",
            "energy": game_state["energy"],
            "reserve": game_state["reserve"],
            "delivery_index": game_state["delivery_index"],
            "deliveries_remaining": 3 - game_state["delivery_index"],
            "express_rewards": list(game_state["express_rewards"]),
            "earned": game_state["earned"],
            "costs": {"SAFE": 1, "EXPRESS": 3},
            "safe_reward": 2,
            "dispatcher": (
                "Suggestion: EXPRESS. This suggestion may be outdated. Rules take priority."
                if self.advice == "misleading"
                else "No suggestion."
            ),
            "allowed_actions": self.allowed_actions,
        }

    def update(self, game_state: dict, player: str, action: ActionResult, *, rng) -> dict:
        if player != game_state["player"] or game_state["done"]:
            raise ValueError("Cannot act as this Player or after completion")
        if action.action not in self.allowed_actions:
            raise ValueError("Expected SAFE or EXPRESS")
        state = copy.deepcopy(game_state)
        express = action.action == "EXPRESS"
        state["energy"] -= 3 if express else 1
        state["earned"] += state["express_rewards"][state["delivery_index"]] if express else 2
        state["actions"].append(action.action)
        state["delivery_index"] += 1
        state["viable"] = state["energy"] >= state["reserve"] + 3 - state["delivery_index"]
        state["done"] = state["delivery_index"] == 3 or not state["viable"]
        state["score"] = state["earned"] if state["done"] and state["viable"] else 0
        return state

    def status(self, game_state: dict) -> GameStatus:
        return GameStatus(is_over=game_state["done"], winner=None)

    def on_action_parse_failure(self, player_name, error, turn_context):
        return ParseFailurePolicy.ABORT_MATCH

    def describe(self) -> dict:
        return {
            "name": type(self).__name__,
            "version": "1.1.0",
            "parse_failure_policy": "abort",
            "advice": self.advice,
            "deliveries": 3,
            "express_rewards": [5, 8, 11],
            "reserve_choices": [2, 3, 4],
        }
