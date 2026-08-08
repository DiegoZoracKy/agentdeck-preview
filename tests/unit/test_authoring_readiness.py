"""Direct checks for SPEC-AUTHORING-READINESS AR1-AR8."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

from agentdeck import MatchRuntime, RandomGenerator, TurnResult, certify_instrument

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "instruments" / "number_duel"
FIXTURE_PACKAGE = FIXTURE / "number_duel"


def test_ar1_external_fixture_uses_only_public_agentdeck_imports() -> None:
    """AR1: canonical external authoring code does not deep-import Core."""
    imported_modules: list[str] = []
    for path in sorted(FIXTURE_PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
            elif isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)

    assert not [name for name in imported_modules if name.startswith("agentdeck.core")]


def test_ar2_ar3_external_fixture_passes_declared_strict_type_boundary() -> None:
    """AR2-AR3: strict-check the complete consumer fixture, not the legacy Core."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--follow-imports=silent",
            str(FIXTURE_PACKAGE),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_ar4_stock_mechanics_do_not_access_private_console() -> None:
    """AR4 and MR8: mechanics rely on the public MatchRuntime gateway."""
    mechanics_root = ROOT / "src" / "agentdeck" / "core" / "mechanics"
    violations = {
        str(path.relative_to(ROOT)): line_number
        for path in sorted(mechanics_root.glob("*.py"))
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "runtime._console" in line
    }
    assert violations == {}
    assert MatchRuntime is not None
    assert TurnResult is not None
    assert RandomGenerator is not None


def test_ar5_ar6_ar7_ci_contains_blocking_audit_commands() -> None:
    """AR5, AR6, AR7: local and hosted CI contain explicit blocking audit gates."""
    local_ci = (ROOT / "scripts" / "ci.sh").read_text(encoding="utf-8")
    hosted_ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for source in (local_ci, hosted_ci):
        assert "pip_audit" in source or "pip-audit" in source
        assert "bandit" in source
        assert "--strict" in source
        assert "--follow-imports=silent" in source
        audit_lines = [line for line in source.splitlines() if "audit" in line or "bandit" in line]
        assert all("|| true" not in line for line in audit_lines)


def test_ar5_runtime_audit_requirements_match_project_dependencies() -> None:
    """AR5: the fast audit input cannot silently drift from runtime dependencies."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10
        import tomli as tomllib  # type: ignore[no-redef]

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = {
        requirement.name.lower(): requirement
        for value in project["project"]["dependencies"]
        for requirement in [Requirement(value)]
    }
    audited = {
        requirement.name.lower(): requirement
        for line in (ROOT / "requirements" / "runtime.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
        for requirement in [Requirement(line.strip())]
    }
    assert audited.keys() == declared.keys()
    for name, audit_requirement in audited.items():
        pins = [
            specifier.version
            for specifier in audit_requirement.specifier
            if specifier.operator == "=="
        ]
        assert len(pins) == 1, f"{name} must have one exact reviewed audit pin"
        assert Version(pins[0]) in declared[name].specifier


def test_ar8_external_fixture_uses_the_public_certifier(tmp_path: Path) -> None:
    """AR8: authoring readiness is awarded by the production certifier."""
    report = certify_instrument(
        FIXTURE,
        trust_mode="trusted-local",
        output_dir=tmp_path / "certification",
    )
    assert report.valid
    assert report.awarded_tiers == ["runnable", "evidence_ready", "presentable"]
