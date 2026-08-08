#!/usr/bin/env python3
"""Build and validate AgentDeck's deterministic specification registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
REGISTRY = SPECS / "registry.json"
PROFILES = SPECS / "authoring-profiles.json"
COMPLIANCE = SPECS / "compliance.json"

METADATA_RE = re.compile(r"^> ([A-Za-z ]+):\s*(.+?)\s*$", re.MULTILINE)
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
INVARIANT_RE = re.compile(r"\*\*([A-Z][A-Z0-9]*[0-9]+)\s+[^*]+\*\*")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
IMPLEMENTATION_PREFIXES = ("Complete", "Partial", "Planned", "Not implemented")
LIFECYCLES = {"Final", "Superseded", "Deprecated"}
REVIEW_STATES = {"Consensus-approved", "Legacy-approved", "Needs review"}


class SpecRegistryError(ValueError):
    """Raised when a spec declaration is incomplete or dishonest."""


@dataclass(frozen=True)
class Contract:
    """Parsed, validated specification contract."""

    path: Path
    metadata: Mapping[str, str]
    invariants: tuple[str, ...]
    links: tuple[str, ...]

    @property
    def spec_id(self) -> str:
        return self.path.stem

    @property
    def active(self) -> bool:
        return self.metadata["Status"] == "Final"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecRegistryError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def _governed_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "specs").glob("SPEC-*.md"), key=lambda path: path.name)


def _parse_contract(path: Path) -> Contract:
    text = path.read_text(encoding="utf-8")
    metadata = dict(METADATA_RE.findall("\n".join(text.splitlines()[:20])))
    required = ("Status", "Version", "Last Updated", "Implementation", "Review State")
    missing = [field for field in required if field not in metadata]
    if missing:
        raise SpecRegistryError(f"{path.name}: missing metadata {', '.join(missing)}")
    if metadata["Status"] not in LIFECYCLES:
        raise SpecRegistryError(f"{path.name}: invalid Status {metadata['Status']!r}")
    if not SEMVER_RE.fullmatch(metadata["Version"]):
        raise SpecRegistryError(f"{path.name}: invalid semantic Version")
    try:
        date.fromisoformat(metadata["Last Updated"])
    except ValueError as exc:
        raise SpecRegistryError(f"{path.name}: invalid Last Updated date") from exc
    if not metadata["Implementation"].startswith(IMPLEMENTATION_PREFIXES):
        raise SpecRegistryError(f"{path.name}: invalid Implementation state")
    if metadata["Review State"] not in REVIEW_STATES:
        raise SpecRegistryError(f"{path.name}: invalid Review State")
    if metadata["Status"] == "Superseded" and "Superseded By" not in metadata:
        raise SpecRegistryError(f"{path.name}: Superseded spec needs Superseded By")
    invariants = tuple(INVARIANT_RE.findall(text))
    links = tuple(match.strip() for match in LINK_RE.findall(text))
    return Contract(path=path, metadata=metadata, invariants=invariants, links=links)


def load_contracts(root: Path = ROOT) -> list[Contract]:
    contracts = [_parse_contract(path) for path in _governed_paths(root)]
    by_name = {contract.path.name: contract for contract in contracts}
    invariant_owner: dict[str, str] = {}
    for contract in contracts:
        if contract.metadata["Status"] == "Superseded":
            target_name = contract.metadata["Superseded By"]
            target = by_name.get(target_name)
            if target is None or not target.active:
                raise SpecRegistryError(
                    f"{contract.path.name}: Superseded By must name a Final spec"
                )
        if not contract.active:
            continue
        for invariant in contract.invariants:
            owner = invariant_owner.setdefault(invariant, contract.path.name)
            if owner != contract.path.name:
                raise SpecRegistryError(
                    f"duplicate active invariant {invariant}: {owner}, {contract.path.name}"
                )
    _validate_links(contracts, root)
    return contracts


def _validate_links(contracts: Iterable[Contract], root: Path) -> None:
    resolved_root = root.resolve()
    for contract in contracts:
        for raw_link in contract.links:
            target = raw_link.split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "/")):
                continue
            candidate = (contract.path.parent / target).resolve()
            try:
                candidate.relative_to(resolved_root)
            except ValueError as exc:
                raise SpecRegistryError(
                    f"{contract.path.name}: link leaves repository: {raw_link}"
                ) from exc
            if not candidate.exists():
                raise SpecRegistryError(
                    f"{contract.path.name}: unresolved relative link {raw_link}"
                )


def build_registry(root: Path = ROOT) -> dict[str, Any]:
    contracts = load_contracts(root)
    hub = root / "specs" / "SPEC.md"
    return {
        "schema_version": 1,
        "hub": {
            "path": hub.relative_to(root).as_posix(),
            "sha256": _sha256(hub.read_bytes()),
        },
        "contracts": [
            {
                "active": contract.active,
                "implementation": contract.metadata["Implementation"],
                "invariants": list(contract.invariants),
                "last_updated": contract.metadata["Last Updated"],
                "path": contract.path.relative_to(root).as_posix(),
                "review_state": contract.metadata["Review State"],
                "sha256": _sha256(contract.path.read_bytes()),
                "spec_id": contract.spec_id,
                "status": contract.metadata["Status"],
                "superseded_by": contract.metadata.get("Superseded By"),
                "version": contract.metadata["Version"],
            }
            for contract in contracts
        ],
    }


def validate_profiles(registry: Mapping[str, Any], root: Path = ROOT) -> Mapping[str, Any]:
    payload = _read_json(root / "specs" / "authoring-profiles.json")
    if payload.get("schema_version") != 1 or not isinstance(payload.get("profiles"), list):
        raise SpecRegistryError("authoring-profiles.json: invalid schema")
    known_sources = {registry["hub"]["path"]}
    known_sources.update(contract["path"] for contract in registry["contracts"])
    known_sources.update({"CONTRIBUTING.md", "SECURITY.md"})
    profile_ids: set[str] = set()
    for profile in payload["profiles"]:
        profile_id = profile.get("profile_id")
        if not isinstance(profile_id, str) or profile_id in profile_ids:
            raise SpecRegistryError("authoring profile IDs must be unique strings")
        profile_ids.add(profile_id)
        if not SEMVER_RE.fullmatch(str(profile.get("version", ""))):
            raise SpecRegistryError(f"profile {profile_id}: invalid version")
        sources = profile.get("sources")
        if not isinstance(sources, list) or not sources or len(sources) != len(set(sources)):
            raise SpecRegistryError(f"profile {profile_id}: sources must be unique")
        for source in sources:
            if source not in known_sources:
                raise SpecRegistryError(f"profile {profile_id}: undeclared source {source}")
            candidate = (root / source).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError as exc:
                raise SpecRegistryError(f"profile {profile_id}: source escapes root") from exc
            if not candidate.is_file():
                raise SpecRegistryError(f"profile {profile_id}: missing source {source}")
    return payload


def validate_compliance(registry: Mapping[str, Any], root: Path = ROOT) -> None:
    payload = _read_json(root / "specs" / "compliance.json")
    if payload.get("schema_version") != 1 or not isinstance(payload.get("contracts"), list):
        raise SpecRegistryError("compliance.json: invalid schema")
    active = {entry["spec_id"]: entry for entry in registry["contracts"] if entry["active"]}
    entries = payload["contracts"]
    by_id = {entry.get("spec_id"): entry for entry in entries}
    if len(by_id) != len(entries) or set(by_id) != set(active):
        raise SpecRegistryError("compliance.json must contain every Final contract exactly once")
    for spec_id, entry in by_id.items():
        status = entry.get("status")
        assurance = entry.get("assurance")
        if status not in {"unverified", "partial", "verified", "violated"}:
            raise SpecRegistryError(f"{spec_id}: invalid compliance status")
        if assurance not in {"mapped", "automated", "semantic"}:
            raise SpecRegistryError(f"{spec_id}: invalid assurance")
        declared = set(active[spec_id]["invariants"])
        evidence = entry.get("evidence", [])
        covered: set[str] = set()
        if not isinstance(evidence, list):
            raise SpecRegistryError(f"{spec_id}: evidence must be a list")
        for item in evidence:
            invariant = item.get("invariant_id")
            test_path = item.get("test")
            if invariant not in declared:
                raise SpecRegistryError(f"{spec_id}: unknown invariant {invariant}")
            if not isinstance(test_path, str) or not (root / test_path).is_file():
                raise SpecRegistryError(f"{spec_id}: missing evidence test {test_path}")
            source = (root / test_path).read_text(encoding="utf-8")
            if invariant not in source:
                raise SpecRegistryError(f"{spec_id}: test {test_path} does not name {invariant}")
            covered.add(invariant)
        if assurance in {"automated", "semantic"} and not evidence:
            raise SpecRegistryError(f"{spec_id}: {assurance} assurance needs evidence")
        if status == "verified" and covered != declared:
            missing = sorted(declared - covered)
            raise SpecRegistryError(f"{spec_id}: verified claim lacks {missing}")
        if assurance == "semantic":
            review = entry.get("semantic_review")
            if not isinstance(review, str) or not (root / review).is_file():
                raise SpecRegistryError(f"{spec_id}: semantic assurance needs review artifact")


def render_bundle(profile_id: str, root: Path = ROOT) -> bytes:
    registry = build_registry(root)
    profiles = validate_profiles(registry, root)
    profile = next(
        (item for item in profiles["profiles"] if item["profile_id"] == profile_id), None
    )
    if profile is None:
        raise SpecRegistryError(f"unknown authoring profile {profile_id}")
    registry_bytes = _canonical_json(registry)
    parts = [
        "# AgentDeck Authoring Context",
        "",
        f"> Profile: {profile_id} v{profile['version']}",
        f"> Purpose: {profile['purpose']}",
        f"> Registry SHA-256: {_sha256(registry_bytes)}",
        "> Generated deterministically; source files remain authoritative.",
        "",
    ]
    for source in profile["sources"]:
        data = (root / source).read_bytes()
        parts.extend(
            [
                "---",
                "",
                f"## Source: `{source}`",
                "",
                f"> SHA-256: `{_sha256(data)}`",
                "",
                data.decode("utf-8").rstrip("\n"),
                "",
            ]
        )
    return ("\n".join(parts).rstrip() + "\n").encode("utf-8")


def write_registry(root: Path = ROOT) -> None:
    (root / "specs" / "registry.json").write_bytes(_canonical_json(build_registry(root)))


def check(root: Path = ROOT) -> None:
    registry = build_registry(root)
    expected = _canonical_json(registry)
    actual = (root / "specs" / "registry.json").read_bytes()
    if actual != expected:
        raise SpecRegistryError("specs/registry.json is stale; run spec_registry.py write")
    validate_profiles(registry, root)
    validate_compliance(registry, root)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("write", help="write the canonical checked-in registry")
    subparsers.add_parser("check", help="validate metadata and checked-in projections")
    bundle = subparsers.add_parser("bundle", help="render one closed authoring profile")
    bundle.add_argument("--profile", required=True)
    bundle.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "write":
            write_registry()
        elif args.command == "check":
            check()
        else:
            payload = render_bundle(args.profile)
            if args.output:
                args.output.write_bytes(payload)
            else:
                sys.stdout.buffer.write(payload)
    except (OSError, SpecRegistryError) as exc:
        print(f"spec registry error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
