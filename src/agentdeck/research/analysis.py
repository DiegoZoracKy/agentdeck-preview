"""Results analysis and visualization for AgentDeck research."""

from typing import Any, Dict

from ..core.types import MatchResults


class ResultsAnalyzer:
    """Analyze and visualize match results."""

    def __init__(self, results: MatchResults):
        """
        Initialize analyzer with match results.

        Args:
            results: MatchResults to analyze
        """
        self.results = results
        self._analyze()

    def _analyze(self):
        """Perform initial analysis."""
        self.total_matches = len(self.results)

        # Win statistics
        self.wins_by_player = {}
        self.turns_per_match = []
        self.match_durations = []

        for match in self.results.matches:
            # Track wins
            if match.winner:
                self.wins_by_player[match.winner] = self.wins_by_player.get(match.winner, 0) + 1

            # Track turns
            turn_count = len([e for e in match.events if e.type == "gameplay"])
            self.turns_per_match.append(turn_count)

            # Track duration
            if match.metadata and "duration" in match.metadata:
                self.match_durations.append(match.metadata["duration"])

    def get_win_rates(self) -> Dict[str, float]:
        """Calculate win rates for each player."""
        total = self.total_matches
        return {player: wins / total for player, wins in self.wins_by_player.items()}

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        stats = {
            "total_matches": self.total_matches,
            "win_rates": self.get_win_rates(),
            "avg_turns_per_match": (
                sum(self.turns_per_match) / len(self.turns_per_match) if self.turns_per_match else 0
            ),
            "min_turns": min(self.turns_per_match) if self.turns_per_match else 0,
            "max_turns": max(self.turns_per_match) if self.turns_per_match else 0,
        }

        if self.match_durations:
            stats["avg_duration"] = sum(self.match_durations) / len(self.match_durations)
            stats["total_duration"] = sum(self.match_durations)

        return stats

    def print_detailed_report(self):
        """Print detailed analysis report."""
        stats = self.get_summary_stats()

        print("\n" + "=" * 70)
        print("DETAILED MATCH ANALYSIS REPORT")
        print("=" * 70)

        print(f"\nTotal Matches Analyzed: {stats['total_matches']}")

        print("\n" + "-" * 70)
        print("WIN RATES BY PLAYER")
        print("-" * 70)

        for player, rate in sorted(stats["win_rates"].items(), key=lambda x: x[1], reverse=True):
            wins = self.wins_by_player.get(player, 0)
            print(f"{player:30} {wins:3d} wins ({rate:6.1%})")

        print("\n" + "-" * 70)
        print("MATCH STATISTICS")
        print("-" * 70)

        print(f"Average Turns per Match: {stats['avg_turns_per_match']:.1f}")
        print(f"Minimum Turns: {stats['min_turns']}")
        print(f"Maximum Turns: {stats['max_turns']}")

        if "avg_duration" in stats:
            print(f"\nAverage Match Duration: {stats['avg_duration']:.2f}s")
            print(f"Total Time: {stats['total_duration']:.2f}s")

        # Action distribution if available
        action_counts = self._analyze_actions()
        if action_counts:
            print("\n" + "-" * 70)
            print("ACTION DISTRIBUTION")
            print("-" * 70)

            for player, actions in action_counts.items():
                print(f"\n{player}:")
                total_actions = sum(actions.values())
                for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / total_actions) * 100
                    print(f"  {action:15} {count:4d} ({percentage:5.1f}%)")

        print("\n" + "=" * 70)

    def _analyze_actions(self) -> Dict[str, Dict[str, int]]:
        """Analyze action distribution across matches."""
        action_counts = {}

        for match in self.results.matches:
            for event in match.events:
                if event.type == "gameplay" and "player" in event.data and "action" in event.data:
                    player = event.data["player"]
                    action = event.data["action"]

                    if player not in action_counts:
                        action_counts[player] = {}

                    action_counts[player][action] = action_counts[player].get(action, 0) + 1

        return action_counts

    def export_csv(self, filename: str):
        """
        Export results to CSV file.

        Args:
            filename: Output CSV filename
        """
        import csv

        with open(filename, "w", encoding="utf-8", newline="") as csvfile:
            fieldnames = ["match_id", "winner", "turns", "duration", "seed"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for i, match in enumerate(self.results.matches):
                row = {
                    "match_id": i + 1,
                    "winner": match.winner or "draw",
                    "turns": len([e for e in match.events if e.type == "gameplay"]),
                    "duration": match.metadata.get("duration", 0) if match.metadata else 0,
                    "seed": match.seed,
                }
                writer.writerow(row)

        print(f"Results exported to {filename}")
