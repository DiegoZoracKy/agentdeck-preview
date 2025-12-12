"""Research module for AgentDeck - Kaggle-inspired statistical tools.

Per SPEC-RESEARCH v1.0.0:
- compare_models(): Head-to-head comparison with SR3 alternation, SR1 test selection
- compare_models_progressive(): Progressive testing with early stopping (PT1-PT4)
- run_benchmark(): Execute benchmark suites with versioned reproducibility
- statistical_test(): Auto-select t-test, Mann-Whitney, or bootstrap
- aggregate_metrics(): Extract and aggregate match metrics with CIs
- ResultsAnalyzer: Analyze MatchResults with summary stats and CSV export

Per SPEC-RESEARCH v1.1.0:
- StatisticalAnalysis: Post-hoc analysis from recordings (win rates, CIs, p-values, effect sizes)
- PerformanceAnalysis: Performance metrics from recordings (duration, throughput, speedup)
- CostAnalysis: Cost metrics from recordings (breakdown, efficiency, savings)
- ComparisonAnalysis: Multi-session comparison and meta-analysis
"""

from .analysis import ResultsAnalyzer
from .comparison import (
    Benchmark,
    BenchmarkGame,
    BenchmarkResult,
    ComparisonResult,
    ProgressiveResult,
    compare_models,
    compare_models_progressive,
    run_benchmark,
)
from .cost_analysis import CostAnalysis
from .multi_session import (
    ComparisonAnalysis,
    ComparisonTable,
    MetaAnalysisResult,
)
from .performance_analysis import PerformanceAnalysis
from .statistical import (
    TestResult,
    aggregate_metrics,
    calculate_confidence_interval,
    calculate_effect_size,
    statistical_significance,
    statistical_test,
)

# v1.1.0: Post-hoc analysis from recordings
from .statistical_analysis import (
    ComparisonStats,
    PairwiseComparison,
    StatisticalAnalysis,
)

__all__ = [
    # Core comparison functions (SPEC-RESEARCH v1.0.0)
    "compare_models",
    "compare_models_progressive",
    "run_benchmark",
    # Data structures (SPEC-RESEARCH v1.0.0)
    "ComparisonResult",
    "ProgressiveResult",
    "Benchmark",
    "BenchmarkGame",
    "BenchmarkResult",
    "TestResult",
    # Statistical utilities (SPEC-RESEARCH v1.0.0)
    "statistical_test",
    "aggregate_metrics",
    "calculate_confidence_interval",
    "calculate_effect_size",
    "statistical_significance",
    # Analysis (SPEC-RESEARCH v1.0.0)
    "ResultsAnalyzer",
    # Post-hoc analysis (SPEC-RESEARCH v1.1.0)
    "StatisticalAnalysis",
    "PerformanceAnalysis",
    "CostAnalysis",
    "ComparisonAnalysis",
    # Post-hoc data structures (SPEC-RESEARCH v1.1.0)
    "PairwiseComparison",
    "ComparisonStats",
    "MetaAnalysisResult",
    "ComparisonTable",
]
