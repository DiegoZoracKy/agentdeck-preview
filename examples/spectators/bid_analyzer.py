"""Spectator that analyzes bid_placed events."""

from __future__ import annotations

from collections import defaultdict

from agentdeck.core.base.spectator import Spectator
from agentdeck.core.types import Event


class BidAnalyzer(Spectator):
    """Collects bid statistics during an auction game replay or live run."""

    def __init__(self) -> None:
        super().__init__()
        self.winning_rounds = defaultdict(list)

    def on_bid_placed(self, event: Event) -> None:
        data = event.data
        context = event.context

        round_index = data.get("round")
        winning_player = data.get("winning_player")
        bids = data.get("bids", {})

        self.winning_rounds[winning_player].append({
            "round": round_index,
            "bids": bids,
            "match_id": context.get("match_id"),
        })

    def summary(self):
        return {
            player: len(rounds)
            for player, rounds in self.winning_rounds.items()
        }
