"""Example: Using spectators to monitor experiments."""

from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    FixedDamageGame,
    MockPlayer,
    StatsTracker,
    ProgressDisplay,
    TokenUsageTracker,
)


def main():
    """Demonstrate spectator usage for real-time monitoring."""

    # Create spectators for monitoring
    stats = StatsTracker()
    progress = ProgressDisplay(show_eta=True)
    tokens = TokenUsageTracker()

    # Configure session
    config = AgentDeckConfig(
        seed=42,
        log_dir="./logs",
        record_dir="./recordings",
        log_level=None,  # Quiet mode
    )

    # Create deck with spectators
    deck = AgentDeck(
        game=FixedDamageGame(),
        spectators=[stats, progress, tokens],  # Session spectators
        session=config,
    )

    # Create players
    players = [
        MockPlayer("Alice", actions=["ATTACK", "POTION"]),
        MockPlayer("Bob", actions=["ATTACK"]),
    ]

    print("="*60)
    print("Running 10 matches with real-time progress...")
    print("="*60)

    # Run matches - spectators will display progress automatically
    results = deck.play(players, matches=10)

    print("\n" + "="*60)
    print("Detailed Statistics")
    print("="*60)

    # Get detailed stats
    stats_summary = stats.get_stats()
    print(f"\nTotal Matches: {stats_summary['total_matches']}")
    print(f"Draws: {stats_summary['draws']}")

    if "avg_match_duration" in stats_summary:
        print(f"Average Match Duration: {stats_summary['avg_match_duration']:.2f}s")

    print("\nPlayer Performance:")
    for player, player_stats in stats_summary["players"].items():
        print(f"\n{player}:")
        print(f"  Wins: {player_stats['wins']}")
        print(f"  Losses: {player_stats['losses']}")
        print(f"  Win Rate: {player_stats['win_rate']:.1%}")
        print(f"  Total Turns: {player_stats['total_turns']}")
        print(f"  Actions: {player_stats['actions']}")

    # Token usage (would show data if using real LLM players)
    token_summary = tokens.get_summary()
    if token_summary["total"]["calls"] > 0:
        print("\n" + "="*60)
        print("Token Usage")
        print("="*60)
        print(f"Total API Calls: {token_summary['total']['calls']}")
        print(f"Total Tokens: {token_summary['total']['total_tokens']:,}")
        print(f"Total Cost: ${token_summary['total']['cost']:.4f}")
    else:
        print("\nNote: No LLM token usage (using MockPlayer)")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
