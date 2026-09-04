"""AgentDeck command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from contextlib import redirect_stdout
from contextvars import ContextVar
from typing import Any, TextIO

from .research import (
    PreparedStudy,
    StudyDiagnostic,
    StudyExecutionError,
    StudyValidationError,
    analyze_study,
    execute_prepared_study,
    load_evidence,
    load_finding,
    load_study_execution,
    prepare_study,
    select_study,
    write_finding_report,
)

_NO_CALL_ASSURANCE = "AgentDeck constructed no Players and invoked no providers."
_TRUSTED_SOURCE_WARNING = "Assembly preparation executed trusted authored Python."
_JSON_OUTPUT: ContextVar[TextIO | None] = ContextVar("agentdeck_cli_json_output", default=None)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the AgentDeck CLI and return a stable process exit code."""

    parser = _parser()
    args = parser.parse_args(argv)
    if args.json:
        token = _JSON_OUTPUT.set(sys.stdout)
        try:
            # Includes trusted preparation prints and default worker monitors.
            # The final envelope alone writes to the caller's original stdout.
            with redirect_stdout(sys.stderr):
                return _execute(args)
        finally:
            _JSON_OUTPUT.reset(token)
    return _execute(args)


def _execute(args: argparse.Namespace) -> int:
    command = f"study.{args.study_command}"
    if args.study_command == "report":
        return _report_finding(args, command)
    try:
        prepared = prepare_study(args.study)
    except StudyValidationError as exc:
        return _render_failure(command, exc, json_mode=args.json)
    except Exception as exc:  # unexpected failures retain a distinct exit code
        diagnostic = StudyDiagnostic(
            code="agentdeck.internal",
            severity="error",
            location="",
            message=str(exc),
        )
        return _render_envelope(
            command=command,
            ok=False,
            study_id=None,
            plan_sha256=None,
            data={},
            diagnostics=[diagnostic.as_dict()],
            json_mode=args.json,
            exit_code=1,
        )

    if args.study_command == "run":
        return _run_study(args, prepared, command)
    if args.study_command == "analyze":
        return _analyze_study(args, prepared, command)

    data = _summary(prepared)
    return _render_envelope(
        command=command,
        ok=True,
        study_id=prepared.definition.id,
        plan_sha256=prepared.plan_sha256,
        data=data,
        diagnostics=[],
        json_mode=args.json,
        exit_code=0,
        prepared=prepared,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentdeck")
    commands = parser.add_subparsers(dest="command", required=True)
    study = commands.add_parser(
        "study",
        help="inspect, execute, analyze, and report behavioral Studies",
    )
    study_commands = study.add_subparsers(dest="study_command", required=True)
    for name, help_text in (
        ("inspect", "inspect a complete content-addressed Study plan"),
        ("validate", "validate a Study before execution"),
    ):
        command = study_commands.add_parser(name, help=help_text)
        command.add_argument("study", help="Study package directory or study.yaml")
        command.add_argument("--json", action="store_true", help="emit one JSON document")
    run = study_commands.add_parser("run", help="execute an explicitly approved Study scope")
    run.add_argument("study", help="Study package directory or study.yaml")
    selectors = run.add_mutually_exclusive_group(required=True)
    selectors.add_argument("--phase", action="append", default=[], help="select one Phase id")
    selectors.add_argument("--group", action="append", default=[], help="select one group id")
    selectors.add_argument("--all", action="store_true", help="select every ExecutionGroup")
    run.add_argument("--approve", required=True, help="full PreparedStudy plan SHA-256")
    run.add_argument("--output-root", required=True, help="host execution output root")
    run.add_argument("--json", action="store_true", help="emit one JSON document")
    analyze = study_commands.add_parser(
        "analyze", help="derive Evidence from an explicit corpus and Measure selection"
    )
    analyze.add_argument("study", help="Study package directory or study.yaml")
    analyze.add_argument("--cell", action="append", required=True, help="select one Cell id")
    analyze.add_argument("--measure", action="append", required=True, help="select one Measure id")
    corpus = analyze.add_mutually_exclusive_group(required=True)
    corpus.add_argument(
        "--execution", action="append", default=[], help="Study execution receipt path"
    )
    corpus.add_argument("--import-manifest", help="pinned imported Record manifest")
    analyze.add_argument("--output-root", required=True, help="host analysis output root")
    analyze.add_argument(
        "--assumption", action="append", default=[], help="authored analysis assumption"
    )
    analyze.add_argument("--json", action="store_true", help="emit one JSON document")
    report = study_commands.add_parser(
        "report", help="render one authored Finding with exact Evidence citations"
    )
    report.add_argument("findings", help="Finding manifest or package directory")
    report.add_argument("--finding", required=True, help="authored Finding id")
    report.add_argument(
        "--evidence", action="append", required=True, help="canonical Evidence artifact"
    )
    report.add_argument("--output", required=True, help="new report output directory")
    report.add_argument("--json", action="store_true", help="emit one JSON document")
    return parser


def _run_study(args: argparse.Namespace, prepared: PreparedStudy, command: str) -> int:
    if args.approve != prepared.plan_sha256:
        diagnostic = StudyDiagnostic(
            code="study.approval_mismatch",
            severity="error",
            location="--approve",
            message=(f"expected full plan {prepared.plan_sha256}; received {args.approve}"),
        )
        return _render_envelope(
            command=command,
            ok=False,
            study_id=prepared.definition.id,
            plan_sha256=prepared.plan_sha256,
            data={},
            diagnostics=[diagnostic.as_dict()],
            json_mode=args.json,
            exit_code=3,
        )
    try:
        selection = select_study(
            prepared,
            phase_ids=args.phase,
            execution_group_ids=args.group,
            all_groups=args.all,
        )
    except ValueError as exc:
        diagnostic = StudyDiagnostic(
            code="study.selection",
            severity="error",
            location="selection",
            message=str(exc),
        )
        return _render_envelope(
            command=command,
            ok=False,
            study_id=prepared.definition.id,
            plan_sha256=prepared.plan_sha256,
            data={},
            diagnostics=[diagnostic.as_dict()],
            json_mode=args.json,
            exit_code=3,
        )
    try:
        execution = execute_prepared_study(
            args.study,
            prepared,
            selection,
            output_root=args.output_root,
        )
    except StudyExecutionError as exc:
        diagnostic = StudyDiagnostic(
            code="study.execution",
            severity="error",
            location="execution",
            message=str(exc),
        )
        data: dict[str, Any] = {}
        if exc.execution is not None:
            data["execution"] = exc.execution.as_dict()
        if exc.receipt_path is not None:
            data["receipt_path"] = exc.receipt_path.name
            data["output_root"] = str(exc.receipt_path.parent)
        return _render_envelope(
            command=command,
            ok=False,
            study_id=prepared.definition.id,
            plan_sha256=prepared.plan_sha256,
            data=data,
            diagnostics=[diagnostic.as_dict()],
            json_mode=args.json,
            exit_code=5,
        )
    except (OSError, FileExistsError) as exc:
        diagnostic = StudyDiagnostic(
            code="study.output",
            severity="error",
            location="--output-root",
            message=str(exc),
        )
        return _render_envelope(
            command=command,
            ok=False,
            study_id=prepared.definition.id,
            plan_sha256=prepared.plan_sha256,
            data={},
            diagnostics=[diagnostic.as_dict()],
            json_mode=args.json,
            exit_code=4,
        )

    data = {
        "execution": execution.as_dict(),
        "receipt_path": execution.receipt_path.name,
        "output_root": str(execution.execution_root),
    }
    if args.json:
        return _render_envelope(
            command=command,
            ok=True,
            study_id=prepared.definition.id,
            plan_sha256=prepared.plan_sha256,
            data=data,
            diagnostics=[],
            json_mode=True,
            exit_code=0,
        )
    print(f"Study: {prepared.definition.title} ({prepared.definition.id})")
    print(f"Question / intent: {prepared.definition.question} [{prepared.definition.intent}]")
    print(f"Plan identity: {prepared.plan_sha256}")
    print(f"Selected scope: {', '.join(selection.execution_group_ids)}")
    print(f"Total Matches: {len(execution.records)}")
    print(f"Output location: {execution.execution_root}")
    print(f"Status / diagnostics: complete; receipt={execution.receipt_path}")
    return 0


def _analyze_study(args: argparse.Namespace, prepared: PreparedStudy, command: str) -> int:
    try:
        executions = tuple(load_study_execution(path) for path in args.execution)
        analysis = analyze_study(
            args.study,
            cell_ids=args.cell,
            measure_ids=args.measure,
            output_root=args.output_root,
            study_executions=executions,
            imported_manifest=args.import_manifest,
            assumptions=args.assumption,
        )
    except Exception as exc:
        diagnostic = StudyDiagnostic(
            code="study.analysis",
            severity="error",
            location="analysis",
            message=str(exc),
        )
        return _render_envelope(
            command=command,
            ok=False,
            study_id=prepared.definition.id,
            plan_sha256=prepared.plan_sha256,
            data={},
            diagnostics=[diagnostic.as_dict()],
            json_mode=args.json,
            exit_code=6,
        )
    data = {
        "analysis": analysis.as_dict(),
        "receipt_path": analysis.receipt_path.name,
        "output_root": str(analysis.analysis_root),
    }
    if args.json:
        return _render_envelope(
            command=command,
            ok=True,
            study_id=prepared.definition.id,
            plan_sha256=prepared.plan_sha256,
            data=data,
            diagnostics=[],
            json_mode=True,
            exit_code=0,
        )
    print(f"Study: {prepared.definition.title} ({prepared.definition.id})")
    print(f"Question / intent: {prepared.definition.question} [{prepared.definition.intent}]")
    print(f"Plan identity: {prepared.plan_sha256}")
    print(f"Cells: {', '.join(analysis.cell_ids)}")
    print(f"Corpus: {analysis.corpus_sha256} ({analysis.corpus_origin_kind})")
    print(f"Measures: {', '.join(measure.id for measure in analysis.measures)}")
    print(f"Evidence: {', '.join(item.evidence_sha256 for item in analysis.evidence)}")
    print(f"Output location: {analysis.analysis_root}")
    print(f"Status / diagnostics: complete; receipt={analysis.receipt_path}")
    return 0


def _report_finding(args: argparse.Namespace, command: str) -> int:
    try:
        declaration = load_finding(args.findings, args.finding)
        evidence = tuple(load_evidence(path) for path in args.evidence)
        finding, finding_path, report_path = write_finding_report(
            declaration,
            evidence,
            output=args.output,
        )
    except Exception as exc:
        diagnostic = StudyDiagnostic(
            code="study.report",
            severity="error",
            location="report",
            message=str(exc),
        )
        return _render_envelope(
            command=command,
            ok=False,
            study_id=None,
            plan_sha256=None,
            data={},
            diagnostics=[diagnostic.as_dict()],
            json_mode=args.json,
            exit_code=6,
        )
    data = {
        "finding": finding.as_dict(),
        "finding_path": finding_path.name,
        "report_path": report_path.name,
        "output_root": str(finding_path.parent),
    }
    if args.json:
        return _render_envelope(
            command=command,
            ok=True,
            study_id=None,
            plan_sha256=None,
            data=data,
            diagnostics=[],
            json_mode=True,
            exit_code=0,
        )
    print(f"Finding: {finding.declaration.id}")
    print(f"Claim: {finding.declaration.claim}")
    print(f"Finding identity: {finding.finding_sha256}")
    print(f"Evidence citations: {len(finding.declaration.citations)}")
    print(f"Output location: {finding_path.parent}")
    print("Status / diagnostics: citations resolved; interpretation remains authored")
    return 0


def _summary(prepared: PreparedStudy) -> dict[str, Any]:
    definition = prepared.definition
    phase_groups = {
        phase.id: [group.id for group in definition.execution_groups if group.phase == phase.id]
        for phase in definition.phases
    }
    groups = []
    for group in prepared.execution_groups:
        runs = []
        for run in group.prepared_assembly.assembly["runs"]:
            runs.append(
                {
                    "name": run["name"],
                    "matches": run["matches"],
                    "players": [player["kwargs"]["name"] for player in run["players"]],
                }
            )
        groups.append(
            {
                "id": group.id,
                "phase": group.phase,
                "entrypoint": group.entrypoint,
                "assembly_plan_sha256": group.prepared_assembly.plan_sha256,
                "assembly_runs": runs,
                "total_matches": group.prepared_assembly.total_matches,
            }
        )
    return {
        "study": {
            "id": definition.id,
            "title": definition.title,
            "question": definition.question,
            "intent": definition.intent,
            "hypotheses": [item.as_dict() for item in definition.hypotheses],
            "lineage": definition.lineage.as_dict() if definition.lineage else None,
        },
        "definition_sha256": prepared.definition_sha256,
        "research_contract_version": prepared.research_contract_version,
        "phases": [
            {**phase.as_dict(), "execution_groups": phase_groups[phase.id]}
            for phase in definition.phases
        ],
        "execution_groups": groups,
        "conditions": [item.as_dict() for item in definition.conditions],
        "cells": [item.as_dict() for item in definition.cells],
        "total_matches": prepared.total_matches,
        "provider_requirements": [dict(item) for item in prepared.provider_requirements],
        "estimated_cost_usd": None,
        "estimated_provider_calls": None,
        "known_limits": [
            "Inspection validates execution structure, identity, and portability; not scientific validity.",
            "Cost and provider-call estimates are unavailable before execution.",
            "Assembly preparation executes trusted authored Python.",
        ],
    }


def _render_failure(command: str, error: StudyValidationError, *, json_mode: bool) -> int:
    return _render_envelope(
        command=command,
        ok=False,
        study_id=error.study_id,
        plan_sha256=None,
        data={},
        diagnostics=[item.as_dict() for item in error.diagnostics],
        json_mode=json_mode,
        exit_code=2,
    )


def _render_envelope(
    *,
    command: str,
    ok: bool,
    study_id: str | None,
    plan_sha256: str | None,
    data: dict[str, Any],
    diagnostics: list[dict[str, str]],
    json_mode: bool,
    exit_code: int,
    prepared: PreparedStudy | None = None,
) -> int:
    if json_mode:
        envelope = {
            "command": command,
            "ok": ok,
            "study_id": study_id,
            "plan_sha256": plan_sha256,
            "data": data,
            "diagnostics": diagnostics,
        }
        output = _JSON_OUTPUT.get() or sys.stdout
        output.write(
            json.dumps(
                envelope,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        return exit_code

    if prepared is not None:
        _render_human(command, prepared, data)
    else:
        for diagnostic in diagnostics:
            location = f"{diagnostic['location']}: " if diagnostic["location"] else ""
            sys.stderr.write(f"{diagnostic['code']}: {location}{diagnostic['message']}\n")
    return exit_code


def _render_human(command: str, prepared: PreparedStudy, data: dict[str, Any]) -> None:
    definition = prepared.definition
    print(f"Study: {definition.title} ({definition.id})")
    print(f"Question / intent: {definition.question} [{definition.intent}]")
    if definition.lineage:
        print(f"Lineage: {definition.lineage.relation} of " f"{definition.lineage.parent}")
    print(f"Plan identity: {prepared.plan_sha256}")
    print("Phases and ExecutionGroups:")
    for phase in data["phases"]:
        groups = ", ".join(phase["execution_groups"]) or "none"
        print(f"  - {phase['id']} ({phase['kind']}): {groups}")
    for group in data["execution_groups"]:
        print(f"  - {group['id']} entrypoint={group['entrypoint']}")
        for run in group["assembly_runs"]:
            players = ", ".join(run["players"])
            print(f"      run={run['name']} matches={run['matches']} players={players}")
    print("Cells and Conditions:")
    for condition in definition.conditions:
        print(f"  - condition {condition.id}: {condition.description}")
    for cell in definition.cells:
        conditions = ", ".join(item.condition for item in cell.assignments) or "none"
        print(
            f"  - {cell.id}: {cell.execution_group}/{cell.assembly_run}; "
            f"conditions={conditions}"
        )
    print(f"Total Matches: {prepared.total_matches}")
    print("Providers / models:")
    if prepared.provider_requirements:
        for requirement in prepared.provider_requirements:
            print(f"  - {requirement['provider']}: {requirement['model']}")
    else:
        print("  - none declared")
    print("Known limits and unknowns:")
    for limit in data["known_limits"]:
        print(f"  - {limit}")
    label = "valid" if command == "study.validate" else "prepared for inspection"
    print(f"Status / diagnostics: {label}; 0 errors")
    print(_NO_CALL_ASSURANCE)
    print(_TRUSTED_SOURCE_WARNING)


if __name__ == "__main__":
    raise SystemExit(main())
