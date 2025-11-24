#!/usr/bin/env python3
"""
Hangman Benchmark: Compare GPT-4o vs GPT-4o-mini with different controllers.

Runs 10 matches each for:
- GPT-4o-mini + ActionOnlyController
- GPT-4o-mini + ReasoningController
- GPT-4o + ActionOnlyController
- GPT-4o + ReasoningController

Run:
    python examples/hangman_benchmark.py
"""

from dotenv import load_dotenv
load_dotenv()

from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    HangmanGame,
    GPTPlayer,
    ActionOnlyController,
    ReasoningController,
    StatsTracker,
)


def run_benchmark(model: str, controller_type: str, matches: int = 10, concurrency: int = 1):
    game = HangmanGame(
        word_list=["AGENT", "TOKEN", "BATCH", "LAYER", "NEURAL"],
        max_wrong_guesses=6,
    )

    if controller_type == "action":
        controller = ActionOnlyController()
    else:
        controller = ReasoningController()

    player = GPTPlayer(
        name=f"{model}",
        model=model,
        controller=controller,
    )

    stats = StatsTracker()

    config = AgentDeckConfig(concurrency=concurrency)

    with AgentDeck(session=config, game=game, spectators=[stats]) as deck:
        results = deck.play(
            players=[player],
            matches=matches,
        )

    wins = sum(1 for m in results.matches if m.winner)
    total_cost = sum(
        cost
        for m in results.matches
        if m.metadata.get("player_costs")
        for cost in m.metadata["player_costs"].values()
    )

    return {
        "model": model,
        "controller": controller_type,
        "wins": wins,
        "matches": matches,
        "win_rate": wins / matches * 100,
        "cost": total_cost,
    }


def main():
    print("=" * 70)
    print("Hangman Benchmark: Tokenization Blindness Study")
    print("=" * 70)
    print()

    configs = [
        ("gpt-4o-mini", "action"),
        ("gpt-4o-mini", "reasoning"),
        ("gpt-4o", "action"),
        ("gpt-4o", "reasoning"),
    ]

    results = []
    for model, controller in configs:
        print(f"Running: {model} + {controller}Controller (30 matches, concurrency=10)...")
        result = run_benchmark(model, controller, matches=30, concurrency=10)
        results.append(result)
        print(f"  Win rate: {result['win_rate']:.0f}% ({result['wins']}/30)")
        print(f"  Cost: ${result['cost']:.4f}")
        print()

    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    print(f"{'Model':<15} {'Controller':<12} {'Wins':<6} {'Win %':<8} {'Cost':<10}")
    print("-" * 51)
    for r in results:
        print(f"{r['model']:<15} {r['controller']:<12} {r['wins']}/30  {r['win_rate']:>5.0f}%   ${r['cost']:.4f}")

    print()
    total_cost = sum(r['cost'] for r in results)
    print(f"Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
