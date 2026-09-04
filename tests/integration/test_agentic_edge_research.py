from pathlib import Path

import pytest

from agentdeck import (
    build_record_corpus,
    derive_evidence,
    execute_prepared_study,
    load_measure,
    prepare_game_research_profile,
    prepare_measure,
    prepare_study,
    select_study,
)

PACKAGE = (
    Path(__file__).resolve().parents[2] / "research" / "2026-04-27-agentic-edge-strategy-stack"
)


@pytest.mark.integration
@pytest.mark.slow
def test_agentic_edge_preflight_closes_study_to_evidence_without_providers(tmp_path):
    study = prepare_study(PACKAGE)

    assert study.total_matches == 540
    assert len(study.definition.cells) == 19
    assert len(study.execution_groups) == 4
    assert {
        item.profile.game_name
        for item in (
            prepare_game_research_profile(PACKAGE / "fixed-damage-research-profile.yaml"),
            prepare_game_research_profile(PACKAGE / "variable-damage-research-profile.yaml"),
        )
    } == {"FixedDamageGame", "VariableDamageGame"}

    execution = execute_prepared_study(
        PACKAGE,
        study,
        select_study(study, phase_ids=["p0"]),
        output_root=tmp_path / "runs",
    )
    corpus = build_record_corpus(
        study,
        cell_ids=["p0-fd-bot-smoke", "p0-vd-bot-smoke"],
        study_executions=[execution],
    )

    assert execution.complete is True
    assert len(execution.records) == 12
    assert corpus.complete is True
    assert len(corpus.records) == 12
    for measure_id in ("agentic-edge-outcomes", "combat-behavior"):
        evidence = derive_evidence(
            study,
            prepare_measure(load_measure(PACKAGE, measure_id)),
            corpus,
        )
        assert evidence.derivation_status == "complete"
        assert evidence.results
