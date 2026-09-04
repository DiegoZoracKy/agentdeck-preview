# SPEC-FINDING v0.1.0

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented
> Review State: approved by maintainer for the Research-axis wave
> Audience: Study authors, AgentDeck users, artifact consumers, Research implementers

## 1. Purpose

Let a person finish a behavioral investigation by authoring an explicit claim
whose exact supporting, qualifying, challenging, and contextual EvidenceResults
can be resolved mechanically.

A Finding answers “what does this author conclude?” It never upgrades Evidence
into truth, mutates source artifacts, or hides interpretation inside a metric.

## 2. Scope & Philosophy Alignment

- Implements `SPEC-RESEARCH` RE10–RE16 and RE18.
- Keeps authorship, mechanical citation validation, and scientific review
  separate.
- Cites individual EvidenceResults rather than ambiguous report prose.
- Supports limitations and contradictory Evidence as first-class relations.
- Defines one narrow immutable artifact, not peer review, publication, or a
  knowledge graph.

## 3. Terminology

- **FindingDeclaration:** authored id, claim, author, Evidence citations, and
  limitations.
- **EvidenceCitation:** exact Evidence/result locator plus semantic relation to
  the Finding.
- **Finding:** immutable declaration with every citation resolved and a stable
  content identity.
- **Finding representation:** Markdown or another human-readable projection of
  the canonical Finding; never the canonical artifact itself.

## 4. Authored Contract

`findings.yaml` schema version `1`:

```yaml
schema_version: 1
findings:
  - id: strategy-stack-fixed-damage
    claim: >-
      Under the declared FixedDamage conditions, the S3 Player won more often
      than the comparison Player.
    author:
      name: AgentDeck study author
      kind: human
    citations:
      - relation: supports
        evidence: sha256:...
        result: sha256:...
      - relation: qualifies
        evidence: sha256:...
        result: sha256:...
    limitations:
      - The result does not establish performance outside the declared Game.
```

Required fields:

- `id`: unique portable identifier.
- `claim`: non-empty authored natural language.
- `author.name`: non-empty identity label.
- `author.kind`: `human`, `ai_assisted`, or `ai`.
- `citations`: non-empty list; at least one relation MUST be `supports`.
- `limitations`: non-empty authored list.

Citation relations:

- `supports`: author relies on the result for the claim;
- `qualifies`: narrows scope or confidence;
- `challenges`: supplies contrary Evidence;
- `contextualizes`: relevant context without direct support.

The artifact MUST NOT contain a generic `valid`, `scientifically_valid`,
`verified`, `peer_reviewed`, or `actionable` field. Review and supersession are
future independent artifacts; changing a Finding creates a new identity.

## 5. Data Structures

- `FindingAuthor`: name and authorship kind.
- `EvidenceCitation`: relation, Evidence SHA-256, and EvidenceResult SHA-256.
- `FindingDeclaration`: authored claim, author, citations, and limitations.
- `Finding`: declaration plus resolved Evidence identities and
  `finding_sha256`.

`finding_sha256` covers every canonical authored field and resolved citation.
It excludes timestamps, output paths, Markdown, UI state, and review metadata.

## 6. Public API

```python
load_finding(path: str | Path, finding_id: str) -> FindingDeclaration
prepare_finding(
    declaration: FindingDeclaration,
    evidence: Sequence[Evidence],
) -> Finding
render_finding_markdown(finding: Finding, evidence: Sequence[Evidence]) -> str
```

### `load_finding`

- MUST parse one explicit authored Finding.
- MUST reject duplicate ids, unsupported fields, missing support, and empty
  limitations.

### `prepare_finding`

- MUST resolve every Evidence and result hash exactly.
- MUST preserve citation relation and canonical order.
- MUST NOT reinterpret result values or assign scientific-validity state.

### `render_finding_markdown`

- MUST be deterministic for equal Finding/Evidence identities.
- MUST show claim, authorship kind, Evidence relations and result values,
  limitations, and the mechanical-assurance boundary.
- MUST cite canonical hashes and remain a representation, not authority.

## 7. Invariants & Guarantees

1. **FI1 — Explicit authorship:** every Finding names its author and whether AI
   participated in authorship.
2. **FI2 — Granular resolution:** every citation resolves one exact Evidence
   hash and one exact EvidenceResult hash.
3. **FI3 — Support required:** every Finding has at least one `supports`
   citation; other relations cannot silently stand in for support.
4. **FI4 — Limitations required:** every Finding contains at least one explicit
   authored limitation.
5. **FI5 — No truth certification:** schema/hash/citation validation MUST NOT
   emit scientific-validity, actionability, or correctness assurance.
6. **FI6 — Neutral Evidence:** Finding policy reads phase, corpus completeness,
   origin, status, and diagnostics from Evidence; it MUST NOT require an
   Evidence-level eligibility bit.
7. **FI7 — Honest relation:** preflight/pilot/supplemental/imported Evidence MAY
   qualify, challenge, or contextualize a Finding. A `supports` citation MUST be
   explicit and its phase/origin shown; v0.1 does not silently promote it.
8. **FI8 — Immutable sources:** preparation/rendering MUST NOT mutate Evidence,
   Measures, Records, or authored Finding source.
9. **FI9 — Stable identity:** equal authored content and citations produce equal
   Finding identity regardless of paths or rendering.
10. **FI10 — Reasoning honesty:** a claim about recorded reasoning MUST label it
    as model-stated output, not hidden internal thought.

## 8. Error Handling

| Condition | Required outcome |
|---|---|
| Unknown/duplicate Finding id | fail loading with source location |
| Missing `supports` citation or limitation | fail loading |
| Unknown Evidence/result hash | fail preparation with citation index |
| Evidence identity changed | stale citation fails; never retarget by metric name |
| Unavailable cited result | preserve explicit state in rendering; no neutral value |
| Rendering fails | canonical Finding remains unchanged |

## 9. Testing Strategy

| Invariants | Behavioral proof |
|---|---|
| FI1–FI4 | missing author/support/limitation and duplicate ids fail |
| FI2 | exact Evidence/result hashes resolve; stale or artifact-only prose fails |
| FI5–FI7 | no validity flag; phase/origin/availability visible for every citation |
| FI8–FI9 | source hashes unchanged; relocation and repeated rendering are stable |
| FI10 | hidden-thought phrasing is not generated by AgentDeck representations |

Acceptance requires:

- one The Agentic Edge Finding with supporting and qualifying citations;
- one single-Player/no-winner Finding citing a non-outcome result;
- deterministic Markdown that links each claim relation to exact result hashes;
- no review workflow or scientific-validity state in the v0.1 object graph.

## 10. Design Rationale

- **Relations on citations:** Evidence can narrow or contradict a claim without
  being mislabeled as primary support.
- **No lifecycle state:** the first complete journey needs an authored claim and
  exact citations, not a speculative review workflow.
- **Limitations required:** a tool for non-specialists should make scope visible
  by default while avoiding automatic scientific prose.
- **Representation separate:** reports can evolve without changing canonical
  Finding identity.

## 11. Non-Goals / Future Work

- peer/scientific review, approvals, or moderation;
- challenged/superseded graph and multi-Finding synthesis;
- automatic Finding generation or claim validation;
- publication, signing, remote registry, or collaboration;
- causal-inference or domain-specific citation policy.

## 12. References

- [`SPEC-RESEARCH`](SPEC-RESEARCH.md)
- [`SPEC-EVIDENCE`](SPEC-EVIDENCE.md)
- [`SPEC-STUDY`](SPEC-STUDY.md)
