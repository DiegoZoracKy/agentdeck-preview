#!/usr/bin/env python3
"""Execute and reproduce the complete Hidden Signal acceptance reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

REFERENCE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="new external output directory")
    args = parser.parse_args(argv)

    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "src"))

    from agentdeck import (  # pylint: disable=import-outside-toplevel
        EvidenceCitation,
        FindingAuthor,
        FindingDeclaration,
        analyze_study,
        execute_prepared_study,
        load_measure,
        prepare_finding,
        prepare_game_research_profile,
        prepare_measure,
        prepare_study,
        render_finding_markdown,
        select_study,
    )
    from scripts.match_surface_export import export_record

    probe = _load_probe(REFERENCE_ROOT / "probe-v3.yaml")
    study_root = _reference_path(probe["study"]["path"])
    study = prepare_study(study_root)
    profile = prepare_game_research_profile(_reference_path(probe["profile"]["path"]))
    measure = prepare_measure(
        load_measure(_reference_path(probe["measure"]["path"]), probe["measure"]["id"])
    )
    source_verification = _verify_probe(probe, study, profile, measure)
    execution = execute_prepared_study(
        study_root,
        study,
        select_study(study, all_groups=True),
        output_root=output / "runs",
    )
    if not execution.complete or len(execution.records) != 40:
        raise ValueError("Hidden Signal execution did not produce 40 complete Records")

    analysis = analyze_study(
        study_root,
        cell_ids=("hidden-condition", "visible-condition"),
        measure_ids=("hidden-signal-inspection",),
        output_root=output / "analysis",
        study_executions=(execution,),
    )
    evidence = analysis.evidence[0]
    hidden = _result(evidence, "inspection-before-commit-rate", "hidden-condition")
    visible = _result(evidence, "inspection-before-commit-rate", "visible-condition")
    _equal(
        "hidden inspection rate",
        hidden.value,
        probe["pattern"]["expected"]["hidden-condition"],
    )
    _equal(
        "visible inspection rate",
        visible.value,
        probe["pattern"]["expected"]["visible-condition"],
    )

    finding = prepare_finding(
        FindingDeclaration(
            "hidden-signal-visibility-policy",
            (
                "Under the two declared Hidden Signal configurations, the calibration "
                "policy inspected before every hidden-signal commitment and made no "
                "inspection when the signal was already visible."
            ),
            FindingAuthor("AgentDeck acceptance reference", "ai_assisted"),
            (
                EvidenceCitation("supports", evidence.evidence_sha256, hidden.result_sha256),
                EvidenceCitation("supports", evidence.evidence_sha256, visible.result_sha256),
            ),
            (
                "The Player is a deterministic authored calibration policy, not an LLM.",
                "Inspection is a Game action and does not establish a general latent construct.",
                "The Finding is scoped to the exact prepared Game configurations and corpus.",
            ),
        ),
        (evidence,),
    )

    hidden_receipts = [item for item in execution.records if item.cell_id == "hidden-condition"]
    if len(hidden_receipts) != 20:
        raise ValueError("Hidden Signal canonical Cell did not resolve exactly 20 Records")
    canonical = sorted(hidden_receipts, key=lambda item: item.match_index)[0]
    record = json.loads(canonical.path.read_text(encoding="utf-8"))
    moment = _moment(record, canonical.record_sha256)

    stage_root = output / "stage"
    stage_root.mkdir()
    copied_record = stage_root / "record.json"
    shutil.copy2(canonical.path, copied_record)
    surface_path = export_record(copied_record, stage_root / "surfaces")
    stage_manifest = {
        "schema_version": 1,
        "epistemic_status": "one_run",
        "label": "ONE RUN · N=1",
        "record": "record.json",
        "record_sha256": canonical.record_sha256,
        "match_surface": f"surfaces/{surface_path.name}",
        "match_surface_sha256": _sha256_file(surface_path),
        "moment": moment,
    }
    _write_json(stage_root / "manifest.json", stage_manifest)

    measure = analysis.measures[0]
    reference = {
        "schema_version": 1,
        "reference": dict(probe["reference"]),
        "probe_sha256": _sha256_json(probe),
        "source_verification": source_verification,
        "probe_revision": {
            "revision": probe["reference"]["revision"],
            "study_id": study.definition.id,
            "execution_plan_sha256": study.plan_sha256,
            "game_research_profile_sha256": profile.profile_sha256,
            "measure_id": measure.id,
            "measure_sha256": measure.measure_sha256,
        },
        "execution": {
            "execution_sha256": execution.execution_sha256,
            "record_count": len(execution.records),
            "origin_kind": evidence.corpus_origin_kind,
        },
        "moment": moment,
        "pattern": {
            "epistemic_status": "derived_pattern",
            "label": "40 RUNS · DERIVED PATTERN",
            "statement": (
                "Inspection-before-commit rate was 100% in the hidden condition and "
                "0% in the visible condition across 20 Runs per condition."
            ),
            "evidence_sha256": evidence.evidence_sha256,
            "corpus_sha256": evidence.corpus_sha256,
            "record_count": evidence.record_count,
            "results": [hidden.as_dict(), visible.as_dict()],
        },
        "finding": finding.as_dict(),
        "stage": stage_manifest,
    }
    _write_json(output / "reference.json", reference)
    (output / "finding.md").write_text(
        render_finding_markdown(finding, (evidence,)), encoding="utf-8", newline="\n"
    )
    (output / "reference.md").write_text(
        _render_reference(reference), encoding="utf-8", newline="\n"
    )

    print(f"Study: {study.definition.id}")
    print(f"Execution: sha256:{execution.execution_sha256} ({len(execution.records)} Records)")
    print(f"Evidence: sha256:{evidence.evidence_sha256}")
    print(f"Finding: sha256:{finding.finding_sha256}")
    print(f"Output: {output}")
    return 0


def _load_probe(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Hidden Signal probe schema_version must equal 1")
    return payload


def _reference_path(relative: str) -> Path:
    path = (REFERENCE_ROOT / relative).resolve()
    if not path.is_relative_to(REPO_ROOT):
        raise ValueError(f"Probe path escapes repository: {relative}")
    return path


def _verify_probe(
    probe: Mapping[str, Any], study: Any, profile: Any, measure: Any
) -> dict[str, Any]:
    from scripts.reference_sources import verify_sources

    _equal("Study id", study.definition.id, probe["study"]["id"])
    _equal("Study plan", study.plan_sha256, probe["study"]["plan_sha256"])
    _equal("Profile id", profile.profile.id, probe["profile"]["id"])
    _equal("Measure id", measure.id, probe["measure"]["id"])
    source_verification = verify_sources(
        REFERENCE_ROOT / "probe-v3.yaml",
        {profile.profile.id: profile},
        {measure.id: measure},
    )

    runs = {
        run["name"]: run
        for group in study.execution_groups
        for run in group.prepared_assembly.assembly["runs"]
    }
    run = runs[probe["game"]["assembly_run"]]
    version = run["game"]["version"]
    _equal("Game family", version["family_id"], probe["game"]["family_id"])
    _equal(
        "Game implementation",
        version["implementation_sha256"],
        probe["game"]["implementation_sha256"],
    )

    canonical = probe["canonical_run"]
    record_path = _reference_path(canonical["record"])
    surface_path = _reference_path(canonical["match_surface"])
    _equal("Canonical Record", _sha256_file(record_path), canonical["record_sha256"])
    _equal(
        "Canonical Match Surface",
        _sha256_file(surface_path),
        canonical["match_surface_sha256"],
    )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    _equal("Canonical Match", record["match_id"], canonical["match_id"])
    event = record["events"][probe["moment"]["event_index"]]
    _equal("Canonical Moment", _action_value(event["data"]["action"]), probe["moment"]["action"])

    for relative in probe["stage"].values():
        if not _reference_path(relative).is_file():
            raise ValueError(f"Pinned Stage asset is missing: {relative}")
    return source_verification


def _result(evidence: Any, metric: str, cell: str) -> Any:
    matches = [
        item
        for item in evidence.results
        if item.metric == metric and dict(item.dimensions) == {"cell": cell}
    ]
    if len(matches) != 1 or matches[0].status != "available":
        raise ValueError(f"Evidence result did not resolve: {metric}/{cell}")
    return matches[0]


def _moment(record: Mapping[str, Any], record_sha256: str) -> dict[str, Any]:
    events = record.get("events") or []
    matches = [
        (index, event)
        for index, event in enumerate(events)
        if event.get("type") == "gameplay"
        and _action_value((event.get("data") or {}).get("action")) == "INSPECT"
    ]
    if len(matches) != 1:
        raise ValueError("Canonical Hidden Signal Record does not contain one INSPECT event")
    event_index, event = matches[0]
    data = event["data"]
    return {
        "epistemic_status": "one_run",
        "label": "ONE RUN · N=1",
        "statement": "SignalPolicy inspected the concealed signal before committing in this Run.",
        "match_id": record["match_id"],
        "record_sha256": record_sha256,
        "source": {
            "event_index": event_index,
            "action_pointer": f"/events/{event_index}/data/action/value",
            "state_before_pointer": f"/events/{event_index}/data/state_before",
            "state_after_pointer": f"/events/{event_index}/data/state_after",
        },
        "observation": {
            "player": data["player"],
            "action": "INSPECT",
            "turn": data["state_before"]["turn"],
            "signal_before": "HIDDEN",
            "signal_after": data["state_after"]["revealed_signal"],
            "inspection_cost": data["state_after"]["inspection_cost_total"],
        },
    }


def _action_value(action: Any) -> str:
    value = action.get("value") if isinstance(action, Mapping) else action
    return str(value).upper()


def _render_reference(reference: Mapping[str, Any]) -> str:
    moment = reference["moment"]
    pattern = reference["pattern"]
    finding = reference["finding"]["finding"]
    return "\n".join(
        (
            "# Hidden Signal",
            "",
            reference["reference"]["summary"],
            "",
            "## Moment",
            "",
            f"**{moment['label']}**",
            "",
            moment["statement"],
            "",
            f"Record: `sha256:{moment['record_sha256']}` · Match: `{moment['match_id']}`",
            "",
            "## Pattern",
            "",
            f"**{pattern['label']}**",
            "",
            pattern["statement"],
            "",
            f"Evidence: `sha256:{pattern['evidence_sha256']}`",
            "",
            "## Finding",
            "",
            finding["claim"],
            "",
            "Authored interpretation; exact Evidence citations and limitations are in finding.md.",
            "",
        )
    )


def _equal(label: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        raise ValueError(f"{label} changed: expected {expected!r}, observed {observed!r}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_json(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    raise SystemExit(main())
