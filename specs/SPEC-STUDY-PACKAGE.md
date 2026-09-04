# SPEC-STUDY-PACKAGE v0.2.0

> Status: Final
> Version: 0.2.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented — authored, execution, derivation, and report boundaries
> Review State: approved
> Audience: Study authors, artifact consumers, AgentDeck contributors

## 1. Purpose

Define a portable, inspectable directory contract for authored Studies and
their execution outputs so a caller can prepare, execute, archive, and transfer
a Study without hidden files, machine-local paths, or mutation of historical
artifacts.

## 2. Scope & Philosophy Alignment

- Implements `SPEC-RESEARCH` RE2, RE7, RE15, and RE16.
- Stores Study intent separately from PreparedAssembly execution truth.
- Keeps authored source immutable during execution.
- Uses explicit manifests, checksums, and relative paths.
- Does not define the internal schema of future Measure, Evidence, Finding, or
  report artifacts.

## 3. Package Layout

Minimal authored package:

```text
my-study/
|-- study.yaml
`-- assembly.py
```

Phased package:

```text
my-study/
|-- study.yaml
|-- assemblies/
|   |-- preflight.py
|   |-- main.py
|   |-- common.py
|   `-- artifacts/
|       `-- prompt.txt
`-- README.md
```

Execution output is separate from authored source:

```text
<output-root>/
`-- <study-id>/
    `-- <execution-id>/
        |-- prepared-study.json
        |-- selection.json
        |-- execution.json
        `-- execution-groups/
            `-- <group-id>/
                |-- prepared-assembly.json
                |-- execution.json
                `-- assembly-output/
                    `-- ... canonical Assembly output ...
```

Research derivation output uses a separate immutable analysis directory:

```text
<output-root>/<study-id>/<analysis-id>/
|-- prepared-study.json
|-- corpus.json
|-- analysis.json
|-- measures/<measure-id>.json
`-- evidence/<measure-id>.json
```

Finding output contains canonical Finding JSON plus a deterministic Markdown
projection. Neither flow alters canonical Records or execution receipts.

## 4. Authored Package Contract

- `study.yaml` is REQUIRED and follows `SPEC-STUDY` §5.
- Every Assembly entrypoint path MUST be relative to the package root, resolve
  inside it, and exist as a regular file.
- Each Assembly artifact path is relative to that entrypoint's directory, as
  required by `SPEC-ASSEMBLY`, and MUST resolve inside the same directory.
- A simple package MAY place `assembly.py` at the root.
- A package with several ExecutionGroups SHOULD use `assemblies/`.
- `artifacts/` MAY contain prompt templates, data, or source assets explicitly
  declared by an ExecutionGroup. For a nested entrypoint it lives under the
  entrypoint directory; shared entrypoints MAY use a common parent directory.
- Credentials, local run outputs, virtual environments, caches, and secrets MUST
  NOT be authored package content.
- Preparation and execution MUST NOT create interpreter or tool caches such as
  `__pycache__` or `.pyc` files inside the authored package; they are generated
  source mutations under SP1.
- Historical external corpora MAY be referenced later by an approved Evidence
  spec; they are not implicit Study inputs in this version.

The package is trusted executable source because Assembly entrypoints are Python.
Portability and content identity do not imply hostile-code sandboxing.

## 5. Output Artifacts

### `prepared-study.json`

Canonical serialization of `PreparedStudy`. It MUST include:

- schema and Research contract versions;
- normalized Study definition;
- authored definition hash;
- each ExecutionGroup id, Phase, entrypoint, and PreparedAssembly identity;
- total matches and provider/model requirements;
- final Study plan hash.

### `selection.json`

Canonical serialization of `StudySelection`. It MUST include:

- Study plan hash;
- ordered selected ExecutionGroup ids;
- selection hash;
- creation timestamp only outside the hashed canonical payload.

### Root `execution.json`

Portable `StudyExecution` receipt. It MUST include:

- Study and selection hashes;
- execution id and status (`complete` or `failed`);
- group receipts in canonical order;
- relative Record paths;
- accumulated usage reported by Assembly executions;
- failure summary when incomplete.

### Group artifacts

- `prepared-assembly.json`: exact PreparedAssembly passed to Core.
- `execution.json`: group status, plan hash, relative Record paths, authoritative
  usage, exact AssemblyRun/match-slot/effective-seed receipts, and failure
  summary.
- `assembly-output/`: output root passed to `execute_prepared_assembly()`.

Serialized receipts MUST NOT claim a group completed until its
`AssemblyExecution` returns successfully with the expected Record count.

## 6. Identity and Serialization

1. JSON canonical identity uses UTF-8, sorted object keys, compact separators,
   and disallows NaN/Infinity.
2. `execution-id` MUST be unique but MUST NOT enter Study or selection identity.
3. Timestamps, hostnames, absolute paths, and local usernames MUST NOT enter
   Study, Assembly, or selection hashes.
4. Paths in JSON MUST be POSIX-style and relative to the package or execution
   root named by the containing artifact.
5. Checksums MUST use SHA-256 and lowercase hexadecimal.
6. Authored source MUST never be rewritten with generated facts or statuses.

## 7. Invariants & Guarantees

1. **SP1 — Source/output separation:** execution MUST NOT create or update files
   inside the authored Study package.
2. **SP2 — Portable source:** every declared authored path resolves inside the
   package root and serializes relatively.
3. **SP3 — Portable output:** every serialized generated path resolves inside
   its execution root and serializes relatively.
4. **SP4 — Atomic plan artifacts:** `prepared-study.json` and `selection.json`
   MUST be durably written before Player construction.
5. **SP5 — Failure preservation:** a failed execution retains prepared plans,
   selection, already emitted Records, and an incomplete receipt.
6. **SP6 — No false completion:** missing group receipts or Record-count
   mismatches MUST prevent root `status=complete`.
7. **SP7 — Immutable history:** a new execution creates a new execution
   directory; it MUST NOT reuse or overwrite an existing one.
8. **SP8 — Credential boundary:** portable artifacts MUST NOT serialize
   credentials resolved by AgentDeck, environment-variable values read by
   AgentDeck, or fields designated credential-bearing by AgentDeck component
   contracts. Optional secret scanning is defense-in-depth and MUST NOT be
   represented as proof that arbitrary authored content contains no secret.
9. **SP9 — Stable identity:** copying an authored package to another directory
   MUST preserve its PreparedStudy identity when file contents and declared
   dependencies are unchanged.
10. **SP10 — Representation boundary:** future CSV, Markdown, plots, and reports
    MUST reference canonical machine artifacts rather than replace them.
11. **SP11 — Exact slot receipts:** execution artifacts MUST preserve exact
    AssemblyRun, zero-based match slot, effective seed, Match id, Record hash,
    and relative path for each emitted canonical Record.

## 8. Data Flow & Interaction

```text
authored package
  -> load/prepare without source mutation
  -> create unique execution directory
  -> write prepared-study.json + selection.json
  -> execute each selected PreparedAssembly into its group output
  -> write group receipt
  -> write root execution receipt
```

The output writer MUST use recoverable temporary-file replacement for individual
JSON artifacts so interruption cannot leave a syntactically valid partial file.
This is an observable atomicity guarantee, not a required internal algorithm.

## 9. Error Handling

| Condition | Required outcome |
|---|---|
| Path escapes package/output root | fail before execution with offending path |
| Declared file missing/not regular | fail preparation with group and path |
| Existing execution directory | fail; never overwrite |
| Plan/selection artifact write fails | fail before Player construction |
| Group execution fails | retain records/artifacts; mark group/root failed |
| Receipt cannot be durably written | surface fatal error and leave directory incomplete |
| AgentDeck-resolved credential, ambient environment value, or designated credential field selected for serialization | fail serialization with field location |

## 10. Contract Example

```text
studies/information-grounding/
|-- study.yaml
`-- assembly.py

agentdeck_runs/studies/information-grounding/run_.../
|-- prepared-study.json
|-- selection.json
|-- execution.json
`-- execution-groups/default/...
```

Moving `studies/information-grounding/` to another checkout and preparing it
with the same AgentDeck version MUST yield the same plan identity. Executing it
MUST create a new output directory rather than edit the Study source.

## 11. Testing Strategy

| Invariants | Behavioral proof |
|---|---|
| SP1, SP7 | hash source before/after preparation/execution, including interpreter-cache absence; reject existing execution id |
| SP2–SP3, SP9 | relocate fixture; compare identities and serialized paths |
| SP4–SP6 | inject write/execution/Record-count failures; inspect durable receipts |
| SP8 | resolved credentials, read environment values, and designated credential fields never enter artifacts; optional scanning carries no completeness claim |
| SP10 | alternate representations resolve to the same canonical artifact ids |

Tests MUST run without provider calls. One failure-path test MUST prove that
already emitted canonical Records survive without a false complete status.

## 12. Design Rationale

- **Separate output root:** makes authored Studies content-addressable and
  prevents generated facts from changing their own source identity.
- **One directory per execution:** preserves history and makes partial failure
  inspectable.
- **Prepared artifacts before calls:** leaves an exact audit trail of what was
  authorized even if execution fails immediately.
- **No Research results yet:** child specs add Evidence/Finding representations
  without turning this package contract into `results.json` 2.0.

## 13. Research Derivation Artifacts

- `corpus.json` is the exact `RecordCorpus` identity and membership contract.
- each `measures/*.json` is the exact `PreparedMeasure` used for derivation.
- each `evidence/*.json` is canonical Evidence from that corpus and Measure.
- `analysis.json` binds the Study plan, corpus, ordered Measures, Evidence
  identities, portable paths, and a final analysis SHA-256.
- reports and other human representations cite canonical Finding/Evidence
  identities and never replace machine artifacts.
- all files use write-once semantics outside authored Study source.

## 14. Non-Goals / Future Work

- publication registries, remotes, upload, or Hugging Face integration;
- archive compression or signing;
- external corpus cache policy;
- hostile-code sandboxing;
- backward compatibility with every historical `research/` package.

## 14. References

- `SPEC-RESEARCH` RE2, RE7, RE15, RE16
- [`SPEC-STUDY`](SPEC-STUDY.md)
- `SPEC-ASSEMBLY` AS4–AS10
- `SPEC-RECORDER` portability and canonical Record requirements
