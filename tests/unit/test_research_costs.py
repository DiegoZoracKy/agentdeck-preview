"""Tests for research metadata capturing API costs."""

from typing import Optional, List

import pytest

from agentdeck import AgentDeck
from agentdeck.controllers import ActionOnlyController
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players.mock import MockPlayer
from agentdeck.research import compare_models
from agentdeck.core.types import MatchResult


class CostTrackingMockPlayer(MockPlayer):
    """Mock player that simulates API spend by incrementing total_cost."""

    def __init__(self, name: str, actions: Optional[List[str]] = None):
        super().__init__(name, actions=actions or ["ATTACK"], controller=ActionOnlyController())
        self.total_cost = 0.0

    def get_response(self, prompt: str) -> str:
        # Increment by a fixed amount for every LLM interaction (handshake + turns).
        self.total_cost += 0.25
        return super().get_response(prompt)


class ConclusionCostMockPlayer(MockPlayer):
    """Mock player that only incurs cost during conclusion phase."""

    def __init__(self, name: str, actions: Optional[List[str]] = None):
        super().__init__(name, actions=actions or ["ATTACK"], controller=ActionOnlyController())
        self.total_cost = 0.0

    def conclude(self, result, *, match_context):
        self.total_cost += 0.5  # Simulate reflection spend
        super().conclude(result, match_context=match_context)
        return "Reflection complete"


def test_match_metadata_includes_player_costs():
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("A")
    player_b = CostTrackingMockPlayer("B")

    deck = AgentDeck(game=game)
    results = deck.play([player_a, player_b], matches=1, seed=123)

    match = results.matches[0]
    assert "cost" in match.metadata
    assert "player_costs" in match.metadata
    assert match.metadata["cost"] > 0
    assert match.metadata["player_costs"]["A"] > 0
    assert match.metadata["player_costs"]["B"] > 0


def test_compare_models_reports_total_cost():
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Aggressive")
    player_b = CostTrackingMockPlayer("Cautious")

    cost_a_before = player_a.total_cost
    cost_b_before = player_b.total_cost

    matches = 2
    result = compare_models(
        model_a=player_a,
        model_b=player_b,
        game=game,
        matches=matches,
        seed=42,
    )

    total_delta = (player_a.total_cost - cost_a_before) + (player_b.total_cost - cost_b_before)
    assert total_delta > 0
    assert result.metadata["total_cost"] == pytest.approx(total_delta)
    assert result.metadata["avg_cost_per_match"] == pytest.approx(total_delta / matches)


def test_calculate_costs_aggregates_from_metadata():
    """AgentDeck._calculate_costs should sum per-match metadata deltas."""

    deck = AgentDeck(game=FixedDamageGame())
    try:
        match1 = MatchResult(
            winner="A",
            final_state={},
            events=[],
            seed=1,
            metadata={"player_costs": {"A": 0.5, "B": 0.3}},
        )
        match2 = MatchResult(
            winner="B",
            final_state={},
            events=[],
            seed=2,
            metadata={"player_costs": {"A": 0.1, "B": 0.7}},
        )

        total, player_costs = deck._calculate_costs([match1, match2])

        assert total == pytest.approx(1.6)
        assert player_costs["A"] == pytest.approx(0.6)
        assert player_costs["B"] == pytest.approx(1.0)
    finally:
        deck._cleanup()


def test_player_costs_in_batch_match_refs():
    """
    Verify that player_costs field from match metadata is included in batch match_refs.

    This is critical for post-hoc cost analysis (SPEC-RESEARCH v1.1.0 MA1, MA3).
    CostAnalysis.from_session() reads from batch match_refs, so player_costs must be present.

    Regression test for bug: Cost aggregation underreporting due to missing player_costs in batch.
    """
    import json
    import tempfile
    from pathlib import Path

    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Player-A")
    player_b = CostTrackingMockPlayer("Player-B")

    # Run matches with recorder enabled
    with tempfile.TemporaryDirectory() as tmpdir:
        from agentdeck import AgentDeckConfig

        # Create config with custom run directory
        config = AgentDeckConfig(seed=42, run_dir=tmpdir)

        deck = AgentDeck(game=game, session=config)
        deck.play([player_a, player_b], matches=2)
        session_id = deck.session.session_id
        deck._cleanup()

        # Read batch recording from disk (recorder saves to session.record_directory)
        records_dir = Path(tmpdir) / session_id / "records"
        batch_files = list(records_dir.glob("batch_*.json"))
        assert batch_files, f"No batch files found in {records_dir}"
        batch_file = batch_files[0]

        with open(batch_file, "r") as f:
            batch_data = json.load(f)

        # Verify match_refs contain player_costs
        match_refs = batch_data.get("match_refs", [])
        assert len(match_refs) == 2, f"Expected 2 match_refs, got {len(match_refs)}"

        for match_ref in match_refs:
            # Critical assertion: player_costs must be present in match_refs
            assert "player_costs" in match_ref, (
                f"player_costs missing from match_ref {match_ref['match_id']}. "
                "This breaks CostAnalysis.from_session() post-hoc analysis."
            )

            # Verify structure
            player_costs = match_ref["player_costs"]
            assert isinstance(player_costs, dict), "player_costs must be a dict"
            assert "Player-A" in player_costs, "Player-A cost missing"
            assert "Player-B" in player_costs, "Player-B cost missing"

            # Verify non-zero costs (CostTrackingMockPlayer increments by 0.25 per interaction)
            assert player_costs["Player-A"] > 0, "Player-A cost should be > 0"
            assert player_costs["Player-B"] > 0, "Player-B cost should be > 0"

            # Optional: cost field should also be present (total match cost)
            assert "cost" in match_ref, "cost field missing from match_ref"
            assert match_ref["cost"] == pytest.approx(
                player_costs["Player-A"] + player_costs["Player-B"]
            ), "cost should equal sum of player_costs"


def test_conclusion_costs_included_in_metadata():
    """Costs incurred during conclude() should be captured in match metadata."""
    game = FixedDamageGame()
    player_a = ConclusionCostMockPlayer("A")
    player_b = ConclusionCostMockPlayer("B")

    with AgentDeck(game=game) as deck:
        results = deck.play([player_a, player_b], matches=1, seed=123)

    match = results.matches[0]
    assert match.metadata["player_costs"]["A"] == pytest.approx(player_a.total_cost)
    assert match.metadata["player_costs"]["B"] == pytest.approx(player_b.total_cost)
    assert match.metadata["cost"] == pytest.approx(player_a.total_cost + player_b.total_cost)
    assert match.metadata["cost"] >= 1.0  # Each player adds 0.5 during conclusion


def test_cost_analysis_no_double_counting(tmp_path):
    """CostAnalysis should sum per-match deltas without double counting."""
    from pathlib import Path
    from agentdeck import AgentDeckConfig
    from agentdeck.research.cost_analysis import CostAnalysis

    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("A")
    player_b = CostTrackingMockPlayer("B")

    run_dir = Path(tmp_path)
    config = AgentDeckConfig(seed=42, run_dir=str(run_dir))

    with AgentDeck(game=game, session=config) as deck:
        deck.play([player_a, player_b], matches=3, seed=99)
        session_id = deck.session.session_id

    expected_total = player_a.total_cost + player_b.total_cost
    analysis = CostAnalysis.from_session(session_id, recordings_dir=run_dir)

    assert analysis.total_cost == pytest.approx(expected_total)
    for name, cost in analysis.player_costs.items():
        if name == player_a.name:
            assert cost == pytest.approx(player_a.total_cost)
        if name == player_b.name:
            assert cost == pytest.approx(player_b.total_cost)
