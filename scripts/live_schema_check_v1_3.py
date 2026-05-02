#!/usr/bin/env python3
"""
Live schema v1.3 provider check.

Runs real OpenAI-backed matches, validates the generated recordings, and replays
them through the public replay API. For offline recording validation, use:

    python scripts/validate_schema_v1_3.py <recording-or-directory>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src and scripts to path for development checkout execution.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from validate_schema_v1_3 import validate_paths


def main() -> int:
    print("=" * 70)
    print("Schema v1.3 Live Provider Check")
    print("=" * 70)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY environment variable not set")
        print("Export your API key: export OPENAI_API_KEY=sk-...")
        return 1

    from agentdeck import AgentDeck
    from agentdeck.controllers import ActionOnlyController
    from agentdeck.core.session import AgentDeckConfig
    from agentdeck.games.examples import FixedDamageGame
    from agentdeck.players import GPTPlayer

    run_dir = Path("agentdeck_runs/schema_v1_3_live_check")
    print(f"\nOutput directory: {run_dir}")

    player_a = GPTPlayer(
        name="Alice",
        model="gpt-4o-mini",
        temperature=0.7,
        controller=ActionOnlyController(),
    )
    player_b = GPTPlayer(
        name="Bob",
        model="gpt-4o-mini",
        temperature=0.7,
        controller=ActionOnlyController(),
    )

    config = AgentDeckConfig(run_dir=str(run_dir), max_turns=30, concurrency=1)
    game = FixedDamageGame(starting_potions=2)

    with AgentDeck(game=game, session=config) as deck:
        print("\nRunning 3 validation matches with real OpenAI calls...")
        try:
            results = deck.play(players=[player_a, player_b], matches=3)
        except Exception as exc:
            print(f"\nMatch execution failed: {exc}")
            return 1

        print("\nMatches completed successfully")
        print(f"Total matches: {len(results.matches)}")
        record_dir = Path(deck.session.record_directory)

    return 0 if validate_paths([record_dir], replay=True) else 1


if __name__ == "__main__":
    sys.exit(main())
