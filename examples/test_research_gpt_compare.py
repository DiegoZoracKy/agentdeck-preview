"""
AgentDeck Research Example: GPT Model Comparison

Purpose:
    Use AgentDeck's research utilities to compare two GPT strategies
    with full statistical reporting (win rates, p-value, confidence interval).

Usage:
    export OPENAI_API_KEY="sk-..."
    python examples/test_research_gpt_compare.py

What This Demonstrates:
    ✓ Real GPT players with different prompting strategies
    ✓ compare_models() over 100 matches (SPEC-RESEARCH default)
    ✓ Reproducible results via seeded AgentDeck session
    ✓ Access to confidence intervals and effect sizes
    ✓ Live progress via ProgressDisplay and MatchReporter spectators
"""

from agentdeck.games.examples import FixedDamageGame
from agentdeck.controllers import ReasoningController
from agentdeck.players import GPTPlayer
from agentdeck.prompts import DEFAULT_CONCLUSION_TEMPLATE_PATH
from agentdeck.research import compare_models
from agentdeck.spectators import MatchReporter, ProgressDisplay


MATCHES = 2  # Small sample for quick GPT comparison
SEED = 42


def build_game() -> FixedDamageGame:
    return FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=1,
        information_level="full",
    )


def build_players() -> tuple[GPTPlayer, GPTPlayer]:
    """Create two GPT players with contrasting styles."""
    aggressive = GPTPlayer(
        name="Aggressive-GPT",
        model="gpt-4o-mini",
        temperature=0.8,
        controller=ReasoningController(),
        conclusion_template=DEFAULT_CONCLUSION_TEMPLATE_PATH,
    )

    cautious = GPTPlayer(
        name="Cautious-GPT",
        model="gpt-4o-mini",
        temperature=0.2,
        controller=ReasoningController(),
        conclusion_template=DEFAULT_CONCLUSION_TEMPLATE_PATH,
    )

    return aggressive, cautious


def main() -> None:
    game = build_game()
    player_a, player_b = build_players()

    result = compare_models(
        model_a=player_a,
        model_b=player_b,
        game=game,
        matches=MATCHES,
        seed=SEED,
        spectators=[ProgressDisplay(), MatchReporter()],
    )

    print("=== AgentDeck Research: GPT Comparison ===")
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
    print(f"Metadata: {result.metadata}")


if __name__ == "__main__":
    main()
