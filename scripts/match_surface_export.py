#!/usr/bin/env python3
"""Export static Match Surface JSON artifacts from Recorder v2.0 match records.

This script is intentionally record/replay-only. Public artifacts should be
generated from fixed Recorder records, not from live play(), so source-event
timestamps and payloads remain stable for deterministic publishing.
"""

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


def _assert_static_record(record: dict, record_path: Path) -> None:
    if str(record.get("schema_version")) != Recorder.SCHEMA_VERSION:
        raise ValueError(
            f"{record_path} is not a Recorder {Recorder.SCHEMA_VERSION} record; "
            "static Match Surface export is record/replay-only"
        )
    if not isinstance(record.get("events"), list):
        raise ValueError(f"{record_path} does not contain a Recorder events list")


def export_record(record_path: Path, output_dir: Path) -> Path:
    record = Recorder.load_match(record_path)
    _assert_static_record(record, record_path)
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
