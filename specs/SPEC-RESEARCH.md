# SPEC-RESEARCH: Research Utilities Contract

> Status: Final
> Version: 1.2.0
> Last Updated: 2026-03-17
> Implementation: Complete
> Review State: Legacy-approved
> Audience: Research engineers, experiment authors, AI practitioners

## 1. Purpose
- Provide a small, reusable research layer for comparing AgentDeck runs, analyzing recorded sessions, and exporting objective summaries.
- Keep live execution separate from analysis: research utilities consume `MatchResults` or recorder artifacts and never influence gameplay.
- Support both interactive workflows (`compare_models`) and post-hoc workflows (`StatisticalAnalysis.from_session(...)`).

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC.md` research-first framing and reproducibility guarantees.
- Favors simple reusable helpers over a large benchmark framework.
- Treats recorder data and experiment packages as the durable source of truth.
- Non-goals:
  - match execution lifecycle (`SPEC-CONSOLE.md`)
  - recording contract ownership (`SPEC-RECORDER.md`)
  - experiment package schema ownership (`SPEC-RESEARCH-EXPERIMENT.md`)

## 3. Responsibilities
- Summarize `MatchResults` with descriptive metrics and CSV export.
- Run live head-to-head comparisons with statistical summaries.
- Support progressive comparisons with early stopping.
- Provide low-level statistical helpers for proportions and aggregate metrics.
- Analyze completed recorded sessions for win rates, confidence intervals, p-values, effect sizes, and pairwise comparisons.
- Compare multiple recorded sessions at a lightweight cross-session level.
- Provide thin spectator wrappers that delegate to standalone post-hoc analysis classes.

## 4. Public API

### 4.1 Live Comparison Utilities
- `ResultsAnalyzer(results: MatchResults)`
  - Methods:
    - `get_win_rates() -> Dict[str, float]`
    - `get_summary_stats() -> Dict[str, Any]`
    - `print_detailed_report() -> None`
    - `export_csv(path) -> None`
- `compare_models(model_a, model_b, game, matches=100, seed=None, *, test="auto", confidence=0.95, parallel=False, spectators=None) -> ComparisonResult`
- `compare_models_progressive(model_a, model_b, game, min_matches=30, max_matches=500, alpha=0.05, check_interval=10, seed=None, *, spectators=None) -> ProgressiveResult`
- `run_benchmark(benchmark: Benchmark, model_a, model_b, seed=None) -> BenchmarkResult`

### 4.2 Statistical Helpers
- `statistical_test(results_a, results_b, test="auto", confidence=0.95) -> TestResult`
- `statistical_significance(successes: int, trials: int, expected_probability: float = 0.5) -> float`
- `calculate_confidence_interval(successes: int, trials: int, confidence_level: float = 0.95) -> Tuple[float, float]`
- `calculate_effect_size(observed_proportion: float, expected_proportion: float, sample_size: int) -> float`
- `aggregate_metrics(matches, metric: str = "winner") -> Dict[str, Any]`

### 4.3 Post-Hoc Session Analysis
- `StatisticalAnalysis.from_session(session_id: str, recordings_dir: Path = Path("agentdeck_runs")) -> StatisticalAnalysis`
  - Methods:
    - `compute_win_rates()`
    - `compute_confidence_intervals(confidence_level=0.95)`
    - `compute_significance_tests(null_hypothesis=0.5)`
    - `compute_effect_sizes(null_hypothesis=0.5)`
    - `compute_pairwise_comparisons(confidence_level=0.95)`
    - `to_dict()`
    - `print_summary()`
    - `export_markdown(path)`
    - `export_json(path)`

`compute_pairwise_comparisons()` MUST compare only direct head-to-head matches.
For sessions or aggregates with more than two players, pairwise entries MUST be
included only for player pairs that actually appeared in the same recorded
matches. It MUST NOT compare players by subtracting or normalizing their
package-level aggregate wins when they did not directly face each other.
- `PerformanceAnalysis.from_session(session_id: str, recordings_dir: Path = Path("agentdeck_runs"), baseline_duration=None, baseline_cost=None) -> PerformanceAnalysis`
  - Methods:
    - `compute_duration_stats()`
    - `compute_throughput()`
    - `compute_speedup(baseline=None)`
    - `compute_concurrency_efficiency()`
    - `to_dict()`
    - `print_summary()`
- `CostAnalysis.from_session(session_id: str, recordings_dir: Path = Path("agentdeck_runs"), baseline_cost=None) -> CostAnalysis`
  - Methods:
    - `compute_cost_breakdown()`
    - `compute_cost_per_match()`
    - `compute_cost_per_win()`
    - `compute_cost_savings(baseline=None)`
    - `to_dict()`
    - `print_summary()`

### 4.4 Cross-Session Comparison
- `ComparisonAnalysis(session_ids: List[str], recordings_dir: Path = Path("agentdeck_runs"))`
  - Methods:
    - `meta_analysis() -> MetaAnalysisResult`
    - `compare_win_rates() -> ComparisonTable`
    - `print_comparison_table() -> None`
    - `export_markdown(path) -> None`
- Scope note:
  - Cross-session comparison currently covers aggregated win-rate views and meta-analysis only.
  - Cross-session cost tables, performance tables, and generalized model-comparison matrices are out of scope for this release.

### 4.5 Convenience Spectators
- `StatisticalAnalysisSpectator(...)`
- `PerformanceTrackerSpectator(...)`
- `CostAnalysisSpectator(...)`

These wrappers live in `agentdeck.spectators` and MUST delegate to the standalone research classes above rather than reimplementing analysis logic.

## 5. Data Structures

### 5.1 ComparisonResult
```python
@dataclass
class ComparisonResult:
    model_a: str
    model_b: str
    game: str
    matches: int
    win_rate_a: float
    win_rate_b: float
    draws: float
    p_value: float
    statistic: float
    test_used: str
    confidence_interval: Tuple[float, float]
    effect_size: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 5.2 ProgressiveResult
```python
@dataclass
class ProgressiveResult:
    comparisons: List[ComparisonResult]
    stopped_early: bool
    total_matches: int
    significance_reached_at: Optional[int] = None
    final_comparison: Optional[ComparisonResult] = None
```

### 5.3 Benchmark Types
```python
@dataclass
class BenchmarkGame:
    game: Game
    name: str
    min_matches: Optional[int] = None
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Benchmark:
    name: str
    version: str
    games: List[BenchmarkGame]
    min_matches: int = 100
    confidence_level: float = 0.95
    early_stopping: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BenchmarkResult:
    benchmark_name: str
    benchmark_version: str
    model_a: str
    model_b: str
    overall_win_rate_a: float
    overall_win_rate_b: float
    games_won_a: int
    games_won_b: int
    total_games: int
    game_results: List[ComparisonResult]
    total_cost: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 5.4 Post-Hoc Comparison Types
```python
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

@dataclass
class PairwiseComparison:
    comparisons: Dict[Tuple[str, str], ComparisonStats]
    matrix: List[List[str]]
    player_a: Optional[str] = None
    player_b: Optional[str] = None
    win_rate_diff: Optional[float] = None
    p_value: Optional[float] = None
    is_significant: Optional[bool] = None
    significance_symbol: Optional[str] = None

@dataclass
class MetaAnalysisResult:
    session_ids: List[str]
    total_matches: int
    aggregate_win_rates: Dict[str, float]
    aggregate_p_values: Dict[str, float]
    aggregate_effect_sizes: Dict[str, float]
    heterogeneity: float = 0.0

@dataclass
class ComparisonTable:
    sessions: List[str]
    metrics: Dict[str, List[Any]]
    confidence_intervals: Dict[str, List[Tuple[float, float]]]
    formatted_table: str
```

## 6. Invariants & Guarantees
- **RS1**: `ResultsAnalyzer` and metric helpers MUST NOT mutate their inputs.
- **RS2**: `compare_models(...)` and `compare_models_progressive(...)` MUST delegate live execution to `AgentDeck` and therefore inherit Console ordering/fairness behavior instead of reimplementing scheduling.
- **RS3**: Live comparison results MUST report wins, draw rate, statistical test metadata, and aggregate match metadata such as turns and cost when available.
- **RS4**: Progressive comparison MUST honor `min_matches`, `check_interval`, and `max_matches`, and MUST record whether early stopping occurred.
- **RS5**: Statistical helpers that depend on `scipy` / `statsmodels` MUST raise informative `ImportError` when unavailable.
- **RS6**: Higher-level research APIs MAY fall back conservatively when scientific dependencies are missing. If they do, fallback outputs MUST remain obviously non-authoritative (`p_value=1.0`, neutral CI/effect defaults, or similar).
- **RS7**: Post-hoc analysis tools MUST read from the unified session layout `agentdeck_runs/<session_id>/records/`.
- **RS8**: Post-hoc analysis tools MUST fail fast with clear `FileNotFoundError` when the session directory, `records/`, or required batch recording is missing.
- **RS9**: Post-hoc statistical analysis for completed sessions MUST derive player identities and outcomes from recorded batch summaries. It MAY use match JSONs indirectly via recorder-produced summaries, but it does not own artifact-integrity validation.
- **RS10**: `ComparisonAnalysis` MUST support meta-analysis and win-rate comparison tables across multiple sessions. Broader cross-session tables are out of scope for this release.
- **RS11**: Research spectators MUST remain thin wrappers that delegate to standalone analysis classes and MUST NOT duplicate analysis logic.

## 7. Data Flow & Interaction
- Live comparison:
  - players + game -> `AgentDeck.play(...)` -> `ComparisonResult` / `ProgressiveResult`
- Post-hoc analysis:
  - `agentdeck_runs/<session_id>/records/` -> `StatisticalAnalysis` / `PerformanceAnalysis` / `CostAnalysis`
- Cross-session analysis:
  - session ids -> `ComparisonAnalysis` -> comparison table + meta-analysis

## 8. Error Handling & Edge Cases
- Missing or empty recordings MUST raise clear file-related errors.
- Zero-trial statistical helper inputs MUST return neutral outputs where mathematically appropriate.
- Missing per-match cost or timing data MUST be handled gracefully rather than crashing aggregation.
- `ComparisonAnalysis` MUST skip missing sessions with a warning and fail only if no valid sessions remain.

## 9. Testing Strategy
- Verify `ResultsAnalyzer` summary/export behavior on synthetic `MatchResults`.
- Verify live comparison helpers return stable metadata and cost aggregates.
- Verify post-hoc analysis loads real recorder output and computes win rates, CIs, p-values, and pairwise summaries.
- Verify research spectators delegate correctly without duplicating analysis logic.
- Verify cross-session comparison produces meta-analysis and win-rate tables.

## 10. References
- `SPEC-CONSOLE.md`
- `SPEC-RECORDER.md`
- `SPEC-RESEARCH-EXPERIMENT.md`
- `src/agentdeck/research/`
