#!/usr/bin/env python3
"""
Hangman Demo: Cooperative word-guessing with MockPlayers.

This example demonstrates:
1. Cooperative multiplayer Hangman
2. Character-level reasoning challenges for LLMs
3. Using spectators to observe behavior

Research Focus:
    Tests "tokenization blindness" - LLMs see words as tokens, not letters.
    This exposes character-level reasoning limitations.

Run:
    python examples/hangman_demo.py

No API keys required - uses deterministic MockPlayers.
"""

from agentdeck import (
    AgentDeck,
    HangmanGame,
    MockPlayer,
    StatsTracker,
    MatchNarrator,
)


def main():
    # Create Hangman game with custom word list
    game = HangmanGame(
        word_list=["NEURAL", "AGENT", "TOKEN", "LAYER", "BATCH"],
        max_wrong_guesses=6,
    )

    # Create cooperative players with predefined guesses
    # Good strategy: frequency-based (E, T, A, O, I, N, S, R)
    # Actions must match ActionOnlyController format: "ACTION: X"
    alice = MockPlayer(
        name="Alice",
        actions=[f"ACTION: {c}" for c in ["E", "T", "A", "O", "I", "N", "S", "R", "L", "U", "Y", "G", "B"]],
    )

    # Bob uses a different pattern
    bob = MockPlayer(
        name="Bob",
        actions=[f"ACTION: {c}" for c in ["E", "A", "R", "N", "T", "O", "L", "S", "U", "K", "Y", "H", "C"]],
    )

    # Spectators to observe the game
    stats = StatsTracker()
    narrator = MatchNarrator()

    # Run matches
    print("=" * 60)
    print("Cooperative Hangman Demo")
    print("=" * 60)
    print(f"Word list: {game.word_list}")
    print(f"Max wrong guesses: {game.max_wrong_guesses}")
    print("=" * 60)
    print()

    with AgentDeck(game=game, spectators=[stats, narrator]) as deck:
        results = deck.play(
            players=[alice, bob],
            matches=5,
            seed=42,
        )

    # Show results
    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"Matches played: {len(results.matches)}")

    wins = sum(1 for r in results.matches if r.winner is not None)
    losses = sum(1 for r in results.matches if r.winner is None)

    print(f"Team wins: {wins}")
    print(f"Team losses: {losses}")
    print(f"Win rate: {wins / len(results.matches) * 100:.1f}%")
    print()

    # Detailed match breakdown
    print("Match Details:")
    for i, result in enumerate(results.matches, 1):
        outcome = "WIN" if result.winner else "LOSS"
        turns = result.metadata.get("turns", "?")
        print(f"  Match {i}: {outcome} in {turns} turns")


def research_experiment():
    """
    Extended example showing how to study LLM behavior with Hangman.

    Replace MockPlayers with LLM players to test:
    - Tokenization blindness across models
    - Character-level reasoning differences
    - Cooperation patterns
    """
    from agentdeck import GPTPlayer, ClaudePlayer, ActionOnlyController

    game = HangmanGame(
        word_list=["TRANSFORMER", "EMBEDDING", "ATTENTION", "GRADIENT"],
        max_wrong_guesses=8,
    )

    # Compare GPT-4 vs Claude on character reasoning
    # Hypothesis: Stronger reasoning models handle this better
    gpt4 = GPTPlayer(
        name="GPT-4",
        model="gpt-4",
        controller=ActionOnlyController(),
    )

    claude = ClaudePlayer(
        name="Claude",
        model="claude-3-sonnet-20240229",
        controller=ActionOnlyController(),
    )

    with AgentDeck(game=game) as deck:
        results = deck.play(
            players=[gpt4, claude],
            matches=10,
            seed=123,
        )

    # Analyze results for tokenization blindness indicators:
    # - Hallucinated letters (guessing letters not in pattern)
    # - Duplicate guesses (context window failures)
    # - Win rate by model
    return results


if __name__ == "__main__":
    main()

    # Uncomment to run LLM experiment (requires API keys):
    # research_experiment()
