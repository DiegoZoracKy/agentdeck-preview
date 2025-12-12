"""Tests for post-hoc statistical analysis from recordings.

Per SPEC-RESEARCH v1.1.0 §10:
- Test post-hoc analysis from recordings (PH1, PH2)
- Test cross-player comparison (CPC1, CPC2, CPC3, CPC4, CPC5)
- Test spectator wrappers (PH4)
- Test missing recordings error (PH5)
- Test multi-session comparison and meta-analysis
"""

from pathlib import Path
from typing import List, Optional

import pytest

from agentdeck import AgentDeck
from agentdeck.controllers import ActionOnlyController
from agentdeck.core.session import AgentDeckConfig
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players.mock import MockPlayer
from agentdeck.research import (
    ComparisonAnalysis,
    CostAnalysis,
    PerformanceAnalysis,
    StatisticalAnalysis,
)
from agentdeck.spectators import (
    CostAnalysisSpectator,
    PerformanceTrackerSpectator,
    StatisticalAnalysisSpectator,
)


class CostTrackingMockPlayer(MockPlayer):
    """Mock player that simulates API costs."""

    def __init__(self, name: str, actions: Optional[List[str]] = None):
        super().__init__(name, actions=actions or ["ATTACK"], controller=ActionOnlyController())
        self.total_cost = 0.0

    def get_response(self, prompt: str) -> str:
        # Increment cost for each interaction
        self.total_cost += 0.01
        return super().get_response(prompt)

    def get_summary(self):
        """Return configuration summary including total_cost."""
        summary = super().get_summary()
        summary["total_cost"] = self.total_cost
        return summary


@pytest.fixture
def temp_recordings_dir(tmp_path):
    """Create temporary recordings directory."""
    recordings_dir = tmp_path / "agentdeck_runs"
    recordings_dir.mkdir()
    return recordings_dir


@pytest.fixture
def sample_session(temp_recordings_dir):
    """Create a sample session with recordings for testing."""
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    config = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck = AgentDeck(game=game, session=config)
    session_id = deck.session.session_id
    results = deck.play([player_a, player_b], matches=10, seed=42)

    return session_id, temp_recordings_dir


@pytest.fixture
def three_player_session(temp_recordings_dir):
    """Create a 3-player session for cross-player comparison tests."""
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])
    player_c = CostTrackingMockPlayer("Charlie", actions=["ATTACK", "ATTACK"])

    config = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck = AgentDeck(game=game, session=config)
    # Create a custom 3-player game or use sequential matches
    results = deck.play([player_a, player_b], matches=5, seed=42)
    results2 = deck.play([player_a, player_c], matches=5, seed=43)
    results3 = deck.play([player_b, player_c], matches=5, seed=44)

    return results.session_id, temp_recordings_dir


# ==============================================================================
# PH1, PH2: Post-hoc Analysis from Recordings
# ==============================================================================


def test_statistical_analysis_from_session(sample_session):
    """Test PH1: Load and analyze from recordings directory."""
    session_id, recordings_dir = sample_session

    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)

    # Should load all matches
    assert analysis.total_matches == 10
    assert "Alice" in analysis.player_names
    assert "Bob" in analysis.player_names

    # Should compute win rates
    win_rates = analysis.compute_win_rates()
    assert "Alice" in win_rates
    assert "Bob" in win_rates
    assert 0.0 <= win_rates["Alice"] <= 1.0
    assert 0.0 <= win_rates["Bob"] <= 1.0


def test_statistical_analysis_confidence_intervals(sample_session):
    """Test PH2: Compute Wilson score confidence intervals."""
    session_id, recordings_dir = sample_session

    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)
    cis = analysis.compute_confidence_intervals(confidence_level=0.95)

    for player in analysis.player_names:
        assert player in cis
        lower, upper = cis[player]
        assert 0.0 <= lower <= 1.0
        assert 0.0 <= upper <= 1.0
        assert lower <= upper


def test_statistical_analysis_significance_tests(sample_session):
    """Test PH2: Compute binomial significance tests."""
    session_id, recordings_dir = sample_session

    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)
    p_values = analysis.compute_significance_tests()

    for player in analysis.player_names:
        assert player in p_values
        assert 0.0 <= p_values[player] <= 1.0


def test_statistical_analysis_effect_sizes(sample_session):
    """Test PH2: Compute Cohen's h effect sizes."""
    session_id, recordings_dir = sample_session

    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)
    effect_sizes = analysis.compute_effect_sizes()

    for player in analysis.player_names:
        assert player in effect_sizes
        # Cohen's h can be negative or positive
        assert isinstance(effect_sizes[player], float)


# ==============================================================================
# CPC1, CPC2, CPC3, CPC4, CPC5: Cross-Player Comparison
# ==============================================================================


def test_cross_player_comparison_two_players(sample_session):
    """Test CPC1: Automatic pairwise comparison for 2 players."""
    session_id, recordings_dir = sample_session

    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)
    comparison = analysis.compute_pairwise_comparisons()

    # Should have direct comparison
    assert comparison.player_a is not None
    assert comparison.player_b is not None
    assert comparison.win_rate_diff is not None
    assert comparison.p_value is not None
    assert comparison.is_significant is not None

    # Should have proper significance symbol
    assert comparison.significance_symbol in ["✅", "❌", "−"]


def test_cross_player_comparison_print_summary(sample_session):
    """Test CPC3: Print comparison summary."""
    session_id, recordings_dir = sample_session

    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)

    # Should not raise error
    analysis.print_summary()


def test_cross_player_comparison_export_markdown(sample_session, tmp_path):
    """Test CPC3: Export markdown report."""
    session_id, recordings_dir = sample_session

    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)
    output_path = tmp_path / "analysis.md"

    analysis.export_markdown(output_path)

    # Should create file
    assert output_path.exists()

    # Should contain key sections
    content = output_path.read_text()
    assert "Statistical Analysis" in content
    assert "Win Rates" in content
    assert "Confidence Intervals" in content


# ==============================================================================
# PH5: Error Handling
# ==============================================================================


def test_missing_session_raises_error(temp_recordings_dir):
    """Test PH5: Graceful error for missing session."""
    with pytest.raises(FileNotFoundError, match="Session directory not found"):
        StatisticalAnalysis.from_session("nonexistent_session", temp_recordings_dir)


def test_empty_session_directory(temp_recordings_dir):
    """Test PH5: Handle empty session directory gracefully."""
    # Create empty session directory with unified structure
    empty_session = temp_recordings_dir / "session_empty"
    empty_session.mkdir()
    records_dir = empty_session / "records"
    records_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="No batch recording found"):
        StatisticalAnalysis.from_session("session_empty", temp_recordings_dir)


# ==============================================================================
# Performance Analysis
# ==============================================================================


def test_performance_analysis_from_session(sample_session):
    """Test performance analysis from recordings."""
    session_id, recordings_dir = sample_session

    analysis = PerformanceAnalysis.from_session(session_id, recordings_dir)

    # Should extract duration metrics
    assert analysis.total_duration > 0
    assert analysis.avg_match_duration > 0
    assert analysis.matches_per_second > 0


def test_performance_analysis_with_baseline(sample_session):
    """Test performance analysis with baseline comparison."""
    session_id, recordings_dir = sample_session

    # Set a baseline
    baseline_duration = 100.0
    analysis = PerformanceAnalysis.from_session(
        session_id, recordings_dir, baseline_duration=baseline_duration
    )

    speedup = analysis.compute_speedup()
    assert speedup is not None
    assert speedup > 0


def test_performance_analysis_concurrency_efficiency(sample_session):
    """Test concurrency efficiency calculation."""
    session_id, recordings_dir = sample_session

    analysis = PerformanceAnalysis.from_session(session_id, recordings_dir)

    # May be None if concurrency=1
    efficiency = analysis.compute_concurrency_efficiency()
    if efficiency is not None:
        assert 0.0 <= efficiency <= 1.0


# ==============================================================================
# Cost Analysis
# ==============================================================================


def test_cost_analysis_from_session(sample_session):
    """Test cost analysis from recordings."""
    session_id, recordings_dir = sample_session

    analysis = CostAnalysis.from_session(session_id, recordings_dir)

    # Should extract costs
    assert analysis.total_cost > 0
    assert "Alice" in analysis.player_costs
    assert "Bob" in analysis.player_costs


def test_cost_analysis_per_win(sample_session):
    """Test cost per win calculation."""
    session_id, recordings_dir = sample_session

    analysis = CostAnalysis.from_session(session_id, recordings_dir)
    cost_per_win = analysis.compute_cost_per_win()

    # Should have entries for both players
    assert "Alice" in cost_per_win
    assert "Bob" in cost_per_win


def test_cost_analysis_with_baseline(sample_session):
    """Test cost analysis with baseline."""
    session_id, recordings_dir = sample_session

    baseline_cost = 0.10
    analysis = CostAnalysis.from_session(session_id, recordings_dir, baseline_cost=baseline_cost)

    savings = analysis.compute_cost_savings()
    assert savings is not None


# ==============================================================================
# Multi-Session Comparison
# ==============================================================================


def test_multi_session_comparison(temp_recordings_dir):
    """Test multi-session comparison and meta-analysis."""
    # Create two sessions
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    config1 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck1 = AgentDeck(game=game, session=config1)
    session_id1 = deck1.session.session_id
    results1 = deck1.play([player_a, player_b], matches=5, seed=42)

    config2 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck2 = AgentDeck(game=game, session=config2)
    session_id2 = deck2.session.session_id
    results2 = deck2.play([player_a, player_b], matches=5, seed=43)

    # Compare sessions
    comparison = ComparisonAnalysis([session_id1, session_id2], temp_recordings_dir)

    # Should load both sessions
    assert len(comparison.analyses) == 2

    # Should compute meta-analysis
    meta = comparison.meta_analysis()
    assert meta.total_matches == 10
    assert "Alice" in meta.aggregate_win_rates
    assert "Bob" in meta.aggregate_win_rates


def test_multi_session_comparison_table(temp_recordings_dir):
    """Test comparison table generation."""
    # Create two sessions
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    config1 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck1 = AgentDeck(game=game, session=config1)
    session_id1 = deck1.session.session_id
    results1 = deck1.play([player_a, player_b], matches=5, seed=42)

    config2 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck2 = AgentDeck(game=game, session=config2)
    session_id2 = deck2.session.session_id
    results2 = deck2.play([player_a, player_b], matches=5, seed=43)

    # Compare sessions
    comparison = ComparisonAnalysis([session_id1, session_id2], temp_recordings_dir)

    # Should generate comparison table
    table = comparison.compare_win_rates()
    assert len(table.sessions) == 2
    assert "Alice" in table.metrics
    assert "Bob" in table.metrics


def test_multi_session_print_comparison(temp_recordings_dir):
    """Test comparison table printing."""
    # Create two sessions
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    config1 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck1 = AgentDeck(game=game, session=config1)
    session_id1 = deck1.session.session_id
    results1 = deck1.play([player_a, player_b], matches=3, seed=42)

    config2 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck2 = AgentDeck(game=game, session=config2)
    session_id2 = deck2.session.session_id
    results2 = deck2.play([player_a, player_b], matches=3, seed=43)

    # Compare sessions
    comparison = ComparisonAnalysis([session_id1, session_id2], temp_recordings_dir)

    # Should not raise error
    comparison.print_comparison_table()


def test_multi_session_export_markdown(temp_recordings_dir, tmp_path):
    """Test comparison markdown export."""
    # Create two sessions
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    config1 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck1 = AgentDeck(game=game, session=config1)
    session_id1 = deck1.session.session_id
    results1 = deck1.play([player_a, player_b], matches=3, seed=42)

    config2 = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck2 = AgentDeck(game=game, session=config2)
    session_id2 = deck2.session.session_id
    results2 = deck2.play([player_a, player_b], matches=3, seed=43)

    # Compare sessions
    comparison = ComparisonAnalysis([session_id1, session_id2], temp_recordings_dir)

    output_path = tmp_path / "comparison.md"
    comparison.export_markdown(output_path)

    # Should create file
    assert output_path.exists()

    # Should contain key sections
    content = output_path.read_text()
    assert "Cross-Session Comparison" in content
    assert "Meta-Analysis" in content


# ==============================================================================
# PH4: Spectator Wrappers (Thin, No Logic Duplication)
# ==============================================================================


def test_statistical_analysis_spectator(temp_recordings_dir):
    """Test PH4: StatisticalAnalysisSpectator is thin wrapper."""
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    spectator = StatisticalAnalysisSpectator(
        print_on_complete=False,  # Don't print during test
        save_report=True,
        # Let spectator auto-generate path with session_id
    )

    config = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck = AgentDeck(game=game, spectators=[spectator], session=config)
    session_id = deck.session.session_id
    deck.play([player_a, player_b], matches=5, seed=42)

    # Should create report via spectator (auto-generated filename)
    report_path = Path(f"analysis_{session_id}.md")
    assert report_path.exists()


def test_performance_tracker_spectator(temp_recordings_dir):
    """Test PH4: PerformanceTrackerSpectator is thin wrapper."""
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    spectator = PerformanceTrackerSpectator(
        print_on_complete=False,  # Don't print during test
        baseline_duration=100.0,
    )

    config = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck = AgentDeck(game=game, spectators=[spectator], session=config)
    results = deck.play([player_a, player_b], matches=5, seed=42)

    # Should complete without error (performance analysis happens in spectator)
    assert len(results.matches) == 5


def test_cost_analysis_spectator(temp_recordings_dir):
    """Test PH4: CostAnalysisSpectator is thin wrapper."""
    game = FixedDamageGame()
    player_a = CostTrackingMockPlayer("Alice", actions=["ATTACK"])
    player_b = CostTrackingMockPlayer("Bob", actions=["POTION", "ATTACK"])

    spectator = CostAnalysisSpectator(
        print_on_complete=False,  # Don't print during test
        baseline_cost=0.05,
    )

    config = AgentDeckConfig(run_dir=str(temp_recordings_dir))
    deck = AgentDeck(game=game, spectators=[spectator], session=config)
    results = deck.play([player_a, player_b], matches=5, seed=42)

    # Should complete without error (cost analysis happens in spectator)
    assert len(results.matches) == 5


# ==============================================================================
# PH3: Graceful Degradation Without scipy
# ==============================================================================


def test_graceful_degradation_without_scipy(sample_session, monkeypatch):
    """Test PH3: Graceful degradation when scipy not available."""
    session_id, recordings_dir = sample_session

    # Mock scipy import to fail
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "scipy" or name.startswith("scipy."):
            raise ImportError("scipy not available")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Should still work with fallback implementations
    analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)

    # Should compute win rates (doesn't need scipy)
    win_rates = analysis.compute_win_rates()
    assert "Alice" in win_rates
    assert "Bob" in win_rates

    # Confidence intervals may use fallback
    cis = analysis.compute_confidence_intervals()
    assert "Alice" in cis
    assert "Bob" in cis
