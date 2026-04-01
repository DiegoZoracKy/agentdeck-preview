#!/usr/bin/env python3
"""
Hangman LLM Test with Reasoning: GPT-4o-mini with reasoning traces.

Tests tokenization blindness with ReasoningController to capture
the model's thought process behind letter guesses.

This reveals:
- Whether the model is "de-tokenizing" correctly
- What candidate words it's considering
- Why it chose specific letters

Run:
    python examples/hangman_llm_test_reasoning.py
"""

from dotenv import load_dotenv
load_dotenv()

from agentdeck import (
    AgentDeck,
    HangmanGame,
    GPTPlayer,
    ReasoningController,
    StatsTracker,
    MatchReporter,
)


def main():
    # Create Hangman game with simple words
    game = HangmanGame(
        word_list=["AGENT", "TOKEN", "BATCH", "LAYER", "NEURAL"],
        max_wrong_guesses=6,
    )

    # GPT-4o-mini with ReasoningController
    # Captures reasoning traces before each action
    player = GPTPlayer(
        name="GPT-4o-mini",
        model="gpt-4o-mini",
        controller=ReasoningController(),
    )

    # Spectators
    stats = StatsTracker()
    reporter = MatchReporter()

    print("=" * 60)
    print("Hangman LLM Test - GPT-4o-mini with Reasoning")
    print("=" * 60)
    print(f"Word list: {game.word_list}")
    print(f"Max wrong guesses: {game.max_wrong_guesses}")
    print("Controller: ReasoningController (captures thought process)")
    print("=" * 60)
    print()

    with AgentDeck(game=game, spectators=[stats, reporter]) as deck:
        results = deck.play(
            players=[player],
            matches=1,
            seed=42,
        )

    # Show results
    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)

    result = results.matches[0]
    outcome = "WIN" if result.winner else "LOSS"
    turns = result.metadata.get("turns", "?")

    print(f"Outcome: {outcome}")
    print(f"Turns: {turns}")

    if result.winner:
        print(f"Team won!")
    else:
        print(f"Team lost - word not guessed")

    # Show cost
    print()
    print("API Costs:")
    for match in results.matches:
        if match.metadata.get("player_costs"):
            for player_name, cost in match.metadata["player_costs"].items():
                print(f"  {player_name}: ${cost:.4f}")

    print()
    print("Note: Check the recordings for reasoning traces in each turn.")
    print("Location: agentdeck_runs/<session>/records/")


if __name__ == "__main__":
    main()
