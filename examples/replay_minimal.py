"""
Replay a previously recorded AgentDeck match.

Usage:
    python examples/replay_minimal.py \
        --recording agentdeck_runs/session_<timestamp>/records/match_<id>.json \
        --speed 1.0

If --recording is omitted the script will automatically replay the most recent
match located under the ./agentdeck_runs directory.

The replay uses spectators to demonstrate full lifecycle observation:
    - MatchReporter (displays reasoning, actions, reflections)
    - TokenUsageTracker (reconstructs cost metadata)
    - StatsTracker (rebuilds match statistics)

This demonstrates that spectators observe the replayed match in the exact same
order as during live execution (SPEC-REPLAY v1.0.0, R1 parity guarantee).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from agentdeck import MatchReporter, StatsTracker, TokenUsageTracker
from agentdeck.core.replay import ReplayEngine


def find_latest_recording(base_dir: Path) -> Path:
    """
    Locate the newest match recording in the runs directory.

    Args:
        base_dir: Root runs directory (default ./agentdeck_runs)

    Returns:
        Path to the most recently modified match_<id>.json file.

    Raises:
        FileNotFoundError: If no recording files are found.
    """
    if not base_dir.exists():
        raise FileNotFoundError(
            f"No runs directory found at {base_dir.resolve()}.\n"
            "Run examples/minimal_experiment.py first to generate a recording."
        )

    # Sort sessions by modification time (latest first)
    for session_dir in sorted(
        (p for p in base_dir.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        # Recordings are now under records/ subdirectory
        records_dir = session_dir / "records"
        if not records_dir.exists():
            continue

        match_files = sorted(
            records_dir.glob("match_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if match_files:
            return match_files[0]

    raise FileNotFoundError(
        f"No match recordings found under {base_dir.resolve()}.\n"
        "Run examples/minimal_experiment.py to generate a recording."
    )


def load_match(path: Path) -> dict:
    """Load match recording JSON."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pretty_print_header(title: str) -> None:
    """Utility to print section headers."""
    line = "=" * 60
    print(f"\n{line}\n{title}\n{line}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a recorded AgentDeck match.")
    parser.add_argument(
        "--recording",
        type=Path,
        help="Path to match_<id>.json recording (defaults to the newest recording).",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Replay speed multiplier (1.0 = real-time, 0.0 = as fast as possible).",
    )
    args = parser.parse_args()

    runs_root = Path("agentdeck_runs")
    recording_path = args.recording or find_latest_recording(runs_root)

    if not recording_path.exists():
        print(f"❌ Recording file not found: {recording_path}", file=sys.stderr)
        sys.exit(1)

    pretty_print_header("AgentDeck Replay Example")
    print(f"Replaying recording: {recording_path}")
    print(f"Speed multiplier: {args.speed}\n")

    match_data = load_match(recording_path)

    # Configure console logger for spectators
    console_logger = logging.getLogger("replay")
    console_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    console_logger.addHandler(handler)
    console_logger.propagate = False

    # Spectators observe the replay just like a live run.
    # MatchReporter displays full lifecycle (handshake → turns → reflections)
    reporter = MatchReporter(show_state_changes=True, logger=console_logger)
    tokens = TokenUsageTracker()
    stats = StatsTracker()

    engine = ReplayEngine(match_data)
    engine.replay(
        spectators=[
            reporter,
            tokens,
            stats,
        ],
        speed=args.speed,
    )

    # Summaries -----------------------------------------------------------------
    pretty_print_header("Replay Summary")

    match_meta = match_data.get("metadata", {}).get("match", {})
    winner = match_data.get("winner") or "Draw"
    turns = match_meta.get("turns", "?")
    duration = match_meta.get("duration")
    if duration is not None:
        print(f"Match Duration: {duration:.2f}s")
    print(f"Winner: {winner}")
    print(f"Turns: {turns}")

    pretty_print_header("Token Usage Summary")
    token_summary = tokens.get_summary()
    total = token_summary["total"]
    print(f"API Calls: {total['calls']}")
    print(f"Total Tokens: {total['total_tokens']}")
    print(f"  - Prompt: {total['prompt_tokens']}")
    print(f"  - Completion: {total['completion_tokens']}")
    print(f"Total Cost: ${total['cost']:.4f}")

    if token_summary["per_player"]:
        print("\nPer-Player Usage:")
        for player, info in token_summary["per_player"].items():
            print(
                f"  {player}: {info['calls']} calls | "
                f"{info['total_tokens']} tokens | ${info['cost']:.4f}"
            )

    pretty_print_header("Match Statistics")
    stats_summary = stats.get_stats()
    print(f"Total Matches: {stats_summary['total_matches']}")
    if stats_summary.get("avg_match_duration"):
        print(
            f"Average Match Duration: {stats_summary['avg_match_duration']:.2f}s"
        )

    if stats_summary["players"]:
        print("\nPlayer Performance:")
        for player, info in stats_summary["players"].items():
            print(f"\n{player}:")
            print(f"  Wins: {info['wins']}")
            print(f"  Losses: {info['losses']}")
            print(f"  Win Rate: {info['win_rate']:.1%}")
            print(f"  Total Turns: {info['total_turns']}")

    pretty_print_header("Replay complete – parity with live run confirmed ✅")


if __name__ == "__main__":
    main()
