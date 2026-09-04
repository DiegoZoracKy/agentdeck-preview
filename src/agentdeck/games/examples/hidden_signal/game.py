"""A small single-Player world for consequential information acquisition."""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, List

from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.core.types import ActionResult, GameStatus, ParseFailurePolicy, RandomGenerator


class HiddenSignalGame(TurnBasedGame):
    """Choose a concealed signal directly or inspect it at a declared cost."""

    SIGNALS = ("RED", "BLUE")
    SUPPORTED_VISIBILITY = {"hidden", "visible"}

    def __init__(
        self,
        signal_visibility: str = "hidden",
        inspection_cost: int = 1,
        correct_reward: int = 2,
    ) -> None:
        super().__init__()
        if signal_visibility not in self.SUPPORTED_VISIBILITY:
            raise ValueError("signal_visibility must be 'hidden' or 'visible'")
        if inspection_cost < 0:
            raise ValueError("inspection_cost must be non-negative")
        if correct_reward <= 0:
            raise ValueError("correct_reward must be positive")
        self.signal_visibility = signal_visibility
        self.inspection_cost = inspection_cost
        self.correct_reward = correct_reward

    @property
    def instructions(self) -> str:
        visibility = (
            "The signal starts concealed. INSPECT reveals it once."
            if self.signal_visibility == "hidden"
            else "The signal is visible from the first turn."
        )
        return f"""
Hidden Signal

{visibility}

Actions:
- INSPECT: reveal the signal at a cost of {self.inspection_cost} point(s)
- CHOOSE_RED: commit to RED
- CHOOSE_BLUE: commit to BLUE

A correct commitment earns {self.correct_reward} point(s) and ends the run.
There is no opponent, ranking, or winner.
An invalid action response aborts this match without inventing a Game outcome.
        """.strip()

    @property
    def allowed_actions(self) -> List[str]:
        return ["INSPECT", "CHOOSE_RED", "CHOOSE_BLUE"]

    def on_action_parse_failure(self, player_name, error, turn_context):
        return ParseFailurePolicy.ABORT_MATCH

    @property
    def default_handshake_template(self) -> str:
        return (
            "{game_instructions}\n\n"
            "When gameplay begins, use this response format:\n"
            "{controller_format}\n\n"
            "{handshake_controller_format}"
        )

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        if len(players) != 1:
            raise ValueError("HiddenSignalGame requires exactly 1 player")
        signal = random.Random(seed).choice(self.SIGNALS)
        state: Dict[str, Any] = {
            "player": players[0],
            "signal": signal,
            "revealed_signal": signal if self.signal_visibility == "visible" else None,
            "signal_visibility": self.signal_visibility,
            "inspections": 0,
            "inspection_cost_total": 0,
            "choice": None,
            "correct": None,
            "score": 0,
            "done": False,
            "turn": 1,
        }
        self.validate_state(state)
        return state

    def update(
        self,
        game_state: Dict[str, Any],
        player: str,
        action: ActionResult,
        *,
        rng: RandomGenerator,
    ) -> Dict[str, Any]:
        del rng
        self.validate_state(game_state)
        if player != game_state["player"]:
            raise ValueError(f"Unknown Player '{player}'")
        if game_state["done"]:
            raise ValueError("HiddenSignalGame is already complete")

        action_token = (action.action or "").strip().upper()
        if action_token not in self.allowed_actions:
            raise ValueError(
                f"Invalid action '{action_token}'. Allowed actions: {self.allowed_actions}"
            )
        if action_token == "INSPECT" and game_state["inspections"]:
            raise ValueError("HiddenSignalGame permits at most one inspection")

        state = copy.deepcopy(game_state)
        if action_token == "INSPECT":
            state["revealed_signal"] = state["signal"]
            state["inspections"] = 1
            state["inspection_cost_total"] = self.inspection_cost
            state["score"] -= self.inspection_cost
        else:
            choice = action_token.removeprefix("CHOOSE_")
            correct = choice == state["signal"]
            state["choice"] = choice
            state["correct"] = correct
            state["score"] += self.correct_reward if correct else 0
            state["done"] = True
        state["turn"] += 1
        self.validate_state(state)
        return state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        self.validate_state(game_state)
        return GameStatus(is_over=game_state["done"], winner=None)

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        self.validate_state(game_state)
        if player != game_state["player"]:
            raise ValueError(f"Unknown Player '{player}'")
        signal = game_state["revealed_signal"] or "HIDDEN"
        return {
            "player": player,
            "signal": signal,
            "signal_visibility": game_state["signal_visibility"],
            "inspection_available": not game_state["inspections"] and not game_state["done"],
            "inspections": game_state["inspections"],
            "inspection_cost_total": game_state["inspection_cost_total"],
            "choice": game_state["choice"],
            "correct": game_state["correct"],
            "score": game_state["score"],
            "done": game_state["done"],
            "turn": game_state["turn"],
            "allowed_actions": self.allowed_actions,
        }

    def validate_state(self, game_state: Dict[str, Any]) -> None:
        required = {
            "player",
            "signal",
            "revealed_signal",
            "signal_visibility",
            "inspections",
            "inspection_cost_total",
            "choice",
            "correct",
            "score",
            "done",
            "turn",
        }
        missing = sorted(required.difference(game_state))
        if missing:
            raise ValueError(f"HiddenSignalGame state is missing: {', '.join(missing)}")
        if game_state["signal"] not in self.SIGNALS:
            raise ValueError("HiddenSignalGame state has an invalid signal")
        if game_state["signal_visibility"] != self.signal_visibility:
            raise ValueError("HiddenSignalGame state visibility differs from configuration")
        if game_state["inspections"] not in {0, 1}:
            raise ValueError("HiddenSignalGame inspections must be 0 or 1")
        if game_state["choice"] not in {*self.SIGNALS, None}:
            raise ValueError("HiddenSignalGame state has an invalid choice")
        if game_state["done"] != (game_state["choice"] is not None):
            raise ValueError("HiddenSignalGame done and choice state disagree")

        expected_reveal = (
            game_state["signal"]
            if self.signal_visibility == "visible" or game_state["inspections"] == 1
            else None
        )
        if game_state["revealed_signal"] != expected_reveal:
            raise ValueError("HiddenSignalGame revealed signal is inconsistent")
        expected_correct = (
            None if game_state["choice"] is None else game_state["choice"] == game_state["signal"]
        )
        if game_state["correct"] != expected_correct:
            raise ValueError("HiddenSignalGame correctness is inconsistent")

        expected_cost = game_state["inspections"] * self.inspection_cost
        expected_score = expected_cost * -1
        if game_state["correct"] is True:
            expected_score += self.correct_reward
        expected_turn = 1 + game_state["inspections"] + int(game_state["done"])
        if game_state["inspection_cost_total"] != expected_cost:
            raise ValueError("HiddenSignalGame inspection cost is inconsistent")
        if game_state["score"] != expected_score:
            raise ValueError("HiddenSignalGame score is inconsistent")
        if game_state["turn"] != expected_turn:
            raise ValueError("HiddenSignalGame turn is inconsistent")


__all__ = ["HiddenSignalGame"]
