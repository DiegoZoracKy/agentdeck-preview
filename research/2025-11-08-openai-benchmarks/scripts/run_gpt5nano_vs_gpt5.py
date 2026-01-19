"""
GPT-5-nano vs GPT-5 Comparison (Both Reasoning)

Research Question: Does full GPT-5 provide strategic advantage over GPT-5-nano?

Configuration:
- Matches: 30
- Seed: 2144
- Concurrency: 10
- Temperature: 1.0 (GPT-5 models only support this value)
- Game: FixedDamageGame (partial info, 2 potions)
- Controllers: Both ReasoningController

Usage:
    python docs/research/2025-11-08-openai-benchmarks/run_gpt5nano_vs_gpt5.py
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.games.examples import FixedDamageGame
from agentdeck.controllers import ReasoningController
from agentdeck.players import GPTPlayer
from agentdeck.core.recorder import Recorder
from agentdeck.spectators import ProgressDisplay, StatsTracker, TokenUsageTracker
from agentdeck.core.types import LogLevel


# Experiment parameters
MATCHES = 30
SEED = 2144
CONCURRENCY = 30
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "recordings")


def build_game() -> FixedDamageGame:
    """Create FixedDamageGame with partial information."""
    return FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=2,
        information_level="partial",
    )


def build_players() -> tuple:
    """Create GPT-5 players with ReasoningController."""

    gpt5_nano = GPTPlayer(
        name="GPT-5-nano",
        model="gpt-5-nano",
        temperature=1.0,
        controller=ReasoningController(),
    )

    gpt5 = GPTPlayer(
        name="GPT-5",
        model="gpt-5",
        temperature=1.0,
        controller=ReasoningController(),
        reasoning_effort="low",
    )

    return gpt5_nano, gpt5


def main():
    print("=" * 60)
    print("GPT-5-nano vs GPT-5 (Both Reasoning)")
    print("=" * 60)
    print(f"Matches: {MATCHES}")
    print(f"Seed: {SEED}")
    print(f"Concurrency: {CONCURRENCY}")
    print("=" * 60)

    # Build components
    game = build_game()
    player_a, player_b = build_players()

    # Create spectators
    recorder = Recorder(output_dir=OUTPUT_DIR)
    stats = StatsTracker()
    tokens = TokenUsageTracker()

    # Configure session
    config = AgentDeckConfig(
        seed=SEED,
        concurrency=CONCURRENCY,
        log_level=LogLevel.INFO,
    )

    # Run experiment
    print("\nStarting experiment...\n")

    with AgentDeck(game=game, session=config) as deck:
        results = deck.play(
            players=[player_a, player_b],
            matches=MATCHES,
            spectators=[recorder, stats, tokens, ProgressDisplay()],
        )

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\nWin Rates:")
    for player, rate in results.win_rates.items():
        print(f"  {player}: {rate:.1%}")

    # Get detailed stats
    stats_data = stats.get_stats()
    print(f"\nTotal Turns:")
    for player, data in stats_data.get("players", {}).items():
        print(f"  {player}: {data['total_turns']} turns")

    # Token usage
    usage = tokens.get_summary()
    print(f"\nToken Usage:")
    print(f"  Total tokens: {usage['total']['total_tokens']:,}")
    print(f"  Total cost: ${usage['total']['cost']:.4f}")

    for player, data in usage.get("per_player", {}).items():
        print(f"  {player}: {data['total_tokens']:,} tokens (${data['cost']:.4f})")

    print(f"\nRecordings saved to: {OUTPUT_DIR}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
