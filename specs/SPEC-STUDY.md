# SPEC-STUDY v0.2.0

> Status: Final
> Version: 0.2.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented — load, prepare, selection, execution, and receipts
> Review State: approved
> Audience: Study authors, AgentDeck users, Research-layer implementers

## 1. Purpose

Let a caller describe one behavioral investigation, bind its semantic design to
exact Prepared Assemblies without duplicating execution configuration, inspect
the complete plan without AgentDeck-initiated provider calls, and execute an
explicitly selected scope with durable lineage and receipts.

`Study` is AgentDeck's public Research aggregate. It connects a Question to
execution facts; it does not calculate Measures, Evidence, or Findings in this
version.

## 2. Scope & Philosophy Alignment

- Implements `SPEC-RESEARCH` RE1–RE7 and RE13–RE17.
- Uses `SPEC-ASSEMBLY` as the sole execution-composition authority.
- Keeps author intent separate from executable configuration.
- Fails before Player construction when a source, reference, or plan changes.
- Supports a small Study with one Assembly and a phased Study with several
  independently executable Assembly groups.
- Does not define statistics, Evidence values, reports, or claim semantics.

## 3. Terminology

- **StudyDefinition**: parsed authored Study intent and references.
- **ExecutionGroup**: one named PreparedAssembly executable as an atomic unit.
- **Phase**: epistemic stage assigned to one or more ExecutionGroups.
- **Cell**: one named observational/comparison unit mapped to one AssemblyRun.
- **Condition**: semantic label assigned to an exact prepared execution target.
  It MAY describe a Player/role, Game/environment treatment, information
  condition, tool policy, initial state, or another factor already embodied by
  the PreparedAssembly. It never defines or overrides that factor.
- **PreparedStudy**: canonical validated Study plan bound to exact
  PreparedAssembly identities.
- **StudySelection**: explicit set of ExecutionGroups authorized for one call.
- **StudyExecution**: receipt for executing a StudySelection.

## 4. Architecture

```text
study.yaml ---------------------> StudyDefinition
    |                                   |
    +-> Assembly entrypoints -----------+-> prepare_study()
                                                |
                                                v
                                          PreparedStudy
                                                |
                                  explicit StudySelection
                                                |
                                                v
                                  execute_prepared_study()
                                                |
                                                v
                                      AssemblyExecution(s)
                                                |
                                                v
                                       canonical Records
```

Research imports public Assembly contracts. Assembly and the execution kernel
MUST NOT import Study types.

Assembly entrypoints are trusted executable Python under `SPEC-ASSEMBLY` §6.
Study preparation scopes its no-call assurance to AgentDeck orchestration; it is
not a sandbox or a claim about arbitrary side effects in authored Python.

## 5. Authored Contract

`study.yaml` schema version `1` contains:

```yaml
schema_version: 1
study:
  id: information-grounding
  title: Information Grounding
  question: Does additional state information change the agent's action?
  intent: confirmatory
  hypotheses: [{id: h1, statement: Full information changes action rate.}]
execution_groups:
  - {id: preflight, phase: p0, entrypoint: assemblies/preflight.py}
  - {id: main, phase: p2, entrypoint: assemblies/main.py}
phases:
  - {id: p0, kind: preflight}
  - {id: p2, kind: study}
conditions:
  - {id: partial_information, description: Partial Game information.}
  - {id: full_information, description: Full Game information.}
cells:
  - id: partial
    execution_group: main
    assembly_run: partial
    assignments: [{condition: partial_information, target: {scope: run}}]
  - id: full
    execution_group: main
    assembly_run: full
    assignments: [{condition: full_information, target: {scope: run}}]
```

Required fields:

- `study.id`: portable lowercase identifier matching `[a-z0-9][a-z0-9._-]*`.
- `study.title`: non-empty human title.
- `study.question`: non-empty behavioral question.
- `study.intent`: `exploratory` or `confirmatory`.
- `execution_groups`: non-empty unique groups, each naming a Phase and an
  Assembly entrypoint.
- `phases`: non-empty unique phase definitions.
- `cells`: non-empty unique mappings to exact Assembly run names.

Optional fields:

- `study.hypotheses`: authored identifiers and statements; exploratory Studies
  MAY omit them.
- `conditions`: semantic labels used by Cell assignments.
- `lineage`: one parent Study identity plus relation `reproduction`,
  `replication`, or `extension`.
- `execution_groups[].artifacts`: paths passed unchanged to
  `prepare_assembly()`.

The manifest MUST NOT contain Game, Player, Controller, Renderer, Spectator,
model, provider, prompt, seed, match-count, or session configuration. Those
fields belong only to Assembly.

Assignment targets use this v0.1 grammar:

- `{scope: run}` assigns the Condition to the complete referenced AssemblyRun;
- `{scope: player, name: <player-name>}` assigns it to one exact Player role in
  that AssemblyRun.

Other target scopes MUST fail validation. A target identifies semantic scope;
it MUST NOT contain a configuration path, executable value, or override.

## 6. Data Structures

- `StudyDefinition`: schema/source, authored metadata, Phases,
  ExecutionGroups, Conditions, Cells, and optional lineage.
- `PreparedStudy`: normalized definition and hash, Research contract version,
  prepared groups, total matches, provider requirements, and `plan_sha256`.
- `StudySelection`: Study plan hash, ordered group ids, and
  `selection_sha256`.
- `StudyExecution`: plan/selection hashes, ordered group receipts, exact
  AssemblyRun/match-slot Record receipts, and completion state.
- `StudyExecutionError(RuntimeError)`: public `receipt_path: Path | None` for a
  failed or partial execution.

Serialized forms MUST use relative paths. Python receipt objects MAY expose
resolved `Path` values for caller convenience, but their portable serialization
MUST be relative to the declared output root.

## 7. Public API

```python
load_study(path: str | Path) -> StudyDefinition
prepare_study(path: str | Path) -> PreparedStudy
select_study(prepared, *, phase_ids=(), execution_group_ids=(), all_groups=False) -> StudySelection
execute_prepared_study(path, prepared, selection, *, output_root) -> StudyExecution
```

- `load_study` MUST parse and structurally validate YAML without importing an
  Assembly entrypoint.
- `prepare_study` MUST load every declared Assembly through
  `prepare_assembly()`. AgentDeck orchestration MUST NOT construct Players,
  resolve credentials, or invoke providers during preparation.
- `select_study` MUST require exactly one selection mode: phases, groups, or
  `all_groups=True`. Empty or mixed modes MUST fail.
- Phase selection MUST resolve to complete ExecutionGroups. This version does
  not execute an individual AssemblyRun inside a group.
- `execute_prepared_study` MUST reprepare the complete Study, compare
  `plan_sha256`, validate `selection_sha256`, then call
  `execute_prepared_assembly()` once per selected group in canonical manifest
  order.
- Successful execution returns `StudyExecution(complete=True)`. A failed or
  partial execution MUST raise `StudyExecutionError` carrying the durable
  incomplete receipt path when one could be written.

## 8. Invariants & Guarantees

1. **ST1 — One authority:** authored Study fields MUST NOT duplicate executable
   Assembly configuration.
2. **ST2 — Scoped preparation safety:** AgentDeck orchestration MUST NOT
   construct a Player, resolve credentials, or invoke a provider during loading
   and preparation. Trusted authored Python remains outside this assurance.
3. **ST3 — Canonical identity:** equal normalized Study content plus equal
   PreparedAssembly identities MUST produce the same `plan_sha256`.
4. **ST4 — Source coverage:** `plan_sha256` MUST cover `study.yaml`, every
   PreparedAssembly plan identity, Research contract version, and lineage.
5. **ST5 — Reference integrity:** every ExecutionGroup references one declared
   Phase; every Cell references one declared group and one run present in that
   group's PreparedAssembly.
6. **ST6 — Complete run mapping:** every AssemblyRun MUST map to exactly one Cell
   in this version; unreferenced and multiply referenced runs MUST fail.
7. **ST7 — Phase consistency:** every Cell in one ExecutionGroup inherits that
   group's Phase; a group MUST NOT span phases.
8. **ST8 — Semantic Conditions:** Conditions and assignments describe intent;
   they MUST NOT alter or override PreparedAssembly values.
9. **ST9 — Explicit selection:** no execution occurs without one non-empty
   StudySelection bound to the exact plan identity.
10. **ST10 — Exact execution:** a changed Study or Assembly identity MUST fail
    before Player construction; selected groups execute only through
    `execute_prepared_assembly()`.
11. **ST11 — Phase semantics:** `preflight` cannot support Findings; `pilot` is
    excluded from confirmatory Evidence by default; `supplemental` remains
    separately scoped unless a new Study revision declares otherwise.
12. **ST12 — Immutable lineage:** reproduction, replication, and extension MUST
    create a new Study identity and MUST NOT overwrite the parent.
13. **ST13 — Portable paths:** authored and serialized paths MUST remain inside
    the Study package or output root and MUST never contain machine-local
    absolute paths.
14. **ST14 — Partial honesty:** a failed selected group preserves prior Records
    and diagnostics, marks `complete=False`, and MUST NOT represent unexecuted
    groups as complete.
15. **ST15 — No domain leakage:** Study primitives MUST NOT assume winners,
    opponents, side swaps, health, strategy tiers, or win rates.
16. **ST16 — Fixed planned execution:** each PreparedAssembly defines the
    complete v0.1 execution count and scheduling policy for its Cells. A selected
    ExecutionGroup either completes that prepared scope or remains incomplete.
    Study orchestration MUST NOT stop early, reduce, increase, or reinterpret the
    prepared scope and still report it complete.
17. **ST17 — Deep plan immutability:** every value reachable from a
    `PreparedStudy` MUST either be immutable or be returned as a detached copy.
    Its serialized representation MUST NOT change while `plan_sha256` remains
    unchanged.
18. **ST18 — Exact Record binding:** every group receipt MUST preserve the Core
    binding `Record -> AssemblyRun -> match slot -> effective seed`; Study adds
    `ExecutionGroup -> Phase -> Cell` semantics without reconstructing the
    binding from paths, filenames, counts, or directory layout.

## 9. Data Flow & Interaction

- **Load:** YAML -> structural validation -> `StudyDefinition`.
- **Prepare:** Definition -> prepare each Assembly -> validate phase/cell/run
  references -> canonical plan -> `PreparedStudy`.
- **Select:** PreparedStudy + exactly one selector -> canonical ordered group set
  -> `StudySelection`.
- **Execute:** reprepare -> compare plan/selection -> execute selected groups ->
  preserve group receipts and Records -> `StudyExecution`.
- **Research continuation:** later Measure/Evidence specs consume the immutable
  PreparedStudy, StudyExecution, and Record corpus; they do not modify them.

## 10. Error Handling

| Condition | Required outcome |
|---|---|
| Missing/invalid YAML or schema version | `ValueError` naming source and field |
| Duplicate identifier | `ValueError` naming kind and identifier |
| Executable field in manifest | `ValueError` naming forbidden field |
| Missing Phase/group/run/Condition reference | `ValueError` with reference path |
| Assembly import/preparation failure | propagate with ExecutionGroup context |
| Empty or mixed selection modes | `ValueError` before execution |
| Plan or selection identity mismatch | `ValueError` before Player construction |
| Execution failure | raise `StudyExecutionError`; preserve emitted Records and receipt location |
| Output path escaping root | `ValueError` before filesystem mutation |

Validation errors MUST distinguish authored Study failures from Assembly
failures. No error handler may substitute an empty valid Study or neutral value.

## 11. Contract Examples

### Small Study

One `execution_group` may reference `assembly.py`, one Phase, and one Cell. The
same contracts must work without matrices, opponents, or winners.

### Phased Study

The Agentic Edge may declare separate `preflight`, `pilot`, `main`, and
`supplemental` ExecutionGroups. `select_study(..., phase_ids=["p0"])` executes
only complete Assemblies assigned to P0; it cannot silently include P1/P2/P3.

### Invalid duplicate authority

```yaml
cells:
  - id: full
    assembly_run: full
    model: gpt-example       # invalid: executable configuration belongs to Assembly
```

Preparation MUST reject this before importing or executing Players.

## 12. Testing Strategy

| Invariants | Behavioral proof |
|---|---|
| ST1, ST8 | Forbidden executable fields fail; semantic assignments do not change Assembly |
| ST2 | AgentDeck PlayerFactory counters, credential resolvers, and provider spies remain untouched during prepare; trusted-source boundary is explicit |
| ST3–ST4 | equal inputs hash equally; source/Assembly/lineage changes alter identity |
| ST5–ST7 | missing, duplicate, unreferenced, cross-phase mappings fail |
| ST9–ST10 | empty/mixed/stale selection fails before Player construction |
| ST11 | preflight/pilot/supplemental scope remains explicit in receipts |
| ST12–ST14 | lineage creates new identity; paths portable; partial failure honest |
| ST15 | Agentic Edge and orthogonal Study share identical framework types |
| ST16 | early, reduced, or expanded group execution remains incomplete; exact prepared scope completes |
| ST17 | nested mutation attempts cannot alter the representation bound to a prepared plan hash |

Acceptance requires one no-provider vertical slice through load, prepare,
select, execute, and canonical Records for both a competitive and a
single-Player/no-winner fixture.

## 13. Design Rationale

- **ExecutionGroups:** current `execute_prepared_assembly()` executes one sealed
  Assembly atomically. Named groups provide phase-level authorization without a
  second runtime or speculative Core selection API.
- **Complete run mapping:** Cells remain traceable to exact execution units while
  the Assembly owns their configuration and match counts.
- **Explicit selection:** makes provider scope legible and prevents a bare Study
  path from accidentally authorizing every phase.
- **No Measures yet:** progressive specification prevents the Study contract
  from guessing the analysis API before `SPEC-MEASURE` and `SPEC-EVIDENCE`.

## 14. Non-Goals / Future Work

- selection of individual AssemblyRuns inside one ExecutionGroup;
- natural-language Study generation;
- adaptive/sequential sampling;
- budget enforcement or provider price prediction;
- Measures, Evidence, Findings, reports, peer review, or collaboration;
- sandboxing hostile Assembly Python.

## 15. References

- `SPEC-RESEARCH` §4–§10
- `SPEC-ASSEMBLY` §3–§8
- `SPEC-RECORDER` canonical Record contract
- [`SPEC-STUDY-PACKAGE`](SPEC-STUDY-PACKAGE.md)
- [`SPEC-STUDY-CLI`](SPEC-STUDY-CLI.md)

### Partial receipt loading

An incomplete StudyExecution MAY contain an ordered prefix of the selected execution_group_ids, including no attempted group. The loader MUST accept that representation without fabricating unattempted groups. It MUST reject duplicate, reordered, skipped or foreign group identifiers. A complete StudyExecution MUST contain every selected group in order and every group MUST be complete. Only the final attempted group may be incomplete.
