#!/usr/bin/env python3
"""
Hangman LLM Test: GPT-4o with ReasoningController.

Compares GPT-4o's reasoning against GPT-4o-mini on tokenization blindness.

Run:
    python examples/hangman_gpt4o_reasoning.py
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
    game = HangmanGame(
        word_list=["AGENT", "TOKEN", "BATCH", "LAYER", "NEURAL"],
        max_wrong_guesses=6,
    )

    player = GPTPlayer(
        name="GPT-4o",
        model="gpt-4o",
        controller=ReasoningController(),
    )

    stats = StatsTracker()
    reporter = MatchReporter()

    print("=" * 60)
    print("Hangman LLM Test - GPT-4o with Reasoning")
    print("=" * 60)
    print(f"Word list: {game.word_list}")
    print(f"Max wrong guesses: {game.max_wrong_guesses}")
    print("Controller: ReasoningController")
    print("=" * 60)
    print()

    with AgentDeck(game=game, spectators=[stats, reporter]) as deck:
        results = deck.play(
            players=[player],
            matches=1,
            seed=42,
        )

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
        print("Team won!")
    else:
        print("Team lost - word not guessed")

    print()
    print("API Costs:")
    for match in results.matches:
        if match.metadata.get("player_costs"):
            for player_name, cost in match.metadata["player_costs"].items():
                print(f"  {player_name}: ${cost:.4f}")


if __name__ == "__main__":
    main()
