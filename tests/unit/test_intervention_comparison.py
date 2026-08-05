import pytest

from agentdeck.research import InterventionComparisonError, compare_intervention_results


def result(player, wins, decisive, ci):
    return {
        "summary": {"total_matches": decisive, "decisive_matches": decisive},
        "statistics": {
            "n_total": decisive,
            "n_decisive": decisive,
            "players": {player: {"wins": wins, "win_rate": wins / decisive, "ci": ci}},
        },
    }


def compare(**overrides):
    values = dict(
        baseline_results=result("baseline", 0, 1, [0.0, 0.79345]),
        intervention_results=result("intervention", 1, 1, [0.20655, 1.0]),
        baseline_player="baseline",
        intervention_player="intervention",
        baseline_run_id="run-baseline",
        intervention_run_id="run-intervention",
        baseline_results_sha256="a" * 64,
        intervention_results_sha256="b" * 64,
        changed_paths=["agents.cohorts[0].controller"],
        preserved_paths_match=True,
        baseline_supports_finding=False,
        intervention_supports_finding=False,
        generated_at="2026-08-04T00:00:00+00:00",
    )
    values.update(overrides)
    return compare_intervention_results(**values)


def test_preview_opposite_outcomes_remain_observational_and_uncertain():
    artifact = compare()
    assert artifact.observed_difference == 1.0
    assert artifact.difference_confidence_interval[0] < 0
    assert artifact.difference_confidence_interval[1] == pytest.approx(1.0)
    assert artifact.p_value == 1.0
    assert artifact.is_significant is False
    assert artifact.evidence_classification == "observational_direction_only"
    assert artifact.baseline_results_sha256 == "a" * 64


def test_evidence_profile_can_report_significance_without_causal_prose():
    artifact = compare(
        baseline_results=result("baseline", 5, 48, [0.04, 0.22]),
        intervention_results=result("intervention", 35, 48, [0.59, 0.83]),
        baseline_supports_finding=True,
        intervention_supports_finding=True,
    )
    assert artifact.evidence_classification == "comparative_evidence"
    assert artifact.is_significant is True
    assert artifact.difference_confidence_interval[0] > 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"baseline_results_sha256": "bad"},
        {"changed_paths": []},
        {"preserved_paths_match": False},
        {"baseline_player": "missing"},
        {
            "baseline_results": result("baseline", 0, 1, [0, 1])
            | {"summary": {"total_matches": 1, "decisive_matches": 0}}
        },
    ],
)
def test_invalid_comparisons_fail_explicitly(overrides):
    with pytest.raises(InterventionComparisonError):
        compare(**overrides)
