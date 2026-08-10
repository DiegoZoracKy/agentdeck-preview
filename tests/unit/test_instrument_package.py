"""Direct invariant tests for SPEC-INSTRUMENT-PACKAGE v0.1.0."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from agentdeck.instruments import certify_instrument, inspect_instrument, validate_instrument
from agentdeck.instruments.cli import main

FIXTURE = Path(__file__).parents[1] / "fixtures" / "instruments" / "number_duel"


def _copy_fixture(tmp_path: Path) -> Path:
    package = tmp_path / "number-duel"
    shutil.copytree(FIXTURE, package)
    return package


def _manifest(package: Path) -> dict:
    return yaml.safe_load((package / "instrument.yaml").read_text(encoding="utf-8"))


def _write_manifest(package: Path, manifest: dict) -> None:
    (package / "instrument.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )


def _check(report, check_id: str) -> dict:
    return next(check for check in report.to_dict()["checks"] if check["id"] == check_id)


def test_ip1_manifest_bytes_are_package_authority(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    first = inspect_instrument(package)
    manifest = _manifest(package)
    manifest["instrument"]["summary"] += " Changed."
    _write_manifest(package, manifest)
    second = inspect_instrument(package)
    assert first.package_sha256 != second.package_sha256
    assert _check(second, "IP1")["status"] == "passed"


def test_ip2_structural_validation_does_not_import_python(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    marker = tmp_path / "imported.txt"
    game = package / "number_duel" / "game.py"
    game.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('imported')\n"
        + game.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    report = validate_instrument(package)
    assert report.valid
    assert not marker.exists()
    assert _check(report, "IP2")["status"] == "passed"


def test_ip3_rejects_package_path_escape(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    manifest = _manifest(package)
    manifest["presentation"] = {
        "redactor_entry_point": "number_duel.game:NumberDuelGame",
        "viewer": "../outside.html",
    }
    (tmp_path / "outside.html").write_text("outside", encoding="utf-8")
    _write_manifest(package, manifest)
    report = validate_instrument(package)
    assert not report.valid
    assert "leaves declared root" in _check(report, "IP3")["message"]


def test_ip4_external_game_certifies_without_registry(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    report = certify_instrument(package, trust_mode="trusted-local", output_dir=tmp_path / "output")
    assert report.valid, report.to_dict()
    assert report.awarded_tiers == ["runnable", "evidence_ready", "presentable"]
    assert _check(report, "IP4")["status"] == "passed"


def test_as8_ip5_ip6_ip7_public_types_config_and_honest_fixture_boundary(
    tmp_path: Path,
) -> None:
    report = certify_instrument(
        _copy_fixture(tmp_path),
        trust_mode="trusted-local",
        output_dir=tmp_path / "output",
    )
    for invariant in ("IP5", "IP6", "IP7"):
        assert _check(report, invariant)["status"] == "passed"
    fixture_boundary = _check(report, "IP7")
    assert fixture_boundary["details"] == {
        "core_supplied_provider_credentials": False,
        "core_supplied_user_input": False,
        "repeated_execution_checked": True,
        "ambient_isolation": "not_proven",
    }
    assert "offline" not in fixture_boundary["message"].lower()


def test_ip6_rejects_effective_config_drift(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    game = package / "number_duel" / "game.py"
    content = game.read_text(encoding="utf-8").replace(
        '"config": {"target": self.target}', '"config": {"target": self.target + 1}'
    )
    game.write_text(content, encoding="utf-8")
    report = certify_instrument(package, trust_mode="trusted-local")
    assert not report.valid
    assert "declared effective config" in _check(report, "IP5")["message"]


def test_ip8_seeded_execution_has_equal_semantic_trace(tmp_path: Path) -> None:
    report = certify_instrument(
        _copy_fixture(tmp_path),
        trust_mode="trusted-local",
        output_dir=tmp_path / "output",
    )
    assert _check(report, "IP8")["status"] == "passed"


def test_ip9_every_recording_replays_with_event_data_parity(tmp_path: Path) -> None:
    report = certify_instrument(
        _copy_fixture(tmp_path),
        trust_mode="trusted-local",
        output_dir=tmp_path / "output",
    )
    assert _check(report, "IP9")["status"] == "passed"


def test_ip10_manifest_rejects_non_json_yaml_scalar(tmp_path: Path) -> None:
    """IP10: non-JSON YAML scalar types are rejected without coercion."""
    package = _copy_fixture(tmp_path)
    path = package / "instrument.yaml"
    path.write_text(
        path.read_text(encoding="utf-8") + "unexpected_date: 2026-08-07\n", encoding="utf-8"
    )
    report = validate_instrument(package)
    assert not report.valid
    assert _check(report, "IP1")["status"] == "failed"


def test_ip11_structural_mode_cannot_award_capability(tmp_path: Path) -> None:
    """IP11: structural trust cannot award executable capability tiers."""
    report = certify_instrument(_copy_fixture(tmp_path), trust_mode="structural")
    assert not report.valid
    assert report.awarded_tiers == []


def test_ip11_rejects_undeclared_tier_prerequisites(tmp_path: Path) -> None:
    """IP11: requested capability tiers require their own declarations."""
    package = _copy_fixture(tmp_path)
    manifest = _manifest(package)
    manifest.pop("evidence")
    manifest["claims"]["requested"] = ["runnable", "evidence_ready"]
    _write_manifest(package, manifest)
    report = validate_instrument(package)
    assert not report.valid
    assert "requires an evidence declaration" in _check(report, "IP3")["message"]


def test_ip14_failed_certification_preserves_prior_success_report(tmp_path: Path) -> None:
    """IP14: failed certification cannot replace a prior successful report."""
    package = _copy_fixture(tmp_path)
    output = tmp_path / "output"
    success = certify_instrument(package, trust_mode="trusted-local", output_dir=output)
    assert success.valid
    prior = (output / "certification.json").read_bytes()
    manifest = _manifest(package)
    manifest["fixture"]["expected_winners"] = ["Beta", "Beta"]
    _write_manifest(package, manifest)
    failure = certify_instrument(package, trust_mode="trusted-local", output_dir=output)
    assert not failure.valid
    assert (output / "certification.json").read_bytes() == prior


def test_ip15_equal_package_and_execution_produce_equal_reports(tmp_path: Path) -> None:
    """IP15: equal package execution produces byte-identical reports."""
    package = _copy_fixture(tmp_path)
    first = certify_instrument(package, trust_mode="trusted-local", output_dir=tmp_path / "one")
    second = certify_instrument(package, trust_mode="trusted-local", output_dir=tmp_path / "two")
    assert first.canonical_json() == second.canonical_json()


def test_ip19_rejects_transient_artifacts_before_package_hash(tmp_path: Path) -> None:
    """IP19: runtime/tool output is not portable authored package source."""
    transient_paths = (
        "number_duel/__pycache__/game.cpython-310.pyc",
        ".mypy_cache/cache.db",
        ".pytest_cache/nodeids",
        ".ruff_cache/content",
        ".coverage",
        ".DS_Store",
        "number_duel/game.pyo",
    )
    for index, relative in enumerate(transient_paths):
        package = _copy_fixture(tmp_path / str(index))
        artifact = package / relative
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(b"transient")
        report = inspect_instrument(package)
        assert not report.valid
        assert report.package_sha256 is None
        assert _check(report, "IP19")["status"] == "failed"
        assert relative in _check(report, "IP19")["message"]

    portable = _copy_fixture(tmp_path / "portable")
    browser_asset = portable / "presentation" / "vendor" / "stage.js.map"
    browser_asset.parent.mkdir(parents=True)
    browser_asset.write_text("{}", encoding="utf-8")
    report = inspect_instrument(portable)
    assert report.valid
    assert report.package_sha256 is not None
    assert _check(report, "IP19")["status"] == "passed"


def test_cli_emits_canonical_json_and_status(capsys, tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    assert main(["validate", str(package)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["operation"] == "validate"


def test_unknown_manifest_fields_fail_loudly(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    manifest = _manifest(package)
    manifest["game"]["silent_typo"] = True
    _write_manifest(package, manifest)
    report = validate_instrument(package)
    assert not report.valid
    assert "unknown fields" in _check(report, "IP3")["message"]


def test_ip13_terminal_oracle_values_require_declared_paths(tmp_path: Path) -> None:
    """IP13: terminal values cannot create an unbounded disclosure scope."""
    package = _copy_fixture(tmp_path)
    manifest = _manifest(package)
    manifest["presentation"]["terminal_oracle_values"] = ["SECRET"]
    _write_manifest(package, manifest)
    report = validate_instrument(package)
    assert not report.valid
    assert "requires terminal_oracle_paths" in _check(report, "IP3")["message"]


def test_ip13_permanent_and_terminal_oracle_scopes_must_not_overlap(tmp_path: Path) -> None:
    """IP13: one oracle declaration cannot be both permanent and terminal."""
    package = _copy_fixture(tmp_path)
    manifest = _manifest(package)
    manifest["presentation"]["oracle_paths"] = {"Alpha": ["/answer"]}
    manifest["presentation"]["terminal_oracle_paths"] = {"Alpha": ["/answer"]}
    _write_manifest(package, manifest)
    report = validate_instrument(package)
    assert not report.valid
    assert "oracle paths must not overlap" in _check(report, "IP3")["message"]
