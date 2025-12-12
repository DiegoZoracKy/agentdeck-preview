"""Multi-session comparison and meta-analysis.

Per SPEC-RESEARCH v1.1.0 §4.2:
- ComparisonAnalysis: Compare statistics across multiple sessions
- Meta-analysis with combined p-values (Fisher's method)
- Generate comparison tables
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .statistical_analysis import StatisticalAnalysis


@dataclass
class MetaAnalysisResult:
    """Meta-analysis results across sessions (SPEC-RESEARCH v1.1.0 §5)."""

    session_ids: List[str]
    total_matches: int
    aggregate_win_rates: Dict[str, float]
    aggregate_p_values: Dict[str, float]  # Combined using Fisher's method
    aggregate_effect_sizes: Dict[str, float]
    heterogeneity: float = 0.0  # I² statistic for consistency


@dataclass
class ComparisonTable:
    """Formatted comparison table (SPEC-RESEARCH v1.1.0 §5)."""

    sessions: List[str]  # Session IDs or names
    metrics: Dict[str, List[Any]]  # metric_name → [value per session]
    confidence_intervals: Dict[str, List[Tuple[float, float]]]
    formatted_table: str  # Markdown/ASCII table


class ComparisonAnalysis:
    """
    Compare statistics across multiple experimental sessions.

    Per SPEC-RESEARCH v1.1.0:
    - Load and aggregate statistics from multiple sessions
    - Compute meta-analysis (combined p-values, aggregate effect sizes)
    - Generate comparison tables

    Example:
        comparison = ComparisonAnalysis([
            "session_20251030_111049_63a6fb",
            "session_20251031_131301_45fe25",
            "session_20251031_131839_7ee163"
        ])
        comparison.print_comparison_table()
    """

    def __init__(self, session_ids: List[str], recordings_dir: Path = Path("agentdeck_runs")):
        """
        Initialize multi-session comparison.

        Args:
            session_ids: List of session IDs to compare
            recordings_dir: Base directory for recordings
        """
        self.session_ids = session_ids
        self.recordings_dir = recordings_dir
        self.analyses: List[StatisticalAnalysis] = []

        # Load all sessions
        for session_id in session_ids:
            try:
                analysis = StatisticalAnalysis.from_session(session_id, recordings_dir)
                self.analyses.append(analysis)
            except FileNotFoundError as e:
                print(f"Warning: Skipping session {session_id}: {e}")

    def meta_analysis(self) -> MetaAnalysisResult:
        """
        Compute meta-analysis across all sessions.

        Returns:
            MetaAnalysisResult with aggregated statistics
        """
        if not self.analyses:
            raise ValueError("No valid sessions loaded for meta-analysis")

        # Aggregate total matches
        total_matches = sum(a.total_matches for a in self.analyses)

        # Get all player names (union across sessions)
        all_players = set()
        for analysis in self.analyses:
            all_players.update(analysis.player_names)
        all_players = sorted(list(all_players))

        # Aggregate win rates (weighted by number of matches)
        aggregate_win_rates = {}
        for player in all_players:
            total_wins = 0
            total_decisive = 0

            for analysis in self.analyses:
                if player in analysis.player_names:
                    win_rates = analysis.compute_win_rates()
                    # Count wins from this session
                    wins_this_session = sum(
                        1 for m in analysis.match_refs if m.get("winner") == player
                    )
                    decisive_this_session = sum(
                        1 for m in analysis.match_refs if m.get("winner") is not None
                    )

                    total_wins += wins_this_session
                    total_decisive += decisive_this_session

            if total_decisive > 0:
                aggregate_win_rates[player] = total_wins / total_decisive
            else:
                aggregate_win_rates[player] = 0.0

        # Aggregate p-values using Fisher's method
        aggregate_p_values = self._fisher_method(all_players)

        # Aggregate effect sizes (simple average for now)
        aggregate_effect_sizes = {}
        for player in all_players:
            effects = []
            for analysis in self.analyses:
                if player in analysis.player_names:
                    player_effects = analysis.compute_effect_sizes()
                    effects.append(player_effects[player])

            if effects:
                aggregate_effect_sizes[player] = sum(effects) / len(effects)
            else:
                aggregate_effect_sizes[player] = 0.0

        # TODO: Compute I² heterogeneity statistic (requires more complex stats)
        heterogeneity = 0.0

        return MetaAnalysisResult(
            session_ids=self.session_ids,
            total_matches=total_matches,
            aggregate_win_rates=aggregate_win_rates,
            aggregate_p_values=aggregate_p_values,
            aggregate_effect_sizes=aggregate_effect_sizes,
            heterogeneity=heterogeneity,
        )

    def _fisher_method(self, players: List[str]) -> Dict[str, float]:
        """
        Combine p-values using Fisher's method.

        Args:
            players: List of player names

        Returns:
            Dict mapping player to combined p-value
        """
        try:
            import math

            from scipy import stats

            combined_p_values = {}

            for player in players:
                p_values = []
                for analysis in self.analyses:
                    if player in analysis.player_names:
                        player_p_values = analysis.compute_significance_tests()
                        p_values.append(player_p_values[player])

                if p_values:
                    # Fisher's method: -2 * sum(log(p_i)) ~ chi-squared(2k)
                    chi_stat = -2 * sum(math.log(max(p, 1e-10)) for p in p_values)
                    df = 2 * len(p_values)
                    combined_p = 1 - stats.chi2.cdf(chi_stat, df)
                    combined_p_values[player] = combined_p
                else:
                    combined_p_values[player] = 1.0

            return combined_p_values

        except ImportError:
            # Fallback: simple average of p-values (not statistically rigorous)
            combined_p_values = {}
            for player in players:
                p_values = []
                for analysis in self.analyses:
                    if player in analysis.player_names:
                        player_p_values = analysis.compute_significance_tests()
                        p_values.append(player_p_values[player])

                if p_values:
                    combined_p_values[player] = sum(p_values) / len(p_values)
                else:
                    combined_p_values[player] = 1.0

            return combined_p_values

    def compare_win_rates(self) -> ComparisonTable:
        """Generate comparison table for win rates."""
        # Get all player names
        all_players = set()
        for analysis in self.analyses:
            all_players.update(analysis.player_names)
        all_players = sorted(list(all_players))

        # Build metrics dict
        metrics = {}
        cis = {}

        for player in all_players:
            player_rates = []
            player_cis = []

            for analysis in self.analyses:
                if player in analysis.player_names:
                    win_rates = analysis.compute_win_rates()
                    confidence_intervals = analysis.compute_confidence_intervals()

                    player_rates.append(win_rates[player])
                    player_cis.append(confidence_intervals[player])
                else:
                    player_rates.append(None)
                    player_cis.append((None, None))

            metrics[player] = player_rates
            cis[player] = player_cis

        # Format table
        formatted = self._format_win_rate_table(all_players, metrics, cis)

        return ComparisonTable(
            sessions=self.session_ids,
            metrics=metrics,
            confidence_intervals=cis,
            formatted_table=formatted,
        )

    def _format_win_rate_table(
        self,
        players: List[str],
        metrics: Dict[str, List[Any]],
        cis: Dict[str, List[Tuple[Optional[float], Optional[float]]]],
    ) -> str:
        """Format win rate comparison table as markdown."""
        lines = []
        lines.append(
            "| Session | "
            + " | ".join(f"{p} Win%" for p in players)
            + " | p-value | Significant? |"
        )
        lines.append("|" + "|".join(["---"] * (len(players) + 3)) + "|")

        for i, session_id in enumerate(self.session_ids):
            analysis = self.analyses[i] if i < len(self.analyses) else None

            if analysis:
                p_values = analysis.compute_significance_tests()
                # Use first player's p-value as representative (simplification)
                p_val = p_values.get(players[0], 1.0) if players else 1.0
                is_sig = "Yes ✅" if p_val < 0.05 else "No"

                row = [f"Exp #{i+1}"]
                for player in players:
                    if player in analysis.player_names:
                        rate = metrics[player][i]
                        ci = cis[player][i]
                        if rate is not None and ci[0] is not None:
                            row.append(f"{rate:.0%} [{ci[0]:.0%}-{ci[1]:.0%}]")
                        else:
                            row.append("N/A")
                    else:
                        row.append("N/A")

                row.append(f"{p_val:.3f}")
                row.append(is_sig)
                lines.append("| " + " | ".join(row) + " |")
            else:
                lines.append(f"| Exp #{i+1} | " + " | ".join(["N/A"] * (len(players) + 2)) + " |")

        return "\n".join(lines)

    def print_comparison_table(self):
        """Print formatted comparison table."""
        print("\n" + "=" * 80)
        print("Cross-Session Comparison")
        print("=" * 80)

        # Win rates table
        win_rate_table = self.compare_win_rates()
        print(win_rate_table.formatted_table)
        print()

        # Meta-analysis
        meta = self.meta_analysis()
        print("Meta-Analysis (Combined):")
        print(f"  Total matches: {meta.total_matches}")

        for player in sorted(meta.aggregate_win_rates.keys()):
            rate = meta.aggregate_win_rates[player]
            p_val = meta.aggregate_p_values.get(player, 1.0)
            print(f"  {player} overall: {rate:.1%} (combined p={p_val:.3f})")

        print()

        # Conclusion
        print("Conclusion:")
        significant_players = [p for p, pval in meta.aggregate_p_values.items() if pval < 0.05]

        if significant_players:
            print(f"  Significant advantages: {', '.join(significant_players)}")
        else:
            print("  No consistent advantage across sessions")

        print("=" * 80)

    def export_markdown(self, path: Path):
        """Export comparison as markdown file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Cross-Session Comparison\n\n")

            # Win rates table
            win_rate_table = self.compare_win_rates()
            f.write(win_rate_table.formatted_table)
            f.write("\n\n")

            # Meta-analysis
            meta = self.meta_analysis()
            f.write("## Meta-Analysis (Combined)\n\n")
            f.write(f"**Total matches**: {meta.total_matches}\n\n")

            for player in sorted(meta.aggregate_win_rates.keys()):
                rate = meta.aggregate_win_rates[player]
                p_val = meta.aggregate_p_values.get(player, 1.0)
                f.write(f"- **{player}**: {rate:.1%} (combined p={p_val:.3f})\n")
