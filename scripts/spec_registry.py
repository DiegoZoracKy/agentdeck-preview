#!/usr/bin/env python3
"""Build and validate AgentDeck's deterministic specification registry."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
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
LEGACY_INVARIANT_RE = re.compile(
    r"^\s*(?:[0-9]+\.\s+|-\s+)(?:\*\*|`)"
    r"([A-Za-z][A-Za-z0-9#]*(?:-[A-Za-z0-9]+)*)(?:\*\*|`)(?=\s*:|\s)",
    re.MULTILINE,
)
INVARIANT_SECTION_RE = re.compile(r"^##\s+.*\bInvariants\b.*$", re.MULTILINE)
TOP_LEVEL_SECTION_RE = re.compile(r"^##\s+", re.MULTILINE)
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
    invariant_sha256: Mapping[str, str]
    unregistered_invariants: tuple[str, ...]
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


def _invariant_sections(text: str) -> str:
    sections: list[str] = []
    for heading in INVARIANT_SECTION_RE.finditer(text):
        next_heading = TOP_LEVEL_SECTION_RE.search(text, heading.end())
        end = next_heading.start() if next_heading else len(text)
        sections.append(text[heading.start() : end])
    return "\n".join(sections)


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
    invariant_text = _invariant_sections(text)
    invariants = tuple(INVARIANT_RE.findall(invariant_text))
    if len(invariants) != len(set(invariants)):
        duplicates = sorted(
            invariant for invariant in set(invariants) if invariants.count(invariant) > 1
        )
        raise SpecRegistryError(f"{path.name}: duplicate invariant declarations {duplicates}")
    registered = set(invariants)
    invariant_sha256 = {
        match.group(1): _sha256(line.strip().encode("utf-8"))
        for line in invariant_text.splitlines()
        if (match := INVARIANT_RE.search(line)) is not None
    }
    unregistered_invariants = tuple(
        dict.fromkeys(
            invariant
            for invariant in LEGACY_INVARIANT_RE.findall(invariant_text)
            if invariant not in registered
        )
    )
    links = tuple(match.strip() for match in LINK_RE.findall(text))
    return Contract(
        path=path,
        metadata=metadata,
        invariants=invariants,
        invariant_sha256=invariant_sha256,
        unregistered_invariants=unregistered_invariants,
        links=links,
    )


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
    active_contracts = [contract for contract in contracts if contract.active]
    return {
        "schema_version": 3,
        "invariant_summary": {
            "scope": "active_contracts",
            "registered": sum(len(contract.invariants) for contract in active_contracts),
            "unregistered": sum(
                len(contract.unregistered_invariants) for contract in active_contracts
            ),
        },
        "hub": {
            "path": hub.relative_to(root).as_posix(),
            "sha256": _sha256(hub.read_bytes()),
        },
        "contracts": [
            {
                "active": contract.active,
                "implementation": contract.metadata["Implementation"],
                "invariants": list(contract.invariants),
                "invariant_sha256": dict(contract.invariant_sha256),
                "last_updated": contract.metadata["Last Updated"],
                "path": contract.path.relative_to(root).as_posix(),
                "review_state": contract.metadata["Review State"],
                "sha256": _sha256(contract.path.read_bytes()),
                "spec_id": contract.spec_id,
                "status": contract.metadata["Status"],
                "superseded_by": contract.metadata.get("Superseded By"),
                "unregistered_invariants": list(contract.unregistered_invariants),
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


def _test_function_names_invariant(path: Path, function_name: str, invariant: str) -> bool:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise SpecRegistryError(f"cannot parse evidence test {path}: {exc}") from exc
    functions = [
        node
        for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    ]
    if len(functions) != 1:
        raise SpecRegistryError(
            f"evidence locator {path.name}::{function_name} must resolve to one test function"
        )
    node = functions[0]
    name_names_invariant = re.search(
        rf"(?:^|_){re.escape(invariant.lower())}(?:_|$)", node.name.lower()
    )
    docstring = ast.get_docstring(node) or ""
    docstring_names_invariant = re.search(rf"\b{re.escape(invariant)}\b", docstring)
    return bool(name_names_invariant or docstring_names_invariant)


def _resolve_test_locator(root: Path, locator: object) -> tuple[Path, str]:
    if not isinstance(locator, str) or locator.count("::") != 1:
        raise SpecRegistryError(
            f"evidence test must use repository-relative path::test_function, got {locator!r}"
        )
    raw_path, function_name = locator.split("::", 1)
    if not raw_path or not function_name:
        raise SpecRegistryError(f"invalid evidence test locator {locator!r}")
    resolved_root = root.resolve()
    path = (root / raw_path).resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise SpecRegistryError(f"evidence test leaves repository: {locator}") from exc
    if not path.is_file():
        raise SpecRegistryError(f"missing evidence test {locator}")
    return path, function_name


def validate_compliance(registry: Mapping[str, Any], root: Path = ROOT) -> None:
    payload = _read_json(root / "specs" / "compliance.json")
    if payload.get("schema_version") != 2 or not isinstance(payload.get("contracts"), list):
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
        unregistered = set(active[spec_id]["unregistered_invariants"])
        evidence = entry.get("evidence", [])
        covered: set[str] = set()
        if not isinstance(evidence, list):
            raise SpecRegistryError(f"{spec_id}: evidence must be a list")
        for item in evidence:
            invariant = item.get("invariant_id")
            test_locator = item.get("test")
            if invariant not in declared:
                raise SpecRegistryError(f"{spec_id}: unknown invariant {invariant}")
            test_path, function_name = _resolve_test_locator(root, test_locator)
            if not _test_function_names_invariant(test_path, function_name, invariant):
                raise SpecRegistryError(
                    f"{spec_id}: test {test_locator} does not name {invariant} directly"
                )
            covered.add(invariant)
        if status == "verified":
            if not declared:
                raise SpecRegistryError(
                    f"{spec_id}: verified claim requires at least one registered invariant"
                )
            if unregistered:
                raise SpecRegistryError(
                    f"{spec_id}: verified claim has unregistered invariants {sorted(unregistered)}"
                )
            if assurance not in {"automated", "semantic"}:
                raise SpecRegistryError(
                    f"{spec_id}: verified claim needs automated or semantic assurance"
                )
            if covered != declared:
                missing = sorted(declared - covered)
                raise SpecRegistryError(f"{spec_id}: verified claim lacks {missing}")
        if assurance in {"automated", "semantic"} and not evidence:
            raise SpecRegistryError(f"{spec_id}: {assurance} assurance needs evidence")
        if assurance == "semantic":
            review = entry.get("semantic_review")
            if not isinstance(review, str) or not (root / review).is_file():
                raise SpecRegistryError(f"{spec_id}: semantic assurance needs review artifact")


def validate_new_work_evidence(
    registry: Mapping[str, Any],
    previous_registry: Mapping[str, Any],
    root: Path = ROOT,
) -> None:
    """Require direct tests for newly completed or normatively changed invariants."""
    compliance = _read_json(root / "specs" / "compliance.json")
    evidence_by_spec = {
        entry["spec_id"]: {item["invariant_id"] for item in entry.get("evidence", [])}
        for entry in compliance["contracts"]
    }
    previous = {
        entry["spec_id"]: entry
        for entry in previous_registry.get("contracts", [])
        if isinstance(entry, dict) and isinstance(entry.get("spec_id"), str)
    }

    for current in registry["contracts"]:
        if not current["active"] or not current["implementation"].startswith("Complete"):
            continue
        prior = previous.get(current["spec_id"])
        current_ids = set(current["invariants"])
        prior_ids = set(prior.get("invariants", [])) if prior else set()
        required = current_ids - prior_ids

        current_hashes = current.get("invariant_sha256", {})
        prior_hashes = prior.get("invariant_sha256", {}) if prior else {}
        required.update(
            invariant
            for invariant in current_ids & prior_ids
            if invariant in prior_hashes
            and current_hashes.get(invariant) != prior_hashes.get(invariant)
        )
        if prior is None or (
            not str(prior.get("implementation", "")).startswith("Complete")
            and current["implementation"].startswith("Complete")
        ):
            required = current_ids

        missing = sorted(required - evidence_by_spec.get(current["spec_id"], set()))
        if missing:
            raise SpecRegistryError(
                f"{current['spec_id']}: completed new work lacks direct evidence {missing}"
            )


def _previous_checked_in_registry(root: Path) -> Mapping[str, Any] | None:
    """Read the nearest Git baseline without making Git part of registry authority."""
    try:
        changed = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", "specs"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        reference = "HEAD" if changed.returncode == 1 else "HEAD^"
        prior = subprocess.run(
            ["git", "show", f"{reference}:specs/registry.json"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if prior.returncode != 0:
        return None
    try:
        payload = json.loads(prior.stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


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
    previous_registry = _previous_checked_in_registry(root)
    if previous_registry is not None:
        validate_new_work_evidence(registry, previous_registry, root)


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
