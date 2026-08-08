"""Direct invariant tests for SPEC-ARTIFACT-SAFETY."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentdeck.core.artifact_safety import (
    atomic_write_json,
    atomic_write_text,
    contained_path,
    ensure_contained_path,
    require_json_value,
    validate_artifact_id,
)


@pytest.mark.parametrize(
    "value",
    ["match_0123abcd", "research_2026-08-07-test", "A.b-c_1"],
)
def test_as1_accepts_portable_artifact_ids(value: str) -> None:
    """AS1: portable artifact identifiers are returned unchanged."""
    assert validate_artifact_id(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "../outside",
        "a/b",
        "a\\b",
        "/absolute",
        "C:drive",
        "caf\u00e9",
        "x\x00y",
        "a" * 129,
    ],
)
def test_as1_as3_reject_unsafe_ids_without_rewriting(value: str) -> None:
    """AS1/AS3: unsafe identities fail instead of being normalized."""
    with pytest.raises(ValueError):
        validate_artifact_id(value)


def test_as2_contained_path_rejects_resolved_escape(tmp_path: Path) -> None:
    """AS2: candidates outside the declared root are rejected after resolution."""
    root = tmp_path / "root"
    outside = tmp_path / "outside.json"
    root.mkdir()

    assert contained_path(root, "match_1") == root / "match_1"
    with pytest.raises(ValueError, match="leaves declared root"):
        ensure_contained_path(root, outside)


@pytest.mark.parametrize(
    "value",
    [{"bad": {1, 2}}, {1: "non-string-key"}, {"tuple": (1, 2)}, {"nan": float("nan")}],
)
def test_as4_rejects_lossy_or_non_json_values(value: object) -> None:
    """AS4: values that would coerce or lose type fail strict JSON validation."""
    with pytest.raises(ValueError, match="strict JSON"):
        require_json_value(value, field="payload")


def test_as4_accepts_nested_strict_json() -> None:
    """AS4: canonical JSON values pass unchanged."""
    require_json_value(
        {"turn": 1, "state": {"hp": [100, 80]}, "terminal": False},
        field="payload",
    )


def test_as5_as9_atomic_json_rejection_preserves_destination(tmp_path: Path) -> None:
    """AS5/AS9: strict validation completes before replacement or temp creation."""
    destination = tmp_path / "results.json"
    destination.write_text('{"status":"before"}', encoding="utf-8")

    with pytest.raises(ValueError, match="strict JSON"):
        atomic_write_json(destination, {"bad": float("nan")}, field="results")

    assert destination.read_text(encoding="utf-8") == '{"status":"before"}'
    assert list(tmp_path.glob(".results.json.*.tmp")) == []


def test_as9_atomic_text_failure_cleans_temp_and_preserves_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AS9: replacement failure cannot expose partial text or orphan its temp file."""
    destination = tmp_path / "artifact.txt"
    destination.write_text("before", encoding="utf-8")

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr("agentdeck.core.artifact_safety.os.replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        atomic_write_text(destination, "after")

    assert destination.read_text(encoding="utf-8") == "before"
    assert list(tmp_path.glob(".artifact.txt.*.tmp")) == []
