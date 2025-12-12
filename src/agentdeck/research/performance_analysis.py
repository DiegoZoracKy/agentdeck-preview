"""Performance analysis from recorded sessions.

Per SPEC-RESEARCH v1.1.0 §4.2:
- PerformanceAnalysis.from_session(): Load and analyze performance metrics
- Compute duration stats, throughput, speedup, concurrency efficiency
- PH1-PH5: Read from agentdeck_runs/, validate recordings
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class PerformanceAnalysis:
    """
    Performance analysis from recorded sessions.

    Per SPEC-RESEARCH v1.1.0:
    - Reads recordings from agentdeck_runs/session_id/
    - Computes duration, throughput, speedup, concurrency efficiency

    Invariants:
    - PH1: Reads from agentdeck_runs/session_id/
    - PH2: Validates recordings exist
    """

    def __init__(
        self,
        session_dir: Path,
        baseline_duration: Optional[float] = None,
        baseline_cost: Optional[float] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize performance analysis.

        Args:
            session_dir: Path to recordings directory
            baseline_duration: Expected duration in seconds (for speedup calc)
            baseline_cost: Expected cost in USD (for efficiency calc)
            session_id: Session identifier (defaults to parent directory name if not provided)
        """
        self.session_dir = Path(session_dir)
        # Extract session_id from parent directory if not provided
        self.session_id = session_id or session_dir.parent.name
        self.baseline_duration = baseline_duration
        self.baseline_cost = baseline_cost

        # Loaded data
        self.batch_data: Optional[Dict[str, Any]] = None
        self.match_refs: List[Dict[str, Any]] = []
        self.total_matches: int = 0

        # Extracted metrics
        self.durations: List[float] = []
        self.total_duration: float = 0.0
        self.concurrency: Optional[int] = None

    @classmethod
    def from_session(
        cls,
        session_id: str,
        recordings_dir: Path = Path("agentdeck_runs"),
        baseline_duration: Optional[float] = None,
        baseline_cost: Optional[float] = None,
    ) -> "PerformanceAnalysis":
        """
        Load performance analysis from session ID.

        Args:
            session_id: Session identifier
            recordings_dir: Base directory for recordings
            baseline_duration: Expected duration for speedup calculation
            baseline_cost: Expected cost for efficiency calculation

        Returns:
            PerformanceAnalysis instance

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
        analysis = cls(records_dir, baseline_duration, baseline_cost, session_id=session_id)
        analysis.load_recordings()
        return analysis

    def load_recordings(self):
        """Load batch recording and extract performance metrics."""
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

        # Extract timestamps and compute durations
        for match_ref in self.match_refs:
            started_at = match_ref.get("started_at")
            ended_at = match_ref.get("ended_at")

            if started_at and ended_at:
                # Parse ISO format timestamps
                start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                duration = (end - start).total_seconds()
                self.durations.append(duration)

        # Compute total duration from first and last match
        if self.match_refs:
            first_start = self.match_refs[0].get("started_at")
            last_end = self.match_refs[-1].get("ended_at")

            if first_start and last_end:
                start = datetime.fromisoformat(first_start.replace("Z", "+00:00"))
                end = datetime.fromisoformat(last_end.replace("Z", "+00:00"))
                self.total_duration = (end - start).total_seconds()

        # Extract concurrency from batch metadata if available
        metadata = self.batch_data.get("metadata", {})
        self.concurrency = metadata.get("concurrency") or metadata.get("workers")

    @property
    def avg_match_duration(self) -> float:
        """Average match duration in seconds."""
        if not self.durations or len(self.durations) == 0:
            return 0.0
        import statistics

        return statistics.mean(self.durations)

    @property
    def matches_per_second(self) -> float:
        """Throughput in matches per second."""
        return self.compute_throughput()

    def compute_duration_stats(self) -> Dict[str, Any]:
        """
        Compute duration statistics.

        Returns:
            Dict with total, avg, min, max, std duration
        """
        if not self.durations:
            return {
                "total": self.total_duration,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std": 0.0,
            }

        import statistics

        return {
            "total": self.total_duration,
            "avg": statistics.mean(self.durations),
            "min": min(self.durations),
            "max": max(self.durations),
            "std": statistics.stdev(self.durations) if len(self.durations) > 1 else 0.0,
        }

    def compute_throughput(self) -> float:
        """
        Compute throughput (matches per second).

        Returns:
            Matches per second
        """
        if self.total_duration == 0:
            return 0.0

        return self.total_matches / self.total_duration

    def compute_speedup(self, baseline: Optional[float] = None) -> Optional[float]:
        """
        Compute speedup vs baseline.

        Args:
            baseline: Baseline duration (uses self.baseline_duration if None)

        Returns:
            Speedup factor (baseline / actual), or None if no baseline
        """
        baseline = baseline or self.baseline_duration

        if baseline is None or self.total_duration == 0:
            return None

        return baseline / self.total_duration

    def compute_concurrency_efficiency(self) -> Optional[float]:
        """
        Compute concurrency efficiency (actual vs theoretical speedup).

        Returns:
            Efficiency as percentage (0-1), or None if concurrency=1 or unknown
        """
        if self.concurrency is None or self.concurrency <= 1:
            return None

        speedup = self.compute_speedup()
        if speedup is None:
            return None

        theoretical_max = float(self.concurrency)
        return speedup / theoretical_max

    def to_dict(self) -> Dict[str, Any]:
        """Return all metrics as dict."""
        duration_stats = self.compute_duration_stats()
        throughput = self.compute_throughput()
        speedup = self.compute_speedup()
        efficiency = self.compute_concurrency_efficiency()

        return {
            "session_id": self.session_id,
            "total_matches": self.total_matches,
            "duration": duration_stats,
            "throughput": throughput,
            "speedup": speedup,
            "concurrency": self.concurrency,
            "concurrency_efficiency": efficiency,
            "baseline_duration": self.baseline_duration,
        }

    def print_summary(self):
        """Print human-readable performance summary."""
        print("\n" + "=" * 70)
        print(f"Performance Analysis: {self.session_id}")
        print("=" * 70)
        print()

        # Duration stats
        print("Duration:")
        stats = self.compute_duration_stats()
        print(f"  Total: {stats['total']:.2f}s")
        if self.baseline_duration:
            print(f"  Baseline: {self.baseline_duration:.2f}s")
            speedup = self.compute_speedup()
            if speedup:
                savings = (1 - 1 / speedup) * 100
                print(f"  Speedup: {speedup:.2f}× faster")
                print(f"  Efficiency: {savings:.0f}% time savings")
        print()

        # Throughput
        print("Throughput:")
        throughput = self.compute_throughput()
        print(f"  Matches/second: {throughput:.2f}")
        print(f"  Avg match duration: {stats['avg']:.2f}s")
        print(f"  Min/Max: {stats['min']:.1f}s / {stats['max']:.1f}s")
        print()

        # Concurrency
        if self.concurrency and self.concurrency > 1:
            print("Concurrency:")
            print(f"  Workers: {self.concurrency}")
            print(f"  Theoretical max speedup: {self.concurrency}×")
            speedup = self.compute_speedup()
            if speedup:
                print(f"  Actual speedup: {speedup:.2f}×")
            efficiency = self.compute_concurrency_efficiency()
            if efficiency:
                overhead = (1 - efficiency) * 100
                print(f"  Efficiency: {efficiency:.0%} (parallel overhead: {overhead:.0f}%)")
            print()

        print("=" * 70)
