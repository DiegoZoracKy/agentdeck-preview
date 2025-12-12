"""Model comparison utilities for AgentDeck research."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..core.agentdeck import AgentDeck
from ..core.base import Game, Player, Spectator
from ..core.session import AgentDeckConfig
from ..spectators.stats import StatsTracker
from .statistical import (
    calculate_effect_size,
)


@dataclass
class ComparisonResult:
    """Result from comparing two models (per SPEC-RESEARCH v1.0.0 §5)."""

    model_a: str  # Model A identifier
    model_b: str  # Model B identifier
    game: str  # Game name
    matches: int  # Matches executed
    win_rate_a: float  # Model A win rate (0.0-1.0)
    win_rate_b: float  # Model B win rate
    draws: float  # Draw rate
    p_value: float  # Statistical significance
    statistic: float  # Test statistic (t-stat, U-stat, etc.)
    test_used: str  # "t-test", "mann-whitney", "bootstrap"
    confidence_interval: Tuple[float, float]  # 95% CI for win rate difference
    effect_size: Optional[float] = None  # Cohen's h, Cohen's d, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)  # avg_turns, costs, decision_times, etc.

    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if result is statistically significant at alpha level."""
        return self.p_value < alpha


@dataclass
class ProgressiveResult:
    """Result from progressive comparison with early stopping (per SPEC-RESEARCH v1.0.0 §5)."""

    comparisons: List[ComparisonResult]  # Intermediate results (one per check)
    stopped_early: bool  # Early stopping triggered
    total_matches: int  # Matches executed
    significance_reached_at: Optional[int] = None  # Match count when significance reached
    final_comparison: Optional[ComparisonResult] = None  # Final statistical test


@dataclass
class BenchmarkGame:
    """Game configuration for benchmark suite (per SPEC-RESEARCH v1.0.0 §5)."""

    game: Game  # Game instance
    name: str  # Human-readable name
    min_matches: Optional[int] = None  # Override benchmark default
    config: Dict[str, Any] = field(default_factory=dict)  # Game-specific params


@dataclass
class Benchmark:
    """Benchmark suite definition (per SPEC-RESEARCH v1.0.0 §5)."""

    name: str  # Benchmark identifier
    version: str  # Semantic version (for evolution)
    games: List[BenchmarkGame]  # Game scenarios
    min_matches: int = 100  # Minimum matches per game
    confidence_level: float = 0.95  # CI level
    early_stopping: bool = False  # Stop when significance reached
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result from benchmark suite execution (per SPEC-RESEARCH v1.0.0 §5)."""

    benchmark_name: str
    benchmark_version: str
    model_a: str
    model_b: str
    overall_win_rate_a: float  # Aggregate across all games
    overall_win_rate_b: float
    games_won_a: int  # Games where A had higher win rate
    games_won_b: int
    total_games: int
    game_results: List[ComparisonResult]  # Per-game results
    total_cost: Optional[float] = None  # Aggregate LLM costs
    metadata: Dict[str, Any] = field(default_factory=dict)


def compare_models(
    model_a: Player,
    model_b: Player,
    game: Game,
    matches: int = 100,
    seed: Optional[int] = None,
    *,
    test: str = "auto",
    confidence: float = 0.95,
    parallel: bool = False,
    spectators: Optional[List[Spectator]] = None,
) -> ComparisonResult:
    """
    Compare two models head-to-head with statistical rigor (per SPEC-RESEARCH v1.0.0 §4).

    Guarantees (per SPEC-RESEARCH):
    - SR3: Fair player ordering via Console's seeded Fisher-Yates shuffle per match
    - SR1: Auto-selects statistical test (t-test, Mann-Whitney, bootstrap)
    - SR2: Reports p-value, confidence interval, effect size, test name
    - RE1: Uses seed for reproducibility (Console derives per-match seeds deterministically)

    Player Ordering:
        Console randomizes first player for each match using Fisher-Yates shuffle.
        Same seed produces identical player ordering across runs. Match metadata
        includes player_order, player_order_source, and first_player fields.

    Args:
        model_a: First player (Model A)
        model_b: Second player (Model B)
        game: Game to use for comparison
        matches: Number of matches to run (default 100)
        seed: Random seed for reproducibility
        test: Statistical test ("auto", "t-test", "mann-whitney", "bootstrap")
        confidence: Confidence level (default 0.95)
        parallel: Run matches in parallel (future feature, currently ignored)
        spectators: Optional spectators to observe matches (ProgressSpectator, Narrator, etc.)

    Returns:
        ComparisonResult with win rates, p-value, CI, effect size, metadata
    """
    from .statistical import statistical_test as run_statistical_test

    # Initialize AgentDeck with seed and spectators
    deck = AgentDeck(
        game=game,
        session=AgentDeckConfig(seed=seed) if seed is not None else None,
        spectators=list(spectators) if spectators else None,
    )

    start_time = time.time()

    # Track results
    wins_a = 0
    wins_b = 0
    draws = 0
    total_turns = []
    total_cost = 0.0
    decision_times = []

    # SR3: Console applies fair player ordering (Fisher-Yates shuffle per match)
    # Run all matches in single batch (Console handles per-match randomization)
    match_results = deck.play([model_a, model_b], matches=matches)

    # Extract results from all matches
    for match in match_results.matches:
        if match.winner == model_a.name:
            wins_a += 1
        elif match.winner == model_b.name:
            wins_b += 1
        else:
            draws += 1

        # Collect metadata
        total_turns.append(len([e for e in match.events if e.type == "gameplay"]))

        # Extract cost if available
        if match.metadata and "cost" in match.metadata:
            total_cost += match.metadata["cost"]

        # Extract decision times if available
        if match.metadata and "decision_times" in match.metadata:
            decision_times.extend(match.metadata["decision_times"])

    # Calculate win rates
    win_rate_a = wins_a / matches
    win_rate_b = wins_b / matches
    draw_rate = draws / matches

    # SR1: Statistical test with auto-selection
    try:
        # Create binary outcome arrays (1 = A wins, 0 = B wins, exclude draws)
        outcomes_a = [1 if i < wins_a else 0 for i in range(wins_a + wins_b)]
        outcomes_b = [1 - o for o in outcomes_a]

        test_result = run_statistical_test(outcomes_a, outcomes_b, test=test, confidence=confidence)

        p_value = test_result.p_value
        statistic = test_result.statistic
        test_used = test_result.test_used
        ci = test_result.confidence_interval

        # SR4: Calculate effect size (Cohen's h for proportion differences)
        # Compare A vs B win rates (exclude draws from denominator)
        effect_size = calculate_effect_size(win_rate_a, win_rate_b, wins_a + wins_b)

    except ImportError:
        # Fallback when scipy not available
        p_value = 1.0
        statistic = 0.0
        test_used = "none"
        ci = (0.0, 0.0)
        effect_size = None

    # Metadata
    elapsed_time = time.time() - start_time
    avg_turns = sum(total_turns) / len(total_turns) if total_turns else 0
    avg_decision_time = sum(decision_times) / len(decision_times) if decision_times else None

    metadata = {
        "avg_turns": avg_turns,
        "total_cost": total_cost,
        "avg_cost_per_match": total_cost / matches if matches > 0 else 0,
        "avg_decision_time": avg_decision_time,
        "elapsed_time": elapsed_time,
        "seed": seed,
    }

    return ComparisonResult(
        model_a=model_a.name,
        model_b=model_b.name,
        game=game.__class__.__name__,
        matches=matches,
        win_rate_a=win_rate_a,
        win_rate_b=win_rate_b,
        draws=draw_rate,
        p_value=p_value,
        statistic=statistic,
        test_used=test_used,
        confidence_interval=ci,
        effect_size=effect_size,
        metadata=metadata,
    )


def compare_models_progressive(
    model_a: Player,
    model_b: Player,
    game: Game,
    min_matches: int = 30,
    max_matches: int = 500,
    alpha: float = 0.05,
    check_interval: int = 10,
    seed: Optional[int] = None,
    *,
    spectators: Optional[List[Spectator]] = None,
) -> ProgressiveResult:
    """
    Progressive comparison with early stopping (per SPEC-RESEARCH v1.0.0 §4).

    Guarantees (per SPEC-RESEARCH):
    - PT1: Runs min_matches before checking significance
    - PT2: Checks significance every check_interval matches
    - PT3: Records stopping decision (early vs max_matches)
    - PT4: Respects max_matches cap even if significance not reached

    Args:
        model_a: First player (Model A)
        model_b: Second player (Model B)
        game: Game to use for comparison
        min_matches: Minimum matches before checking (default 30)
        max_matches: Maximum matches to run (default 500)
        alpha: Significance threshold (default 0.05)
        check_interval: Check every N matches (default 10)
        seed: Random seed for reproducibility
        spectators: Optional spectators to observe matches throughout the progressive run

    Returns:
        ProgressiveResult with intermediate comparisons and stopping metadata
    """
    # Initialize AgentDeck with seed
    deck = AgentDeck(
        game=game,
        session=AgentDeckConfig(seed=seed) if seed is not None else None,
        spectators=list(spectators) if spectators else None,
    )

    # Track results
    wins_a = 0
    wins_b = 0
    draws = 0
    matches_played = 0
    total_turns = []
    total_cost = 0.0
    decision_times = []

    comparisons = []  # Intermediate ComparisonResult objects
    stopped_early = False
    significance_reached_at = None

    # PT1 & PT4: Run matches until min_matches, then check at intervals until max_matches
    while matches_played < max_matches:
        # Determine batch size (check_interval or remaining to reach min_matches)
        if matches_played < min_matches:
            batch_size = min(check_interval, min_matches - matches_played)
        else:
            batch_size = check_interval

        # SR3: Console applies fair player ordering (Fisher-Yates shuffle per match)
        # Run batch of matches (Console handles per-match randomization)
        batch_results = deck.play([model_a, model_b], matches=batch_size)

        # Extract results from batch
        for match in batch_results.matches:
            if match.winner == model_a.name:
                wins_a += 1
            elif match.winner == model_b.name:
                wins_b += 1
            else:
                draws += 1

            # Collect metadata
            total_turns.append(len([e for e in match.events if e.type == "gameplay"]))

            if match.metadata and "cost" in match.metadata:
                total_cost += match.metadata["cost"]

            if match.metadata and "decision_times" in match.metadata:
                decision_times.extend(match.metadata["decision_times"])

        matches_played += batch_size

        # PT2: Check significance after min_matches and at intervals
        if matches_played >= min_matches:
            # Create intermediate comparison result
            win_rate_a = wins_a / matches_played
            win_rate_b = wins_b / matches_played
            draw_rate = draws / matches_played

            # Run statistical test
            try:
                from .statistical import statistical_test as run_statistical_test

                outcomes_a = [1 if i < wins_a else 0 for i in range(wins_a + wins_b)]
                outcomes_b = [1 - o for o in outcomes_a]

                test_result = run_statistical_test(
                    outcomes_a, outcomes_b, test="auto", confidence=0.95
                )

                p_value = test_result.p_value
                statistic = test_result.statistic
                test_used = test_result.test_used
                ci = test_result.confidence_interval

                effect_size = calculate_effect_size(win_rate_a, win_rate_b, wins_a + wins_b)

            except ImportError:
                p_value = 1.0
                statistic = 0.0
                test_used = "none"
                ci = (0.0, 0.0)
                effect_size = None

            # Create intermediate comparison
            avg_turns = sum(total_turns) / len(total_turns) if total_turns else 0
            avg_decision_time = (
                sum(decision_times) / len(decision_times) if decision_times else None
            )

            intermediate = ComparisonResult(
                model_a=model_a.name,
                model_b=model_b.name,
                game=game.__class__.__name__,
                matches=matches_played,
                win_rate_a=win_rate_a,
                win_rate_b=win_rate_b,
                draws=draw_rate,
                p_value=p_value,
                statistic=statistic,
                test_used=test_used,
                confidence_interval=ci,
                effect_size=effect_size,
                metadata={
                    "avg_turns": avg_turns,
                    "total_cost": total_cost,
                    "avg_cost_per_match": total_cost / matches_played if matches_played > 0 else 0,
                    "avg_decision_time": avg_decision_time,
                    "seed": seed,
                },
            )

            comparisons.append(intermediate)

            # PT3: Check if significance reached
            if p_value < alpha:
                stopped_early = True
                significance_reached_at = matches_played
                break

    # Create final comparison (same as last intermediate or final state)
    final_comparison = comparisons[-1] if comparisons else None

    return ProgressiveResult(
        comparisons=comparisons,
        stopped_early=stopped_early,
        total_matches=matches_played,
        significance_reached_at=significance_reached_at,
        final_comparison=final_comparison,
    )


def run_benchmark(
    benchmark: Benchmark, model_a: Player, model_b: Player, seed: Optional[int] = None
) -> BenchmarkResult:
    """
    Execute benchmark suite (per SPEC-RESEARCH v1.0.0 §4).

    Guarantees:
    - Runs all games in benchmark
    - Aggregates results across games (overall win rate, games won)
    - Records benchmark version for reproducibility

    Args:
        benchmark: Benchmark suite definition
        model_a: First player (Model A)
        model_b: Second player (Model B)
        seed: Random seed for reproducibility

    Returns:
        BenchmarkResult with per-game and aggregate results
    """
    game_results = []
    total_wins_a = 0
    total_wins_b = 0
    total_cost = 0.0

    # Run each game in benchmark
    for bench_game in benchmark.games:
        # Use game-specific min_matches or benchmark default
        min_matches = (
            bench_game.min_matches if bench_game.min_matches is not None else benchmark.min_matches
        )

        # Run comparison (with early stopping if enabled)
        if benchmark.early_stopping:
            progressive_result = compare_models_progressive(
                model_a=model_a,
                model_b=model_b,
                game=bench_game.game,
                min_matches=min_matches,
                max_matches=min_matches * 5,  # Cap at 5x min_matches
                alpha=1 - benchmark.confidence_level,
                seed=seed,
            )
            game_result = progressive_result.final_comparison
        else:
            game_result = compare_models(
                model_a=model_a,
                model_b=model_b,
                game=bench_game.game,
                matches=min_matches,
                seed=seed,
                confidence=benchmark.confidence_level,
            )

        game_results.append(game_result)

        # Track which game "won" (higher win rate)
        if game_result.win_rate_a > game_result.win_rate_b:
            total_wins_a += 1
        elif game_result.win_rate_b > game_result.win_rate_a:
            total_wins_b += 1

        # Aggregate cost
        if "total_cost" in game_result.metadata:
            total_cost += game_result.metadata["total_cost"]

    # Calculate overall win rates (aggregate across all games)
    overall_win_rate_a = (
        sum(gr.win_rate_a for gr in game_results) / len(game_results) if game_results else 0
    )
    overall_win_rate_b = (
        sum(gr.win_rate_b for gr in game_results) / len(game_results) if game_results else 0
    )

    return BenchmarkResult(
        benchmark_name=benchmark.name,
        benchmark_version=benchmark.version,
        model_a=model_a.name,
        model_b=model_b.name,
        overall_win_rate_a=overall_win_rate_a,
        overall_win_rate_b=overall_win_rate_b,
        games_won_a=total_wins_a,
        games_won_b=total_wins_b,
        total_games=len(benchmark.games),
        game_results=game_results,
        total_cost=total_cost if total_cost > 0 else None,
        metadata={"seed": seed, "benchmark_metadata": benchmark.metadata},
    )


class ComparisonResults:
    """Results from model comparison with analysis methods."""

    def __init__(self, data: Dict[str, Any], stats_tracker: StatsTracker):
        """Initialize with comparison data."""
        self.data = data
        self.stats_tracker = stats_tracker

    def print_summary(self):
        """Print formatted summary of results."""
        print("\n" + "=" * 60)
        print("MODEL COMPARISON RESULTS")
        print("=" * 60)
        print(f"Total Matches: {self.data['total_matches']}")
        print(f"Elapsed Time: {self.data['elapsed_time']:.2f}s")

        print("\n" + "-" * 60)
        print("WIN RATES")
        print("-" * 60)

        # Sort by win rate
        sorted_players = sorted(self.data["win_rates"].items(), key=lambda x: x[1], reverse=True)

        for player, rate in sorted_players:
            print(f"{player:20} {rate:6.1%}", end="")

            # Add confidence interval if available
            if player in self.data["confidence_intervals"]:
                ci = self.data["confidence_intervals"][player]
                print(f" (95% CI: {ci[0]:.1%} - {ci[1]:.1%})", end="")

            # Add p-value if available
            if player in self.data["p_values"]:
                p = self.data["p_values"][player]
                if p < 0.001:
                    print(" ***", end="")
                elif p < 0.01:
                    print(" **", end="")
                elif p < 0.05:
                    print(" *", end="")

            print()

        if self.data["p_values"]:
            print("\n* p < 0.05, ** p < 0.01, *** p < 0.001")

        # Show early stopping info if applicable
        if self.data.get("early_stopped"):
            print(f"\n[Early stopped: {self.data['early_stop_reason']}]")

        print("=" * 60)

    def plot_matrix(self):
        """Plot win rate matrix (requires matplotlib)."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            print("Matplotlib not installed. Cannot create plot.")
            return

        # Extract unique players
        players = list(self.data["win_rates"].keys())
        n = len(players)

        # Create matrix
        matrix = np.zeros((n, n))
        for i, p1 in enumerate(players):
            for j, p2 in enumerate(players):
                if i == j:
                    matrix[i, j] = 0.5  # Self vs self
                else:
                    key1 = f"{p1}_vs_{p2}"
                    key2 = f"{p2}_vs_{p1}"

                    if key1 in self.data["matchups"]:
                        matches = self.data["matchups"][key1]
                        if hasattr(matches, "matches") and len(matches.matches) > 0:
                            wins = sum(1 for m in matches.matches if m.winner == p1)
                            matrix[i, j] = wins / len(matches.matches)
                    elif key2 in self.data["matchups"]:
                        matches = self.data["matchups"][key2]
                        if hasattr(matches, "matches") and len(matches.matches) > 0:
                            wins = sum(1 for m in matches.matches if m.winner == p1)
                            matrix[i, j] = wins / len(matches.matches)

        # Create heatmap
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1)

        # Set ticks
        ax.set_xticks(np.arange(n))
        ax.set_yticks(np.arange(n))
        ax.set_xticklabels(players)
        ax.set_yticklabels(players)

        # Rotate labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        # Add colorbar
        plt.colorbar(im)

        # Add title
        ax.set_title("Win Rate Matrix")

        plt.tight_layout()
        plt.show()

    def to_latex(self) -> str:
        """Generate LaTeX table for papers."""
        lines = []
        lines.append("\\begin{table}[h]")
        lines.append("\\centering")
        lines.append("\\begin{tabular}{lcc}")
        lines.append("\\hline")
        lines.append("Model & Win Rate & 95\\% CI \\\\")
        lines.append("\\hline")

        sorted_players = sorted(self.data["win_rates"].items(), key=lambda x: x[1], reverse=True)

        for player, rate in sorted_players:
            ci_str = ""
            if player in self.data["confidence_intervals"]:
                ci = self.data["confidence_intervals"][player]
                ci_str = f"[{ci[0]:.3f}, {ci[1]:.3f}]"

            lines.append(f"{player} & {rate:.3f} & {ci_str} \\\\")

        lines.append("\\hline")
        lines.append("\\end{tabular}")
        lines.append("\\caption{Model Comparison Results}")
        lines.append("\\end{table}")

        return "\n".join(lines)
