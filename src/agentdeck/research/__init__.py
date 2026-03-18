"""Research utilities for live comparisons, post-hoc analysis, and packaging support."""

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
from .recording_metrics import (
    compute_format_strictness,
    compute_inferential_statistics,
    compute_position_effect,
)
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
    "compute_inferential_statistics",
    "compute_format_strictness",
    "compute_position_effect",
    # Post-hoc data structures (SPEC-RESEARCH v1.1.0)
    "PairwiseComparison",
    "ComparisonStats",
    "MetaAnalysisResult",
    "ComparisonTable",
]
