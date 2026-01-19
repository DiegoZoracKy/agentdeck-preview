"""
Gemini 2.5 Pro vs GPT-4o-mini Comparison Experiment

Research Question: How does Gemini 2.5 Pro compare to GPT-4o-mini in strategic gameplay
when both use ReasoningController?

Configuration:
- Matches: 30
- Seed: 2084
- Concurrency: 10
- Temperature: 1.0 (Gemini + GPT parity)
- Game: FixedDamageGame (partial info, 2 potions)
- Controller: ReasoningController

Usage:
    python docs/research/2025-11-19-multi-provider-benchmarks/run_gemini25pro_vs_gpt4omini.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from dotenv import load_dotenv

load_dotenv()

from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.games.examples import FixedDamageGame
from agentdeck.controllers import ReasoningController
from agentdeck.players import GPTPlayer, GeminiPlayer
from agentdeck.core.recorder import Recorder
from agentdeck.spectators import ProgressDisplay, StatsTracker, TokenUsageTracker
from agentdeck.core.types import LogLevel


MATCHES = 30
SEED = 2084
CONCURRENCY = 1
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'recordings')


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
    """Create Gemini 2.5 Pro and GPT-4o-mini players using ReasoningController."""

    gemini = GeminiPlayer(
        name='Gemini-2.5-Pro',
        model='gemini-2.5-pro',
        temperature=1.0,
        controller=ReasoningController(),
    )

    gpt4o_mini = GPTPlayer(
        name='GPT-4o-mini',
        model='gpt-4o-mini',
        temperature=1.0,
        controller=ReasoningController(),
    )

    return gemini, gpt4o_mini


def main():
    game = build_game()
    player_a, player_b = build_players()

    recorder = Recorder(output_dir=OUTPUT_DIR)
    stats = StatsTracker()
    tokens = TokenUsageTracker()

    config = AgentDeckConfig(
        seed=SEED,
        concurrency=CONCURRENCY,
        log_level=LogLevel.INFO,
    )

    with AgentDeck(game=game, session=config) as deck:
        results = deck.play(
            players=[player_a, player_b],
            matches=MATCHES,
            spectators=[recorder, stats, tokens, ProgressDisplay()],
        )

    return results


if __name__ == '__main__':
    main()
