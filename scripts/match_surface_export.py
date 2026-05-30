#!/usr/bin/env python3
"""Export Match Surface JSON artifacts from Recorder v2.0 match records."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentdeck.core.recorder import Recorder
from agentdeck.core.replay import ReplayEngine
from agentdeck.spectators.match_surface import JsonArtifactSink, MatchSurfaceProjector


def export_record(record_path: Path, output_dir: Path) -> Path:
    record = Recorder.load_match(record_path)
    sink = JsonArtifactSink(output_dir)
    ReplayEngine(record).replay(spectators=[MatchSurfaceProjector(sink=sink)], speed=0.0)
    if sink.last_path is None:
        raise RuntimeError(f"No Match Surface artifact written for {record_path}")
    return sink.last_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path, help="Recorder v2.0 match JSON files")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for record_path in args.records:
        artifact_path = export_record(record_path, args.output_dir)
        print(artifact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
