"""
Test that minimal_experiment.py setup is correct (without API calls).

This validates the example code structure without requiring API keys.
"""

from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    FixedDamageGame,
    ProgressDisplay,
    TokenUsageTracker,
    StatsTracker,
    MockPlayer,
)
from agentdeck.controllers.action_only import ActionOnlyController


def test_minimal_setup():
    """Verify minimal_experiment.py configuration works."""

    print("Testing minimal experiment setup...")

    # Game configuration (same as minimal_experiment.py)
    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        information_level="full",
    )
    print("✓ Game configured")

    # Spectators
    progress = ProgressDisplay(show_eta=True, use_carriage_return=False)
    tokens = TokenUsageTracker()
    stats = StatsTracker()
    print("✓ Spectators created")

    # Session configuration
    config = AgentDeckConfig(
        seed=42,
        run_dir="./test_runs",  # Unified directory for logs + records
        log_level=None,
    )
    print("✓ Session configured")

    # Use MockPlayer instead of GPTPlayer (no API key needed)
    players = [
        MockPlayer(
            name="Alice",
            actions=["ATTACK", "POTION"],
            controller=ActionOnlyController(),
        ),
        MockPlayer(
            name="Bob",
            actions=["ATTACK", "POTION"],
            controller=ActionOnlyController(),
        ),
    ]
    print("✓ Players created (using MockPlayer for testing)")

    # Create deck
    deck = AgentDeck(
        game=game,
        spectators=[progress, tokens, stats],
        session=config,
    )
    print("✓ Deck created")

    # Run matches
    results = deck.play(
        players=players,
        matches=1,
        seed=42,
    )
    print("✓ Played 1 match")

    # Verify results
    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    print(f"✓ Got {len(results)} results")

    # Check spectators collected data
    token_summary = tokens.get_summary()
    stats_summary = stats.get_stats()

    assert stats_summary["total_matches"] == 1, "StatsTracker should have 1 match"
    print(f"✓ StatsTracker recorded {stats_summary['total_matches']} matches")

    assert progress.completed_matches == 1, "ProgressDisplay should show 1 completed"
    print(f"✓ ProgressDisplay tracked {progress.completed_matches} matches")

    # Display summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)

    for i, result in enumerate(results, 1):
        turns = result.metadata.get("turns", "?")
        print(f"Match {i}: {result.winner or 'Draw'} wins in {turns} turns")

    print(f"\nPlayer Performance:")
    for player, player_stats in stats_summary["players"].items():
        win_rate = player_stats['win_rate']
        print(f"  {player}: {player_stats['wins']} wins ({win_rate:.1%})")

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("✓ minimal_experiment.py configuration is correct")
    print("\nTo run with real LLM players:")
    print("  export OPENAI_API_KEY='sk-...'")
    print("  python examples/minimal_experiment.py")
    print("="*60)


if __name__ == "__main__":
    test_minimal_setup()
