"""Release-hardening tests for the current Agentic Edge reproducer and Measures."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "research" / "2026-04-27-agentic-edge-strategy-stack"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


REPRODUCER = _load_module(
    "agentdeck_agentic_edge_reproducer", STUDY_ROOT / "scripts" / "reproduce_current.py"
)
MEASURES = _load_module("agentdeck_agentic_edge_measures", STUDY_ROOT / "measures.py")


def test_source_checksum_verification_rejects_tampered_cached_record(tmp_path):
    relative = "p0/raw_recordings/run/records/match_001.json"
    source = tmp_path / "source"
    target = source / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="failed checksum verification"):
        REPRODUCER._materialize_source(
            source,
            (relative,),
            {relative: hashlib.sha256(b"frozen").hexdigest()},
        )


def test_checksum_manifest_identity_is_pinned_even_for_cached_source(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    manifest = source / "checksums.sha256"
    manifest.write_text(f"{'0' * 64}  record.json\n", encoding="utf-8")
    monkeypatch.setattr(REPRODUCER, "HF_CHECKSUMS_SHA256", "f" * 64)

    with pytest.raises(ValueError, match="checksum manifest diverges"):
        REPRODUCER._source_checksums(source)


def test_outcome_measure_never_turns_missing_support_into_neutral_values():
    record = SimpleNamespace(
        cell_id="draw-only",
        payload={
            "players": ["Alice", "Bob"],
            "winner": None,
            "metadata": {"match": {"first_player": {"name": "Alice"}, "turns": 0}},
            "events": [],
        },
    )

    results = MEASURES.outcome_measure(SimpleNamespace(records=(record,)))
    indexed = {
        (item["metric"], tuple(sorted(item["dimensions"].items()))): item for item in results
    }

    for player in ("Alice", "Bob"):
        dimensions = (("cell", "draw-only"), ("player", player))
        for metric in (
            "win-rate",
            "win-rate-ci-lower",
            "win-rate-ci-upper",
            "exact-binomial-p-value",
            "cohens-h-versus-half",
        ):
            assert indexed[(metric, dimensions)]["status"] == "unavailable"

    assert (
        indexed[("win-rate-as-second", (("cell", "draw-only"), ("player", "Alice")))]["status"]
        == "unavailable"
    )
    assert (
        indexed[("win-rate-as-first", (("cell", "draw-only"), ("player", "Bob")))]["status"]
        == "unavailable"
    )
    assert indexed[("total-cost", (("cell", "draw-only"),))]["status"] == "unavailable"
    assert indexed[("average-cost", (("cell", "draw-only"),))]["status"] == "unavailable"
    assert indexed[("average-duration", (("cell", "draw-only"),))]["status"] == "unavailable"
