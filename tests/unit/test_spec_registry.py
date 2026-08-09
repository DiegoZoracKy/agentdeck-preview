"""Direct invariant tests for SPEC-SPEC-REGISTRY."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "spec_registry.py"
SPEC = importlib.util.spec_from_file_location("agentdeck_spec_registry", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
registry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = registry
SPEC.loader.exec_module(registry)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "CONTRIBUTING.md").write_text("contributing\n", encoding="utf-8")
    (root / "SECURITY.md").write_text("security\n", encoding="utf-8")
    (root / "specs" / "SPEC.md").write_text("# Hub\n", encoding="utf-8")
    return root


def _write_spec(
    root: Path,
    name: str = "SPEC-EXAMPLE.md",
    *,
    status: str = "Final",
    extra: str = "",
) -> Path:
    path = root / "specs" / name
    path.write_text(
        "# Example\n\n"
        f"> Status: {status}\n"
        "> Version: 1.0.0\n"
        "> Last Updated: 2026-08-07\n"
        "> Implementation: Complete\n"
        "> Review State: Consensus-approved\n"
        f"{extra}\n"
        "## Invariants\n\n1. **EX1 Exact Example**: It is exact.\n",
        encoding="utf-8",
    )
    return path


def _write_profiles(root: Path, sources: list[str]) -> None:
    (root / "specs" / "authoring-profiles.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profiles": [
                    {
                        "profile_id": "test",
                        "version": "1.0.0",
                        "purpose": "test",
                        "sources": sources,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_sr1_rejects_incomplete_metadata(tmp_path: Path) -> None:
    """SR1: governed contracts require complete canonical metadata."""
    root = _repo(tmp_path)
    path = _write_spec(root)
    path.write_text(path.read_text().replace("> Version: 1.0.0\n", ""), encoding="utf-8")
    with pytest.raises(registry.SpecRegistryError, match="missing metadata Version"):
        registry.build_registry(root)


def test_sr2_validates_superseded_lifecycle_target(tmp_path: Path) -> None:
    """SR2: a superseded contract must name an existing Final target."""
    root = _repo(tmp_path)
    _write_spec(root, status="Superseded")
    with pytest.raises(registry.SpecRegistryError, match="Superseded spec needs"):
        registry.build_registry(root)


def test_sr3_registry_is_deterministic(tmp_path: Path) -> None:
    """SR3: equal spec bytes produce byte-identical canonical registry JSON."""
    root = _repo(tmp_path)
    _write_spec(root)
    first = registry._canonical_json(registry.build_registry(root))
    second = registry._canonical_json(registry.build_registry(root))
    assert first == second
    assert b"generated_at" not in first


def test_sr4_rejects_duplicate_active_invariants(tmp_path: Path) -> None:
    """SR4: active invariant IDs are globally unique."""
    root = _repo(tmp_path)
    _write_spec(root, "SPEC-ONE.md")
    _write_spec(root, "SPEC-TWO.md")
    with pytest.raises(registry.SpecRegistryError, match="duplicate active invariant EX1"):
        registry.build_registry(root)

    root = _repo(tmp_path / "same-contract")
    path = _write_spec(root)
    path.write_text(
        path.read_text(encoding="utf-8") + "\n2. **EX1 Duplicate Rule**: Duplicate.\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.SpecRegistryError, match="duplicate invariant declarations"):
        registry.build_registry(root)


def test_sr5_rejects_unresolved_relative_links(tmp_path: Path) -> None:
    """SR5: relative spec links resolve inside the repository."""
    root = _repo(tmp_path)
    path = _write_spec(root)
    path.write_text(path.read_text() + "\n[missing](MISSING.md)\n", encoding="utf-8")
    with pytest.raises(registry.SpecRegistryError, match="unresolved relative link"):
        registry.build_registry(root)


def test_sr6_profile_is_a_closed_ordered_source_list(tmp_path: Path) -> None:
    """SR6: undeclared and duplicate profile sources fail."""
    root = _repo(tmp_path)
    _write_spec(root)
    _write_profiles(root, ["specs/SPEC.md", "unexpected.md"])
    with pytest.raises(registry.SpecRegistryError, match="undeclared source"):
        registry.validate_profiles(registry.build_registry(root), root)


def test_sr7_bundle_is_deterministic_and_ordered(tmp_path: Path) -> None:
    """SR7: bundles have stable bytes and preserve declared source order."""
    root = _repo(tmp_path)
    _write_spec(root)
    _write_profiles(root, ["CONTRIBUTING.md", "specs/SPEC-EXAMPLE.md"])
    first = registry.render_bundle("test", root)
    second = registry.render_bundle("test", root)
    assert first == second
    assert first.index(b"CONTRIBUTING.md") < first.index(b"SPEC-EXAMPLE.md")


def test_sr8_rejects_verified_claim_without_direct_evidence(tmp_path: Path) -> None:
    """SR8: verified automated assurance requires every invariant's direct test."""
    root = _repo(tmp_path)
    _write_spec(root)
    (root / "specs" / "compliance.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contracts": [
                    {
                        "spec_id": "SPEC-EXAMPLE",
                        "status": "verified",
                        "assurance": "mapped",
                        "evidence": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(registry.SpecRegistryError, match="automated or semantic"):
        registry.validate_compliance(registry.build_registry(root), root)


def test_sr9_does_not_expand_one_invariant_into_a_range(tmp_path: Path) -> None:
    """SR9: one named invariant does not verify adjacent IDs."""
    root = _repo(tmp_path)
    path = _write_spec(root)
    path.write_text(
        path.read_text() + "\n2. **EX2 Another Rule**: It is separate.\n",
        encoding="utf-8",
    )
    test_path = root / "tests" / "test_example.py"
    test_path.write_text(
        "def test_ex1_direct():\n" '    """EX1: direct evidence."""\n' "    assert True\n",
        encoding="utf-8",
    )
    (root / "specs" / "compliance.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contracts": [
                    {
                        "spec_id": "SPEC-EXAMPLE",
                        "status": "verified",
                        "assurance": "automated",
                        "evidence": [
                            {
                                "invariant_id": "EX1",
                                "test": "tests/test_example.py::test_ex1_direct",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(registry.SpecRegistryError, match="EX2"):
        registry.validate_compliance(registry.build_registry(root), root)


def test_sr10_check_rejects_stale_checked_in_registry(tmp_path: Path) -> None:
    """SR10: check fails instead of silently rewriting stale registry bytes."""
    root = _repo(tmp_path)
    _write_spec(root)
    _write_profiles(root, ["specs/SPEC.md"])
    (root / "specs" / "compliance.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contracts": [
                    {
                        "spec_id": "SPEC-EXAMPLE",
                        "status": "partial",
                        "assurance": "mapped",
                        "evidence": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "specs" / "registry.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(registry.SpecRegistryError, match="is stale"):
        registry.check(root)


def test_sr11_requires_exact_test_function_locator(tmp_path: Path) -> None:
    """SR11: file-level mentions cannot masquerade as direct executable evidence."""
    root = _repo(tmp_path)
    _write_spec(root)
    test_path = root / "tests" / "test_example.py"
    test_path.write_text(
        "# EX1 appears only outside the test.\n"
        "def test_neighboring_behavior():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    (root / "specs" / "compliance.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contracts": [
                    {
                        "spec_id": "SPEC-EXAMPLE",
                        "status": "verified",
                        "assurance": "automated",
                        "evidence": [
                            {
                                "invariant_id": "EX1",
                                "test": "tests/test_example.py::test_neighboring_behavior",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    missing_function_payload = json.loads(
        (root / "specs" / "compliance.json").read_text(encoding="utf-8")
    )
    missing_function_payload["contracts"][0]["evidence"][0][
        "test"
    ] = "tests/test_example.py::test_missing"
    (root / "specs" / "compliance.json").write_text(
        json.dumps(missing_function_payload), encoding="utf-8"
    )
    with pytest.raises(registry.SpecRegistryError, match="must resolve to one test function"):
        registry.validate_compliance(registry.build_registry(root), root)

    missing_function_payload["contracts"][0]["evidence"][0][
        "test"
    ] = "tests/test_example.py::test_neighboring_behavior"
    (root / "specs" / "compliance.json").write_text(
        json.dumps(missing_function_payload), encoding="utf-8"
    )
    with pytest.raises(registry.SpecRegistryError, match="does not name EX1 directly"):
        registry.validate_compliance(registry.build_registry(root), root)


def test_sr12_rejects_vacuous_verified_contract(tmp_path: Path) -> None:
    """SR12: an empty invariant set cannot satisfy verified by set equality."""
    root = _repo(tmp_path)
    path = _write_spec(root)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "## Invariants\n\n1. **EX1 Exact Example**: It is exact.\n", ""
        ),
        encoding="utf-8",
    )
    (root / "specs" / "compliance.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contracts": [
                    {
                        "spec_id": "SPEC-EXAMPLE",
                        "status": "verified",
                        "assurance": "mapped",
                        "evidence": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(registry.SpecRegistryError, match="at least one registered invariant"):
        registry.validate_compliance(registry.build_registry(root), root)


def test_sr13_exposes_unregistered_legacy_invariants(tmp_path: Path) -> None:
    """SR13: legacy IDs remain visible and block verified assurance."""
    root = _repo(tmp_path)
    path = _write_spec(root)
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n- **EX2**: This legacy invariant remains normative.\n"
        + "- `VD-B2a`: Hyphenated legacy identities remain visible too.\n",
        encoding="utf-8",
    )
    built = registry.build_registry(root)
    contract = built["contracts"][0]
    assert contract["unregistered_invariants"] == ["EX2", "VD-B2a"]
    assert built["invariant_summary"] == {
        "scope": "active_contracts",
        "registered": 1,
        "unregistered": 2,
    }

    test_path = root / "tests" / "test_example.py"
    test_path.write_text(
        "def test_ex1_direct():\n" '    """EX1: direct evidence."""\n' "    assert True\n",
        encoding="utf-8",
    )
    (root / "specs" / "compliance.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contracts": [
                    {
                        "spec_id": "SPEC-EXAMPLE",
                        "status": "verified",
                        "assurance": "automated",
                        "evidence": [
                            {
                                "invariant_id": "EX1",
                                "test": "tests/test_example.py::test_ex1_direct",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(registry.SpecRegistryError, match="unregistered invariants.*EX2"):
        registry.validate_compliance(built, root)


def test_sr14_summary_counts_only_active_contracts(tmp_path: Path) -> None:
    """SR14: summary scope excludes inactive debt without hiding its contract."""
    root = _repo(tmp_path)
    active_path = _write_spec(root, "SPEC-CURRENT.md")
    active_path.write_text(
        active_path.read_text(encoding="utf-8")
        + "\n- **EX2**: Active legacy debt contributes to the summary.\n",
        encoding="utf-8",
    )
    inactive_path = _write_spec(
        root,
        "SPEC-OLD.md",
        status="Superseded",
        extra="> Superseded By: SPEC-CURRENT.md\n",
    )
    inactive_path.write_text(
        inactive_path.read_text(encoding="utf-8")
        + "\n- **OLD1**: Inactive legacy debt remains discoverable.\n",
        encoding="utf-8",
    )

    built = registry.build_registry(root)

    assert built["invariant_summary"] == {
        "scope": "active_contracts",
        "registered": 1,
        "unregistered": 1,
    }
    old_contract = next(
        contract for contract in built["contracts"] if contract["spec_id"] == "SPEC-OLD"
    )
    assert old_contract["active"] is False
    assert old_contract["unregistered_invariants"] == ["OLD1"]


def test_sr15_complete_new_work_requires_direct_evidence(tmp_path: Path) -> None:
    """SR15: new Complete invariants need tests without backfilling untouched debt."""
    root = _repo(tmp_path)
    _write_spec(root)
    test_path = root / "tests" / "test_example.py"
    test_path.write_text(
        "def test_ex1_direct():\n" '    """EX1: direct evidence."""\n' "    assert True\n",
        encoding="utf-8",
    )
    _write_profiles(root, ["specs/SPEC.md"])
    (root / "specs" / "compliance.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contracts": [
                    {
                        "spec_id": "SPEC-EXAMPLE",
                        "status": "partial",
                        "assurance": "mapped",
                        "evidence": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    current = registry.build_registry(root)
    previous = json.loads(json.dumps(current))
    previous["contracts"][0]["invariants"] = []
    previous["contracts"][0]["invariant_sha256"] = {}

    with pytest.raises(registry.SpecRegistryError, match="lacks direct evidence.*EX1"):
        registry.validate_new_work_evidence(current, previous, root)

    payload = json.loads((root / "specs" / "compliance.json").read_text(encoding="utf-8"))
    payload["contracts"][0]["assurance"] = "automated"
    payload["contracts"][0]["evidence"] = [
        {"invariant_id": "EX1", "test": "tests/test_example.py::test_ex1_direct"}
    ]
    (root / "specs" / "compliance.json").write_text(json.dumps(payload), encoding="utf-8")
    registry.validate_new_work_evidence(current, previous, root)

    unchanged_previous = json.loads(json.dumps(current))
    payload["contracts"][0]["assurance"] = "mapped"
    payload["contracts"][0]["evidence"] = []
    (root / "specs" / "compliance.json").write_text(json.dumps(payload), encoding="utf-8")
    registry.validate_new_work_evidence(current, unchanged_previous, root)
