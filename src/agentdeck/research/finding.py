"""Authored Findings with exact Evidence-result citations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from ._canonical import sha256_json, write_json_once, write_text_once
from .evidence import Evidence


@dataclass(frozen=True)
class FindingAuthor:
    name: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "kind": self.kind}


@dataclass(frozen=True)
class EvidenceCitation:
    relation: str
    evidence_sha256: str
    result_sha256: str

    def as_dict(self) -> dict[str, str]:
        return {
            "relation": self.relation,
            "evidence_sha256": self.evidence_sha256,
            "result_sha256": self.result_sha256,
        }


@dataclass(frozen=True)
class FindingDeclaration:
    id: str
    claim: str
    author: FindingAuthor
    citations: tuple[EvidenceCitation, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "citations", tuple(self.citations))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim": self.claim,
            "author": self.author.as_dict(),
            "citations": [citation.as_dict() for citation in self.citations],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class Finding:
    schema_version: int
    declaration: FindingDeclaration
    finding_sha256: str

    def identity_payload(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "finding": self.declaration.as_dict()}

    def as_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "finding_sha256": self.finding_sha256}


def load_finding(path: str | Path, finding_id: str) -> FindingDeclaration:
    """Load one explicit Finding declaration."""

    source = Path(path).expanduser().resolve()
    if source.is_dir():
        source = source / "findings.yaml"
    if not source.is_file():
        raise ValueError(f"Finding manifest is missing: {source}")
    try:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Finding manifest could not be read: {exc}") from exc
    if not isinstance(payload, Mapping) or set(payload) != {"schema_version", "findings"}:
        raise ValueError("Finding manifest must contain only schema_version and findings")
    if payload.get("schema_version") != 1:
        raise ValueError("Finding manifest schema_version must equal 1")
    items = payload.get("findings")
    if not isinstance(items, list) or not items:
        raise ValueError("Finding manifest must contain a non-empty findings list")
    declarations = tuple(_parse_finding(item, index) for index, item in enumerate(items))
    ids = [item.id for item in declarations]
    if len(set(ids)) != len(ids):
        raise ValueError("Finding manifest contains duplicate ids")
    matches = [item for item in declarations if item.id == finding_id]
    if len(matches) != 1:
        raise ValueError(f"Finding id {finding_id!r} is not declared exactly once")
    return matches[0]


def prepare_finding(
    declaration: FindingDeclaration,
    evidence: Sequence[Evidence],
) -> Finding:
    """Resolve every granular citation and seal one immutable authored Finding."""

    by_hash = {item.evidence_sha256: item for item in evidence}
    if len(by_hash) != len(evidence):
        raise ValueError("Finding Evidence inputs contain duplicate identities")
    for index, citation in enumerate(declaration.citations):
        artifact = by_hash.get(citation.evidence_sha256)
        if artifact is None:
            raise ValueError(f"Finding citation {index} references unknown Evidence")
        try:
            artifact.result(citation.result_sha256)
        except KeyError as exc:
            raise ValueError(f"Finding citation {index} references unknown EvidenceResult") from exc
    identity = {"schema_version": 1, "finding": declaration.as_dict()}
    return Finding(
        schema_version=1,
        declaration=declaration,
        finding_sha256=sha256_json(identity),
    )


def render_finding_markdown(finding: Finding, evidence: Sequence[Evidence]) -> str:
    """Render a deterministic human-readable projection of one Finding."""

    by_hash = {item.evidence_sha256: item for item in evidence}
    lines = [
        f"# Finding: {finding.declaration.id}",
        "",
        finding.declaration.claim,
        "",
        f"Author: {finding.declaration.author.name} ({finding.declaration.author.kind})",
        f"Finding: `sha256:{finding.finding_sha256}`",
        "",
        "## Evidence citations",
        "",
    ]
    for citation in finding.declaration.citations:
        artifact = by_hash[citation.evidence_sha256]
        result = artifact.result(citation.result_sha256)
        value = result.value if result.status == "available" else "unavailable"
        dimensions = json.dumps(
            dict(result.dimensions),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        lines.append(
            f"- **{citation.relation}** `{result.metric}` = `{value}` "
            f"(Evidence `sha256:{artifact.evidence_sha256}`, "
            f"result `sha256:{result.result_sha256}`, dimensions `{dimensions}`, "
            f"origin `{artifact.corpus_origin_kind}`, phase "
            f"`{', '.join(item['kind'] for item in artifact.phases)}`)"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in finding.declaration.limitations)
    lines.extend(
        [
            "",
            "## Assurance boundary",
            "",
            "AgentDeck validated artifact identities and citation resolution. "
            "This Finding remains authored interpretation, not mechanically certified truth.",
            "",
        ]
    )
    return "\n".join(lines)


def write_finding_report(
    declaration: FindingDeclaration,
    evidence: Sequence[Evidence],
    *,
    output: str | Path,
) -> tuple[Finding, Path, Path]:
    """Resolve and persist one Finding plus its deterministic Markdown projection."""

    root = Path(output).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=False)
    finding = prepare_finding(declaration, evidence)
    finding_path = root / "finding.json"
    report_path = root / "report.md"
    write_json_once(finding_path, finding.as_dict())
    write_text_once(report_path, render_finding_markdown(finding, evidence))
    return finding, finding_path, report_path


def _parse_finding(value: Any, index: int) -> FindingDeclaration:
    location = f"findings[{index}]"
    if not isinstance(value, Mapping):
        raise ValueError(f"{location} must be a mapping")
    allowed = {"id", "claim", "author", "citations", "limitations"}
    unknown = set(value) - allowed
    if unknown or set(value) != allowed:
        raise ValueError(f"{location} must contain exactly {', '.join(sorted(allowed))}")
    finding_id = _text(value.get("id"), f"{location}.id")
    if not _portable_id(finding_id):
        raise ValueError(f"{location}.id must be a portable lowercase identifier")
    claim = _text(value.get("claim"), f"{location}.claim")
    author_value = value.get("author")
    if not isinstance(author_value, Mapping) or set(author_value) != {"name", "kind"}:
        raise ValueError(f"{location}.author must contain name and kind")
    author = FindingAuthor(
        _text(author_value.get("name"), f"{location}.author.name"),
        _text(author_value.get("kind"), f"{location}.author.kind"),
    )
    if author.kind not in {"human", "ai_assisted", "ai"}:
        raise ValueError(f"{location}.author.kind is unsupported")
    raw_citations = value.get("citations")
    if not isinstance(raw_citations, list) or not raw_citations:
        raise ValueError(f"{location}.citations must be a non-empty list")
    citations = tuple(
        _parse_citation(item, location, citation_index)
        for citation_index, item in enumerate(raw_citations)
    )
    if not any(item.relation == "supports" for item in citations):
        raise ValueError(f"{location} requires at least one supports citation")
    raw_limitations = value.get("limitations")
    if not isinstance(raw_limitations, list) or not raw_limitations:
        raise ValueError(f"{location}.limitations must be a non-empty list")
    limitations = tuple(_text(item, f"{location}.limitations") for item in raw_limitations)
    return FindingDeclaration(finding_id, claim, author, citations, limitations)


def _parse_citation(value: Any, location: str, index: int) -> EvidenceCitation:
    if not isinstance(value, Mapping) or set(value) != {"relation", "evidence", "result"}:
        raise ValueError(f"{location}.citations[{index}] must contain relation, evidence, result")
    relation = _text(value.get("relation"), f"{location}.citations[{index}].relation")
    if relation not in {"supports", "qualifies", "challenges", "contextualizes"}:
        raise ValueError(f"{location}.citations[{index}].relation is unsupported")
    evidence_hash = _sha_reference(value.get("evidence"), f"{location}.citations[{index}].evidence")
    result_hash = _sha_reference(value.get("result"), f"{location}.citations[{index}].result")
    return EvidenceCitation(relation, evidence_hash, result_hash)


def _sha_reference(value: Any, location: str) -> str:
    text = _text(value, location)
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{location} must be a lowercase SHA-256 reference")
    return text


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a non-empty string")
    return value.strip()


def _portable_id(value: str) -> bool:
    return value[0].isalnum() and all(
        character.islower() or character.isdigit() or character in "._-" for character in value
    )


__all__ = [
    "EvidenceCitation",
    "Finding",
    "FindingAuthor",
    "FindingDeclaration",
    "load_finding",
    "prepare_finding",
    "render_finding_markdown",
    "write_finding_report",
]
