"""Deterministic comparison of a declared baseline and intervention."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
import re

from scipy.stats import fisher_exact
from statsmodels.stats.proportion import confint_proportions_2indep


class InterventionComparisonError(ValueError):
    """Raised when exact intervention evidence cannot be compared."""


@dataclass(frozen=True)
class OutcomeEvidence:
    player: str
    wins: int
    decisive_matches: int
    total_matches: int
    win_rate: float
    confidence_interval: tuple[float, float]


@dataclass(frozen=True)
class InterventionComparisonArtifact:
    schema: str
    version: str
    kind: str
    generated_at: str
    design: str
    test_name: str
    confidence_level: float
    baseline_run_id: str
    intervention_run_id: str
    baseline_results_sha256: str
    intervention_results_sha256: str
    changed_paths: tuple[str, ...]
    baseline: OutcomeEvidence
    intervention: OutcomeEvidence
    observed_difference: float
    difference_confidence_interval: tuple[float, float]
    p_value: float
    is_significant: bool
    evidence_classification: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[a-fA-F0-9]{64}", str(value)))


def _outcome(results: Mapping[str, Any], player: str) -> OutcomeEvidence:
    summary = results.get("summary")
    statistics = results.get("statistics")
    if not isinstance(summary, Mapping) or not isinstance(statistics, Mapping):
        raise InterventionComparisonError("Results must contain summary and statistics mappings.")
    players = statistics.get("players")
    if not isinstance(players, Mapping) or player not in players:
        raise InterventionComparisonError(
            f"Focal player {player!r} is absent from Core statistics."
        )
    item = players[player]
    decisive = int(summary.get("decisive_matches", statistics.get("n_decisive", 0)))
    total = int(summary.get("total_matches", statistics.get("n_total", 0)))
    wins = int(item.get("wins", 0))
    if decisive <= 0:
        raise InterventionComparisonError("Each result requires at least one decisive match.")
    if wins < 0 or wins > decisive or total < decisive:
        raise InterventionComparisonError("Core outcome counts are internally inconsistent.")
    ci = item.get("ci")
    if not isinstance(ci, Sequence) or len(ci) != 2:
        raise InterventionComparisonError(
            "Focal player statistics require a two-value confidence interval."
        )
    return OutcomeEvidence(
        player=player,
        wins=wins,
        decisive_matches=decisive,
        total_matches=total,
        win_rate=float(item.get("win_rate", wins / decisive)),
        confidence_interval=(float(ci[0]), float(ci[1])),
    )


def compare_intervention_results(
    baseline_results: Mapping[str, Any],
    intervention_results: Mapping[str, Any],
    *,
    baseline_player: str,
    intervention_player: str,
    baseline_run_id: str,
    intervention_run_id: str,
    baseline_results_sha256: str,
    intervention_results_sha256: str,
    changed_paths: Sequence[str],
    preserved_paths_match: bool,
    baseline_supports_finding: bool,
    intervention_supports_finding: bool,
    confidence_level: float = 0.95,
    generated_at: str | None = None,
) -> InterventionComparisonArtifact:
    """Compare focal binary outcomes without inferring lineage or causality."""
    if not _valid_sha256(baseline_results_sha256) or not _valid_sha256(intervention_results_sha256):
        raise InterventionComparisonError("Exact source results require valid SHA-256 values.")
    normalized_paths = tuple(str(path) for path in changed_paths if str(path))
    if not normalized_paths or not preserved_paths_match:
        raise InterventionComparisonError(
            "A non-empty method change and preserved-path parity are required."
        )
    if not 0 < confidence_level < 1:
        raise InterventionComparisonError("confidence_level must be between zero and one.")

    baseline = _outcome(baseline_results, baseline_player)
    intervention = _outcome(intervention_results, intervention_player)
    alpha = 1.0 - confidence_level
    low, high = confint_proportions_2indep(
        intervention.wins,
        intervention.decisive_matches,
        baseline.wins,
        baseline.decisive_matches,
        method="newcomb",
        compare="diff",
        alpha=alpha,
        correction=True,
    )
    failures_intervention = intervention.decisive_matches - intervention.wins
    failures_baseline = baseline.decisive_matches - baseline.wins
    _, p_value = fisher_exact(
        [[intervention.wins, failures_intervention], [baseline.wins, failures_baseline]],
        alternative="two-sided",
    )
    supports_finding = baseline_supports_finding and intervention_supports_finding
    evidence_classification = (
        "comparative_evidence" if supports_finding else "observational_direction_only"
    )
    limitations = ["Separate runs are analyzed as independent binary samples."]
    if not supports_finding:
        limitations.append("At least one execution profile does not support a finding.")
    if low <= 0 <= high:
        limitations.append("The confidence interval for the difference includes zero.")

    return InterventionComparisonArtifact(
        schema="agentdeck.research.intervention_comparison",
        version="0.1.0",
        kind="baseline_intervention_difference",
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
        design="independent_binary",
        test_name="two_sided_fisher_exact_with_newcombe_difference_interval",
        confidence_level=confidence_level,
        baseline_run_id=baseline_run_id,
        intervention_run_id=intervention_run_id,
        baseline_results_sha256=baseline_results_sha256,
        intervention_results_sha256=intervention_results_sha256,
        changed_paths=normalized_paths,
        baseline=baseline,
        intervention=intervention,
        observed_difference=intervention.win_rate - baseline.win_rate,
        difference_confidence_interval=(float(low), float(high)),
        p_value=float(p_value),
        is_significant=bool(supports_finding and p_value < alpha),
        evidence_classification=evidence_classification,
        limitations=tuple(limitations),
    )
