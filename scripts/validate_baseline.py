#!/usr/bin/env python3
"""
Baseline Validation Script - Phase 0 Quality Gate

Runs mirror matches (same model vs itself) to detect system bias.
Expected: 50% ± 18% win rate (95% Wilson CI for n=30)

Usage:
    python scripts/validate_baseline.py --model gpt-4o-mini --matches 30 --seed 42
    python scripts/validate_baseline.py --model gpt-4o --matches 30 --seed 43

Part of: OpenAI Strategic Benchmarks Experiment
See: docs/research/2025-11-08-openai-benchmarks/
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Tuple

# Add src to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    GPTPlayer,
    FixedDamageGame,
    ActionOnlyController,
    TextRenderer,
)
from agentdeck.spectators import ProgressDisplay
from agentdeck.research.statistical import (
    calculate_confidence_interval,
    statistical_significance,
)


@dataclass
class BaselineOutcome:
    """Structured result for a baseline run."""

    model: str
    matches: int
    wins_a: int
    win_rate_a: float
    confidence_interval: Tuple[float, float]
    p_value: float
    passed: bool
    tolerance: float
    session_id: str
    record_dir: str


def validate_baseline(
    model: str,
    matches: int = 30,
    seed: int = 42,
    tolerance: float = 0.18,
    show_summary: bool = False,
) -> BaselineOutcome:
    """
    Run mirror match baseline validation.

    Args:
        model: OpenAI model name (e.g., "gpt-4o-mini", "gpt-4o")
        matches: Number of matches to run (default: 30)
        seed: Random seed for reproducibility
        tolerance: Acceptable deviation from 50% (default: 0.18 = ±18%)

    Returns:
        True if baseline passes quality gate, False otherwise
    """
    # Setup game
    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=2
    )

    # Setup players - mirror match (same model vs itself)
    renderer = TextRenderer()
    controller = ActionOnlyController()

    player_a = GPTPlayer(
        name=f"{model}-A",
        model=model,
        renderer=renderer,
        controller=controller
    )

    player_b = GPTPlayer(
        name=f"{model}-B",
        model=model,
        renderer=renderer,
        controller=controller
    )

    # Setup AgentDeck with explicit configuration
    config = AgentDeckConfig(
        seed=seed,
        run_dir="agentdeck_runs",
        max_turns=30,
        concurrency=1  # Sequential for baseline
    )

    # Attach spectators - let AgentDeck handle observability
    spectators = [ProgressDisplay()]

    deck = AgentDeck(
        game=game,
        session=config,
        spectators=spectators,
    )

    # Run matches - rely on spectators for live feedback
    results = deck.play(
        players=[player_a, player_b],
        matches=matches
    )

    # Post-hoc analysis using research utilities
    wins_a = sum(1 for m in results.matches if m.winner == player_a.name)
    win_rate_a = wins_a / matches

    ci_lower, ci_upper = calculate_confidence_interval(
        successes=wins_a,
        trials=matches,
        confidence_level=0.95
    )

    p_value = statistical_significance(
        successes=wins_a,
        trials=matches,
        expected_probability=0.5
    )

    passed = abs(win_rate_a - 0.5) <= tolerance

    outcome = BaselineOutcome(
        model=model,
        matches=matches,
        wins_a=wins_a,
        win_rate_a=win_rate_a,
        confidence_interval=(ci_lower, ci_upper),
        p_value=p_value,
        passed=passed,
        tolerance=tolerance,
        session_id=deck.session.session_id,
        record_dir=str(deck.session.record_directory),
    )

    if show_summary:
        status = "PASS" if passed else "FAIL"
        print(
            f"Baseline {model}: {status} | "
            f"Win rate: {win_rate_a:.1%} "
            f"[{ci_lower:.1%}, {ci_upper:.1%}] p={p_value:.3f}"
        )
        print(f"Session artifacts: {outcome.record_dir}")

    return outcome


def main():
    parser = argparse.ArgumentParser(
        description="Baseline validation for OpenAI models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_baseline.py --model gpt-4o-mini --matches 30 --seed 42
  python scripts/validate_baseline.py --model gpt-4o --matches 30 --seed 43

Part of: OpenAI Strategic Benchmarks Experiment
See: docs/research/2025-11-08-openai-benchmarks/
        """
    )

    parser.add_argument(
        '--model',
        type=str,
        required=True,
        choices=['gpt-4o-mini', 'gpt-4o'],
        help='OpenAI model to validate'
    )

    parser.add_argument(
        '--matches',
        type=int,
        default=30,
        help='Number of matches to run (default: 30)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )

    parser.add_argument(
        '--tolerance',
        type=float,
        default=0.18,
        help='Acceptable deviation from 50%% (default: 0.18)'
    )

    parser.add_argument(
        '--report',
        action='store_true',
        help='Print summary after run (default: rely on spectators/logs only)'
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        print("Set it with: export OPENAI_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    # Run validation
    outcome = validate_baseline(
        model=args.model,
        matches=args.matches,
        seed=args.seed,
        tolerance=args.tolerance,
        show_summary=args.report,
    )

    # Exit with appropriate code
    sys.exit(0 if outcome.passed else 1)


if __name__ == '__main__':
    main()
