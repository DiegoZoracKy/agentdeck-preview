# SPEC-RESEARCH v0.1.0: Research Constitution

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented — execution, derivation, Evidence, Finding, and flagship acceptance path
> Review State: approved
> Audience: Study authors, AgentDeck contributors, research-tooling implementers, reviewers

## 1. Purpose

Define the constitutional boundary that lets an AgentDeck user move from a
behavioral Question or Game to a traceable Finding without weakening canonical
execution truth.

AgentDeck exposes two linked contracts:

- **Execution contract:** what exactly happened?
- **Research contract:** what exactly supports this conclusion?

This spec defines their dependency direction, epistemic object graph, assurance
vocabulary, and cross-component invariants. Child specs define concrete Study,
Measure, Evidence, Finding, package, and CLI contracts.

## 2. Scope & Philosophy Alignment

- **Research is first-class:** AgentDeck MUST close the user journey from
  Question to Finding rather than stop at data export.
- **Execution truth is foundational:** Research MUST consume public execution
  contracts; the execution kernel MUST NOT import Research.
- **Separation:** Recorded facts, deterministic derivations, and authored
  interpretations MUST remain different artifacts.
- **Composition:** Study design references exact Prepared Assemblies; it MUST NOT
  reconstruct AgentDeck components.
- **Reproducibility:** Every derived value MUST identify the inputs, method, and
  materially relevant environment required to reproduce it.
- **Simplicity:** The framework MUST contain only concepts required by both the
  flagship and orthogonal acceptance Studies.

## 3. Responsibilities

SPEC-RESEARCH owns one responsibility: preserve the epistemic chain from
execution facts to authored conclusions.

It defines:

- the one-way dependency between Research and the execution kernel;
- the roles of Study, Condition, Run, Record, Measure, Evidence, and Finding;
- the boundary around stochastic/intelligent operations;
- deterministic derivation and identity requirements;
- mechanical validation versus authored/scientific review;
- citation granularity and lineage guarantees;
- fail-closed behavior for incomplete or unsupported derivations.

It does not define component APIs, statistical methods, report layouts, Game
semantics, or automatic experimental design.

## 4. Constitutional Object Graph

```text
Game
  -> Game Research Profile -> Research Opportunity / Operationalization
  -> Question / Study
  -> Conditions
  -> Prepared Assembly
  -> Runs
  -> canonical Records
  -> deterministic Measures
  -> Evidence
  -> authored Findings
```

### 4.1 Study

Aggregate root and durable identity of one investigation. Definition,
PreparedPlan, Runs, Evidence, Findings, and lineage remain separate versioned
artifacts navigable under that identity.

### 4.1a Game Research Profile

Independent Research-layer metadata explaining what one Game plausibly makes
observable, which exact Measures can currently be prepared, and what must not be
claimed. It aids discovery but never selects a Measure, creates a Study, or
duplicates execution authority.

### 4.2 Condition

Semantic assignment to an exact prepared experimental configuration or role.
A Condition MAY describe an intended treatment/control distinction, but MUST
reference execution already embodied by the Prepared Assembly.

### 4.3 Run and Record

A Run is concrete execution governed by AgentDeck's execution specs. A Record is
the canonical, immutable account of what happened. Research annotations and
derivations MUST NOT be written into canonical Records.

### 4.4 Measure

Deterministic, versioned transformation of an identified Record corpus. Measure
identity covers its implementation, parameters, and every dependency or
environment factor materially required to reproduce its output.

### 4.5 Evidence

Immutable binding from an identified corpus, Measure/method, Study scope, and
assumptions to reproducible derived values. Evidence does not inherit the
stronger execution-fact semantics of Records.

Evidence is a narrow machine-readable contract. CSV, Markdown, tables, plots,
dashboards, and narrative reports are representations of Evidence, not Evidence
fields.

### 4.6 Finding

Authored interpretation supported by granular Evidence result references.
Finding lifecycle and review metadata remain distinct; neither makes the claim
mechanically true.

## 5. Assurance Vocabulary

AgentDeck MUST present assurance by layer rather than collapse it into a generic
`verified` state.

| Layer | Permitted assurance | Explicitly not implied |
|---|---|---|
| Record | canonical execution artifact; schema/identity validated | complete or unbiased Study design |
| Measure | deterministic derivation reproduced from declared inputs | scientific validity of the chosen metric |
| Evidence | corpus/method/scope binding mechanically validated | causal or general scientific truth |
| Finding | citations resolve; authorship/review metadata present | correctness merely because validation passed |

Review metadata MUST identify reviewer, review type, scope, date, and notes.
Human, AI-assisted, and scientific/peer review MUST NOT share the assurance label
used for schema validation, hash matching, or citation resolution.

## 6. Invariants & Guarantees

1. **RE1 — One-way dependency:** Research MAY import public execution contracts;
   execution-kernel modules MUST NOT import Research.
2. **RE2 — Record immutability:** Research MUST NOT mutate, enrich, or overwrite
   canonical Records.
3. **RE3 — Observation boundary:** Every intelligence-mediated or externally
   non-deterministic operation that introduces an observation or judgment
   affecting Evidence MUST terminate in canonical Records before deterministic
   derivation begins. Deterministic analysis MAY use explicitly seeded
   algorithms when algorithm/version, seed, parameters, and material environment
   enter the derivation identity.
4. **RE4 — Deterministic derivation:** Given identical identified Records,
   Measure identity, parameters, and material environment, Evidence values MUST
   be identical.
5. **RE5 — No hidden inference:** A Measure MUST NOT call a model, judge, network,
   current time, or ambient mutable service.
6. **RE6 — Assembly authority:** Prepared Assembly is the sole authority for
   executable composition. Study and Condition MUST NOT duplicate an executable
   field as an independent authority.
7. **RE7 — Exact execution binding:** Study execution MUST bind to the exact
   PreparedAssembly identity inspected before execution.
8. **RE8 — Material environment identity:** Measure identity MUST include every
   library, algorithm version, runtime property, or declared external artifact
   whose variation can change a derived value.
9. **RE9 — Evidence identity:** Every Evidence result MUST identify Study scope,
   corpus/Record hashes, Measure identity, parameters, method, and material
   environment.
10. **RE10 — Narrow Evidence:** Reports and visualizations MUST reference
    Evidence; they MUST NOT become the canonical Evidence representation.
11. **RE11 — Granular support:** A Finding MUST cite the smallest stable Evidence
    result that supports each claim when an Evidence artifact contains multiple
    results.
12. **RE12 — Authored interpretation:** Evidence-to-Finding is explicitly
    authored. Mechanical validation MUST NOT certify natural-language truth.
13. **RE13 — Explicit unavailability:** Missing fields, unsupported Measures,
    incomplete Cells, ambiguous phase membership, or incompatible corpora MUST
    fail or produce an explicit unavailable result; they MUST NOT produce neutral
    fabricated values.
14. **RE14 — Phase isolation:** Preflight, pilot, Study, and supplemental Records
    MUST NOT enter another phase's Evidence silently.
15. **RE15 — Portable artifacts:** Research artifacts MUST NOT contain
    credentials resolved by AgentDeck, environment-variable values read by
    AgentDeck, fields designated credential-bearing by AgentDeck contracts, or
    machine-local absolute paths. Optional scanning cannot prove arbitrary
    authored content secret-free.
16. **RE16 — Immutable history:** Replay uses existing Records; reproduction,
    replication, and extension MUST create explicit identities and lineage rather
    than rewrite a historical Study.
17. **RE17 — No domain leakage:** Framework primitives MUST NOT encode concepts
    specific to an acceptance Study, including winner, opponent, side swap,
    health, strategy tier, or win rate.
18. **RE18 — Reasoning honesty:** Recorded reasoning is model output, not
    privileged access to hidden model thought.
19. **RE19 — Discovery is not authority:** a Game Research Profile MAY reference
    Questions and Measures, but only an explicit Study/analysis action controls
    execution and derivation.

## 7. Data Flow & Interaction

Standard derivation:

```text
Study -> PreparedAssembly -> AgentDeck execution -> Records
Records + Measure identity + material environment -> Evidence
Evidence result references -> authored Finding
```

Semantic/LLM evaluation:

```text
Source Records -> Judge Assembly -> Judge Records -> deterministic Measure -> Evidence
```

The judge's model, provider, prompt, parameters, retries, raw responses, costs,
and failures remain execution facts in Judge Records. They MUST NOT disappear
inside analysis code.

## 8. Error Handling & Edge Cases

- Changed PreparedAssembly identity: fail before Player construction/provider
  calls under `SPEC-ASSEMBLY`.
- Missing or changed source Record: reject the corpus/Evidence identity.
- Incomplete material environment: refuse reproducibility assurance and fail
  when the missing factor can change output.
- Unsupported or missing Measure input: emit explicit unavailable diagnostics;
  never coerce to zero, `1.0`, success, or an empty valid result.
- Invalid Finding locator: reject citation validation and identify the unresolved
  Evidence result.
- Partial Run/Cell: preserve emitted Records and diagnostics, but MUST NOT mark
  the Study or affected Evidence complete.
- Mixed incompatible Games/schemas: reject unless the Measure explicitly declares
  and validates support for each input contract.

## 9. Contract Examples

These examples describe cross-component guarantees; child specs provide runnable
API examples after their public contracts are approved.

### 9.1 Deterministic Measure

```text
corpus sha256:A + measure sha256:B + environment sha256:C
  -> evidence result potion_rate = 0.375
```

Repeating the same identified inputs MUST produce the same value.

### 9.2 LLM judge

```text
source corpus A -> judge Assembly J -> judge corpus K -> Measure M -> Evidence E
```

Calling the judge directly from `M` violates RE3 and RE5.

### 9.3 Granular Finding support

```yaml
claim: "Condition S1 improved the declared outcome over S0."
support:
  - evidence: fd-controller-effect
    result: estimates.win_rate_difference
```

The locator MUST resolve; citation validation does not certify the claim's
scientific interpretation.

## 10. Testing Strategy

| Contract | Required behavioral proof |
|---|---|
| RE1 | Import-boundary test: Core installs/tests without Research dependencies |
| RE2 | Hash canonical Records before/after full Research workflow |
| RE3–RE5 | Reject network/model/time access in Measure; Judge path emits Records; seeded analysis reproduces from its identified method |
| RE6–RE7 | Duplicate executable authority rejected; changed plan fails before calls |
| RE8–RE9 | Material dependency change changes identity or fails explicitly |
| RE10 | JSON Evidence remains stable across Markdown/CSV/plot rendering |
| RE11–RE12 | Granular locator resolves; mechanical validation never sets claim truth |
| RE13–RE14 | Missing data and phase mixing fail without fabricated fallback |
| RE15 | Absolute paths and AgentDeck-resolved/designated credential material rejected; optional scanning carries no completeness claim |
| RE16 | Reproduction/replication/extension preserve immutable parent lineage |
| RE17 | The Agentic Edge and orthogonal Study use the same framework primitives |
| RE18 | UI/report labels recorded reasoning without hidden-thought claims |
| RE19 | Profile discovery never executes a Game, creates a Study, or invokes a Measure |

Acceptance requires both:

- The Agentic Edge historical and current workflow;
- a single-Player, no-winner, two-information-Condition Study with a non-win-rate
  Measure and no framework exception.

## 11. Design Rationale

- **Deterministic Measures:** keeping observations and judgments before the
  Record boundary makes evaluators inspectable with the same execution
  guarantees as Players while allowing identified, explicitly seeded analysis.
- **Narrow Evidence:** one stable machine contract can support multiple UIs,
  reports, exports, and future consumers without becoming `results.json` 2.0.
- **Authored Findings:** AgentDeck helps any person finish the research journey
  while preserving the difference between traceability and truth.
- **Progressive child specs:** constitutional boundaries are fixed first; later
  APIs are specified only before the implementation wave they govern.

## 12. Open Questions / Future Work

- Define the minimum default material-environment manifest without pretending a
  full container image is required for every Measure.
- Define how human annotation becomes a provenance-carrying Record corpus.
- Define Evidence result locator syntax and stability in `SPEC-EVIDENCE`.
- Define review types and lineage in `SPEC-FINDING` without implementing peer
  review or social workflows in the first release.

## 13. References

- [`SPEC.md`](SPEC.md)
- [`SPEC-ASSEMBLY`](SPEC-ASSEMBLY.md)
- [`SPEC-GAME-RESEARCH-PROFILE`](SPEC-GAME-RESEARCH-PROFILE.md)
- [`SPEC-RECORDER`](SPEC-RECORDER.md)
- [`SPEC-REPLAY`](SPEC-REPLAY.md)
- [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- [The Agentic Edge](../research/2026-04-27-agentic-edge-strategy-stack/README.md)
