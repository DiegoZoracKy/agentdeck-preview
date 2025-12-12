"""Research spectators for auto-running post-hoc analysis.

Per SPEC-RESEARCH v1.1.0 §4.2, §6.9:
- Thin wrappers that call standalone analysis classes from agentdeck.research
- Auto-run analysis at batch end (on_batch_end)
- PH4: No logic duplication - import and call standalone classes
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..core.base.spectator import Spectator


class StatisticalAnalysisSpectator(Spectator):
    """
    Auto-run statistical analysis when batch completes.

    Per SPEC-RESEARCH v1.1.0:
    - Thin wrapper around StatisticalAnalysis.from_session()
    - Captures session_id on session start
    - Runs analysis on batch end
    - No logic duplication (PH4)

    Example:
        spectator = StatisticalAnalysisSpectator(
            print_on_complete=True,
            save_report=True,
            output_path="analysis.md"
        )

        with AgentDeck(game=game, spectators=[spectator]) as deck:
            deck.play(players, matches=100)

        # Analysis automatically runs and prints when batch completes
    """

    def __init__(
        self,
        *,
        print_on_complete: bool = True,
        save_report: bool = False,
        output_path: Optional[Path] = None,
        confidence_level: float = 0.95,
        logger: Any = None,
    ):
        """
        Initialize spectator.

        Args:
            print_on_complete: Print summary when batch completes (default True)
            save_report: Save markdown report to file (default False)
            output_path: Path for markdown report (default None = auto-generate)
            confidence_level: Confidence level for CIs (default 0.95)
            logger: Optional logger (framework may inject)
        """
        super().__init__(logger=logger)
        self.print_on_complete = print_on_complete
        self.save_report = save_report
        self.output_path = Path(output_path) if output_path else None
        self.confidence_level = confidence_level
        self.session_id: Optional[str] = None
        self.recordings_dir: Optional[Path] = None

    def on_session_start(self, context=None, **kwargs):
        """Capture session ID and recordings directory."""
        # Extract session_id and record_directory from kwargs (Console emits them)
        self.session_id = kwargs.get("session_id")
        if not self.session_id and context and isinstance(context, dict):
            self.session_id = context.get("session_id")

        # Extract recordings base directory from record_directory path
        # record_directory is {run_dir}/{session_id}/records/, we want {run_dir}
        record_dir = kwargs.get("record_directory")
        if record_dir:
            # Go up two levels: from records/ to session_id/ to run_dir/
            self.recordings_dir = Path(record_dir).parent.parent

    def on_batch_end(self, batch_id, results, context=None, **kwargs):
        """Run statistical analysis when batch completes (PH4)."""
        if not self.session_id:
            if self.logger:
                self.logger.warning(
                    "StatisticalAnalysisSpectator: No session_id captured, skipping analysis"
                )
            return

        try:
            # Import standalone class (no logic duplication - PH4)
            from ..research import StatisticalAnalysis

            # Call standalone analysis with recordings directory
            if self.recordings_dir:
                analysis = StatisticalAnalysis.from_session(self.session_id, self.recordings_dir)
            else:
                analysis = StatisticalAnalysis.from_session(self.session_id)

            # Print summary if requested
            if self.print_on_complete:
                analysis.print_summary()

            # Save report if requested
            if self.save_report:
                output = self.output_path or Path(f"analysis_{self.session_id}.md")
                analysis.export_markdown(output)
                if self.logger:
                    self.logger.info(f"Statistical analysis saved to: {output}")

        except FileNotFoundError as e:
            if self.logger:
                self.logger.warning(f"StatisticalAnalysisSpectator: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"StatisticalAnalysisSpectator failed: {e}")


class PerformanceTrackerSpectator(Spectator):
    """
    Auto-run performance analysis when batch completes.

    Per SPEC-RESEARCH v1.1.0:
    - Thin wrapper around PerformanceAnalysis.from_session()
    - No logic duplication (PH4)

    Example:
        spectator = PerformanceTrackerSpectator(
            print_on_complete=True,
            baseline_duration=300.0
        )

        with AgentDeck(game=game, spectators=[spectator]) as deck:
            deck.play(players, matches=100)
    """

    def __init__(
        self,
        *,
        print_on_complete: bool = True,
        baseline_duration: Optional[float] = None,
        baseline_cost: Optional[float] = None,
        logger: Any = None,
    ):
        """
        Initialize spectator.

        Args:
            print_on_complete: Print summary when batch completes
            baseline_duration: Expected duration in seconds
            baseline_cost: Expected cost in USD
            logger: Optional logger
        """
        super().__init__(logger=logger)
        self.print_on_complete = print_on_complete
        self.baseline_duration = baseline_duration
        self.baseline_cost = baseline_cost
        self.session_id: Optional[str] = None
        self.recordings_dir: Optional[Path] = None

    def on_session_start(self, context=None, **kwargs):
        """Capture session ID and recordings directory."""
        # Extract session_id and record_directory from kwargs (Console emits them)
        self.session_id = kwargs.get("session_id")
        if not self.session_id and context and isinstance(context, dict):
            self.session_id = context.get("session_id")

        # Extract recordings base directory from record_directory path
        record_dir = kwargs.get("record_directory")
        if record_dir:
            self.recordings_dir = Path(record_dir).parent.parent

    def on_batch_end(self, batch_id, results, context=None, **kwargs):
        """Run performance analysis when batch completes (PH4)."""
        if not self.session_id:
            if self.logger:
                self.logger.warning(
                    "PerformanceTrackerSpectator: No session_id captured, skipping analysis"
                )
            return

        try:
            # Import standalone class (PH4)
            from ..research import PerformanceAnalysis

            # Call standalone analysis with recordings directory
            if self.recordings_dir:
                analysis = PerformanceAnalysis.from_session(
                    self.session_id,
                    self.recordings_dir,
                    baseline_duration=self.baseline_duration,
                    baseline_cost=self.baseline_cost,
                )
            else:
                analysis = PerformanceAnalysis.from_session(
                    self.session_id,
                    baseline_duration=self.baseline_duration,
                    baseline_cost=self.baseline_cost,
                )

            # Print summary if requested
            if self.print_on_complete:
                analysis.print_summary()

        except FileNotFoundError as e:
            if self.logger:
                self.logger.warning(f"PerformanceTrackerSpectator: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"PerformanceTrackerSpectator failed: {e}")


class CostAnalysisSpectator(Spectator):
    """
    Auto-run cost analysis when batch completes.

    Per SPEC-RESEARCH v1.1.0:
    - Thin wrapper around CostAnalysis.from_session()
    - No logic duplication (PH4)

    Example:
        spectator = CostAnalysisSpectator(
            print_on_complete=True,
            baseline_cost=0.04
        )

        with AgentDeck(game=game, spectators=[spectator]) as deck:
            deck.play(players, matches=100)
    """

    def __init__(
        self,
        *,
        print_on_complete: bool = True,
        baseline_cost: Optional[float] = None,
        logger: Any = None,
    ):
        """
        Initialize spectator.

        Args:
            print_on_complete: Print summary when batch completes
            baseline_cost: Expected cost in USD
            logger: Optional logger
        """
        super().__init__(logger=logger)
        self.print_on_complete = print_on_complete
        self.baseline_cost = baseline_cost
        self.session_id: Optional[str] = None
        self.recordings_dir: Optional[Path] = None

    def on_session_start(self, context=None, **kwargs):
        """Capture session ID and recordings directory."""
        # Extract session_id and record_directory from kwargs (Console emits them)
        self.session_id = kwargs.get("session_id")
        if not self.session_id and context and isinstance(context, dict):
            self.session_id = context.get("session_id")

        # Extract recordings base directory from record_directory path
        record_dir = kwargs.get("record_directory")
        if record_dir:
            self.recordings_dir = Path(record_dir).parent.parent

    def on_batch_end(self, batch_id, results, context=None, **kwargs):
        """Run cost analysis when batch completes (PH4)."""
        if not self.session_id:
            if self.logger:
                self.logger.warning(
                    "CostAnalysisSpectator: No session_id captured, skipping analysis"
                )
            return

        try:
            # Import standalone class (PH4)
            from ..research import CostAnalysis

            # Call standalone analysis with recordings directory
            if self.recordings_dir:
                analysis = CostAnalysis.from_session(
                    self.session_id, self.recordings_dir, baseline_cost=self.baseline_cost
                )
            else:
                analysis = CostAnalysis.from_session(
                    self.session_id, baseline_cost=self.baseline_cost
                )

            # Print summary if requested
            if self.print_on_complete:
                analysis.print_summary()

        except FileNotFoundError as e:
            if self.logger:
                self.logger.warning(f"CostAnalysisSpectator: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"CostAnalysisSpectator failed: {e}")
