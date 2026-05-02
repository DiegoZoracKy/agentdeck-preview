"""
Non-combat ArchivistChoiceGame demo.

Runs deterministic mock policies through a manuscript-triage benchmark and
prints the generated replay recording path. No API keys are required.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from agentdeck import AgentDeck, AgentDeckConfig, ArchivistChoiceGame, MatchReporter, MockPlayer
from agentdeck.controllers import ActionOnlyController
from agentdeck.spectators import StatsTracker


def build_players():
    controller = ActionOnlyController()
    return [
        MockPlayer(
            name="Cataloger",
            actions=["CATALOG", "CATALOG", "CATALOG", "CATALOG"],
            controller=controller,
        ),
        MockPlayer(
            name="Conservator",
            actions=["RESTORE", "QUARANTINE", "CATALOG", "RESTORE"],
            controller=controller,
        ),
    ]


def run_demo(*, viewer_output: Path | None = None) -> Path:
    stats = StatsTracker()
    config = AgentDeckConfig(seed=11, run_dir="agentdeck_runs/archivist_choice_demo")

    with AgentDeck(
        game=ArchivistChoiceGame(),
        session=config,
        spectators=[MatchReporter(), stats],
    ) as deck:
        results = deck.play(players=build_players(), matches=1, seed=11)
        record_dir = Path(deck.session.record_directory)

    recording = sorted(record_dir.glob("match_*.json"))[-1]
    print(f"\nWinner: {results.single.winner or 'Draw'}")
    print(f"Win rates: {results.win_rates}")
    print(f"Recording: {recording}")

    if viewer_output is not None:
        viewer_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(recording, viewer_output)
        print(f"Viewer sample: {viewer_output}")
        return viewer_output

    return recording


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ArchivistChoiceGame mock demo.")
    parser.add_argument(
        "--viewer-output",
        type=Path,
        help="Optional path to copy the generated recording for viewer samples.",
    )
    args = parser.parse_args()
    run_demo(viewer_output=args.viewer_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
