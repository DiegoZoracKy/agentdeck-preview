"""Simple auction game demonstrating domain event emission."""

from __future__ import annotations

from typing import Any, Dict, List

from agentdeck.core.base.game import TurnBasedGame
from agentdeck.core.types import ActionResult, GameStatus, RandomGenerator


class AuctionGame(TurnBasedGame):
    """Each player submits a bid; highest bid wins the round."""

    def __init__(self, rounds: int = 3) -> None:
        super().__init__()
        self.rounds = rounds

    @property
    def instructions(self) -> str:
        return "Submit a numeric bid between 0 and 100 each round. Highest bid wins the round."

    def setup(self, players: List[str]) -> Dict[str, Any]:
        return {
            "players": players,
            "round": 0,
            "scores": {p: 0 for p in players},
        }

    def update(self, state: Dict[str, Any], player: str, action: ActionResult, *, rng: RandomGenerator) -> Dict[str, Any]:
        bid = int(action.action)
        state.setdefault("bids", {})[player] = bid

        if len(state["bids"]) == len(state["players"]):
            winner = max(state["bids"].items(), key=lambda item: item[1])[0]
            state["scores"][winner] += 1
            state["round"] += 1

            self.emit_event(
                "bid_placed",
                round=state["round"],
                bids=dict(state["bids"]),
                winning_player=winner,
                scores=dict(state["scores"]),
            )

            state["bids"].clear()

        return state

    def status(self, state: Dict[str, Any]) -> GameStatus:
        is_over = state["round"] >= self.rounds
        if not is_over:
            return GameStatus(is_over=False)

        winner = max(state["scores"].items(), key=lambda item: item[1])[0]
        return GameStatus(is_over=True, winner=winner)
