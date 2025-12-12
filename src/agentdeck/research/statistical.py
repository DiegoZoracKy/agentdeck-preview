"""Statistical utilities for AgentDeck research.

This module provides thin wrappers around scipy/statsmodels for statistical analysis.
SciPy and statsmodels are bundled with AgentDeck as core dependencies.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# Try to import scipy and statsmodels
try:
    from scipy import stats
    from statsmodels.stats.proportion import proportion_confint

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class TestResult:
    """Result from statistical test (per SPEC-RESEARCH v1.0.0 §4)."""

    p_value: float  # Two-tailed p-value
    statistic: float  # Test statistic (t, U, etc.)
    test_used: str  # Test name ("t-test", "mann-whitney", "bootstrap")
    confidence_interval: Tuple[float, float]  # Confidence interval for difference


def _require_scipy():
    """Check if scipy is available, raise helpful error if not."""
    if not HAS_SCIPY:
        raise ImportError(
            "Research utilities require scipy and statsmodels, which should install with AgentDeck. "
            "If you see this message, verify your environment has scipy and statsmodels available."
        )


def calculate_confidence_interval(
    successes: int, trials: int, confidence_level: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate confidence interval for a proportion using Wilson score interval.

    This is a thin wrapper around statsmodels.stats.proportion.proportion_confint.
    The Wilson score interval is preferred over the normal approximation because
    it has better coverage properties, especially for small sample sizes or
    proportions near 0 or 1.

    Args:
        successes: Number of successful outcomes
        trials: Total number of trials
        confidence_level: Confidence level (e.g., 0.95 for 95%)

    Returns:
        Tuple of (lower_bound, upper_bound)

    Raises:
        ImportError: If scipy/statsmodels not installed
    """
    _require_scipy()

    if trials == 0:
        return (0.0, 0.0)

    # statsmodels uses alpha = 1 - confidence_level
    alpha = 1 - confidence_level
    lower, upper = proportion_confint(successes, trials, alpha=alpha, method="wilson")

    return (float(lower), float(upper))


def statistical_significance(
    successes: int, trials: int, expected_probability: float = 0.5
) -> float:
    """
    Calculate p-value using exact binomial test.

    This is a thin wrapper around scipy.stats.binomtest. The exact binomial test
    is more accurate than normal approximations, especially for small sample sizes.

    Args:
        successes: Number of successful outcomes
        trials: Total number of trials
        expected_probability: Expected probability under null hypothesis

    Returns:
        Two-tailed p-value

    Raises:
        ImportError: If scipy not installed
    """
    _require_scipy()

    if trials == 0:
        return 1.0

    # Use exact binomial test (scipy handles all sample sizes optimally)
    result = stats.binomtest(successes, trials, expected_probability, alternative="two-sided")
    return float(result.pvalue)


def calculate_effect_size(
    observed_proportion: float, expected_proportion: float, sample_size: int
) -> float:
    """
    Calculate Cohen's h effect size for proportions.

    Cohen's h is an effect size measure for the difference between two proportions.
    It uses the arcsine transformation to stabilize variance.

    Interpretation (from Cohen, 1988):
    - |h| < 0.2: Small effect
    - 0.2 ≤ |h| < 0.5: Medium effect
    - |h| ≥ 0.5: Large effect

    Args:
        observed_proportion: Observed proportion (between 0 and 1)
        expected_proportion: Expected proportion (between 0 and 1)
        sample_size: Sample size (not used in calculation, kept for API compatibility)

    Returns:
        Cohen's h effect size

    Note:
        This function does not require scipy and uses only the math module.
    """
    # Arcsine transformation (stabilizes variance)
    phi_observed = 2 * math.asin(math.sqrt(observed_proportion))
    phi_expected = 2 * math.asin(math.sqrt(expected_proportion))

    # Cohen's h is the difference
    h = phi_observed - phi_expected

    return h


def statistical_test(
    results_a: List[float], results_b: List[float], test: str = "auto", confidence: float = 0.95
) -> TestResult:
    """
    Perform statistical test comparing two samples (per SPEC-RESEARCH v1.0.0 §4).

    Auto-selects appropriate test based on sample size and normality:
    - t-test: n>30 and data appears normal
    - mann-whitney: Non-parametric alternative
    - bootstrap: Small samples (n<30)

    Args:
        results_a: Sample A values
        results_b: Sample B values
        test: "auto", "t-test", "mann-whitney", or "bootstrap"
        confidence: Confidence level for CI (default 0.95)

    Returns:
        TestResult with p_value, statistic, test_used, confidence_interval

    Raises:
        ImportError: If scipy/statsmodels not installed
    """
    _require_scipy()

    if len(results_a) == 0 or len(results_b) == 0:
        # No data: return neutral result
        return TestResult(
            p_value=1.0, statistic=0.0, test_used="none", confidence_interval=(0.0, 0.0)
        )

    # Auto-select test if requested
    if test == "auto":
        n = min(len(results_a), len(results_b))
        if n < 30:
            test = "bootstrap"
        else:
            # Check normality with Shapiro-Wilk test (p > 0.05 suggests normal)
            _, p_a = stats.shapiro(results_a) if len(results_a) <= 5000 else (0, 0.1)
            _, p_b = stats.shapiro(results_b) if len(results_b) <= 5000 else (0, 0.1)
            if p_a > 0.05 and p_b > 0.05:
                test = "t-test"
            else:
                test = "mann-whitney"

    # Perform selected test
    if test == "t-test":
        statistic, p_value = stats.ttest_ind(results_a, results_b)

        # Calculate confidence interval for difference in means
        mean_a = sum(results_a) / len(results_a)
        mean_b = sum(results_b) / len(results_b)
        diff = mean_a - mean_b

        # Pooled standard error
        var_a = sum((x - mean_a) ** 2 for x in results_a) / (len(results_a) - 1)
        var_b = sum((x - mean_b) ** 2 for x in results_b) / (len(results_b) - 1)
        se = math.sqrt(var_a / len(results_a) + var_b / len(results_b))

        # t critical value
        df = len(results_a) + len(results_b) - 2
        t_crit = stats.t.ppf((1 + confidence) / 2, df)
        ci = (diff - t_crit * se, diff + t_crit * se)

    elif test == "mann-whitney":
        statistic, p_value = stats.mannwhitneyu(results_a, results_b, alternative="two-sided")

        # Bootstrap CI for median difference
        # (Mann-Whitney doesn't have closed-form CI, so bootstrap approximation)
        median_a = sorted(results_a)[len(results_a) // 2]
        median_b = sorted(results_b)[len(results_b) // 2]
        diff = median_a - median_b

        # Simple approximation: use interquartile range for CI width
        import numpy as np

        q25_a, q75_a = np.percentile(results_a, [25, 75])
        q25_b, q75_b = np.percentile(results_b, [25, 75])
        iqr = max(q75_a - q25_a, q75_b - q25_b)
        ci_width = iqr / math.sqrt(min(len(results_a), len(results_b)))
        ci = (diff - ci_width, diff + ci_width)

    elif test == "bootstrap":
        # Bootstrap resampling for small samples
        import numpy as np

        # Calculate observed difference in means
        mean_a = sum(results_a) / len(results_a)
        mean_b = sum(results_b) / len(results_b)
        observed_diff = mean_a - mean_b

        # Bootstrap: resample and compute distribution of differences
        n_bootstrap = 10000
        bootstrap_diffs = []
        combined = results_a + results_b

        for _ in range(n_bootstrap):
            resample_a = np.random.choice(combined, size=len(results_a), replace=True)
            resample_b = np.random.choice(combined, size=len(results_b), replace=True)
            boot_diff = resample_a.mean() - resample_b.mean()
            bootstrap_diffs.append(boot_diff)

        # p-value: proportion of bootstrap diffs as extreme as observed
        bootstrap_diffs = np.array(bootstrap_diffs)
        p_value = 2 * min(
            np.mean(bootstrap_diffs >= abs(observed_diff)),
            np.mean(bootstrap_diffs <= -abs(observed_diff)),
        )

        # CI from bootstrap distribution
        alpha = 1 - confidence
        ci = (
            np.percentile(bootstrap_diffs, 100 * alpha / 2),
            np.percentile(bootstrap_diffs, 100 * (1 - alpha / 2)),
        )

        statistic = observed_diff

    else:
        raise ValueError(
            f"Unknown test: {test}. Use 'auto', 't-test', 'mann-whitney', or 'bootstrap'"
        )

    return TestResult(
        p_value=float(p_value),
        statistic=float(statistic),
        test_used=test,
        confidence_interval=(float(ci[0]), float(ci[1])),
    )


def aggregate_metrics(matches: List, metric: str = "winner") -> Dict[str, Any]:
    """
    Extract and aggregate metrics from matches (per SPEC-RESEARCH v1.0.0 §4).

    Supports metrics: "winner", "turns", "cost", "decision_time"
    Computes: mean, median, std, min, max, confidence_interval

    Args:
        matches: List of MatchResult objects
        metric: Metric to aggregate ("winner", "turns", "cost", "decision_time")

    Returns:
        Dictionary with aggregated statistics

    Raises:
        ImportError: If scipy/statsmodels not installed (for confidence intervals)
    """
    values = []

    # Extract metric values
    for match in matches:
        if metric == "winner":
            # Binary: 1 if first player won, 0 if second player won, skip draws
            if match.winner and match.metadata and "players" in match.metadata:
                players = match.metadata["players"]
                # First player is index 0
                values.append(1 if match.winner == players[0] else 0)

        elif metric == "turns":
            # Count gameplay events
            turn_count = len([e for e in match.events if e.type == "gameplay"])
            values.append(turn_count)

        elif metric == "cost":
            # Extract from metadata if available
            if match.metadata and "cost" in match.metadata:
                values.append(match.metadata["cost"])

        elif metric == "decision_time":
            # Extract from metadata if available
            if match.metadata and "decision_times" in match.metadata:
                values.extend(match.metadata["decision_times"])

        else:
            raise ValueError(
                f"Unknown metric: {metric}. Use 'winner', 'turns', 'cost', or 'decision_time'"
            )

    if not values:
        # No data available for this metric
        return {
            "metric": metric,
            "n": 0,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "ci": None,
        }

    # Calculate basic statistics
    n = len(values)
    mean = sum(values) / n
    sorted_values = sorted(values)
    median = sorted_values[n // 2]

    # Standard deviation
    variance = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0
    std = math.sqrt(variance)

    min_val = min(values)
    max_val = max(values)

    # Confidence interval
    try:
        _require_scipy()

        # For proportions (winner metric), use Wilson score
        if metric == "winner":
            successes = sum(values)
            ci_lower, ci_upper = calculate_confidence_interval(successes, n, 0.95)
            ci = (ci_lower, ci_upper)
        else:
            # For continuous metrics, use t-distribution
            se = std / math.sqrt(n)
            t_crit = stats.t.ppf(0.975, n - 1)  # 95% CI
            ci = (mean - t_crit * se, mean + t_crit * se)

    except ImportError:
        ci = None

    return {
        "metric": metric,
        "n": n,
        "mean": mean,
        "median": median,
        "std": std,
        "min": min_val,
        "max": max_val,
        "ci": ci,
    }
