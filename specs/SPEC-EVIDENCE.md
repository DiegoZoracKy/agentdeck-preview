# SPEC-EVIDENCE v0.1.0

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented
> Review State: approved by maintainer for the Research-axis wave
> Audience: AgentDeck users, Study authors, artifact consumers, Research implementers

## 1. Purpose

Turn a deterministic MeasureOutput into a durable Evidence artifact by binding it
to an exact Record corpus, Study scope, Measure identity, material environment,
authored assumptions, and mechanical derivation state.

Evidence answers: "what do these exact Records support under this declared
Measure and Study scope?" It is not an execution Record, report, Finding,
eligibility decision, or certificate of scientific truth.

## 2. Scope & Philosophy Alignment

- Implements `SPEC-RESEARCH` RE2–RE4 and RE8–RE17.
- Makes corpus membership and completeness explicit before analysis.
- Keeps RecordCorpus independent from any Measure.
- Distinguishes current Study execution provenance from authored import binding.
- Separates Measure-authored output from AgentDeck-owned Evidence provenance.
- Preserves immutable original Records and historical sources.
- Provides granular stable result locators for later Findings and UI navigation.
- Does not define Finding eligibility, narrative reports, peer review, remote
  publication, legacy Record migration, or a universal statistics schema.

## 3. Terminology

- **CorpusOrigin**: provenance of the Record bytes: a current StudyExecution or
  an explicitly pinned imported source.
- **CorpusBinding**: exact current Study/Cell semantics under which those Records
  will be analyzed.
- **CorpusRecord**: immutable current-schema Record plus its origin and exact
  semantic CorpusBinding.
- **RecordCorpus**: canonical ordered manifest of CorpusRecords selected by
  explicit Cells, independent of any Measure.
- **Corpus completeness**: exact agreement between expected and present Records
  for every selected Cell under the current CorpusBinding.
- **EvidenceResult**: validated copy of one MeasureResult under Evidence
  provenance.
- **Evidence locator**: stable pair of Evidence hash and result hash.
- **Derivation status**: whether deterministic Evidence derivation completed or
  remained unavailable; not a scientific judgment.

## 4. Architecture

```text
completed StudyExecution ---------+
                                  +-> build_record_corpus() -> RecordCorpus
pinned imported corpus manifest --+                            |
                                                               +-> Measure A
                                                               +-> Measure B

PreparedMeasure + RecordCorpus -> evaluate_measure() -> MeasureOutput
        |                 |                |
        +-----------------+----------------+
                          v
             bind scope + assumptions + validate
                          |
                          v
                 immutable Evidence
```

Measure code cannot author Study, corpus origin, completeness, environment, or
Evidence provenance. AgentDeck constructs that envelope from PreparedStudy,
RecordCorpus, PreparedMeasure, authored assumptions, and validated MeasureOutput
identities.

## 5. Record Corpus Contract

### 5.1 Corpus origin and binding

One corpus uses exactly one origin kind:

- `study_execution`: one or more exact, non-overlapping StudyExecution receipts
  for the same PreparedStudy plan;
- `imported`: explicit portable manifest with logical source id, pinned revision,
  current-schema Record paths and SHA-256 values, original protocol/plan identity
  when known, and authored mappings to the current Study Cells.

A `study_execution` origin is admissible only when receipts map every Record
through `ExecutionGroup -> AssemblyRun -> match slot/ordinal -> effective seed`
to the Cell that the PreparedStudy assigns to that run. A flat ordered Record
list, directory-name convention, expected-count slicing, or path inference is
insufficient. Multiple receipts MUST name the same Study plan, MUST NOT select
the same ExecutionGroup twice, and are canonically ordered by Study group order.

An `imported` origin MUST NOT claim that its Records were produced by the current
PreparedStudy or current Assembly identities. It preserves original source
provenance separately and labels the current `Record -> Cell` mapping as authored
import binding. Original plan, protocol, model, and revision identities are
retained when available; unknown values remain explicitly unknown.

Filesystem globs, "latest" directories, mutable URLs, batch summaries, and
filename inference MUST NOT define corpus membership.

Imported provenance is trusted authored metadata whose Record bytes are still
verified mechanically. Unsupported historical schemas require a separately
specified deterministic adapter; v0.1 MUST NOT rewrite originals or silently
normalize them during Evidence construction.

### 5.2 CorpusRecord

Each entry contains:

- exact Record artifact SHA-256;
- Record schema version and `match_id`;
- portable Record path relative to the declared source root;
- current Study id and plan SHA-256;
- phase id/kind, ExecutionGroup id, AssemblyRun name, match slot/ordinal,
  effective seed, and Cell id;
- binding authority: `execution_receipt` or `authored_import_manifest`.

The path resolves bytes but does not define content identity. Entries are
canonically ordered by Study Cell order and Record SHA-256. Duplicate hashes,
duplicate `match_id` values, unassigned Records, and one Record assigned to more
than one Cell MUST fail.

### 5.3 RecordCorpus

Portable serialization contains:

```json
{
  "schema_version": 1,
  "study_binding": {
    "study_id": "information-grounding",
    "plan_sha256": "...",
    "cells": ["partial", "full"]
  },
  "origin": {
    "kind": "study_execution",
    "identity_sha256": "..."
  },
  "expected_records": {"partial": 20, "full": 20},
  "records": [],
  "complete": true,
  "corpus_sha256": "..."
}
```

For an imported corpus, `origin` additionally records the logical source id,
pinned revision, original identities when known, and import-manifest hash.

`corpus_sha256` covers origin identity, current Study binding, selected Cells,
expected counts, binding authority, Record schema/match ids, and Record hashes.
It excludes Measure identity, assumptions, host source-root path, and timestamps.

The Python object exposes deeply immutable Record payloads loaded through the
current Recorder contract. It MUST NOT expose batch aggregate statistics as
substitutes for canonical Match Records.

## 6. Evidence Contract

Canonical Evidence contains only:

- schema and Research contract versions;
- current Study id, plan hash, intent, selected Cell ids, and phase ids/kinds;
- corpus origin kind/identity and binding-authority summary;
- corpus hash, Record count, expected count, and completeness;
- Measure id, Measure hash, parameters, implementation identity, and declared
  material-environment hash;
- authored assumptions, explicitly labeled as assumptions;
- derivation status: `complete` or `unavailable`;
- flat EvidenceResults copied from validated MeasureOutput;
- mechanical diagnostics;
- final `evidence_sha256`.

It MUST NOT contain raw Records, unrestricted narrative, chart configuration,
Markdown, Finding text/status/eligibility, reviewer approval, `is_actionable`, or
a generic `scientifically_valid` flag.

`study.intent=confirmatory` describes authored Study intent. It does not prove
that the Measure, Cell selection, assumptions, or analysis method were fixed
before execution. V0.1 Evidence MUST make no pre-registration claim without a
future protocol artifact that was sealed before the relevant Records existed.

### EvidenceResult

An EvidenceResult preserves the MeasureResult metric, dimensions, availability,
value, unit, support, optional SourceLocators, and `result_sha256`. It adds no
interpretation.

Stable locator:

```text
sha256:<evidence_sha256>#result=sha256:<result_sha256>
```

A future Finding contract resolves both hashes and the exact result. This spec
does not decide whether a result is suitable for any Finding.

### Derivation status

- `complete`: the corpus is complete and Measure evaluation returned a valid
  canonical MeasureOutput. Individual MeasureResults MAY still be explicitly
  unavailable.
- `unavailable`: the corpus is incomplete or another anticipated condition
  prevented Measure evaluation. No result is silently treated as available.

An incomplete corpus MUST NOT invoke the Measure in v0.1. AgentDeck creates an
unavailable Evidence artifact with exact missing-count diagnostics.

Invalid custom Measure output is a contract failure, not Evidence. AgentDeck
MUST reject it and MUST NOT seal an artifact that could be mistaken for a valid
derivation.

Phase kinds, Study intent, completeness, result availability, and diagnostics
remain explicit inputs for a future Finding policy. Evidence MUST NOT collapse
them into a global eligibility bit.

## 7. Public API

```python
build_record_corpus(
    study: PreparedStudy,
    *,
    cell_ids: Sequence[str],
    study_executions: Sequence[StudyExecution] = (),
    imported_manifest: str | Path | None = None,
) -> RecordCorpus

derive_evidence(
    study: PreparedStudy,
    measure: PreparedMeasure,
    corpus: RecordCorpus,
    *,
    assumptions: Sequence[str] = (),
) -> Evidence
```

### `build_record_corpus`

- MUST require exactly one origin kind.
- For current execution, MUST accept one or more disjoint receipts for the same
  exact Study plan so independently authorized ExecutionGroups can form one
  corpus without being relabeled as external data.
- MUST require a non-empty explicit Cell selection in canonical Study order.
- MUST load and hash every Record, validate current schema, resolve semantic
  bindings, compare expected counts, and canonicalize order.
- MUST distinguish execution-receipt binding from authored import binding.
- MUST perform no provider/model/network calls and never mutate source Records.

### `derive_evidence`

- MUST validate exact Study binding, corpus, and Measure identity.
- MUST record authored assumptions without including them in Measure identity.
- MUST refuse Measure invocation for an incomplete corpus.
- MUST call `evaluate_measure()` once when admissible, validate MeasureOutput,
  construct the authoritative Evidence envelope, and seal its hash.
- MUST write no Finding, eligibility decision, or narrative report.

Canonical Evidence MUST be self-validatable from its identified artifacts. The
exact stable standalone validation API and CLI surface are deferred to the
package/CLI specification rather than frozen prematurely in this contract.
Structural identity validation, derivation reproduction, and scientific review
MUST remain distinct operations and vocabulary.

## 8. Identity, Portability, and Representation

Canonical JSON uses UTF-8, sorted keys, compact separators, and rejects
NaN/Infinity. Evidence identity covers every canonical field in §6 except output
path and non-canonical host metadata.

Corpus, PreparedMeasure, MeasureOutput, and Evidence remain separate immutable
artifacts. CSV, Markdown, plots, tables, and later reports are derived
representations that cite Evidence identity.

The exact filesystem layout, directory naming, and write transaction belong to
`SPEC-STUDY-PACKAGE` and its future analysis-output revision. This spec requires
only that serialization remain portable and that existing canonical artifacts
never be overwritten.

## 9. Invariants & Guarantees

1. **EV1 — Exact membership:** every corpus Record is named explicitly by hash
   and semantic Cell binding; no implicit discovery controls inclusion.
2. **EV2 — Record integrity:** Record bytes MUST match their declared SHA-256 and
   current Recorder schema before Measure invocation.
3. **EV3 — Scope integrity:** every Record belongs to exactly one selected Cell
   under the current Study binding; unassigned, inferred, duplicate, or
   out-of-scope Records fail.
4. **EV4 — Completeness honesty:** observed counts MUST equal prepared expected
   counts for every Cell before Measure invocation and complete derivation.
5. **EV5 — Explicit phase scope:** every Cell's phase id/kind remains explicit.
   Corpora MUST NOT silently mix phases; any multi-phase selection is authored
   and preserved without an Evidence-level eligibility decision.
6. **EV6 — Immutable sources:** corpus construction, derivation, validation, and
   representation MUST NOT modify canonical or imported source Records.
7. **EV7 — Authoritative envelope:** Measure code supplies results only;
   AgentDeck derives Study binding, origin, completeness, phase, environment,
   derivation status, and Evidence identities from authoritative inputs.
8. **EV8 — Deterministic Evidence:** identical Study binding, corpus,
   PreparedMeasure, MeasureOutput, assumptions, and environment MUST produce
   byte-equivalent canonical Evidence.
9. **EV9 — Honest traceability:** every EvidenceResult identifies exact corpus
   and Measure provenance. Any optional SourceLocator MUST resolve, but does not
   certify exhaustive field-level support.
10. **EV10 — Explicit unavailability:** incomplete corpus, missing input,
    unsupported schema, unavailable result, or failed anticipated derivation
    MUST remain named; no neutral or empty available result is permitted.
11. **EV11 — Narrow artifact:** Evidence values remain flat and addressable;
    reports, plots, raw Record copies, and unrestricted authored claims stay out.
12. **EV12 — Granular citation:** each EvidenceResult has a stable locator;
    future Findings can cite results without ambiguous artifact-level prose.
13. **EV13 — Mechanical assurance only:** schema/hash/citation validation and
    derivation reproduction MUST NOT imply scientific validity or causal truth.
14. **EV14 — Portable identity:** relocation with identical logical origin,
    bytes, bindings, Measure, assumptions, and environment preserves
    corpus/Evidence identity.
15. **EV15 — Immutable history:** a new derivation, reproduction, replication, or
    extension creates new artifacts and never rewrites previous Evidence.
16. **EV16 — No domain leakage:** Evidence has no winner, opponent, position,
    action, health, strategy-tier, or win-rate field.
17. **EV17 — Measure-independent corpus:** changing or adding a Measure MUST NOT
    change corpus identity.
18. **EV18 — Honest imported provenance:** imported Records MUST NOT be
    represented as outputs of the current StudyExecution or current Assembly.
19. **EV19 — No registration inference:** Study intent, artifact timestamps, or
    current Measure identity MUST NOT be represented as proof that analysis was
    pre-registered.
20. **EV20 — Exact execution slots:** current-execution corpus membership MUST
    validate each planned match slot and effective seed from authoritative
    receipts; equal counts alone never prove completeness.
21. **EV21 — Disjoint receipt composition:** multiple current StudyExecution
    receipts MAY compose one corpus only when their plan identities match and
    their selected ExecutionGroups do not overlap.

## 10. Data Flow & Interaction

Current execution:

```text
StudyExecution receipts + canonical Records
  -> explicit Cell selection
  -> RecordCorpus(origin=study_execution)
  -> PreparedMeasure
  -> MeasureOutput
  -> Evidence
```

Historical analysis:

```text
pinned imported manifest + immutable current-schema Records
  -> preserve original provenance + author current Study binding
  -> RecordCorpus(origin=imported)
  -> PreparedMeasure
  -> MeasureOutput
  -> new Evidence artifact
```

The historical source and any previously authored analysis remain unchanged.
New Evidence is a derived descendant, not a replacement and not a claim that the
current Study execution produced historical Records.

## 11. Error Handling & Edge Cases

| Condition | Required outcome |
|---|---|
| Both/neither corpus origins supplied | fail before reading Records |
| Empty/unknown Cell selection | fail before reading Records |
| Glob/latest/mutable source requested | reject as non-explicit corpus |
| Record hash/schema mismatch | fail corpus construction with exact entry |
| Duplicate hash or match id | fail rather than double count |
| Missing/out-of-scope Cell binding | fail with Record and expected Cell |
| Imported Record presented as current execution output | reject provenance |
| Record-count mismatch | create unavailable Evidence; do not invoke Measure |
| Stale Study/Measure/corpus identity | fail before Measure invocation |
| Invalid MeasureOutput or locator | fail derivation; seal no Evidence |
| Representation generation fails | retain canonical Evidence unchanged |
| Existing canonical artifact target | fail; never overwrite |

## 12. Contract Examples

### Complete no-winner corpus

Twenty `partial` and twenty `full` Records match their prepared counts. The same
corpus is evaluated by action-rate and cost Measures without changing
`corpus_sha256`. Evidence is complete without a winner or ranking field.

### Partial execution

Thirty-nine of forty Records exist. Evidence has
`derivation_status=unavailable`, includes `corpus.record_count_mismatch`, and the
Measure is not invoked.

### Historical Agentic Edge corpus

The import manifest pins the Hugging Face revision and Record hashes, preserves
the original Study/protocol identities where present, and authors explicit
mappings to current Cells. The resulting corpus declares `origin=imported`; it
does not claim a current StudyExecution produced those Records.

### Preflight Evidence

A complete preflight corpus may produce mechanically complete artifact-integrity
Evidence. The Evidence preserves `phase.kind=preflight`; a future Finding spec,
not this artifact, decides whether and how it may be cited.

## 13. Testing Strategy

| Invariants | Behavioral proof |
|---|---|
| EV1–EV3 | explicit membership/bindings required; glob, duplicate, and foreign Record fail |
| EV4, EV10 | missing/extra Record creates unavailable Evidence and leaves Measure spy untouched |
| EV5 | phase kinds remain explicit; hidden mixing fails and authored mixing is preserved |
| EV6, EV15 | hash source before/after; new analysis cannot overwrite prior artifacts |
| EV7–EV8 | output cannot set provenance; equal inputs produce byte-equivalent Evidence |
| EV9, EV12 | declared source and result locators resolve; changed pointer/hash fails |
| EV11 | nested result maps and report/claim fields rejected |
| EV13 | structural validation, reproduction, and scientific review remain separate |
| EV14 | relocate corpus source and representation roots; identities remain equal |
| EV16 | competitive and no-winner fixtures use identical Evidence types |
| EV17 | two Measures reuse byte-identical corpus identity |
| EV18 | imported and current-execution provenance remain distinguishable |
| EV19 | confirmatory Study intent produces no pre-registration assurance |
| EV20 | missing, duplicated, or seed-mismatched match slot fails even when counts match |
| EV21 | disjoint same-plan receipts compose; overlapping or foreign-plan receipts fail |

Acceptance requires:

- regenerate selected The Agentic Edge outcome, position, cost, format, and
  artifact-integrity values from an explicit hashed imported fixture corpus;
- surface VariableDamage uncertainty/seat-confounding as explicit results or
  diagnostics without an automatic claim;
- derive one non-win-rate Evidence artifact from the single-Player/no-winner
  fixture;
- preserve corpus identity while applying two different Measures;
- resolve every accepted Evidence result to its exact corpus and Measure, plus
  exact Record fields when SourceLocators are declared;
- preserve pinned historical source artifacts byte-for-byte.

## 14. Design Rationale

- **Corpus before Measure:** prevents directory layout, stale files, and implicit
  globs from silently changing N or phase membership.
- **Measure-independent corpus:** one identified observational base can support
  multiple transparent derivations without duplicating or relabeling Records.
- **Origin separate from binding:** enables historical analysis without claiming
  that old Records came from current code or current execution plans.
- **AgentDeck-owned envelope:** custom Measure code cannot self-certify corpus
  completeness, environment, or Evidence identity.
- **No Evidence eligibility:** phase and completeness remain facts; the Finding
  contract owns the future policy for interpreting citation suitability.
- **Unavailable incomplete corpus:** the first release favors epistemic honesty
  over convenient partial aggregates; descriptive partial analysis can be
  specified later if demanded.
- **Current schema only:** avoids hiding Record conversion inside analysis and
  preserves immutable historical originals.
- **Flat Evidence:** keeps one stable machine contract underneath multiple future
  representations and Findings.

## 15. Non-Goals / Future Work

- Finding citation eligibility or lifecycle;
- exact analysis-output directory layout or CLI validation surface;
- legacy Record adapters or in-place migration;
- partial/descriptive Evidence from incomplete Cells;
- cross-Study meta-analysis;
- Measure composition;
- remote corpus resolution, caching, upload, or Hugging Face mutation;
- signing, attestations, or hostile-source sandboxing;
- report/plot/CSV schema;
- review workflows or causal inference guarantees;
- pre-registration/protocol artifacts and related assurance.

## 16. References

- `SPEC-RESEARCH` §4–§10
- `SPEC-STUDY` Phase, Cell, execution, and completion contracts
- `SPEC-STUDY-PACKAGE` immutable output boundary
- `SPEC-RECORDER` canonical Record schema
- [`SPEC-MEASURE`](SPEC-MEASURE.md)
- [The Agentic Edge](../research/2026-04-27-agentic-edge-strategy-stack/README.md)
