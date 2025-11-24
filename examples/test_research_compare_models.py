"""
AgentDeck Research Example: Model Comparison

Purpose:
    Demonstrate how to run statistical comparisons between two player strategies
    using the research utilities shipped with AgentDeck.

Usage:
    python examples/test_research_compare_models.py

    (Uses MockPlayer implementations, so no API keys or network access required.)

What This Demonstrates:
    ✓ compare_models() with deterministic players
    ✓ 100-match experiment (default per SPEC-RESEARCH v1.0.0)
    ✓ Reproducible results via seeded AgentDeck sessions
    ✓ Access to p-value, confidence interval, and effect size
"""

from agentdeck.games.examples import FixedDamageGame
from agentdeck.players.mock import MockPlayer
from agentdeck.controllers import ActionOnlyController
from agentdeck.research import compare_models
import random


MATCHES = 100
SEED = 12345


def make_game() -> FixedDamageGame:
    """Create a small deterministic FixedDamageGame configuration."""
    return FixedDamageGame(
        max_health=60,
        attack_damage=15,
        potion_heal=20,
        starting_potions=1,
        information_level="full",
    )


def make_players() -> tuple[MockPlayer, MockPlayer]:
    """Create two biased-but-random strategies using MockPlayer."""
    rng = random.Random(SEED)

    def random_actions(primary: str, secondary: str, primary_bias: float, length: int = 2000) -> list[str]:
        return [primary if rng.random() < primary_bias else secondary for _ in range(length)]

    aggressive_actions = random_actions("ATTACK", "POTION", primary_bias=0.85)
    cautious_actions = random_actions("POTION", "ATTACK", primary_bias=0.65)

    aggressive = MockPlayer(
        "AggressiveBot",
        actions=aggressive_actions,
        controller=ActionOnlyController(),
    )

    cautious = MockPlayer(
        "CautiousBot",
        actions=cautious_actions,
        controller=ActionOnlyController(),
    )

    return aggressive, cautious


def main() -> None:
    game = make_game()
    player_a, player_b = make_players()

    # Run a 100-match comparison (SPEC-RESEARCH default) with deterministic seed.
    result = compare_models(
        model_a=player_a,
        model_b=player_b,
        game=game,
        matches=MATCHES,
        seed=SEED,
    )

    print("=== AgentDeck Research: compare_models() ===")
    print(f"Game: {result.game}")
    print(f"Matches: {result.matches}")
    print(f"Win rate {result.model_a}: {result.win_rate_a:.2%}")
    print(f"Win rate {result.model_b}: {result.win_rate_b:.2%}")
    print(f"Draw rate: {result.draws:.2%}")
    print(f"Statistical test: {result.test_used}")
    print(f"p-value: {result.p_value:.4f}")
    print(f"Confidence interval (difference): {result.confidence_interval}")
    if result.effect_size is not None:
        print(f"Effect size (Cohen's h): {result.effect_size:.3f}")
    print(f"Metadata: {result.metadata}\n")


if __name__ == "__main__":
    main()
