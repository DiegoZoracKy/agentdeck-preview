from __future__ import annotations

import copy
import json

from agentdeck.research import export as research_export

from agentdeck.games.examples.archivist_choice_behavioral import (
    ArchivistChoiceBehavioralScorer,
)
from agentdeck.research.behavioral import compute_behavioral_profile


def _payload(*, match_id: str = "match_001", alpha_action: str = "RESTORE") -> dict:
    alpha_entries = [
        {
            "manuscript_id": "field-journal",
            "action": alpha_action,
            "best_action": "RESTORE",
            "score_delta": 3 if alpha_action == "RESTORE" else 1,
        },
        {
            "manuscript_id": "letters",
            "action": "CATALOG",
            "best_action": "CATALOG",
            "score_delta": 2,
        },
    ]
    beta_entries = [
        {
            "manuscript_id": "field-journal",
            "action": "RESTORE",
            "best_action": "RESTORE",
            "score_delta": 3,
        },
        {
            "manuscript_id": "letters",
            "action": "CATALOG",
            "best_action": "CATALOG",
            "score_delta": 2,
        },
    ]
    return {
        "match_id": match_id,
        "game": "ArchivistChoiceGame",
        "players": ["Alpha", "Beta"],
        "winner": "Alpha",
        "final_state": {
            "scores": {"Alpha": sum(item["score_delta"] for item in alpha_entries), "Beta": 5},
            "processed": {"Alpha": alpha_entries, "Beta": beta_entries},
        },
        "events": [
            {"type": "gameplay", "data": {"turn_context": {"turn_number": 1}}},
            {"type": "gameplay", "data": {"turn_context": {"turn_number": 2}}},
            {"type": "gameplay", "data": {"turn_context": {"turn_number": 3}}},
            {"type": "gameplay", "data": {"turn_context": {"turn_number": 4}}},
        ],
        "metadata": {
            "player_summaries": [
                {"name": "Alpha", "controller": "ActionOnlyController"},
                {"name": "Beta", "controller": "ActionOnlyController"},
            ],
            "match": {
                "players": ["Alpha", "Beta"],
                "turns": 4,
                "duration": 1.0,
                "cost": 0.0,
                "first_player": {"name": "Alpha"},
            },
        },
    }


def test_archivist_profile_scores_recorded_final_state_and_post_hoc_action_fit() -> None:
    profile = compute_behavioral_profile(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=[_payload()],
        profile_id="auto",
    )

    assert profile is not None
    assert profile["profile_id"] == "archivist_choice_behavioral"
    assert profile["coverage"] == {
        "matches_total": 1,
        "matches_evaluable": 1,
        "turns_total": 4,
        "turns_evaluable": 4,
    }
    assert profile["per_player"]["Alpha"] == {
        "mean_final_score": 5.0,
        "mean_processed_cases": 2.0,
        "best_action_rate": 1.0,
        "mean_score_delta_per_processed_case": 2.5,
    }
    assert profile["state_metrics"]["by_manuscript"]["field-journal"] == {
        "processed_cases": 2,
        "best_action_rate": 1.0,
        "mean_score_delta": 3.0,
    }
    assert profile["quality_flags"] == {"complete": True, "unsupported_metrics": []}


def test_archivist_profile_is_deterministic_and_does_not_mutate_records() -> None:
    records = [
        _payload(match_id="match_001"),
        _payload(match_id="match_002", alpha_action="CATALOG"),
    ]
    original = copy.deepcopy(records)
    scorer = ArchivistChoiceBehavioralScorer()

    first = scorer.score(players=[{"name": "Alpha"}, {"name": "Beta"}], match_payloads=records)
    second = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}], match_payloads=list(reversed(records))
    )

    assert scorer.canonical_json(first) == scorer.canonical_json(second)
    assert records == original
    assert (
        json.loads(scorer.canonical_json(first))["per_player"]["Alpha"]["best_action_rate"] == 0.75
    )


def test_archivist_profile_surfaces_missing_post_hoc_fields_without_fabricating_values() -> None:
    record = _payload()
    del record["final_state"]["processed"]["Alpha"][0]["best_action"]
    del record["final_state"]["processed"]["Beta"][0]["score_delta"]
    profile = ArchivistChoiceBehavioralScorer().score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=[record],
    )

    assert profile["per_player"]["Alpha"]["best_action_rate"] == 1.0
    assert profile["per_player"]["Beta"]["mean_score_delta_per_processed_case"] == 2.0
    assert profile["quality_flags"]["complete"] is False
    assert "best_action_rate" in profile["quality_flags"]["unsupported_metrics"]
    assert "mean_score_delta_per_processed_case" in profile["quality_flags"]["unsupported_metrics"]


def test_export_results_resolves_archivist_profile_automatically(tmp_path, monkeypatch) -> None:
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    (records_dir / "match_001.json").write_text(json.dumps(_payload()), encoding="utf-8")
    monkeypatch.setattr(
        research_export,
        "validate_artifact_invariants",
        lambda payloads: {
            "matches_checked": len(payloads),
            "all_passed": True,
            "checks": {},
            "failures": [],
        },
    )

    output_dir = tmp_path / "package"
    research_export.export_results(
        records_dir,
        output_dir,
        experiment_id="archivist-profile-export",
        include_generated_at=False,
    )

    results = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    assert results["behavioral_profile"]["profile_id"] == "archivist_choice_behavioral"
    assert results["behavioral_profile"]["per_player"]["Alpha"]["mean_final_score"] == 5.0
