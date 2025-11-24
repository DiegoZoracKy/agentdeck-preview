"""Run an auction match end-to-end and replay it with BidAnalyzer."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentdeck.core.agentdeck import AgentDeck
from agentdeck.core.session import AgentDeckConfig
from agentdeck.players.mock import MockPlayer
from examples.games.auction import AuctionGame
from examples.spectators.bid_analyzer import BidAnalyzer


def _build_players() -> List[MockPlayer]:
    """Create deterministic mock players with scripted bids."""
    return [
        MockPlayer("Alice", actions=["ACTION: 45", "ACTION: 55", "ACTION: 65"]),
        MockPlayer("Bob", actions=["ACTION: 60", "ACTION: 50", "ACTION: 40"]),
    ]


def _latest_recording(record_dir: Path) -> Path:
    """Return the most recent match recording in the directory."""
    matches = sorted(record_dir.glob("match_*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No match recordings found in {record_dir}. "
            "Ensure a match was played before replaying."
        )
    return matches[-1]


def main(rounds: int, seed: int) -> None:
    config = AgentDeckConfig(seed=seed)
    live_analyzer = BidAnalyzer()
    deck = AgentDeck(
        game=AuctionGame(rounds=rounds),
        spectators=[live_analyzer],
        session=config,
    )

    players = _build_players()
    print(f"Playing AuctionGame for {rounds} round(s)...")
    deck.play(players, matches=1)

    record_dir = Path(deck.session.record_directory)
    match_path = _latest_recording(record_dir)
    print(f"Recording saved to {match_path}")
    print("Live BidAnalyzer summary:", live_analyzer.summary())

    replay_analyzer = BidAnalyzer()
    print("Replaying recorded match...")
    deck.replay(path=match_path, spectators=[replay_analyzer], speed=0.0)
    print("Replay BidAnalyzer summary:", replay_analyzer.summary())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Play and replay the AuctionGame example with BidAnalyzer."
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=2,
        help="Number of rounds to play during the live match (default: 2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Deterministic seed for reproducible runs (default: 123)",
    )
    args = parser.parse_args()
    main(rounds=args.rounds, seed=args.seed)
