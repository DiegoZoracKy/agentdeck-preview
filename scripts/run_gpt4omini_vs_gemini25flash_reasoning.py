"""
GPT-4o-mini vs Claude Sonnet 4.5 - Single Match with ReasoningController

Both players use ReasoningController for reasoning output.

Usage:
    python scripts/run_gpt4omini_vs_gemini25flash_reasoning.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv

load_dotenv()

from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.games.examples import FixedDamageGame
from agentdeck.controllers import ReasoningController
from agentdeck.players import GPTPlayer, ClaudePlayer
from agentdeck.core.recorder import Recorder
from agentdeck.spectators import ProgressDisplay, StatsTracker, TokenUsageTracker
from agentdeck.core.types import LogLevel


MATCHES = 1
SEED = 42


def build_game() -> FixedDamageGame:
    """Create FixedDamageGame with partial info."""
    return FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=2,
        information_level='partial',
    )


def build_players() -> tuple:
    """Create GPT-4o-mini and Claude Sonnet 4.5 players using ReasoningController."""

    gpt4o_mini = GPTPlayer(
        name='GPT-4o-mini',
        model='gpt-4o-mini',
        temperature=1.0,
        controller=ReasoningController(),
    )

    claude = ClaudePlayer(
        name='Claude-Sonnet-4.5',
        model='claude-sonnet-4-5-20250929',
        temperature=1.0,
        max_tokens=1024,
        controller=ReasoningController(),
    )

    return gpt4o_mini, claude


def main():
    game = build_game()
    player_a, player_b = build_players()

    recorder = Recorder()
    stats = StatsTracker()
    tokens = TokenUsageTracker()

    config = AgentDeckConfig(
        seed=SEED,
        concurrency=1,
        log_level=LogLevel.INFO,
    )

    print("=" * 60)
    print("GPT-4o-mini vs Claude-Sonnet-4.5 (ReasoningController)")
    print("=" * 60)
    print(f"Match count: {MATCHES}")
    print(f"Seed: {SEED}")
    print("=" * 60)
    print()

    with AgentDeck(game=game, session=config) as deck:
        results = deck.play(
            players=[player_a, player_b],
            matches=MATCHES,
            spectators=[recorder, stats, tokens, ProgressDisplay()],
        )

    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)

    if results.matches:
        match = results.matches[0]
        print(f"Winner: {match.winner or 'Draw'}")
        print(f"Turns: {match.metadata.get('turns', '?')}")
        print(f"Outcome: {match.metadata.get('outcome', '?')}")

    print()
    print(f"Session path: {recorder.output_dir}")

    return results


if __name__ == '__main__':
    main()
