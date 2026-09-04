#!/usr/bin/env python3
"""Reproduce The Agentic Edge through the current AgentDeck Research contracts.

The Hugging Face source is pinned and read-only. Historical Recorder v1.3
artifacts are copied into a local cache, adapted non-destructively to v2.0,
bound to the current Study through an import manifest, and then processed by
the same ``analyze_study`` and Finding APIs available to every AgentDeck user.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
STUDY_ROOT = Path(__file__).resolve().parents[1]
HF_REPOSITORY = "agentdeck/agentic-edge-strategy-stack-study"
HF_REVISION = "f7ac119f69da08261269bc5cf85fb65741e8ae88"
HF_CHECKSUMS_SHA256 = "51af2551c19482551d3dd79a8d6fde8f45d5c08dd62fbb2d6a94ce9e6f7e5f4c"
ORIGINAL_STUDY_COMMIT = "d659bdf244d1f0462c0d43aa2609be6c3c4a7672"
PRIMARY_CELLS = (
    "p2-fd-tier-gap-s0",
    "p2-fd-controller-effect-s1",
    "p2-fd-full-stack-effect-s3",
    "p2-fd-frontier-s3",
    "p2-vd-tier-gap-s0",
    "p2-vd-controller-effect-s1",
    "p2-vd-full-stack-effect-s3",
    "p2-vd-frontier-s3",
    "p3-fd-frontier-s1",
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", required=True, help="local cache for verified source copies")
    parser.add_argument("--output-root", required=True, help="new Research output root")
    parser.add_argument(
        "--source-dir",
        help="optional pre-downloaded HF tree; network is skipped for present files",
    )
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT / "src"))
    from agentdeck import (  # pylint: disable=import-outside-toplevel
        EvidenceCitation,
        FindingAuthor,
        FindingDeclaration,
        analyze_study,
        write_finding_report,
    )
    from agentdeck.research._canonical import (  # pylint: disable=import-outside-toplevel
        write_json_once,
    )

    cache = Path(args.cache_dir).expanduser().resolve()
    source = Path(args.source_dir).expanduser().resolve() if args.source_dir else cache / "source"
    current = cache / "current"
    checksums = _source_checksums(source)
    inventory = _source_inventory(source, checksums)
    _materialize_source(source, inventory, checksums)
    manifest, migration = _adapt_records(source, current, inventory, checksums)

    analysis = analyze_study(
        STUDY_ROOT,
        cell_ids=PRIMARY_CELLS,
        measure_ids=("agentic-edge-outcomes", "combat-behavior"),
        imported_manifest=manifest,
        output_root=args.output_root,
        assumptions=(
            "Recorder v1.3 artifacts were adapted non-destructively to schema 2.0.",
            f"The source dataset is pinned to Hugging Face revision {HF_REVISION}.",
        ),
    )
    outcomes = next(
        item for item in analysis.evidence if item.measure_id == "agentic-edge-outcomes"
    )
    comparisons = _compare_historical_results(outcomes)
    reproduction_root = analysis.analysis_root / "reproduction"
    reproduction_root.mkdir(parents=True, exist_ok=False)
    write_json_once(reproduction_root / "migration.json", migration)
    receipt = {
        "schema_version": 1,
        "study_id": analysis.study_id,
        "source": {
            "repository": f"hf://datasets/{HF_REPOSITORY}",
            "revision": HF_REVISION,
            "checksums_sha256": HF_CHECKSUMS_SHA256,
            "mutation": "none",
        },
        "adapter": "scripts/migrate_agentic_edge_records_v2.py",
        "analysis_sha256": analysis.analysis_sha256,
        "record_count": sum(
            item["observed"] for item in comparisons if item["metric"] == "match-count"
        ),
        "comparisons": comparisons,
        "all_historical_values_matched": all(item["matched"] for item in comparisons),
    }
    write_json_once(reproduction_root / "reproduction.json", receipt)
    if not receipt["all_historical_values_matched"]:
        raise RuntimeError("Current Research derivation diverged from frozen historical results")

    findings = _authored_findings(outcomes, EvidenceCitation, FindingAuthor, FindingDeclaration)
    for declaration in findings:
        write_finding_report(
            declaration,
            [outcomes],
            output=reproduction_root / "findings" / declaration.id,
        )

    print(f"Study: {analysis.study_id}")
    print(f"Frozen source: {HF_REPOSITORY}@{HF_REVISION}")
    print(f"Records: 432 primary/supplemental Matches")
    print(f"Analysis: sha256:{analysis.analysis_sha256}")
    print(f"Historical checks: {len(comparisons)}/{len(comparisons)} matched")
    print(f"Output: {analysis.analysis_root}")
    print("Hugging Face mutation: none")
    return 0


def _source_inventory(source: Path, checksums: Mapping[str, str]) -> tuple[str, ...]:
    records = tuple(
        sorted(
            relative
            for relative in checksums
            if relative.endswith(".json") and "/records/match_" in relative
        )
    )
    if len(records) != 540:
        raise ValueError(f"Pinned checksum manifest expected 540 Records; observed {len(records)}")
    inventory_path = source / "source-inventory.json"
    if inventory_path.is_file():
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        if payload.get("repository") != HF_REPOSITORY or payload.get("revision") != HF_REVISION:
            raise ValueError("Cached source inventory is not pinned to the required revision")
        if tuple(payload.get("records", ())) != records:
            raise ValueError("Cached source inventory diverges from the pinned checksum manifest")
        return records

    source.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {"repository": HF_REPOSITORY, "revision": HF_REVISION, "records": records},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return records


def _source_checksums(source: Path) -> dict[str, str]:
    manifest = source / "checksums.sha256"
    if not manifest.is_file():
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_bytes(_download("checksums.sha256"))
    observed_manifest_sha256 = _sha256_path(manifest)
    if observed_manifest_sha256 != HF_CHECKSUMS_SHA256:
        raise ValueError(
            "Cached checksum manifest diverges from the pinned Hugging Face snapshot: "
            f"expected {HF_CHECKSUMS_SHA256}, observed {observed_manifest_sha256}"
        )
    checksums = _parse_checksums(manifest.read_text(encoding="utf-8"))
    return checksums


def _parse_checksums(text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"Malformed checksum manifest line {line_number}")
        digest, relative = parts
        relative = relative.removeprefix("*")
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError(f"Malformed SHA-256 on checksum manifest line {line_number}")
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError(f"Non-portable path on checksum manifest line {line_number}")
        if relative in checksums:
            raise ValueError(f"Duplicate path on checksum manifest line {line_number}")
        checksums[relative] = digest
    return checksums


def _materialize_source(
    source: Path,
    inventory: Sequence[str],
    checksums: Mapping[str, str],
) -> None:
    for index, relative in enumerate(inventory, start=1):
        target = source / relative
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_download(relative))
        observed = _sha256_path(target)
        expected = checksums[relative]
        if observed != expected:
            raise ValueError(
                f"Frozen source Record failed checksum verification: {relative}; "
                f"expected {expected}, observed {observed}"
            )
        if index % 50 == 0 or index == len(inventory):
            print(f"Verified {index}/{len(inventory)} frozen Records", file=sys.stderr)


def _download(relative: str) -> bytes:
    encoded = urllib.parse.quote(relative, safe="/")
    url = (
        f"https://huggingface.co/datasets/{HF_REPOSITORY}/resolve/"
        f"{HF_REVISION}/{encoded}?download=true"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "AgentDeck-Reproduction/1"})
    with urllib.request.urlopen(request) as response:  # nosec: pinned public artifact
        return response.read()


def _adapt_records(
    source: Path,
    current: Path,
    inventory: Sequence[str],
    checksums: Mapping[str, str],
) -> tuple[Path, dict[str, Any]]:
    migrate = _migration_function()
    study = _prepared_study()
    cells = {cell.assembly_run: cell for cell in study.definition.cells}
    groups = {group.id: group for group in study.definition.execution_groups}
    phases = {phase.id: phase for phase in study.definition.phases}
    entries: list[dict[str, Any]] = []
    migration_records: list[dict[str, str]] = []
    for relative in inventory:
        source_path = source / relative
        parts = Path(relative).parts
        raw_index = parts.index("raw_recordings")
        assembly_run = parts[raw_index + 1]
        cell = cells[assembly_run]
        target_relative = Path("records") / assembly_run / source_path.name
        target = current / target_relative
        if not target.is_file():
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            migrated = migrate(payload, source_path=source_path)
            adapted_bytes = (json.dumps(migrated, ensure_ascii=False, indent=2) + "\n").encode()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(adapted_bytes)
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
        current_payload = json.loads(target.read_text(encoding="utf-8"))
        provenance = current_payload.get("migration_provenance") or {}
        if provenance.get("source_match_id") != source_payload.get("match_id") or provenance.get(
            "source_schema_version"
        ) != str(source_payload.get("schema_version")):
            raise ValueError(f"Cached adapted Record does not bind to verified source: {relative}")
        adapted_sha256 = _sha256_path(target)
        context = current_payload.get("metadata", {}).get("context", {})
        group = groups[cell.execution_group]
        entries.append(
            {
                "path": target_relative.as_posix(),
                "record_sha256": adapted_sha256,
                "match_id": current_payload["match_id"],
                "cell_id": cell.id,
                "phase_id": group.phase,
                "phase_kind": phases[group.phase].kind,
                "execution_group_id": group.id,
                "assembly_run": cell.assembly_run,
                "match_index": context["match_index"],
                "effective_seed": current_payload["seed"],
            }
        )
        migration_records.append(
            {
                "source_path": relative,
                "source_sha256": checksums[relative],
                "adapted_path": target_relative.as_posix(),
                "adapted_sha256": adapted_sha256,
            }
        )
    cell_order = {cell.id: index for index, cell in enumerate(study.definition.cells)}
    entries.sort(key=lambda item: (cell_order[item["cell_id"]], item["match_index"]))
    manifest = current / "import-manifest.yaml"
    if not manifest.exists():
        manifest.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "source": {
                        "id": f"hf://datasets/{HF_REPOSITORY}",
                        "revision": HF_REVISION,
                        "source_schema": "1.3",
                        "adapter": "scripts/migrate_agentic_edge_records_v2.py",
                        "original_study_commit": ORIGINAL_STUDY_COMMIT,
                    },
                    "records": entries,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    else:
        existing = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        if existing.get("records") != entries:
            raise ValueError("Cached import manifest diverges from adapted Records")
    migration_payload: dict[str, Any] = {
        "schema_version": 1,
        "source": {
            "repository": f"hf://datasets/{HF_REPOSITORY}",
            "revision": HF_REVISION,
            "checksums_sha256": HF_CHECKSUMS_SHA256,
        },
        "adapter": "scripts/migrate_agentic_edge_records_v2.py",
        "record_count": len(migration_records),
        "records": migration_records,
    }
    migration_payload["migration_sha256"] = _sha256_json(migration_payload)
    return manifest, migration_payload


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_json(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _prepared_study():
    from agentdeck import prepare_study  # pylint: disable=import-outside-toplevel

    return prepare_study(STUDY_ROOT)


def _migration_function() -> Callable[..., dict[str, Any]]:
    path = REPO_ROOT / "scripts" / "migrate_agentic_edge_records_v2.py"
    spec = importlib.util.spec_from_file_location("agentdeck_record_migration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Record migration adapter could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.migrate_match_payload


def _compare_historical_results(evidence) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for cell_id in PRIMARY_CELLS:
        historical = json.loads(
            (STUDY_ROOT / "artifacts" / cell_id.replace("-", "_") / "results.json").read_text(
                encoding="utf-8"
            )
        )
        checks.append(
            _comparison(
                evidence, cell_id, "match-count", {}, historical["summary"]["total_matches"]
            )
        )
        checks.append(
            _comparison(evidence, cell_id, "total-cost", {}, historical["summary"]["total_cost"])
        )
        checks.append(
            _comparison(evidence, cell_id, "average-turns", {}, historical["summary"]["avg_turns"])
        )
        checks.append(
            _comparison(
                evidence, cell_id, "average-duration", {}, historical["summary"]["avg_duration"]
            )
        )
        checks.append(
            _comparison(
                evidence,
                cell_id,
                "first-player-win-rate",
                {},
                historical["position_effect"]["first_player_win_rate"],
            )
        )
        for player, win_rate in historical["summary"]["win_rates"].items():
            checks.append(_comparison(evidence, cell_id, "win-rate", {"player": player}, win_rate))
            statistics = historical["statistics"]["players"][player]
            checks.append(
                _comparison(
                    evidence,
                    cell_id,
                    "exact-binomial-p-value",
                    {"player": player},
                    statistics["p_value"],
                )
            )
            checks.append(
                _comparison(
                    evidence,
                    cell_id,
                    "cohens-h-versus-half",
                    {"player": player},
                    statistics["effect_size"],
                )
            )
    return checks


def _comparison(
    evidence,
    cell_id: str,
    metric: str,
    dimensions: Mapping[str, Any],
    expected: int | float,
) -> dict[str, Any]:
    target = {"cell": cell_id, **dimensions}
    matches = [
        item
        for item in evidence.results
        if item.metric == metric and dict(item.dimensions) == target
    ]
    if len(matches) != 1:
        raise ValueError(f"Result did not resolve exactly once: {metric} {target}")
    observed = matches[0].value
    tolerance = 1e-12
    matched = abs(float(observed) - float(expected)) <= tolerance
    return {
        "cell_id": cell_id,
        "metric": metric,
        "dimensions": dimensions,
        "expected": expected,
        "observed": observed,
        "tolerance": tolerance,
        "matched": matched,
        "result_sha256": matches[0].result_sha256,
    }


def _authored_findings(evidence, citation_type, author_type, declaration_type):
    def cite(relation: str, metric: str, cell: str, player: str | None = None):
        dimensions = {"cell": cell}
        if player is not None:
            dimensions["player"] = player
        matches = [
            item
            for item in evidence.results
            if item.metric == metric and dict(item.dimensions) == dimensions
        ]
        if len(matches) != 1:
            raise ValueError(f"Finding selector did not resolve: {metric} {dimensions}")
        return citation_type(relation, evidence.evidence_sha256, matches[0].result_sha256)

    author = author_type("The Agentic Edge authors", "human")
    common = (
        "The findings apply to the declared Games, Players, provider snapshots, prompts, and schedule.",
        "First-player effects and explicit strategy instructions limit broader causal interpretation.",
    )
    return (
        declaration_type(
            "fixed-damage-cross-tier-inversion",
            "In FixedDamage, the scaffolded FlashLite S3 Player beat the unscaffolded GPT-4o-mini Player in 38 of 48 frozen Matches.",
            author,
            (
                cite("supports", "win-rate", "p2-fd-frontier-s3", "FlashLite-S3-HP"),
                cite(
                    "contextualizes",
                    "exact-binomial-p-value",
                    "p2-fd-frontier-s3",
                    "FlashLite-S3-HP",
                ),
                cite("qualifies", "first-player-win-rate", "p2-fd-frontier-s3"),
            ),
            common,
        ),
        declaration_type(
            "variable-damage-transfer-caveat",
            "In VariableDamage, the corresponding scaffolded FlashLite S3 Player won 28 of 48 Matches; this result alone does not establish a cross-tier advantage.",
            author,
            (
                cite("supports", "win-rate", "p2-vd-frontier-s3", "FlashLite-S3-RISK"),
                cite(
                    "qualifies", "exact-binomial-p-value", "p2-vd-frontier-s3", "FlashLite-S3-RISK"
                ),
                cite("contextualizes", "first-player-win-rate", "p2-vd-frontier-s3"),
            ),
            common,
        ),
        declaration_type(
            "fixed-damage-reasoning-ladder",
            "In the supplemental FixedDamage Cell, the FlashLite S1 reasoning Player beat the unscaffolded GPT-4o-mini Player in 34 of 48 frozen Matches.",
            author,
            (
                cite("supports", "win-rate", "p3-fd-frontier-s1", "FlashLite-S1-RC"),
                cite(
                    "contextualizes",
                    "exact-binomial-p-value",
                    "p3-fd-frontier-s1",
                    "FlashLite-S1-RC",
                ),
                cite("qualifies", "first-player-win-rate", "p3-fd-frontier-s1"),
            ),
            common,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
