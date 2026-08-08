"""Direct invariant tests for SPEC-ARTIFACT-SAFETY."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentdeck.core.artifact_safety import (
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
