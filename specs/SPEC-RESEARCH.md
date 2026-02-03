# SPEC-RESEARCH: Analysis & Statistical Testing Contract

> Status: Final
> Version: 1.1.0
> Last Updated: 2026-02-03
> Implementation: ✅ Complete (I^2 heterogeneity currently reported as 0.0)
> Authors: Diego ZoracKy, Codex, Claude (consensus)
> Audience: Research engineers, data scientists, AI practitioners

## 1. Purpose
- Provide standardized utilities for analyzing match results, comparing models, and computing statistical significance for AI agent research.
- Guarantee statistical rigor via proper test selection (t-test, Mann-Whitney, bootstrap) with confidence interval reporting for publication-ready results.
- Enable progressive testing with early stopping to minimize API costs while maintaining statistical validity.
- **[v1.1.0]** Enable post-hoc statistical analysis from recorded sessions, allowing researchers to analyze experiments hours/days after execution without re-running matches.

## 2. Scope & Philosophy Alignment
- Supports `SPEC.md` §1.1 success criteria (built-in statistical analysis tools).
- Grounded in `SPEC.md` §2.4: data-driven iteration via comprehensive metrics and reproducible benchmarks.
- Maintains separation of concerns: research utilities consume `MatchResults` and recorder outputs, never influence live execution.
- **Clean slate design**: v1.0.0 assumes modern recorder schema (SPEC-RECORDER v1.3.0) with complete metadata capture—no legacy format compatibility, no backward compatibility shims.
- **Statistical transparency**: All comparisons MUST report p-values, confidence intervals, test selection, and effect sizes for reproducibility.
- Non-goals: match execution (`SPEC-CONSOLE.md`), data recording (`SPEC-RECORDER.md`), live visualization frameworks.

## 3. Responsibilities
- **Results summarization**: Provide `ResultsAnalyzer` for descriptive statistics (win rates, turn counts, durations, costs).
- **Model comparison**: Execute head-to-head comparisons (ModelA vs ModelB) with statistical significance testing.
- **Progressive testing**: Support early stopping when statistical significance reached (minimize matches while maintaining validity).
- **Statistical testing**: Select appropriate tests (t-test for normal, Mann-Whitney for non-parametric, bootstrap for small samples) and report p-values, effect sizes, confidence intervals.
- **Benchmark management**: Define, version, and execute benchmark suites (collections of games/configurations) for reproducible evaluation.
- **Dependency signaling**: Raise informative errors when optional libraries are required; fall back to conservative defaults where feasible.
- **[v1.1.0] Post-hoc analysis**: Provide standalone analysis tools that read recordings from disk and compute comprehensive statistics without re-execution.
- **[v1.1.0] Cross-player comparison**: Automatically compute pairwise comparisons for 2-player games (direct) and 3+ player games (matrix).
- **[v1.1.0] Spectator conveniences**: Provide thin spectator wrappers that auto-run post-hoc analysis at batch end for zero-config UX.

## 4. Public API

### ResultsAnalyzer
- `ResultsAnalyzer(results: MatchResults)`
  - Methods: `get_win_rates()`, `get_summary_stats()`, `print_detailed_report()`, `export_csv(path)`
  - Guarantees: MUST accept `MatchResults` and MUST NOT mutate input data

### Model Comparison
- `compare_models(model_a, model_b, game, matches=100, seed=None, *, test="auto", confidence=0.95, spectators=None, parallel=False) -> ComparisonResult`
  - Head-to-head model comparison with statistical testing
  - Guarantees:
    - MUST execute exactly `matches` games with fair player ordering (Console applies seeded shuffle per match unless game overrides)
    - MUST select statistical test: "t-test" (normal), "mann-whitney" (non-parametric), "bootstrap" (small samples)
    - MUST compute p-value, confidence interval, effect size
    - MUST return ComparisonResult with metadata (avg_turns, costs, decision_times)
    - MUST use seed for reproducibility (derives per-match seeds deterministically)
    - MAY accept optional spectators list; MUST pass through to `AgentDeck` so observers receive lifecycle events without affecting gameplay
    - `parallel` is reserved for future use and currently ignored

- `compare_models_progressive(model_a, model_b, game, min_matches=30, max_matches=500, alpha=0.05, check_interval=10, seed=None, *, spectators=None) -> ProgressiveResult`
  - Progressive comparison with early stopping
  - Guarantees:
    - MUST run min_matches before checking significance
    - MUST check significance every check_interval matches
    - MUST stop when p_value < alpha or max_matches reached
    - MUST return ProgressiveResult with intermediate results and stopping metadata
    - MAY accept optional spectators list; MUST pass through to `AgentDeck` for observability parity

### Benchmark Execution
- `run_benchmark(benchmark: Benchmark, model_a, model_b, seed=None) -> BenchmarkResult`
  - Execute benchmark suite
  - Guarantees:
    - MUST run all games in benchmark
    - MUST aggregate results across games (overall win rate, average p-value, games won)
    - MUST record benchmark version in result for reproducibility

### Statistical Helpers
- `statistical_test(results_a: List[float], results_b: List[float], test="auto", confidence=0.95) -> TestResult`
  - Low-level statistical testing utility
  - Requires: `scipy` or `statsmodels`
  - Guarantees: MUST select appropriate test based on sample size/normality, return p_value, statistic, confidence_interval, test_used

- `statistical_significance(successes: int, trials: int, expected_probability: float = 0.5) -> float`
  - Exact binomial test for p-values
  - Requires: `scipy`

- `calculate_confidence_interval(successes, trials, confidence_level=0.95) -> Tuple[float, float]`
  - Binomial proportion confidence interval (Wilson score method)
  - Requires: `scipy` or `statsmodels`

- `calculate_effect_size(observed_proportion, expected_proportion, sample_size) -> float`
  - Cohen's h (arcsine transformation) for proportion differences
  - Requires: None (uses standard math)

### Metrics Aggregation
- `aggregate_metrics(matches: List[MatchResult], metric: str = "winner") -> Dict[str, Any]`
  - Extract and aggregate metrics from matches
  - Guarantees:
    - MUST support metrics: "winner", "turns", "cost", "decision_time"
    - MUST compute mean, median, std, min, max, confidence_interval
    - MUST handle missing metrics gracefully (e.g., costs unavailable for non-LLM players)

### [v1.1.0] Post-Hoc Analysis (Standalone)

#### StatisticalAnalysis
- `StatisticalAnalysis.from_session(session_id: str, recordings_dir: Path = Path("agentdeck_runs")) -> StatisticalAnalysis`
  - Load and analyze recorded session from disk
  - Guarantees:
    - MUST read batch and match recordings from `recordings_dir/session_id/records/`
    - MUST validate recordings exist and are complete before computing
    - MUST compute win rates, confidence intervals, significance tests, effect sizes
    - MUST automatically compute cross-player comparisons (2-player direct, 3+ pairwise matrix)
    - MUST handle missing scipy/statsmodels gracefully (fall back to conservative defaults: CI +/- 0.1, p-values 1.0)

- Methods:
  - `compute_win_rates() -> Dict[str, float]`
  - `compute_confidence_intervals(confidence_level: float = 0.95) -> Dict[str, Tuple[float, float]]`
  - `compute_significance_tests(null_hypothesis: float = 0.5) -> Dict[str, float]`  # p-values
  - `compute_effect_sizes() -> Dict[str, float]`  # Cohen's h
  - `compute_pairwise_comparisons() -> PairwiseComparison`  # Cross-player analysis
  - `to_dict() -> Dict[str, Any]`  # Programmatic access
  - `print_summary()`  # Human-readable formatted output
  - `export_markdown(path: Path)`
  - `export_json(path: Path)`

#### PerformanceAnalysis
- `PerformanceAnalysis.from_session(session_id: str, baseline_duration: Optional[float] = None, baseline_cost: Optional[float] = None) -> PerformanceAnalysis`
  - Analyze performance metrics from recordings
  - Guarantees:
    - MUST extract timestamps and durations from recordings
    - MUST compute throughput (matches/second), speedup vs baseline, concurrency efficiency
    - MUST handle baseline comparisons when provided

- Methods:
  - `compute_duration_stats() -> Dict[str, Any]`  # total, avg, min, max, std
  - `compute_throughput() -> float`  # matches per second
  - `compute_speedup(baseline: float) -> float`
  - `compute_concurrency_efficiency() -> float`  # actual vs theoretical speedup
  - `to_dict() -> Dict[str, Any]`
  - `print_summary()`

#### CostAnalysis
- `CostAnalysis.from_session(session_id: str, baseline_cost: Optional[float] = None) -> CostAnalysis`
  - Analyze cost metrics from recordings
  - Guarantees:
    - MUST extract cost data from LLM player metadata in recordings
    - MUST handle missing cost data gracefully (non-LLM players return None)
    - MUST compute cost efficiency (cost per win) for performance comparison

- Methods:
  - `compute_cost_breakdown() -> Dict[str, float]`  # per player, total
  - `compute_cost_per_match() -> float`
  - `compute_cost_per_win() -> Dict[str, float]`  # cost efficiency
  - `compute_cost_savings(baseline: float) -> float`
  - `to_dict() -> Dict[str, Any]`
  - `print_summary()`

#### ComparisonAnalysis
- `ComparisonAnalysis(session_ids: List[str], recordings_dir: Path = Path("agentdeck_runs"))`
  - Compare statistics across multiple experimental sessions
  - Guarantees:
    - MUST load and aggregate statistics from all provided sessions
    - MUST compute meta-analysis (combined p-values via Fisher's method, aggregate effect sizes)
    - MUST generate comparison tables with confidence intervals
    - MUST handle sessions with different player counts/names gracefully

- Methods:
  - `meta_analysis() -> MetaAnalysisResult`  # Aggregate statistics
  - `compare_win_rates() -> ComparisonTable`
  - `compare_costs() -> ComparisonTable`
  - `compare_performance() -> ComparisonTable`
  - `model_comparison_matrix() -> ModelComparisonResult`  # When sessions use different models
  - `print_comparison_table()`
  - `export_markdown(path: Path)`

### [v1.1.0] Spectator Wrappers (Convenience)

#### StatisticalAnalysisSpectator
- `StatisticalAnalysisSpectator(print_on_complete: bool = True, save_report: bool = False, output_path: Optional[Path] = None, confidence_level: float = 0.95)`
  - Thin wrapper that auto-runs `StatisticalAnalysis.from_session()` at batch end
  - Guarantees:
    - MUST capture session_id during `on_session_start()`
    - MUST call standalone StatisticalAnalysis at `on_batch_end()`
    - MUST NOT duplicate analysis logic (imports and wraps standalone class)
    - MUST handle analysis errors gracefully (log warning, don't crash batch)

#### PerformanceTrackerSpectator
- `PerformanceTrackerSpectator(print_on_complete: bool = True, baseline_duration: Optional[float] = None, baseline_cost: Optional[float] = None)`
  - Auto-run performance analysis at batch end

#### CostAnalysisSpectator
- `CostAnalysisSpectator(print_on_complete: bool = True, baseline_cost: Optional[float] = None)`
  - Auto-run cost analysis at batch end

## 5. Data Structures

### ComparisonResult
```python
@dataclass
class ComparisonResult:
    model_a: str                                   # Model A identifier
    model_b: str                                   # Model B identifier
    game: str                                      # Game name
    matches: int                                   # Matches executed
    win_rate_a: float                             # Model A win rate (0.0-1.0)
    win_rate_b: float                             # Model B win rate
    draws: float                                  # Draw rate
    p_value: float                                # Statistical significance
    statistic: float                              # Test statistic (t-stat, U-stat, etc.)
    test_used: str                                # "t-test", "mann-whitney", "bootstrap"
    confidence_interval: Tuple[float, float]      # 95% CI for win rate difference
    effect_size: Optional[float] = None           # Cohen's h, Cohen's d, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)  # avg_turns, costs, decision_times, etc.

    @property
    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if result is statistically significant at alpha level."""
        return self.p_value < alpha
```

### ProgressiveResult
```python
@dataclass
class ProgressiveResult:
    comparisons: List[ComparisonResult]           # Intermediate results (one per check)
    stopped_early: bool                           # Early stopping triggered
    total_matches: int                            # Matches executed
    significance_reached_at: Optional[int] = None # Match count when significance reached
    final_comparison: ComparisonResult            # Final statistical test
```

### Benchmark
```python
@dataclass
class Benchmark:
    name: str                                     # Benchmark identifier
    version: str                                  # Semantic version (for evolution)
    games: List[BenchmarkGame]                    # Game scenarios
    min_matches: int = 100                        # Minimum matches per game
    confidence_level: float = 0.95                # CI level
    early_stopping: bool = False                  # Stop when significance reached
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BenchmarkGame:
    game: Game                                    # Game instance
    name: str                                     # Human-readable name
    min_matches: Optional[int] = None             # Override benchmark default
    config: Dict[str, Any] = field(default_factory=dict)  # Game-specific params
```

### BenchmarkResult
```python
@dataclass
class BenchmarkResult:
    benchmark_name: str
    benchmark_version: str
    model_a: str
    model_b: str
    overall_win_rate_a: float                     # Aggregate across all games
    overall_win_rate_b: float
    games_won_a: int                              # Games where A had higher win rate
    games_won_b: int
    total_games: int
    game_results: List[ComparisonResult]          # Per-game results
    total_cost: Optional[float] = None            # Aggregate LLM costs
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### [v1.1.0] PairwiseComparison
```python
@dataclass
class PairwiseComparison:
    comparisons: Dict[Tuple[str, str], ComparisonStats]  # (player_a, player_b) → stats
    matrix: List[List[str]]                               # Formatted matrix for display

@dataclass
class ComparisonStats:
    player_a: str
    player_b: str
    win_rate_a: float
    win_rate_b: float
    p_value: float
    effect_size: float
    is_significant: bool
    confidence_interval: Tuple[float, float]
```

### [v1.1.0] MetaAnalysisResult
```python
@dataclass
class MetaAnalysisResult:
    session_ids: List[str]
    total_matches: int
    aggregate_win_rates: Dict[str, float]
    aggregate_p_values: Dict[str, float]  # Combined using Fisher's method
    aggregate_effect_sizes: Dict[str, float]
    heterogeneity: float  # I^2 statistic (currently reported as 0.0; not computed yet)
```

### [v1.1.0] ComparisonTable
```python
@dataclass
class ComparisonTable:
    sessions: List[str]                   # Session IDs or names
    metrics: Dict[str, List[Any]]         # metric_name → [value per session]
    confidence_intervals: Dict[str, List[Tuple[float, float]]]
    formatted_table: str                  # Markdown/ASCII table for display
```

## 6. Invariants & Guarantees

### 6.1 Data Integrity (DI)
1. **DI1**: `ResultsAnalyzer` MUST accept `MatchResults` and MUST NOT mutate input data. Helpers that accept match lists (e.g., `aggregate_metrics`) MUST document their element types and avoid mutation.
2. **DI2**: CSV export MUST preserve winner, turn count, duration, and seed per match for external analysis.
3. **DI3**: Comparison functions MUST track total matches. Elapsed time tracking is RECOMMENDED for reporting transparency.

### 6.2 Statistical Rigor (SR)
4. **SR1**: MUST select appropriate statistical test: t-test (n>30 + normal), Mann-Whitney U (non-parametric), bootstrap (small samples n<30).
5. **SR2**: MUST report p-value, confidence interval (default 95%), test name, and effect size (when applicable).
6. **SR3** (Player Fairness): Research utilities MUST ensure fair player ordering to control for first-player advantage bias. **Implementation**: Rely on Console's automatic ordering strategy (default: seeded shuffle per match via Fisher-Yates, overridable by `game.get_player_order()` per SPEC-GAME §4). **Anti-Pattern**: Do NOT manually alternate players by calling `deck.play()` multiple times with swapped player lists—this creates separate batches and bypasses Console's fairness guarantees. **Metadata**: Use `player_order_source` field in MatchResult.metadata to distinguish console randomization from game-controlled ordering for post-hoc analysis.
7. **SR4**: Effect size calculation MUST follow Cohen's h formula (arcsine transformation) for proportion differences.

### 6.3 Progressive Testing (PT)
8. **PT1**: MUST run `min_matches` before checking significance (avoid premature stopping on noisy early data).
9. **PT2**: MUST check significance at regular intervals (`check_interval` matches) to minimize overhead.
10. **PT3**: MUST record stopping decision (early vs max_matches reached) in `ProgressiveResult` for transparency.
11. **PT4**: MUST respect `max_matches` cap even if significance not reached (budget enforcement).

### 6.4 Reproducibility (RE)
12. **RE1**: MUST accept seed parameter and derive per-match seeds deterministically (same seed → identical comparison).
13. **RE2**: MUST record seed in result metadata. Model/game configs SHOULD be recorded when available for enhanced reproducibility.
14. **RE3**: MUST version benchmarks (semantic versioning) for long-term reproducibility.

### 6.5 Metrics Aggregation (MA)
15. **MA1**: MUST collect win rates, draw rates, average turns, costs, decision times from matches.
16. **MA2**: SHOULD compute confidence intervals for aggregated metrics where statistically meaningful (win rates, turns). Point estimates are acceptable for metrics with unclear distributions.
17. **MA3**: MUST handle missing metrics gracefully (e.g., costs unavailable for scripted players, report None or exclude).

### 6.6 Dependency Handling (DH)
18. **DH1**: Statistical helpers that require scientific libraries (`statistical_test`, `statistical_significance`, `calculate_confidence_interval`) MUST raise `ImportError` when `scipy`/`statsmodels` are missing. Install guidance SHOULD be included in the error message.
19. **DH2**: `compare_models` MUST fall back gracefully when scientific libraries are unavailable (p_value=1.0, statistic=0.0, test_used="none", confidence_interval=(0.0, 0.0), effect_size=None).
20. **DH3**: Optional dependencies MUST be documented (`pip install agentdeck-ai[research]`). Runtime checks enforce availability.

### 6.7 Experiment Execution (EE)
21. **EE1**: `compare_models` and `compare_models_progressive` reuse provided player instances across matches; callers are responsible for player state management between matches.
22. **EE2**: Utilities rely on `deck.play()` to complete the session lifecycle; no explicit close is required.

### [v1.1.0] 6.8 Cross-Player Comparison (CPC)
23. **CPC1**: For 2-player games, `StatisticalAnalysis` MUST automatically compute head-to-head comparison (win rates, CI, p-value, effect size).
24. **CPC2**: For 3+ player games, `StatisticalAnalysis` MUST compute pairwise comparison matrix (all player pairs).
25. **CPC3**: Cross-player comparisons MUST use binomial test for win rate significance (vs null hypothesis of equal probability).
26. **CPC4**: Pairwise matrix MUST indicate significance level with symbols (✅ = significantly better, ❌ = significantly worse, − = not significant).
27. **CPC5**: Cross-player results MUST include effect sizes for all significant comparisons.

### [v1.1.0] 6.9 Post-Hoc Analysis (PH)
28. **PH1**: Post-hoc analysis tools MUST read recordings from `agentdeck_runs/session_id/records/` directory structure.
29. **PH2**: Tools SHOULD validate that batch recording and match recordings exist before computing statistics. Missing recordings MUST produce clear error messages.
30. **PH3**: Tools MUST support SPEC-RECORDER v1.0.0+ payloads with unified `records/` layout. Older schema versions are not supported.
31. **PH4**: Spectator wrappers MUST NOT duplicate analysis logic—they MUST import and call standalone classes.
32. **PH5**: Analysis failures (missing recordings, corrupt files) MUST raise informative errors with guidance for resolution.

## 7. Data Flow & Interaction

### Model Comparison Workflow
1. `compare_models()` validates inputs, initializes seed, constructs `AgentDeck` (injecting optional spectators when provided)
2. Execute matches in single batch (Console applies per-match player shuffling automatically)
3. Collect results: wins_a, wins_b, draws, turns, costs, decision_times
4. Run statistical test (auto-select based on distribution)
5. Compute confidence interval, effect size
6. Return ComparisonResult with complete metadata

### Progressive Testing Workflow
1. Run `min_matches` (collect baseline data) using `AgentDeck` configured with optional spectators when supplied
2. Check significance via `statistical_test()`
3. If p < alpha → stop early, return ProgressiveResult
4. Else → run `check_interval` more matches, repeat step 2
5. Stop at `max_matches` if significance not reached
6. Return ProgressiveResult with intermediate comparisons and stopping metadata

### Benchmark Execution Workflow
1. Load benchmark definition (games, min_matches, version)
2. For each game: run `compare_models()` or `compare_models_progressive()`
3. Aggregate results: overall win rate, p-values, games won
4. Return BenchmarkResult with per-game and aggregate stats

### Results Analysis Workflow
1. Researcher loads `MatchResults` from recorder
2. Instantiate `ResultsAnalyzer(results)`
3. Compute stats (`get_win_rates()`, `get_summary_stats()`) or export CSV
4. Use statistical helpers for custom analyses

### [v1.1.0] Post-Hoc Statistical Analysis Workflow
1. Researcher runs `StatisticalAnalysis.from_session(session_id)`
2. Tool loads batch recording (`batch_*.json`) and match recordings (`match_*.json`)
3. Tool validates all recordings present and schema-compliant
4. Tool computes win rates, confidence intervals, p-values, effect sizes
5. Tool automatically computes cross-player comparisons (2-player direct, 3+ matrix)
6. Researcher accesses results via `to_dict()` (programmatic) or `print_summary()` (human-readable)
7. Optionally export to markdown/JSON for reports

### [v1.1.0] Spectator Auto-Analysis Workflow
1. User attaches `StatisticalAnalysisSpectator` to AgentDeck
2. Spectator captures session_id during `on_session_start()`
3. Matches execute normally (spectator observes but doesn't interfere)
4. On `on_batch_end()`, spectator calls `StatisticalAnalysis.from_session(session_id)`
5. Analysis reads recordings from disk, computes statistics
6. If `print_on_complete=True`, results printed automatically
7. If `save_report=True`, markdown file saved to specified path

### [v1.1.0] Multi-Session Comparison Workflow
1. Researcher runs `ComparisonAnalysis([session_id1, session_id2, session_id3])`
2. Tool loads recordings for all sessions
3. Tool aggregates statistics across sessions
4. Tool computes meta-analysis (combined p-values via Fisher's method)
5. Tool generates comparison tables with confidence intervals
6. Researcher views comparison via `print_comparison_table()` or exports

## 8. Error Handling & Edge Cases
- MUST raise `ImportError` for missing scientific libraries, informing user how to install extras (`pip install agentdeck-ai[research]`).
- `export_csv` MUST handle file I/O errors (propagate Python exceptions) so callers can react (e.g., display message).
- `compare_models` SHOULD guard against dividing by zero (no matches) by returning neutral stats (0.5 win rates, p-value 1.0).
- `progressive_comparison` MUST cap matches at `max_matches` even if significance not reached (budget enforcement).
- Statistical helpers MUST handle zero-trial cases by returning neutral results (e.g., `(0, 0)` confidence interval, p-value `1.0`).
- MUST handle tied results appropriately: draws excluded from win rate denominator OR counted as 0.5 wins (configurable).
- MUST handle non-normal data by selecting Mann-Whitney U test when normality assumption violated.

## 9. Examples

### Example 1: Basic Model Comparison
```python
from agentdeck.research import compare_models
from agentdeck.players import GPTPlayer
from agentdeck.games import CombatGame

model_a = GPTPlayer(name="Alice", model="gpt-4o")
model_b = GPTPlayer(name="Bob", model="gpt-4o-mini")
game = CombatGame()

result = compare_models(model_a, model_b, game, matches=100, seed=42)

print(f"Win rate: A={result.win_rate_a:.2f}, B={result.win_rate_b:.2f}, Draws={result.draws:.2f}")
print(f"p-value: {result.p_value:.4f} ({result.test_used})")
print(f"95% CI: ({result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f})")
print(f"Effect size (Cohen's h): {result.effect_size:.2f}")
print(f"Significant at α=0.05: {result.is_significant()}")

# Output:
# Win rate: A=0.65, B=0.30, Draws=0.05
# p-value: 0.0023 (t-test)
# 95% CI: (0.50, 0.80)
# Effect size (Cohen's h): 0.72
# Significant at α=0.05: True
```

### Example 2: Progressive Testing (Cost Optimization)
```python
from agentdeck.research import compare_models_progressive

result = compare_models_progressive(
    model_a, model_b, game,
    min_matches=30,        # Baseline (must run at least 30)
    max_matches=500,       # Budget cap
    alpha=0.05,            # Significance threshold
    check_interval=10,     # Check every 10 matches
    seed=42
)

print(f"Stopped at {result.total_matches} matches")
print(f"Significance reached: {result.stopped_early}")
print(f"Final win rate A: {result.final_comparison.win_rate_a:.2f}")
print(f"Final p-value: {result.final_comparison.p_value:.4f}")

if result.stopped_early:
    print(f"Early stopping saved {500 - result.total_matches} matches!")

# Output:
# Stopped at 80 matches
# Significance reached: True (p<0.05 at match 80)
# Final win rate A: 0.62
# Final p-value: 0.0341
# Early stopping saved 420 matches!
```

### Example 3: Benchmark Suite
```python
from agentdeck.research import Benchmark, BenchmarkGame, run_benchmark
from agentdeck.games import CombatGame, NegotiationGame, PuzzleGame

benchmark = Benchmark(
    name="GPT-4o vs GPT-4o-mini Suite",
    version="1.0.0",
    games=[
        BenchmarkGame(CombatGame(), "Combat", min_matches=100),
        BenchmarkGame(NegotiationGame(), "Negotiation", min_matches=50),
        BenchmarkGame(PuzzleGame(), "Puzzle", min_matches=30),
    ],
    early_stopping=True,  # Enable progressive testing per game
    confidence_level=0.95
)

result = run_benchmark(benchmark, model_a, model_b, seed=42)

print(f"Benchmark: {result.benchmark_name} v{result.benchmark_version}")
print(f"Overall win rate: A={result.overall_win_rate_a:.2f}, B={result.overall_win_rate_b:.2f}")
print(f"Games won by A: {result.games_won_a} / {result.total_games}")
print(f"Total cost: ${result.total_cost:.2f}")

# Per-game breakdown
for game_result in result.game_results:
    print(f"\n{game_result.game}:")
    print(f"  Win rate A: {game_result.win_rate_a:.2f}")
    print(f"  p-value: {game_result.p_value:.4f}")
    print(f"  Matches: {game_result.matches}")
```

### Example 4: Results Analysis from Recorder
```python
from agentdeck.research import ResultsAnalyzer
from agentdeck.recorder import load_match

# Load recorded matches
matches = [load_match(f"results/match_{i}.json") for i in range(100)]

analyzer = ResultsAnalyzer(matches)

# Get summary statistics
stats = analyzer.get_summary_stats()
print(f"Total matches: {stats['total_matches']}")
print(f"Win rates: {stats['win_rates']}")
print(f"Average turns: {stats['avg_turns']} (95% CI: {stats['turns_ci']})")
print(f"Average cost: ${stats['avg_cost']:.2f}")

# Export to CSV for external analysis (Excel, R, etc.)
analyzer.export_csv("results/analysis.csv")

# Detailed report
analyzer.print_detailed_report()
```

### Example 5: Custom Statistical Analysis
```python
from agentdeck.research import statistical_test, aggregate_metrics

# Extract turn counts from matches
turn_data_a = [m.turn_count for m in matches_a]
turn_data_b = [m.turn_count for m in matches_b]

# Run statistical test
test_result = statistical_test(turn_data_a, turn_data_b, test="mann-whitney", confidence=0.95)

print(f"Test: {test_result.test_used}")
print(f"p-value: {test_result.p_value:.4f}")
print(f"Statistic: {test_result.statistic:.2f}")
print(f"95% CI: {test_result.confidence_interval}")

# Aggregate custom metrics
cost_stats = aggregate_metrics(matches, metric="cost")
print(f"Cost distribution:")
print(f"  Mean: ${cost_stats['mean']:.2f}")
print(f"  Median: ${cost_stats['median']:.2f}")
print(f"  95% CI: (${cost_stats['ci'][0]:.2f}, ${cost_stats['ci'][1]:.2f})")
```

### [v1.1.0] Example 6: Post-Hoc Statistical Analysis
```python
from agentdeck.research import StatisticalAnalysis

# Analyze session after it completed
analysis = StatisticalAnalysis.from_session("session_20251030_111049_63a6fb")

# Programmatic access
stats = analysis.to_dict()
print(f"Player-1 win rate: {stats['win_rates']['Player-1']:.2%}")
print(f"p-value: {stats['p_values']['Player-1']:.4f}")
print(f"95% CI: {stats['confidence_intervals']['Player-1']}")

# Pretty-print summary
analysis.print_summary()

# Output:
"""
Statistical Analysis: session_20251030_111049_63a6fb
===========================================================

Win Rates:
  Player-1: 40.0% [CI: 32.1%-48.5%]
  Player-2: 60.0% [CI: 51.5%-67.9%]

Cross-Player Comparison:
  Player-1 vs Player-2: p=0.145 (not significant)
  Effect size (Cohen's h): 0.403 (small-medium)

Conclusion:
  No significant difference at α=0.05
  Both players perform comparably in this game
===========================================================
"""
```

### [v1.1.0] Example 7: Multi-Session Comparison
```python
from agentdeck.research import ComparisonAnalysis

# Compare 3 experimental sessions
comparison = ComparisonAnalysis([
    "session_20251030_111049_63a6fb",  # Exp #1
    "session_20251031_131301_45fe25",  # Exp #2
    "session_20251031_131839_7ee163"   # Exp #3
])

comparison.print_comparison_table()

# Output:
"""
Cross-Session Comparison
========================================================================
| Session | Player-1 Win% | Player-2 Win% | p-value | Significant? |
|---------|---------------|---------------|---------|--------------|
| Exp #1  | 40% [32-48%]  | 60% [52-68%]  | 0.145   | No           |
| Exp #2  | 65% [55-74%]  | 35% [26-45%]  | 0.002   | Yes ✅       |
| Exp #3  | 52% [42-62%]  | 48% [38-58%]  | 0.687   | No           |

Meta-Analysis (Combined):
  Total matches: 40
  Player-1 overall: 52.5% [44.2%-60.6%]
  Player-2 overall: 47.5% [39.4%-55.8%]
  Combined p-value: 0.421 (Fisher's method)

Conclusion:
  No consistent advantage across sessions
  Results vary by experimental condition
========================================================================
"""
```

### [v1.1.0] Example 8: Spectator Auto-Analysis
```python
from agentdeck.spectators import StatisticalAnalysisSpectator

# Zero-config: automatically analyze when batch completes
spectator = StatisticalAnalysisSpectator(
    print_on_complete=True,
    save_report=True,
    output_path="analysis.md"
)

with AgentDeck(game=game, spectators=[spectator]) as deck:
    results = deck.play(players, matches=100)

# Analysis automatically prints and saves to analysis.md when batch ends
```

### [v1.1.0] Example 9: Performance Analysis
```python
from agentdeck.research import PerformanceAnalysis

analysis = PerformanceAnalysis.from_session(
    "session_20251030_111049_63a6fb",
    baseline_duration=300.0,  # Expected 5 minutes
    baseline_cost=0.04         # Expected cost
)

analysis.print_summary()

# Output:
"""
Performance Analysis: session_20251030_111049_63a6fb
===========================================================

Duration:
  Total: 67.27s
  Baseline: 300.0s
  Speedup: 4.46× faster
  Efficiency: 77% time savings

Throughput:
  Matches/second: 0.30
  Avg match duration: 3.36s
  Min/Max: 2.1s / 5.8s

Concurrency:
  Workers: 5
  Theoretical max speedup: 5×
  Actual speedup: 4.46×
  Efficiency: 89% (parallel overhead: 11%)
===========================================================
"""
```

## 10. Testing Strategy
| Focus | Invariants | Verification |
|-------|------------|--------------|
| Data integrity | DI1-DI3 | Feed synthetic MatchResults; ensure outputs match expected stats, inputs remain unmutated. |
| Statistical rigor | SR1-SR4 | Verify test selection logic, p-value accuracy, player ordering fairness (Console shuffle), effect size formulas. |
| Progressive testing | PT1-PT4 | Simulate progressive runs with known data; verify early stopping logic and stopping metadata. |
| Reproducibility | RE1-RE3 | Run same comparison with same seed twice; assert identical results. Verify benchmark versioning. |
| Metrics aggregation | MA1-MA3 | Collect metrics from matches; verify aggregation formulas and confidence interval computation. |
| Dependency handling | DH1-DH3 | Mock `scipy` availability; verify correct errors when missing and accurate stats when present. |
| Experiment execution | EE1-EE2 | Run small comparisons with seeded AgentDeck; check session cleanup and resource management. |
| **[v1.1.0] Cross-player comparison** | **CPC1-CPC5** | Test 2-player direct comparison and 3+ player pairwise matrix generation. Verify significance symbols (✅/❌/−). |
| **[v1.1.0] Post-hoc analysis** | **PH1-PH5** | Test recording loading from agentdeck_runs/session_id/records/, schema validation, error handling for missing/corrupt files. Verify spectator wrappers call standalone classes. |

### Concrete Test Examples

#### Test 1: Player ordering fairness (SR3)
```python
def test_player_ordering_fairness():
    from agentdeck.research import compare_models

    result = compare_models(
        model_a, model_b, game,
        matches=100,
        seed=42
    )

    # Verify Console applied shuffling (check metadata)
    for match in result.matches:
        assert "player_order" in match.metadata
        assert "player_order_source" in match.metadata
        # Most matches should have console-sourced ordering
        # (unless game overrides with custom logic)
        assert match.metadata["player_order_source"] in ["console", "game"]

    # Verify reproducibility: same seed → same ordering
    result2 = compare_models(model_a, model_b, game, matches=100, seed=42)
    for i in range(100):
        assert result.matches[i].metadata["player_order"] == result2.matches[i].metadata["player_order"]
```

#### Test 2: Statistical test selection (SR1)
```python
def test_statistical_test_selection():
    from agentdeck.research import compare_models

    # Large sample, normal distribution → t-test
    result_large = compare_models(model_a, model_b, game, matches=100, seed=42)
    assert result_large.test_used == "t-test"

    # Small sample → bootstrap
    result_small = compare_models(model_a, model_b, game, matches=15, seed=42)
    assert result_small.test_used == "bootstrap"
```

#### Test 3: Progressive early stopping (PT1, PT2, PT3)
```python
def test_progressive_early_stopping():
    from agentdeck.research import compare_models_progressive

    result = compare_models_progressive(
        model_a, model_b, game,
        min_matches=20,
        max_matches=200,
        alpha=0.05,
        check_interval=10,
        seed=42
    )

    # Verify min_matches enforced
    assert result.total_matches >= 20

    # If stopped early, verify significance reached
    if result.stopped_early:
        assert result.final_comparison.p_value < 0.05
        assert result.significance_reached_at is not None
        assert result.significance_reached_at == result.total_matches

    # Verify never exceeds max_matches
    assert result.total_matches <= 200

    # Verify intermediate comparisons recorded
    assert len(result.comparisons) > 0
```

#### Test 4: Reproducibility via seed (RE1)
```python
def test_reproducibility_with_seed():
    from agentdeck.research import compare_models

    # Run same comparison twice with same seed
    result1 = compare_models(model_a, model_b, game, matches=50, seed=42)
    result2 = compare_models(model_a, model_b, game, matches=50, seed=42)

    # Results should be identical
    assert result1.win_rate_a == result2.win_rate_a
    assert result1.win_rate_b == result2.win_rate_b
    assert result1.p_value == result2.p_value
    assert result1.matches == result2.matches

    # Run with different seed
    result3 = compare_models(model_a, model_b, game, matches=50, seed=99)

    # Should differ (high probability)
    assert result3.win_rate_a != result1.win_rate_a or result3.win_rate_b != result1.win_rate_b
```

#### Test 5: Dependency error handling (DH1)
```python
def test_missing_scipy_error():
    import sys
    from unittest.mock import patch

    # Mock missing scipy
    with patch.dict(sys.modules, {'scipy': None, 'scipy.stats': None}):
        with pytest.raises(ImportError, match="pip install agentdeck\\[research\\]"):
            from agentdeck.research import calculate_confidence_interval
            calculate_confidence_interval(60, 100)
```

#### Test 6: Metrics aggregation with missing data (MA3)
```python
def test_metrics_aggregation_missing_data():
    from agentdeck.research import aggregate_metrics

    # Create matches with some missing cost data
    matches = [
        MockMatch(winner="A", turns=10, cost=1.50),
        MockMatch(winner="B", turns=12, cost=None),  # Missing cost
        MockMatch(winner="A", turns=8, cost=2.00),
    ]

    # Aggregate costs (should handle None gracefully)
    cost_stats = aggregate_metrics(matches, metric="cost")

    # Should compute stats only from available data
    assert cost_stats['mean'] == 1.75  # (1.50 + 2.00) / 2
    assert cost_stats['n'] == 2  # Only 2 matches with cost data
    assert 'ci' in cost_stats  # CI should still be computed
```

#### [v1.1.0] Test 7: Post-hoc analysis from recordings (PH1, PH2)
```python
def test_post_hoc_analysis_from_recordings():
    from agentdeck.research import StatisticalAnalysis

    # Run matches and save recordings
    with AgentDeck(game=game, session=config) as deck:
        deck.play(players, matches=20)
        session_id = deck.session_id

    # Later: analyze from recordings
    analysis = StatisticalAnalysis.from_session(session_id)

    # Verify recordings loaded
    assert analysis.session_id == session_id
    assert analysis.total_matches == 20

    # Verify statistics computed
    stats = analysis.to_dict()
    assert 'win_rates' in stats
    assert 'confidence_intervals' in stats
    assert 'p_values' in stats
    assert 'effect_sizes' in stats
```

#### [v1.1.0] Test 8: Cross-player comparison (CPC1, CPC2)
```python
def test_cross_player_comparison():
    from agentdeck.research import StatisticalAnalysis

    # 2-player game: automatic direct comparison
    analysis_2p = StatisticalAnalysis.from_session("session_2player")
    pairwise = analysis_2p.compute_pairwise_comparisons()

    # Verify single comparison for 2 players
    assert len(pairwise.comparisons) == 1
    comparison = list(pairwise.comparisons.values())[0]
    assert comparison.player_a in ["Player-1", "Player-2"]
    assert comparison.player_b in ["Player-1", "Player-2"]
    assert 0 <= comparison.p_value <= 1

    # 3-player game: pairwise matrix
    analysis_3p = StatisticalAnalysis.from_session("session_3player")
    pairwise_3p = analysis_3p.compute_pairwise_comparisons()

    # Verify 3 comparisons (P1 vs P2, P1 vs P3, P2 vs P3)
    assert len(pairwise_3p.comparisons) == 3
    assert pairwise_3p.matrix is not None  # Formatted matrix exists
```

#### [v1.1.0] Test 9: Spectator wrapper (PH4)
```python
def test_spectator_wrapper_calls_standalone():
    from agentdeck.spectators import StatisticalAnalysisSpectator
    from agentdeck.research import StatisticalAnalysis
    from unittest.mock import patch

    spectator = StatisticalAnalysisSpectator(print_on_complete=False)

    # Mock the standalone class
    with patch.object(StatisticalAnalysis, 'from_session') as mock_from_session:
        # Simulate batch end
        event = Event(type="batch_end", data={"session_id": "test_session"})
        spectator.on_session_start(Event(type="session_start", data={"session_id": "test_session"}))
        spectator.on_batch_end(event)

        # Verify standalone was called (no logic duplication)
        mock_from_session.assert_called_once_with("test_session")
```

#### [v1.1.0] Test 10: Missing recordings error (PH5)
```python
def test_missing_recordings_error():
    from agentdeck.research import StatisticalAnalysis

    # Attempt to analyze non-existent session
    with pytest.raises(FileNotFoundError, match="session_nonexistent"):
        analysis = StatisticalAnalysis.from_session("session_nonexistent")
```

## 11. Open Questions / Future Work

### Multi-Model Comparisons
- Should we support **multi-way comparisons** (A vs B vs C vs D)?
- How to visualize and report n-way statistical tests (ANOVA, Kruskal-Wallis)?

### Bayesian Methods
- Should we support **Bayesian statistical methods** (credible intervals, Bayes factors)?
- How to balance frequentist and Bayesian approaches for different audiences?

### Weighted Benchmarks
- Should benchmarks support **game weights** (some games more important than others)?
- How to compute weighted aggregate statistics while maintaining statistical rigor?

### Meta-Analysis Metrics
- Implement I^2 heterogeneity statistic (currently reported as 0.0 placeholder).

### Visualization Tools
- What **visualization tools** should we provide (plotting, dashboards, notebooks)?
- Should we integrate with existing libraries (plotly, matplotlib, streamlit)?

### Concept Drift Handling
- How do we handle **concept drift** (model updates, API changes, game evolution)?
- Should benchmark results track model versions and flag incompatibilities?

### Parallel Execution
- Should comparison utilities support **parallel execution** or distributed runners for large benchmarks?
- How to balance resource usage vs experiment turnaround time?

### Sample Size Recommendations
- Should utilities provide **sample size calculators** (power analysis) to recommend min_matches?
- How to guide researchers on appropriate effect size thresholds?

### Result Persistence
- Should we provide **result storage** (database, file system) for longitudinal studies?
- How to integrate with experiment tracking tools (MLflow, Weights & Biases)?

## 12. Design Rationale
- **Thin wrappers** around scientific libraries keep maintenance light while giving researchers familiar statistical functions.
- **AgentDeck integration** ensures comparisons use the same execution pipeline as production experiments.
- **Optional dependencies** isolate heavy statistical packages from core install unless needed (`pip install agentdeck-ai[research]`).
- **Progressive testing** can save 50-80% of API budget while maintaining statistical validity.
- **Console-managed player ordering** (SR3): Research utilities rely on Console's fairness mechanism (Fisher-Yates shuffle per match) rather than manual alternation. This simplifies research code, produces single-batch executions (better performance), and respects game-specific ordering overrides when semantically meaningful.
- **Versioned benchmarks** enable long-term reproducibility as games and models evolve.
- **Seed-based reproducibility** enables identical comparisons for debugging and validation.
- **Statistical transparency** (report p-values, CIs, test names) ensures publication-ready results.

### [v1.1.0] Post-Hoc Analysis Design
- **Recordings as source of truth**: Post-hoc tools read recordings from disk, validating that recordings are complete and self-contained. This aligns with AgentDeck's recorder/replay philosophy.
- **Zero execution overhead**: Analysis happens after matches complete, keeping execution fast and observation-free during gameplay.
- **Hybrid architecture** (standalone + spectator): Standalone classes provide primary interface (flexible, powerful, can analyze old sessions), while spectators provide convenience wrappers (zero-config UX, auto-run at batch end).
- **No logic duplication**: Spectators are thin wrappers (<20 lines) that import and call standalone classes. All computation lives in one place (research/ module).
- **Automatic cross-player comparison**: For 2-player games, StatisticalAnalysis automatically computes head-to-head comparison (reduces boilerplate). For 3+ player games, generates pairwise matrix automatically.
- **Module organization**: Standalone tools live in `research/` (tools), spectators live in `spectators/` (observers). Clean separation of concerns, consistent with existing architecture.
- **Longitudinal analysis support**: Multi-session comparison (ComparisonAnalysis) enables meta-analysis across experiments conducted over weeks/months.
- **Graceful degradation**: When scipy unavailable, falls back to conservative defaults (CI margin 0.1, p-values 1.0) to maintain functionality without optional deps.

## 13. References

### Specifications
- [SPEC.md](./SPEC.md) §1.1 (Research focus), §2.4 (Reproducibility)
- [SPEC.md](./SPEC.md) §2.4 (Data-driven iteration)
- [SPEC-AGENTDECK.md](./SPEC-AGENTDECK.md) v0.3.0 (Match execution, seed handling)
- [SPEC-CONSOLE.md](./SPEC-CONSOLE.md) v0.3.0 (Match orchestration)
- [SPEC-RECORDER.md](./SPEC-RECORDER.md) v1.3.0 (Match metadata capture, load_match() utilities)
- [SPEC-PLAYER.md](./SPEC-PLAYER.md) v1.2.0 (Player contract, three-phase lifecycle)
- [SPEC-SPECTATOR.md](./SPEC-SPECTATOR.md) v1.2.0 (Observer API for custom analytics during comparison)
- [SPEC-OBSERVABILITY.md](./SPEC-OBSERVABILITY.md) v1.0.0 (Event system for tracking comparison progress)
- [SPEC-RESEARCH-EXPERIMENT.md](./SPEC-RESEARCH-EXPERIMENT.md) v1.0.0 (Experiment package contracts)
