"""Post-hoc statistical analysis from recorded sessions.

Per SPEC-RESEARCH v1.1.0 §4.2, §6.8, §6.9:
- StatisticalAnalysis.from_session(): Load and analyze recordings
- Compute win rates, confidence intervals, p-values, effect sizes
- Automatic cross-player comparisons (CPC1-CPC5)
- PH1-PH5: Read from agentdeck_runs/, validate recordings, handle errors
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .statistical import (
    calculate_confidence_interval,
    calculate_effect_size,
    statistical_significance,
)


@dataclass
class ComparisonStats:
    """Statistics for a single player-vs-player comparison (SPEC-RESEARCH v1.1.0 §5)."""

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
    """
    Cross-player comparison results (SPEC-RESEARCH v1.1.0 §5).

    For 2-player games: Direct comparison fields (player_a, player_b, etc.)
    For 3+ player games: Comparison matrix
    """

    comparisons: Dict[Tuple[str, str], ComparisonStats]
    matrix: List[List[str]]  # Formatted matrix for display

    # Direct comparison fields for 2-player case (CPC1)
    player_a: Optional[str] = None
    player_b: Optional[str] = None
    win_rate_diff: Optional[float] = None
    p_value: Optional[float] = None
    is_significant: Optional[bool] = None
    significance_symbol: Optional[str] = None


class StatisticalAnalysis:
    """
    Post-hoc statistical analysis from recorded sessions.

    Per SPEC-RESEARCH v1.1.0:
    - Reads recordings from agentdeck_runs/session_id/
    - Computes win rates, CIs, p-values, effect sizes
    - Automatically computes cross-player comparisons

    Invariants:
    - PH1: Reads from agentdeck_runs/session_id/
    - PH2: Validates batch + match recordings exist
    - CPC1: Auto-compute 2-player direct comparison
    - CPC2: Auto-compute 3+ player pairwise matrix
    """

    def __init__(self, session_dir: Path, session_id: Optional[str] = None):
        """
        Initialize analysis for a session.

        Args:
            session_dir: Path to recordings directory (e.g., agentdeck_runs/session_id/records/)
            session_id: Session identifier (defaults to parent directory name if not provided)
        """
        self.session_dir = Path(session_dir)
        # Extract session_id from parent directory if not provided
        self.session_id = session_id or session_dir.parent.name

        # Loaded data
        self.batch_data: Optional[Dict[str, Any]] = None
        self.match_refs: List[Dict[str, Any]] = []
        self.total_matches: int = 0
        self.player_names: List[str] = []

        # Computed statistics
        self._win_rates: Optional[Dict[str, float]] = None
        self._confidence_intervals: Optional[Dict[str, Tuple[float, float]]] = None
        self._p_values: Optional[Dict[str, float]] = None
        self._effect_sizes: Optional[Dict[str, float]] = None
        self._pairwise: Optional[PairwiseComparison] = None

    @classmethod
    def from_session(
        cls, session_id: str, recordings_dir: Path = Path("agentdeck_runs")
    ) -> "StatisticalAnalysis":
        """
        Load analysis from session ID (SPEC-RESEARCH v1.1.0 §4.2).

        Args:
            session_id: Session identifier
            recordings_dir: Base directory for recordings (default: agentdeck_runs)

        Returns:
            StatisticalAnalysis instance with loaded recordings

        Raises:
            FileNotFoundError: If session directory doesn't exist (PH5)

        Note:
            Per unified session structure, recordings are in {recordings_dir}/{session_id}/records/
        """
        session_base = recordings_dir / session_id

        if not session_base.exists():
            raise FileNotFoundError(
                f"Session directory not found: {session_base}\n"
                f"Ensure recordings exist in {recordings_dir}/"
            )

        # Per unified structure: recordings are in records/ subdirectory
        records_dir = session_base / "records"
        if not records_dir.exists():
            raise FileNotFoundError(
                f"Records directory not found: {records_dir}\n"
                f"Expected unified session structure: {session_base}/records/"
            )

        # Pass session_id explicitly to avoid using "records" as the identifier
        analysis = cls(records_dir, session_id=session_id)
        analysis.load_recordings()
        return analysis

    def load_recordings(self):
        """
        Load batch and match recordings from disk (PH1, PH2).

        Raises:
            FileNotFoundError: If batch recording missing (PH5)
            ValueError: If recordings incomplete or malformed
        """
        # Find batch recording (PH2)
        batch_files = list(self.session_dir.glob("batch_*.json"))
        if not batch_files:
            raise FileNotFoundError(
                f"No batch recording found in {self.session_dir}\n" "Expected: batch_*.json file"
            )

        # Load batch data
        batch_file = batch_files[0]
        with open(batch_file, "r", encoding="utf-8") as f:
            self.batch_data = json.load(f)

        # Extract match references
        self.match_refs = self.batch_data.get("match_refs", [])
        self.total_matches = len(self.match_refs)

        if self.total_matches == 0:
            raise ValueError(f"Batch recording contains no matches: {batch_file}")

        # Extract player names from first match (assume consistent across batch)
        if self.match_refs:
            # Get player names from match_refs[0].player_summaries (per SPEC-RECORDER v1.1.0 MC3)
            first_match = self.match_refs[0]
            if "player_summaries" in first_match and first_match["player_summaries"]:
                self.player_names = [p["name"] for p in first_match["player_summaries"]]
            elif "player_order" in first_match:
                self.player_names = first_match["player_order"]
            else:
                # Fallback: collect all unique player names from all matches
                all_players = set()
                for m in self.match_refs:
                    if m.get("winner"):
                        all_players.add(m["winner"])
                    # Try to infer loser from player_summaries if available
                    if "player_summaries" in m:
                        for p in m["player_summaries"]:
                            if "name" in p:
                                all_players.add(p["name"])
                self.player_names = sorted(list(all_players))

    def compute_win_rates(self) -> Dict[str, float]:
        """
        Compute win rates per player.

        Returns:
            Dict mapping player name to win rate (0.0-1.0)
        """
        if self._win_rates is not None:
            return self._win_rates

        # Count wins per player
        wins = {player: 0 for player in self.player_names}
        total_decisive = 0  # Matches with a winner (exclude draws)

        for match_ref in self.match_refs:
            winner = match_ref.get("winner")
            if winner and winner in wins:
                wins[winner] += 1
                total_decisive += 1

        # Compute win rates (exclude draws from denominator)
        if total_decisive == 0:
            self._win_rates = {player: 0.0 for player in self.player_names}
        else:
            self._win_rates = {
                player: wins[player] / total_decisive for player in self.player_names
            }

        return self._win_rates

    def compute_confidence_intervals(
        self, confidence_level: float = 0.95
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute Wilson score confidence intervals for win rates.

        Args:
            confidence_level: Confidence level (default 0.95)

        Returns:
            Dict mapping player name to (lower, upper) CI bounds
        """
        if self._confidence_intervals is not None:
            return self._confidence_intervals

        win_rates = self.compute_win_rates()

        # Count wins per player
        wins = {player: 0 for player in self.player_names}
        total_decisive = sum(1 for m in self.match_refs if m.get("winner"))

        for match_ref in self.match_refs:
            winner = match_ref.get("winner")
            if winner and winner in wins:
                wins[winner] += 1

        # Compute CIs
        self._confidence_intervals = {}
        for player in self.player_names:
            try:
                ci = calculate_confidence_interval(
                    wins[player], total_decisive if total_decisive > 0 else 1, confidence_level
                )
                self._confidence_intervals[player] = ci
            except ImportError:
                # Fallback if scipy not available
                rate = win_rates[player]
                margin = 0.1  # Rough approximation
                self._confidence_intervals[player] = (max(0, rate - margin), min(1, rate + margin))

        return self._confidence_intervals

    def compute_significance_tests(self, null_hypothesis: float = 0.5) -> Dict[str, float]:
        """
        Compute p-values for significance tests.

        Args:
            null_hypothesis: Expected win rate under null (default 0.5 for fair game)

        Returns:
            Dict mapping player name to p-value
        """
        if self._p_values is not None:
            return self._p_values

        # Count wins per player
        wins = {player: 0 for player in self.player_names}
        total_decisive = sum(1 for m in self.match_refs if m.get("winner"))

        for match_ref in self.match_refs:
            winner = match_ref.get("winner")
            if winner and winner in wins:
                wins[winner] += 1

        # Compute p-values
        self._p_values = {}
        for player in self.player_names:
            try:
                p_value = statistical_significance(
                    wins[player], total_decisive if total_decisive > 0 else 1, null_hypothesis
                )
                self._p_values[player] = p_value
            except ImportError:
                # Fallback if scipy not available
                self._p_values[player] = 1.0  # Conservative (not significant)

        return self._p_values

    def compute_effect_sizes(self, null_hypothesis: float = 0.5) -> Dict[str, float]:
        """
        Compute Cohen's h effect sizes.

        Args:
            null_hypothesis: Expected proportion under null (default 0.5)

        Returns:
            Dict mapping player name to effect size
        """
        if self._effect_sizes is not None:
            return self._effect_sizes

        win_rates = self.compute_win_rates()

        # Count wins per player
        wins = {player: 0 for player in self.player_names}
        total_decisive = sum(1 for m in self.match_refs if m.get("winner"))

        for match_ref in self.match_refs:
            winner = match_ref.get("winner")
            if winner and winner in wins:
                wins[winner] += 1

        # Compute effect sizes
        self._effect_sizes = {}
        for player in self.player_names:
            effect = calculate_effect_size(
                win_rates[player], null_hypothesis, total_decisive if total_decisive > 0 else 1
            )
            self._effect_sizes[player] = effect

        return self._effect_sizes

    def compute_pairwise_comparisons(self, confidence_level: float = 0.95) -> PairwiseComparison:
        """
        Compute cross-player comparisons (CPC1, CPC2).

        For 2-player games: Direct comparison
        For 3+ players: All pairwise comparisons

        Args:
            confidence_level: CI level (default 0.95)

        Returns:
            PairwiseComparison with comparison stats and formatted matrix
        """
        if self._pairwise is not None:
            return self._pairwise

        win_rates = self.compute_win_rates()

        # Count wins per player
        wins = {player: 0 for player in self.player_names}
        for match_ref in self.match_refs:
            winner = match_ref.get("winner")
            if winner and winner in wins:
                wins[winner] += 1

        total_decisive = sum(wins.values())

        comparisons: Dict[Tuple[str, str], ComparisonStats] = {}

        # Generate all pairwise comparisons (CPC2)
        for i, player_a in enumerate(self.player_names):
            for j, player_b in enumerate(self.player_names):
                if i >= j:  # Only compare each pair once
                    continue

                # Compute comparison stats
                win_a = wins[player_a]
                win_b = wins[player_b]
                rate_a = win_rates[player_a]
                rate_b = win_rates[player_b]

                # Significance test (binomial test for Player A vs Player B)
                # Test if A's wins are significantly different from 50% in A+B matches
                head_to_head_matches = win_a + win_b
                try:
                    p_value = statistical_significance(win_a, head_to_head_matches, 0.5)
                except ImportError:
                    p_value = 1.0

                # Effect size
                effect = calculate_effect_size(rate_a, rate_b, head_to_head_matches)

                # Confidence interval for Player A's win rate in head-to-head matches
                try:
                    ci = calculate_confidence_interval(
                        win_a, head_to_head_matches, confidence_level
                    )
                except ImportError:
                    head_to_head_rate = (
                        win_a / head_to_head_matches if head_to_head_matches > 0 else 0.5
                    )
                    ci = (max(0, head_to_head_rate - 0.1), min(1, head_to_head_rate + 0.1))

                is_significant = p_value < 0.05

                comparisons[(player_a, player_b)] = ComparisonStats(
                    player_a=player_a,
                    player_b=player_b,
                    win_rate_a=rate_a,
                    win_rate_b=rate_b,
                    p_value=p_value,
                    effect_size=effect,
                    is_significant=is_significant,
                    confidence_interval=ci,
                )

        # Generate matrix for display (CPC4)
        matrix = self._format_comparison_matrix(comparisons)

        # For 2-player games, populate direct comparison fields (CPC1)
        if len(self.player_names) == 2 and len(comparisons) == 1:
            (player_a, player_b), stats = next(iter(comparisons.items()))
            significance_symbol = (
                "✅"
                if stats.is_significant and stats.win_rate_a > stats.win_rate_b
                else "❌" if stats.is_significant else "−"
            )

            self._pairwise = PairwiseComparison(
                comparisons=comparisons,
                matrix=matrix,
                player_a=player_a,
                player_b=player_b,
                win_rate_diff=stats.win_rate_a - stats.win_rate_b,
                p_value=stats.p_value,
                is_significant=stats.is_significant,
                significance_symbol=significance_symbol,
            )
        else:
            self._pairwise = PairwiseComparison(comparisons=comparisons, matrix=matrix)

        return self._pairwise

    def _format_comparison_matrix(
        self, comparisons: Dict[Tuple[str, str], ComparisonStats]
    ) -> List[List[str]]:
        """Format pairwise comparisons as matrix (CPC4)."""
        n = len(self.player_names)
        matrix = [["-" for _ in range(n + 1)] for _ in range(n + 1)]

        # Header row and column
        matrix[0][0] = ""
        for i, player in enumerate(self.player_names):
            matrix[0][i + 1] = player
            matrix[i + 1][0] = player

        # Fill matrix
        for (player_a, player_b), stats in comparisons.items():
            i = self.player_names.index(player_a)
            j = self.player_names.index(player_b)

            # Determine symbol based on significance
            if stats.is_significant:
                if stats.win_rate_a > stats.win_rate_b:
                    matrix[i + 1][j + 1] = "✅"  # A significantly better
                    matrix[j + 1][i + 1] = "❌"  # B significantly worse
                else:
                    matrix[i + 1][j + 1] = "❌"  # A significantly worse
                    matrix[j + 1][i + 1] = "✅"  # B significantly better
            else:
                matrix[i + 1][j + 1] = "−"  # Not significant
                matrix[j + 1][i + 1] = "−"

        return matrix

    def to_dict(self) -> Dict[str, Any]:
        """
        Return all statistics as dict for programmatic access.

        Returns:
            Dict with win_rates, confidence_intervals, p_values, effect_sizes, pairwise
        """
        win_rates = self.compute_win_rates()
        cis = self.compute_confidence_intervals()
        p_values = self.compute_significance_tests()
        effects = self.compute_effect_sizes()
        pairwise = self.compute_pairwise_comparisons()

        return {
            "session_id": self.session_id,
            "total_matches": self.total_matches,
            "players": self.player_names,
            "win_rates": win_rates,
            "confidence_intervals": cis,
            "p_values": p_values,
            "effect_sizes": effects,
            "pairwise_comparisons": {
                f"{a}_vs_{b}": {
                    "win_rate_a": stats.win_rate_a,
                    "win_rate_b": stats.win_rate_b,
                    "p_value": stats.p_value,
                    "effect_size": stats.effect_size,
                    "is_significant": stats.is_significant,
                }
                for (a, b), stats in pairwise.comparisons.items()
            },
        }

    def print_summary(self):
        """Print human-readable statistical summary."""
        print("\n" + "=" * 70)
        print(f"Statistical Analysis: {self.session_id}")
        print("=" * 70)
        print()

        # Win rates with CIs
        print("Win Rates:")
        win_rates = self.compute_win_rates()
        cis = self.compute_confidence_intervals()
        for player in self.player_names:
            rate = win_rates[player]
            ci = cis[player]
            print(f"  {player}: {rate:.1%} [CI: {ci[0]:.1%}-{ci[1]:.1%}]")
        print()

        # Cross-player comparison (CPC1 for 2-player, CPC2 for 3+)
        print("Cross-Player Comparison:")
        pairwise = self.compute_pairwise_comparisons()

        if len(self.player_names) == 2:
            # Direct comparison for 2-player (CPC1)
            (p_a, p_b), stats = list(pairwise.comparisons.items())[0]
            print(
                f"  {p_a} vs {p_b}: p={stats.p_value:.3f} {'(SIGNIFICANT ✅)' if stats.is_significant else '(not significant)'}"
            )
            print(f"  Effect size (Cohen's h): {stats.effect_size:.3f}")

            if stats.is_significant:
                winner = p_a if stats.win_rate_a > stats.win_rate_b else p_b
                print(f"\n  Conclusion: {winner} is significantly better at α=0.05")
            else:
                print(f"\n  Conclusion: No significant difference at α=0.05")
        else:
            # Pairwise matrix for 3+ players (CPC2, CPC4)
            print("  Pairwise Matrix:")
            for row in pairwise.matrix:
                print("  " + "  ".join(f"{cell:^10}" for cell in row))
            print()
            print(
                "  ✅ = significantly better  |  ❌ = significantly worse  |  − = not significant"
            )

        print("=" * 70)

    def export_markdown(self, path: Path):
        """Export analysis as markdown report."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Statistical Analysis: {self.session_id}\n\n")
            f.write(f"**Total Matches**: {self.total_matches}\n\n")

            f.write("## Win Rates\n\n")
            win_rates = self.compute_win_rates()
            for player in self.player_names:
                rate = win_rates[player]
                f.write(f"- **{player}**: {rate:.1%}\n")

            f.write("\n## Confidence Intervals\n\n")
            cis = self.compute_confidence_intervals()
            for player in self.player_names:
                ci = cis[player]
                f.write(f"- **{player}**: [{ci[0]:.1%}, {ci[1]:.1%}]\n")

            f.write("\n## Statistical Tests\n\n")
            p_values = self.compute_significance_tests()
            for player in self.player_names:
                p = p_values[player]
                sig = "SIGNIFICANT ✅" if p < 0.05 else "not significant"
                f.write(f"- **{player}**: p={p:.4f} ({sig})\n")

    def export_json(self, path: Path):
        """Export analysis as JSON."""
        data = self.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
