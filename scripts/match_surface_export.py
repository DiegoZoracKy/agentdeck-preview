#!/usr/bin/env python3
"""Export static Match Surface JSON artifacts from Recorder v2.0 match records.

This script is intentionally record/replay-only. Public artifacts should be
generated from fixed Recorder records, not from live play(), so source-event
timestamps and payloads remain stable for deterministic publishing.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentdeck.core.recorder import Recorder
from agentdeck.core.replay import ReplayEngine
from agentdeck.spectators.match_surface import JsonArtifactSink, MatchSurfaceProjector


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return payload


def _assert_static_record(record: dict, record_path: Path) -> None:
    if str(record.get("schema_version")) != Recorder.SCHEMA_VERSION:
        raise ValueError(
            f"{record_path} is not a Recorder {Recorder.SCHEMA_VERSION} record; "
            "static Match Surface export is record/replay-only"
        )
    if not isinstance(record.get("events"), list):
        raise ValueError(f"{record_path} does not contain a Recorder events list")


def _resolve_sidecar_path(record_path: Path, sidecar_dir: Path | None) -> Path | None:
    if sidecar_dir is None:
        candidate = record_path.with_suffix(".meta.json")
        return candidate if candidate.exists() else None

    candidate = sidecar_dir / f"{record_path.stem}.meta.json"
    if not candidate.exists():
        raise ValueError(f"Missing curation sidecar for {record_path}: expected {candidate}")
    return candidate


def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must contain non-empty string field: {key}")
    return value


def _normalize_sidecar(sidecar_path: Path) -> dict[str, Any]:
    payload = _load_json(sidecar_path)
    highlights_raw = payload.get("highlights")
    if not isinstance(highlights_raw, list):
        raise ValueError(f"{sidecar_path} must contain highlights as an array")

    highlights: list[dict[str, Any]] = []
    for index, item in enumerate(highlights_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{sidecar_path} highlight {index} must be an object")
        try:
            turn = int(item["turn"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{sidecar_path} highlight {index} must contain integer turn") from exc
        if turn < 1:
            raise ValueError(f"{sidecar_path} highlight {index} turn must be >= 1")
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"{sidecar_path} highlight {index} must contain non-empty label")
        kind = item.get("kind")
        if kind is not None and not isinstance(kind, str):
            raise ValueError(f"{sidecar_path} highlight {index} kind must be a string")
        highlights.append({"turn": turn, "label": label, "kind": kind})

    return {
        "version": int(payload.get("version", 1)),
        "subtitle": _require_string(payload, "subtitle", sidecar_path),
        "synopsis": _require_string(payload, "synopsis", sidecar_path),
        "highlights": highlights,
        "artifact": sidecar_path.name,
    }


def _marker_from_highlight(
    highlight: dict[str, Any],
    *,
    index: int,
    sidecar: dict[str, Any],
) -> dict[str, Any]:
    turn = int(highlight["turn"])
    marker = {
        "id": f"curation-highlight-{turn}-{index}",
        "phase_index": turn - 1,
        "turn": turn,
        "source": "upstream",
        "rule": "curation_sidecar.highlight",
        "label": highlight["label"],
        "severity": "info",
        "data": {
            "sidecar_version": sidecar["version"],
            "sidecar_artifact": sidecar["artifact"],
        },
    }
    if highlight.get("kind"):
        marker["data"]["kind"] = highlight["kind"]
    return marker


def _apply_sidecar(document: dict[str, Any], sidecar: dict[str, Any]) -> None:
    frames = document.get("frames") or []
    frames_by_phase = {
        frame.get("phase_index"): frame for frame in frames if isinstance(frame, dict)
    }
    markers = [
        _marker_from_highlight(highlight, index=index, sidecar=sidecar)
        for index, highlight in enumerate(sidecar["highlights"], start=1)
    ]

    for marker in markers:
        frame = frames_by_phase.get(marker["phase_index"])
        if frame is None:
            raise ValueError(
                f"{sidecar['artifact']} highlight turn {marker['turn']} does not map "
                "to a Match Surface frame"
            )
        frame.setdefault("markers", []).append(copy.deepcopy(marker))

    document["markers"] = list(document.get("markers") or []) + markers
    document["curation"] = {
        "version": sidecar["version"],
        "subtitle": sidecar["subtitle"],
        "synopsis": sidecar["synopsis"],
        "source": {
            "type": "curation_sidecar",
            "artifact": sidecar["artifact"],
        },
    }


def _build_static_post_processor(
    raw_record: dict[str, Any],
    *,
    sidecar: dict[str, Any] | None,
    errors: list[BaseException] | None = None,
):
    def post_process(document: dict[str, Any]) -> dict[str, Any]:
        try:
            document = copy.deepcopy(document)
            source = document.setdefault("source", {})
            source["record_schema_version"] = str(raw_record.get("schema_version"))
            source["match_id"] = raw_record.get("match_id") or source.get("match_id")
            if isinstance(raw_record.get("migration_provenance"), dict):
                source["provenance"] = copy.deepcopy(raw_record["migration_provenance"])
            if sidecar is not None:
                _apply_sidecar(document, sidecar)
            return document
        except Exception as exc:
            if errors is not None:
                errors.append(exc)
            raise

    return post_process


def export_record(record_path: Path, output_dir: Path, sidecar_dir: Path | None = None) -> Path:
    raw_record = _load_json(record_path)
    _assert_static_record(raw_record, record_path)
    sidecar_path = _resolve_sidecar_path(record_path, sidecar_dir)
    sidecar = _normalize_sidecar(sidecar_path) if sidecar_path is not None else None

    record = Recorder.load_match(record_path)
    sink = JsonArtifactSink(output_dir)
    post_process_errors: list[BaseException] = []
    projector = MatchSurfaceProjector(
        sink=sink,
        redactor=_build_static_post_processor(
            raw_record,
            sidecar=sidecar,
            errors=post_process_errors,
        ),
    )
    ReplayEngine(record).replay(spectators=[projector], speed=0.0)
    if post_process_errors:
        raise post_process_errors[0]
    if sink.last_path is None:
        raise RuntimeError(f"No Match Surface artifact written for {record_path}")
    return sink.last_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path, help="Recorder v2.0 match JSON files")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--sidecar-dir",
        type=Path,
        default=None,
        help=(
            "Optional directory containing <record-stem>.meta.json curation sidecars. "
            "When provided, every input record must have a matching sidecar."
        ),
    )
    args = parser.parse_args()

    for record_path in args.records:
        artifact_path = export_record(record_path, args.output_dir, sidecar_dir=args.sidecar_dir)
        print(artifact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
