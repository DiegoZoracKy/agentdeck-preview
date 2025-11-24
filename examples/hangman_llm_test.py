#!/usr/bin/env python3
"""
Hangman LLM Test: GPT-4o-mini cooperative match.

Tests tokenization blindness with real LLMs using only game instructions
and response format - no additional behavioral prompts.

Run:
    python examples/hangman_llm_test.py
"""

from dotenv import load_dotenv
load_dotenv()

from agentdeck import (
    AgentDeck,
    HangmanGame,
    GPTPlayer,
    ActionOnlyController,
    StatsTracker,
    MatchNarrator,
)


def main():
    # Create Hangman game with simple words
    game = HangmanGame(
        word_list=["AGENT", "TOKEN", "BATCH", "LAYER", "NEURAL"],
        max_wrong_guesses=6,
    )

    # Single GPT-4o player - minimal config
    # Only receives game.instructions and controller format
    player = GPTPlayer(
        name="GPT-4o",
        model="gpt-4o",
        controller=ActionOnlyController(),
    )

    # Spectators
    stats = StatsTracker()
    narrator = MatchNarrator()

    print("=" * 60)
    print("Hangman LLM Test - GPT-4o-mini Solo")
    print("=" * 60)
    print(f"Word list: {game.word_list}")
    print(f"Max wrong guesses: {game.max_wrong_guesses}")
    print("=" * 60)
    print()

    with AgentDeck(game=game, spectators=[stats, narrator]) as deck:
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
            for player, cost in match.metadata["player_costs"].items():
                print(f"  {player}: ${cost:.4f}")


if __name__ == "__main__":
    main()
