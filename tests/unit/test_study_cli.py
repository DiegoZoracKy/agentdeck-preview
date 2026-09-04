import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from test_study import study_payload, write_study
from test_research_derivation import _write_research_files


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "agentdeck.cli", *args],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_root_help_describes_the_complete_study_journey():
    result = run_cli("--help")

    assert result.returncode == 0
    assert "inspect, execute, analyze, and report behavioral Studies" in result.stdout


def test_inspect_human_output_has_contract_order_and_assurances(tmp_path):
    manifest = write_study(tmp_path / "study")

    result = run_cli("study", "inspect", str(manifest))

    assert result.returncode == 0
    assert result.stderr == ""
    labels = [
        "Study:",
        "Question / intent:",
        "Plan identity:",
        "Phases and ExecutionGroups:",
        "Cells and Conditions:",
        "Total Matches:",
        "Providers / models:",
        "Known limits and unknowns:",
        "Status / diagnostics:",
        "AgentDeck constructed no Players and invoked no providers.",
        "Assembly preparation executed trusted authored Python.",
    ]
    positions = [result.stdout.index(label) for label in labels]
    assert positions == sorted(positions)
    assert "Evidence" not in result.stdout
    assert "Finding" not in result.stdout


def test_validate_json_is_one_portable_stable_document_after_relocation(tmp_path):
    first_root = tmp_path / "first"
    manifest = write_study(first_root)
    second_root = tmp_path / "second"
    import shutil

    shutil.copytree(first_root, second_root)

    first = run_cli("study", "validate", str(manifest), "--json")
    second = run_cli("study", "validate", str(second_root), "--json")

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert payload["command"] == "study.validate"
    assert payload["ok"] is True
    assert len(payload["plan_sha256"]) == 64
    assert payload["diagnostics"] == []
    assert payload["data"]["estimated_cost_usd"] is None
    assert payload["data"]["estimated_provider_calls"] is None
    assert str(first_root) not in first.stdout
    assert str(second_root) not in first.stdout


def test_validate_json_reports_multiple_diagnostics_and_exit_two(tmp_path):
    payload = study_payload()
    payload["study"]["model"] = "duplicate-authority"
    payload["execution_groups"][0]["phase"] = "unknown"
    manifest = write_study(tmp_path / "study", payload=payload)

    result = run_cli("study", "validate", str(manifest), "--json")

    assert result.returncode == 2
    assert result.stderr == ""
    document = json.loads(result.stdout)
    assert document["ok"] is False
    assert document["plan_sha256"] is None
    assert len(document["diagnostics"]) >= 2


def test_validate_human_errors_are_only_on_stderr(tmp_path):
    payload = study_payload()
    payload["schema_version"] = 99
    manifest = write_study(tmp_path / "study", payload=payload)

    result = run_cli("study", "validate", str(manifest))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "study.schema_version" in result.stderr


def test_cli_json_changes_when_study_authority_changes(tmp_path):
    root = tmp_path / "study"
    manifest = write_study(root)
    initial = run_cli("study", "inspect", str(manifest), "--json")

    payload = study_payload()
    payload["study"]["question"] = "A different behavioral question?"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    changed = run_cli("study", "inspect", str(manifest), "--json")

    assert initial.returncode == changed.returncode == 0
    assert json.loads(initial.stdout)["plan_sha256"] != json.loads(changed.stdout)["plan_sha256"]


def test_packaging_declares_one_agentdeck_entrypoint_and_includes_research():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["scripts"] == {"agentdeck": "agentdeck.cli:main"}
    assert "agentdeck.research*" not in project["tool"]["setuptools"]["packages"]["find"]["exclude"]


def test_run_requires_exact_approval_and_emits_exact_receipt(tmp_path):
    manifest = write_study(tmp_path / "study")
    inspected = run_cli("study", "inspect", str(manifest), "--json")
    plan = json.loads(inspected.stdout)["plan_sha256"]

    stale = run_cli(
        "study",
        "run",
        str(manifest),
        "--all",
        "--approve",
        "0" * 64,
        "--output-root",
        str(tmp_path / "runs"),
        "--json",
    )
    assert stale.returncode == 3
    assert json.loads(stale.stdout)["diagnostics"][0]["code"] == "study.approval_mismatch"

    result = run_cli(
        "study",
        "run",
        str(manifest),
        "--all",
        "--approve",
        plan,
        "--output-root",
        str(tmp_path / "runs"),
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    execution = payload["data"]["execution"]
    assert execution["complete"] is True
    assert execution["record_count"] == 4
    assert execution["groups"][0]["runs"][0]["records"][0]["match_index"] == 0
    assert payload["data"]["receipt_path"] == "execution.json"
    assert (Path(payload["data"]["output_root"]) / payload["data"]["receipt_path"]).is_file()


def test_analyze_and_report_close_explicit_cli_journey(tmp_path):
    root = tmp_path / "study"
    manifest = write_study(root)
    _write_research_files(root)
    inspected = run_cli("study", "inspect", str(manifest), "--json")
    plan = json.loads(inspected.stdout)["plan_sha256"]
    executed = run_cli(
        "study",
        "run",
        str(manifest),
        "--all",
        "--approve",
        plan,
        "--output-root",
        str(tmp_path / "runs"),
        "--json",
    )
    execution_data = json.loads(executed.stdout)["data"]
    receipt = str(Path(execution_data["output_root"]) / execution_data["receipt_path"])

    analyzed = run_cli(
        "study",
        "analyze",
        str(manifest),
        "--cell",
        "partial",
        "--cell",
        "full",
        "--measure",
        "observe-rate",
        "--execution",
        receipt,
        "--output-root",
        str(tmp_path / "analysis"),
        "--json",
    )

    assert analyzed.returncode == 0, analyzed.stderr
    analysis = json.loads(analyzed.stdout)["data"]
    analysis_root = Path(analysis["output_root"])
    evidence_path = analysis_root / "evidence" / "observe-rate.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    result = evidence["results"][0]
    (root / "findings.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "findings": [
                    {
                        "id": "observe-policy-executed",
                        "claim": "The fixture selected OBSERVE.",
                        "author": {"name": "Fixture author", "kind": "human"},
                        "citations": [
                            {
                                "relation": "supports",
                                "evidence": f"sha256:{evidence['evidence_sha256']}",
                                "result": f"sha256:{result['result_sha256']}",
                            }
                        ],
                        "limitations": ["This is a fixture, not a model claim."],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    reported = run_cli(
        "study",
        "report",
        str(root),
        "--finding",
        "observe-policy-executed",
        "--evidence",
        str(evidence_path),
        "--output",
        str(tmp_path / "report"),
        "--json",
    )

    assert reported.returncode == 0, reported.stderr
    report = json.loads(reported.stdout)["data"]
    assert (Path(report["output_root"]) / report["finding_path"]).is_file()
    assert (Path(report["output_root"]) / report["report_path"]).is_file()
    assert "authored interpretation" in (
        Path(report["output_root"]) / report["report_path"]
    ).read_text(encoding="utf-8")
