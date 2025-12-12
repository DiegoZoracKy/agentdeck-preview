"""Cost analysis from recorded sessions.

Per SPEC-RESEARCH v1.1.0 §4.2:
- CostAnalysis.from_session(): Load and analyze cost metrics
- Compute cost breakdown, cost per match, cost per win, cost savings
- PH1-PH5: Read from agentdeck_runs/, handle missing cost data gracefully
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


class CostAnalysis:
    """
    Cost analysis from recorded sessions.

    Per SPEC-RESEARCH v1.1.0:
    - Reads recordings from agentdeck_runs/session_id/
    - Computes cost breakdown, efficiency metrics
    - Handles missing cost data gracefully (non-LLM players)

    Invariants:
    - PH1: Reads from agentdeck_runs/session_id/
    - PH2: Validates recordings exist
    """

    def __init__(
        self,
        session_dir: Path,
        baseline_cost: Optional[float] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize cost analysis.

        Args:
            session_dir: Path to recordings directory
            baseline_cost: Expected cost in USD (for savings calc)
            session_id: Session identifier (defaults to parent directory name if not provided)
        """
        self.session_dir = Path(session_dir)
        # Extract session_id from parent directory if not provided
        self.session_id = session_id or session_dir.parent.name
        self.baseline_cost = baseline_cost

        # Loaded data
        self.batch_data: Optional[Dict[str, Any]] = None
        self.match_refs: List[Dict[str, Any]] = []
        self.total_matches: int = 0

        # Extracted metrics
        self.player_costs: Dict[str, float] = {}
        self.player_wins: Dict[str, int] = {}
        self.total_cost: float = 0.0

    @classmethod
    def from_session(
        cls,
        session_id: str,
        recordings_dir: Path = Path("agentdeck_runs"),
        baseline_cost: Optional[float] = None,
    ) -> "CostAnalysis":
        """
        Load cost analysis from session ID.

        Args:
            session_id: Session identifier
            recordings_dir: Base directory for recordings
            baseline_cost: Expected cost for savings calculation

        Returns:
            CostAnalysis instance

        Raises:
            FileNotFoundError: If session directory doesn't exist

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
        analysis = cls(records_dir, baseline_cost, session_id=session_id)
        analysis.load_recordings()
        return analysis

    def load_recordings(self):
        """Load batch recording and extract cost metrics."""
        # Find batch recording
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

        # Extract player summaries from first match to get player names
        player_names: List[str] = []
        if self.match_refs:
            first_match_ref = self.match_refs[0]
            if "player_summaries" in first_match_ref:
                player_names = [p["name"] for p in first_match_ref["player_summaries"]]
            elif "player_order" in first_match_ref:
                player_names = first_match_ref["player_order"]

        # Initialize cost and win trackers
        for player in player_names:
            self.player_costs[player] = 0.0
            self.player_wins[player] = 0

        last_total_costs: Dict[str, float] = defaultdict(float)

        # Extract costs and wins from match refs
        for match_ref in self.match_refs:
            if "player_costs" in match_ref and isinstance(match_ref["player_costs"], dict):
                for player_name, cost in match_ref["player_costs"].items():
                    if player_name not in self.player_costs:
                        self.player_costs[player_name] = 0.0
                        self.player_wins.setdefault(player_name, 0)
                    cost_value = float(cost) if cost is not None else 0.0
                    self.player_costs[player_name] += cost_value
            elif "player_summaries" in match_ref:
                for player_summary in match_ref["player_summaries"]:
                    player_name = player_summary.get("name")
                    if not player_name:
                        continue
                    cumulative = float(player_summary.get("total_cost", 0.0) or 0.0)
                    previous = last_total_costs[player_name]
                    delta = cumulative - previous
                    if delta < 0:
                        delta = 0.0
                    if player_name not in self.player_costs:
                        self.player_costs[player_name] = 0.0
                        self.player_wins.setdefault(player_name, 0)
                    self.player_costs[player_name] += delta
                    last_total_costs[player_name] = cumulative

            # Count wins
            winner = match_ref.get("winner")
            if winner and winner in self.player_wins:
                self.player_wins[winner] += 1

        # Compute total cost
        self.total_cost = sum(self.player_costs.values())

    def compute_cost_breakdown(self) -> Dict[str, float]:
        """
        Compute cost breakdown per player.

        Returns:
            Dict mapping player name to total cost
        """
        return dict(self.player_costs)

    def compute_cost_per_match(self) -> float:
        """
        Compute average cost per match.

        Returns:
            Cost per match in USD
        """
        if self.total_matches == 0:
            return 0.0

        return self.total_cost / self.total_matches

    def compute_cost_per_win(self) -> Dict[str, Optional[float]]:
        """
        Compute cost per win for each player (cost efficiency).

        Returns:
            Dict mapping player name to cost per win, or None if no wins
        """
        cost_per_win = {}

        for player, cost in self.player_costs.items():
            wins = self.player_wins.get(player, 0)
            if wins > 0:
                cost_per_win[player] = cost / wins
            else:
                cost_per_win[player] = None  # No wins

        return cost_per_win

    def compute_cost_savings(self, baseline: Optional[float] = None) -> Optional[float]:
        """
        Compute cost savings vs baseline.

        Args:
            baseline: Baseline cost (uses self.baseline_cost if None)

        Returns:
            Savings percentage (0-1), or None if no baseline
        """
        baseline = baseline or self.baseline_cost

        if baseline is None or baseline == 0:
            return None

        return (baseline - self.total_cost) / baseline

    def to_dict(self) -> Dict[str, Any]:
        """Return all metrics as dict."""
        breakdown = self.compute_cost_breakdown()
        per_match = self.compute_cost_per_match()
        per_win = self.compute_cost_per_win()
        savings = self.compute_cost_savings()

        return {
            "session_id": self.session_id,
            "total_matches": self.total_matches,
            "total_cost": self.total_cost,
            "cost_per_match": per_match,
            "cost_breakdown": breakdown,
            "cost_per_win": per_win,
            "baseline_cost": self.baseline_cost,
            "cost_savings": savings,
        }

    def print_summary(self):
        """Print human-readable cost summary."""
        print("\n" + "=" * 70)
        print(f"Cost Analysis: {self.session_id}")
        print("=" * 70)
        print()

        # Total and baseline
        print("Total Cost:")
        print(f"  Actual: ${self.total_cost:.4f}")
        if self.baseline_cost:
            print(f"  Baseline: ${self.baseline_cost:.4f}")
            savings = self.compute_cost_savings()
            if savings is not None:
                if savings > 0:
                    print(f"  Savings: {savings:.0%} under budget")
                else:
                    print(f"  Overage: {-savings:.0%} over budget")
        print()

        # Per match
        per_match = self.compute_cost_per_match()
        print("Cost per Match:")
        print(f"  ${per_match:.6f}")
        print()

        # Per player
        print("Cost Breakdown:")
        for player, cost in self.player_costs.items():
            wins = self.player_wins.get(player, 0)
            print(f"  {player}: ${cost:.4f} ({wins} wins)")
        print()

        # Cost efficiency
        print("Cost Efficiency (cost per win):")
        cost_per_win = self.compute_cost_per_win()
        for player, cpw in cost_per_win.items():
            if cpw is not None:
                print(f"  {player}: ${cpw:.4f} per win")
            else:
                print(f"  {player}: No wins")

        print("=" * 70)
