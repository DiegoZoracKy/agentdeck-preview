"""
AgentDeck Zero-Dependency Demo

Purpose:
    Run AgentDeck end-to-end with no API keys or external SDKs. Uses MockPlayer
    for deterministic actions so you can verify install, recording, and
    spectator output locally.

Usage:
    python examples/mock_demo.py

What You'll See:
    - MatchNarrator commentary for each turn
    - ProgressDisplay updates (no carriage returns for clean logs)
    - StatsTracker win/loss summary
    - Recordings saved under agentdeck_runs/mock_demo/<session>/records/
"""

from pathlib import Path

from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    FixedDamageGame,
    LogLevel,
    MatchNarrator,
    MockPlayer,
    ProgressDisplay,
    Recorder,
    StatsTracker,
)


def main() -> None:
    """Run a small mock experiment with deterministic actions."""
    game = FixedDamageGame(
        max_health=60,
        attack_damage=15,
        potion_heal=20,
        starting_potions=1,
        information_level="full",
    )

    # Deterministic players: actions cycle in order provided
    players = [
        MockPlayer(name="Alice", actions=["ATTACK", "ATTACK", "POTION"]),
        MockPlayer(name="Bob", actions=["POTION", "ATTACK", "ATTACK"]),
    ]

    # Keep artifacts contained under agentdeck_runs/mock_demo
    config = AgentDeckConfig(
        seed=7,
        run_dir="agentdeck_runs/mock_demo",
        log_level=LogLevel.INFO,
    )

    # Spectators for human-friendly output + recording
    narrator = MatchNarrator()
    progress = ProgressDisplay(show_eta=False, use_carriage_return=False)
    stats = StatsTracker()
    recorder = Recorder()  # Auto-bound to session; writes JSON recordings

    match_count = 3

    with AgentDeck(
        game=game,
        spectators=[narrator, progress, stats],
        recorder=recorder,
        session=config,
    ) as deck:
        print("=" * 60)
        print("AgentDeck Mock Demo (no API keys required)")
        print("=" * 60)
        print(f"Running {match_count} matches with deterministic players...\n")

        results = deck.play(players=players, matches=match_count)

        print("\n" + "=" * 60)
        print("Results")
        print("=" * 60)
        for i, result in enumerate(results, start=1):
            turns = result.metadata.get("turns", "?")
            print(f"Match {i}: {result.winner or 'Draw'} wins in {turns} turns (seed={result.seed})")

        stats_summary = stats.get_stats()
        print("\nMatch Statistics:")
        print(f"  Total Matches: {stats_summary['total_matches']}")
        for name, info in stats_summary["players"].items():
            print(f"  {name}: {info['wins']}W/{info['losses']}L  (win rate {info['win_rate']:.0%})")

        # Surface recording location for easy inspection
        record_dir = Path(deck.session.record_directory)
        session_root = record_dir.parent
        latest_recordings = sorted(record_dir.glob("match_*.json"))

        print("\nArtifacts:")
        print(f"  Session root: {session_root}")
        print(f"  Logs:        {deck.session.log_directory}")
        print(f"  Recordings:  {record_dir}")
        if latest_recordings:
            print(f"  Latest match file: {latest_recordings[-1]}")
        print("\nOpen a recording JSON to see prompt/response payloads.")

    print("\n✓ Done. No API calls were made.")


if __name__ == "__main__":
    main()
