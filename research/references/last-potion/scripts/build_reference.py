#!/usr/bin/env python3
"""Build the Last Potion acceptance projection from canonical AgentDeck artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

REFERENCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-root",
        required=True,
        help="analysis_* directory produced by the current Agentic Edge reproducer",
    )
    parser.add_argument("--output", required=True, help="new output directory")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from agentdeck import (  # pylint: disable=import-outside-toplevel
        EvidenceCitation,
        FindingAuthor,
        FindingDeclaration,
        load_evidence,
        prepare_finding,
        render_finding_markdown,
    )

    probe = load_probe(REFERENCE_ROOT / "probe.yaml")
    source_verification = verify_pinned_sources(probe)
    analysis_root = Path(args.analysis_root).expanduser().resolve()
    evidence_path = analysis_root / probe["pattern"]["evidence_file"]
    evidence = load_evidence(evidence_path)
    verify_evidence_binding(evidence, probe, source_verification)
    result = select_result(evidence, probe["pattern"])
    verify_expected_result(result.as_dict(), probe["pattern"]["expected"])

    citation = EvidenceCitation("supports", evidence.evidence_sha256, result.result_sha256)
    finding_config = probe["finding"]
    author_config = finding_config["author"]
    finding = prepare_finding(
        FindingDeclaration(
            finding_config["id"],
            finding_config["claim"],
            FindingAuthor(author_config["name"], author_config["kind"]),
            (citation,),
            tuple(finding_config["limitations"]),
        ),
        (evidence,),
    )

    payload = build_payload(probe, evidence.as_dict(), result.as_dict(), finding.as_dict())
    payload["source_verification"] = source_verification
    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "reference.json", payload)
    (output / "reference.md").write_text(
        render_reference_markdown(payload, render_finding_markdown(finding, (evidence,))),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Reference: {payload['reference']['id']} revision {payload['reference']['revision']}")
    print(f"Probe: sha256:{payload['probe_sha256']}")
    print(f"Moment: {payload['moment']['statement']}")
    print(f"Pattern: {payload['pattern']['statement']}")
    print(f"Output: {output}")
    return 0


def load_probe(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Last Potion probe schema_version must equal 1")
    return payload


def verify_pinned_sources(probe: Mapping[str, Any]) -> dict[str, Any]:
    """Verify frozen sources while retaining current environment identities."""

    from agentdeck import (  # pylint: disable=import-outside-toplevel
        load_measure,
        prepare_game_research_profile,
        prepare_measure,
        prepare_study,
    )
    from scripts.reference_sources import verify_sources

    study_root = resolve_reference_path(probe["study"]["path"])
    study = prepare_study(study_root)
    _equal("Study id", study.definition.id, probe["study"]["id"])
    _equal("Study plan", study.plan_sha256, probe["study"]["plan_sha256"])

    profiles = {
        item["id"]: prepare_game_research_profile(resolve_reference_path(item["path"]))
        for item in probe["profiles"]
    }
    measures = {
        item["id"]: prepare_measure(load_measure(study_root, item["id"]))
        for item in probe["measures"]
    }
    source_verification = verify_sources(REFERENCE_ROOT / "probe.yaml", profiles, measures)

    runs: dict[str, Mapping[str, Any]] = {}
    for group in study.execution_groups:
        for run in group.prepared_assembly.assembly["runs"]:
            runs[run["name"]] = run
    for item in probe["games"]:
        game = runs[item["assembly_run"]]["game"]["version"]
        _equal(f"Game family {item['id']}", game["family_id"], item["family_id"])
        _equal(
            f"Game implementation {item['id']}",
            game["implementation_sha256"],
            item["implementation_sha256"],
        )

    record_path = resolve_reference_path(probe["canonical_run"]["record"])
    _equal(
        "Canonical Record",
        hashlib.sha256(record_path.read_bytes()).hexdigest(),
        probe["canonical_run"]["record_sha256"],
    )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    _equal("Canonical Match", record["match_id"], probe["canonical_run"]["match_id"])
    event = record["events"][probe["moment"]["event_index"]]
    data = event["data"]
    for label, observed in (
        ("turn", data["state_before"]["turn"]),
        ("player", data["player"]),
        ("action", data["action"]),
    ):
        _equal(f"Moment {label}", observed, probe["moment"][label])

    for key in ("viewer", "renderer"):
        path = resolve_reference_path(probe["stage"][key])
        if not path.is_file():
            raise ValueError(f"Stage {key} is missing: {path}")
    return source_verification


def select_result(evidence: Any, pattern: Mapping[str, Any]) -> Any:
    dimensions = dict(pattern["dimensions"])
    matches = [
        item
        for item in evidence.results
        if item.metric == pattern["metric"] and dict(item.dimensions) == dimensions
    ]
    if evidence.measure_id != pattern["measure_id"] or len(matches) != 1:
        raise ValueError("Last Potion Pattern did not resolve exactly once")
    return matches[0]


def verify_evidence_binding(
    evidence: Any, probe: Mapping[str, Any], source_verification: Mapping[str, Any]
) -> None:
    expected = probe["pattern"]["expected"]["corpus"]
    measure = source_verification["measures"][probe["pattern"]["measure_id"]]
    for label, observed, wanted in (
        ("Evidence Study", evidence.study_id, probe["study"]["id"]),
        ("Evidence plan", evidence.plan_sha256, probe["study"]["plan_sha256"]),
        ("Evidence Measure", evidence.measure_id, probe["pattern"]["measure_id"]),
        (
            "Evidence Measure identity",
            evidence.measure_sha256,
            measure["measure_sha256"],
        ),
        (
            "Evidence material environment",
            evidence.material_environment_sha256,
            measure["material_environment_sha256"],
        ),
        ("Evidence origin", evidence.corpus_origin_kind, expected["origin_kind"]),
        ("Evidence Record count", evidence.record_count, expected["record_count"]),
        (
            "Evidence expected Record count",
            evidence.expected_record_count,
            expected["expected_record_count"],
        ),
        ("Evidence completeness", evidence.corpus_complete, expected["complete"]),
    ):
        _equal(label, observed, wanted)


def verify_expected_result(result: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    for field in ("value", "unit", "support"):
        _equal(f"Pattern {field}", result[field], expected[field])


def build_payload(
    probe: Mapping[str, Any],
    evidence: Mapping[str, Any],
    result: Mapping[str, Any],
    finding: Mapping[str, Any],
) -> dict[str, Any]:
    record_path = resolve_reference_path(probe["canonical_run"]["record"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    event = record["events"][probe["moment"]["event_index"]]
    data = event["data"]
    probe_sha256 = sha256_json(probe)
    return {
        "schema_version": 1,
        "reference": dict(probe["reference"]),
        "probe_sha256": probe_sha256,
        "probe_revision": {
            "games": list(probe["games"]),
            "profiles": list(probe["profiles"]),
            "study": dict(probe["study"]),
            "measures": list(probe["measures"]),
        },
        "stage": {
            "viewer": probe["stage"]["viewer"],
            "renderer": probe["stage"]["renderer"],
            "record": probe["canonical_run"]["record"],
            "sidecar": probe["canonical_run"]["sidecar"],
        },
        "moment": {
            "epistemic_status": "one_run",
            "label": "ONE RUN · N=1",
            "statement": probe["moment"]["statement"],
            "match_id": record["match_id"],
            "record_sha256": probe["canonical_run"]["record_sha256"],
            "source": {
                "event_index": probe["moment"]["event_index"],
                "action_pointer": f"/events/{probe['moment']['event_index']}/data/action",
                "state_before_pointer": (
                    f"/events/{probe['moment']['event_index']}/data/state_before"
                ),
            },
            "observation": {
                "turn": data["state_before"]["turn"],
                "player": data["player"],
                "action": data["action"],
                "health_before": data["state_before"]["health"][data["player"]],
                "health_after": data["state_after"]["health"][data["player"]],
                "potions_before": data["state_before"]["potions"][data["player"]],
                "potions_after": data["state_after"]["potions"][data["player"]],
            },
        },
        "pattern": {
            "epistemic_status": "derived_pattern",
            "label": "48 RUNS · 189 CRITICAL-STATE TURNS · DERIVED PATTERN",
            "statement": probe["pattern"]["statement"],
            "evidence_sha256": evidence["evidence_sha256"],
            "result_sha256": result["result_sha256"],
            "metric": result["metric"],
            "dimensions": result["dimensions"],
            "value": result["value"],
            "unit": result["unit"],
            "support": result["support"],
            "corpus": evidence["corpus"],
        },
        "finding": finding,
        "frozen_source": dict(probe["frozen_source"]),
    }


def render_reference_markdown(payload: Mapping[str, Any], finding_markdown: str) -> str:
    moment = payload["moment"]
    pattern = payload["pattern"]
    observation = moment["observation"]
    return "\n".join(
        [
            f"# {payload['reference']['title']}",
            "",
            payload["reference"]["summary"],
            "",
            "## Moment",
            "",
            f"**{moment['label']}**",
            "",
            moment["statement"],
            "",
            (
                f"Turn {observation['turn']}: `{observation['player']}` chose "
                f"`{observation['action']}` at {observation['health_before']} HP with "
                f"{observation['potions_before']} potion remaining."
            ),
            "",
            f"Record: `sha256:{moment['record_sha256']}` · Match: `{moment['match_id']}`",
            "",
            "## Pattern",
            "",
            f"**{pattern['label']}**",
            "",
            pattern["statement"],
            "",
            (
                f"Evidence: `sha256:{pattern['evidence_sha256']}` · "
                f"Result: `sha256:{pattern['result_sha256']}`"
            ),
            "",
            finding_markdown.rstrip(),
            "",
            "## Reference boundary",
            "",
            "The Moment is one exact recorded occurrence. The Pattern is a deterministic "
            "projection of one EvidenceResult over an identified corpus. The Finding remains "
            "authored interpretation. The frozen Hugging Face source was read without mutation.",
            "",
        ]
    )


def resolve_reference_path(value: str) -> Path:
    path = (REFERENCE_ROOT / value).resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"Reference path escapes the repository: {value}") from exc
    return path


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _equal(label: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        raise ValueError(f"{label} changed: expected {expected!r}, observed {observed!r}")


if __name__ == "__main__":
    raise SystemExit(main())
