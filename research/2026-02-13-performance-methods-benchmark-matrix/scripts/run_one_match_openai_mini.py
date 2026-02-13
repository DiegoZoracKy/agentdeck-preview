#!/usr/bin/env python3
"""
Run one out-of-the-box FixedDamageGame match with two gpt-4o-mini players.

This script intentionally avoids custom analytics and custom reporting logic.
All runtime visibility comes from built-in AgentDeck spectators and recorder.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Local development import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from agentdeck import (  # noqa: E402
    ActionOnlyController,
    AgentDeck,
    AgentDeckConfig,
    FixedDamageGame,
    GPTPlayer,
    LogLevel,
    ReasoningController,
)
from agentdeck.spectators import (  # noqa: E402
    ProgressDisplay,
    StatisticalAnalysisSpectator,
    StatsTracker,
    TokenUsageTracker,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one gpt-4o-mini vs gpt-4o-mini match using AgentDeck defaults."
    )
    parser.add_argument(
        "--controller",
        choices=["reasoning", "action"],
        default="reasoning",
        help="Controller type for both players (default: reasoning).",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model for both players (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=420000,
        help="Match seed (default: 420000).",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Turn cap for the match (default: 30).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Sampling temperature for both players (default: 1.0).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    controller_cls = ReasoningController if args.controller == "reasoning" else ActionOnlyController

    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=2,
        information_level="partial",
    )

    players = [
        GPTPlayer(
            name=f"{args.model}-A",
            model=args.model,
            controller=controller_cls(),
            temperature=args.temperature,
        ),
        GPTPlayer(
            name=f"{args.model}-B",
            model=args.model,
            controller=controller_cls(),
            temperature=args.temperature,
        ),
    ]

    config = AgentDeckConfig(
        seed=args.seed,
        concurrency=1,
        max_turns=args.max_turns,
        log_level=LogLevel.INFO,
    )

    spectators = [
        ProgressDisplay(),
        StatsTracker(),
        TokenUsageTracker(),
        StatisticalAnalysisSpectator(print_on_complete=True, save_report=False),
    ]

    with AgentDeck(game=game, session=config, spectators=spectators) as deck:
        deck.play(players=players, matches=1, seed=args.seed)


if __name__ == "__main__":
    main()
