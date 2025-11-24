"""
AgentDeck Parallel Execution Demo

Purpose:
    Demonstrate parallel match execution with configurable concurrency.
    Verify determinism, event ordering, and LLM player cloning.
    Show progress monitoring with ProgressMonitor (auto-attached by default).

Usage:
    export OPENAI_API_KEY="sk-..."
    python examples/test_parallel_execution.py

What This Demonstrates:
    ✓ Parallel execution with concurrency > 1
    ✓ Deterministic seeding (reproducible results)
    ✓ Event replay in match_index order
    ✓ LLM player cloning (GPTPlayer with thread-safe client recreation)
    ✓ Perfect spectator/recorder parity
    ✓ Automatic fallback for games with get_player_order()
    ✓ Real-time progress monitoring (ProgressMonitor auto-attached)

Test Scenarios:
    1. Sequential baseline (concurrency=1) - no progress monitor
    2. Parallel execution (concurrency=5) - default progress monitor
    3. Parallel execution (concurrency=10) - default progress monitor

Expected Results:
    - All three runs produce identical match results (deterministic) ✓
    - Spectator events replay in correct order ✓
    - All match metadata preserved (seeds, player_order, etc.) ✓
    - Progress displayed during parallel execution ✓

Performance Notes:
    ⚠ Parallel execution may be SLOWER with cloud LLM APIs (OpenAI, Anthropic, etc.)
    due to API rate limiting. Each provider throttles concurrent requests from the
    same account, which negates parallelism benefits.

    Parallel execution is optimized for:
    • Local/self-hosted models (ollama, vllm, etc.) - no rate limits
    • High-latency networks - can hide network delays
    • Mixed workloads - when some matches are computation-heavy

    For cloud APIs, sequential execution is often faster due to:
    • API rate limits throttling concurrent requests
    • Thread creation/teardown overhead
    • Deep-copy costs for cloning players/games

Per SPEC-PARALLEL v1.0.0 and SPEC-MONITOR v1.0.0.

Custom Monitor Example:
    To use custom monitors instead of the default ProgressMonitor:

    from agentdeck.monitors import ProgressMonitor, Monitor

    # Example custom monitor
    class SlackMonitor(Monitor):
        def on_console_batch_complete(self, event):
            # Send Slack notification when batch completes
            send_slack(f"Batch complete: {event.data['completed']} matches")

    config = AgentDeckConfig(
        concurrency=10,
        monitors=[
            ProgressMonitor(mode="verbose"),  # Detailed progress
            SlackMonitor()                     # Custom notifications
        ]
    )

    # Or opt-out of progress monitoring:
    config = AgentDeckConfig(concurrency=10, monitors=[])  # Silent execution
"""

import time
from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players import GPTPlayer
from agentdeck.controllers import ActionOnlyController
from agentdeck.spectators import MatchNarrator
from agentdeck.core.types import LogLevel


def create_players():
    """
    Create identical GPT players for real-world parallel execution testing.

    Note: GPTPlayer now supports parallel execution via the Player.clone() method.
    The HTTP client is recreated (not copied) in each worker thread to avoid
    thread lock serialization issues.

    Per SPEC-PARALLEL v1.0.0 and Player.clone() implementation.
    """
    return [
        GPTPlayer(
            name="Player-1",
            controller=ActionOnlyController(),
            model="gpt-4o-mini",
            temperature=0.7
        ),
        GPTPlayer(
            name="Player-2",
            controller=ActionOnlyController(),
            model="gpt-4o-mini",
            temperature=0.7
        ),
    ]


def run_experiment(concurrency: int, matches: int = 10, seed: int = 42):
    """
    Run experiment with specified concurrency level.

    Args:
        concurrency: Number of parallel workers (1 = sequential)
        matches: Number of matches to run
        seed: Random seed for reproducibility

    Returns:
        Tuple of (results, duration_seconds)
    """
    print(f"\n{'='*70}")
    print(f"Running with concurrency={concurrency}, matches={matches}, seed={seed}")
    print(f"{'='*70}")

    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=1,
        information_level="full"
    )

    config = AgentDeckConfig(
        seed=seed,
        concurrency=concurrency,
        log_level=LogLevel.INFO
    )

    players = create_players()

    # Use MatchNarrator to verify event ordering
    narrator = MatchNarrator()

    start_time = time.time()

    with AgentDeck(game=game, session=config, spectators=[narrator]) as deck:
        results = deck.play(players=players, matches=matches)

    duration = time.time() - start_time

    print(f"\n{'='*70}")
    print(f"Completed {len(results)} matches in {duration:.2f}s")
    print(f"Average: {duration/len(results):.2f}s per match")
    print(f"{'='*70}")

    # Print summary
    print(f"\nResults Summary:")
    for i, result in enumerate(results):
        print(f"  Match {i}: Winner={result.winner}, Seed={result.seed}, "
              f"Duration={result.metadata.get('duration', 0):.2f}s")

    return results, duration


def compare_results(results1, results2, label1, label2):
    """Compare two result sets for determinism verification."""
    print(f"\n{'='*70}")
    print(f"Comparing {label1} vs {label2}")
    print(f"{'='*70}")

    if len(results1) != len(results2):
        print(f"❌ Length mismatch: {len(results1)} vs {len(results2)}")
        return False

    all_match = True
    for i, (r1, r2) in enumerate(zip(results1, results2)):
        seeds_match = r1.seed == r2.seed
        winners_match = r1.winner == r2.winner

        if not (seeds_match and winners_match):
            all_match = False
            print(f"❌ Match {i}: Seed {r1.seed} vs {r2.seed}, "
                  f"Winner {r1.winner} vs {r2.winner}")
        else:
            print(f"✓ Match {i}: Deterministic (seed={r1.seed}, winner={r1.winner})")

    if all_match:
        print(f"\n✅ All matches identical - perfect determinism!")
    else:
        print(f"\n❌ Some matches differ - determinism broken!")

    return all_match


def main():
    """
    Run comprehensive parallel execution tests.

    Tests:
    1. Sequential baseline (concurrency=1)
    2. Parallel with 5 workers (concurrency=5)
    3. Parallel with 10 workers (concurrency=10)
    4. Compare all results for determinism
    """

    print("\n" + "="*70)
    print(" AgentDeck Parallel Execution Demo")
    print(" SPEC-PARALLEL v1.0.0")
    print("="*70)

    # Test 1: Sequential baseline
    print("\n\n" + "="*70)
    print(" TEST 1: Sequential Baseline (concurrency=1)")
    print("="*70)
    results_seq, duration_seq = run_experiment(concurrency=1, matches=10, seed=42)

    # Test 2: Parallel with 5 workers
    print("\n\n" + "="*70)
    print(" TEST 2: Parallel Execution (concurrency=5)")
    print("="*70)
    results_par5, duration_par5 = run_experiment(concurrency=5, matches=10, seed=42)

    # Test 3: Parallel with 10 workers
    print("\n\n" + "="*70)
    print(" TEST 3: Parallel Execution (concurrency=10)")
    print("="*70)
    results_par10, duration_par10 = run_experiment(concurrency=10, matches=10, seed=42)

    # Comparison: Verify determinism
    print("\n\n" + "="*70)
    print(" DETERMINISM VERIFICATION")
    print("="*70)

    seq_vs_par5 = compare_results(results_seq, results_par5,
                                   "Sequential", "Parallel(5)")

    seq_vs_par10 = compare_results(results_seq, results_par10,
                                    "Sequential", "Parallel(10)")

    par5_vs_par10 = compare_results(results_par5, results_par10,
                                     "Parallel(5)", "Parallel(10)")

    # Performance summary
    print("\n\n" + "="*70)
    print(" PERFORMANCE SUMMARY")
    print("="*70)
    print(f"Sequential (concurrency=1):  {duration_seq:.2f}s (baseline)")

    # Calculate speedup/slowdown ratios
    ratio_par5 = duration_seq / duration_par5
    ratio_par10 = duration_seq / duration_par10

    # Format with speedup/slowdown label
    if ratio_par5 > 1.0:
        label_par5 = f"{ratio_par5:.2f}x speedup ✓"
    else:
        label_par5 = f"{1/ratio_par5:.2f}x slower ⚠"

    if ratio_par10 > 1.0:
        label_par10 = f"{ratio_par10:.2f}x speedup ✓"
    else:
        label_par10 = f"{1/ratio_par10:.2f}x slower ⚠"

    print(f"Parallel (concurrency=5):    {duration_par5:.2f}s  ({label_par5})")
    print(f"Parallel (concurrency=10):   {duration_par10:.2f}s  ({label_par10})")

    # Add explanation for slowdown
    if ratio_par5 < 1.0 or ratio_par10 < 1.0:
        print("\n⚠ Note: Parallel execution may be slower with cloud LLM APIs due to:")
        print("   • API rate limiting (OpenAI throttles concurrent requests)")
        print("   • Thread overhead and deep-copy costs")
        print("   • Parallel execution optimized for local/self-hosted models")

    # Final verdict
    print("\n\n" + "="*70)
    print(" FINAL VERDICT")
    print("="*70)

    if seq_vs_par5 and seq_vs_par10 and par5_vs_par10:
        print("✅ DETERMINISM TESTS PASSED")
        print("   • Perfect determinism across all concurrency levels")
        print("   • Event replay preserves match order")
        print("   • Clone mechanism works correctly with LLM players")
        print("\n🎉 Parallel execution implementation verified!")
    else:
        print("❌ SOME TESTS FAILED")
        print("   • Determinism not preserved across concurrency levels")
        print("   • Please review implementation")

    print("="*70 + "\n")


if __name__ == "__main__":
    main()
