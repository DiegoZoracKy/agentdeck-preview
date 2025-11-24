"""
AgentDeck: Minimal Configuration Example

Purpose:
    Demonstrate that researchers can run experiments with absolute minimal configuration.
    Smart defaults handle templates, controllers, and rendering automatically.

Usage:
    export OPENAI_API_KEY="sk-..."
    python examples/minimal_experiment.py

What This Demonstrates:
    ✓ Zero template configuration (smart defaults used)
    ✓ Zero extras needed (baseline experiment)
    ✓ Minimal player setup (just controller required)
    ✓ Out-of-the-box three-phase lifecycle (handshake → turn → conclusion)
    ✓ Real-time progress monitoring with spectators
    ✓ Automatic cost tracking

Smart Defaults Used (SPEC-PLAYER v1.0.0):
    handshake_controller: HandshakeController(accepted=["OK", "READY", "YES"])
    renderer: TextRenderer()
    prompt_builder: PromptBuilder() with default templates
    handshake_template: System-provided default
    turn_template: "{game_view}"
    conclusion_template: None (optional phase)

Note: {player_instructions} renders as empty string when not in extras (no error).
"""

import os
from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    FixedDamageGame,
    ProgressDisplay,
    TokenUsageTracker,
    StatsTracker,
)
from agentdeck.players.openai_player import GPTPlayer
from agentdeck.controllers.action_only import ActionOnlyController


def main():
    """
    Run FixedDamageGame with absolute minimal configuration.

    This is the simplest possible setup - just game + players + controller.
    Everything else uses smart defaults. No custom templates, no extras.
    """

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='sk-...'")
        return

    print("="*60)
    print("AgentDeck Minimal Configuration Example")
    match_count = 3
    print("="*60)
    print(f"\nRunning {match_count} matches with GPT-4o-mini players...")
    print("Using default templates and smart defaults\n")

    # Game configuration
    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        information_level="full",
    )

    # Spectators for monitoring (optional but recommended)
    progress = ProgressDisplay(show_eta=True, use_carriage_return=False)
    tokens = TokenUsageTracker()
    stats = StatsTracker()

    # Session configuration
    config = AgentDeckConfig(
        seed=42,
        log_dir="./logs",
        record_dir="./recordings",
        # log_level defaults to LogLevel.INFO (stdout summaries)
        # log_file_levels defaults to None (creates both info.log and debug.log)
    )

    # Minimal players - only required: name, model, controller
    # All other components use smart defaults:
    # - handshake_controller: HandshakeController()
    # - renderer: TextRenderer()
    # - prompt_builder: PromptBuilder() with default templates
    players = [
        GPTPlayer(
            name="Alice",
            model="gpt-4o-mini",
            temperature=0.7,
            controller=ActionOnlyController(),
        ),
        GPTPlayer(
            name="Bob",
            model="gpt-4o-mini",
            temperature=0.7,
            controller=ActionOnlyController(),
        ),
    ]

    # Run experiment
    deck = AgentDeck(
        game=game,
        spectators=[progress, tokens, stats],
        session=config,
    )

    results = deck.play(
        players=players,
        matches=match_count,
        seed=42,
    )

    # Display results
    print("\n" + "="*60)
    print("Results")
    print("="*60)

    for i, result in enumerate(results, 1):
        turns = result.metadata.get("turns", "?")
        print(f"\nMatch {i}: {result.winner or 'Draw'} wins in {turns} turns")

    # Display token usage
    print("\n" + "="*60)
    print("Token Usage Summary")
    print("="*60)

    token_summary = tokens.get_summary()
    total = token_summary["total"]

    print(f"\nTotal API Calls: {total['calls']}")
    print(f"Total Tokens: {total['total_tokens']:,}")
    print(f"  - Prompt: {total['prompt_tokens']:,}")
    print(f"  - Completion: {total['completion_tokens']:,}")
    print(f"Total Cost: ${total['cost']:.4f}")

    if token_summary["per_player"]:
        print("\nPer-Player Usage:")
        for player, player_stats in token_summary["per_player"].items():
            print(f"  {player}:")
            print(f"    Calls: {player_stats['calls']}")
            print(f"    Tokens: {player_stats['total_tokens']:,}")
            print(f"    Cost: ${player_stats['cost']:.4f}")

    # Display match statistics
    print("\n" + "="*60)
    print("Match Statistics")
    print("="*60)

    stats_summary = stats.get_stats()
    print(f"\nTotal Matches: {stats_summary['total_matches']}")
    print(f"Average Match Duration: {stats_summary.get('avg_match_duration', 0):.2f}s")

    print("\nPlayer Performance:")
    for player, player_stats in stats_summary["players"].items():
        win_rate = player_stats['win_rate']
        print(f"\n{player}:")
        print(f"  Wins: {player_stats['wins']}")
        print(f"  Losses: {player_stats['losses']}")
        print(f"  Win Rate: {win_rate:.1%}")

    print("\n" + "="*60)
    print("\n✓ Experiment complete!")
    print("✓ All components used smart defaults")
    print("✓ Zero template configuration required")
    print("✓ Recordings saved to ./recordings/")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
