# SPEC-STUDY-CLI v0.3.0

> Status: Final
> Version: 0.3.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented — inspect, validate, run, analyze, and report
> Review State: approved
> Audience: AgentDeck CLI users, Study authors, automation authors

## 1. Purpose

Provide one legible command tree for inspecting, validating, and explicitly
authorizing a Study execution without exposing the internal sequence of loaders,
Assembly preparation, or artifact writers.

This version specifies the minimum complete command journey:

```text
agentdeck study inspect
agentdeck study validate
agentdeck study run
agentdeck study analyze
agentdeck study report
```

Reproduction, replication, extension, publication, and automatic Finding
authorship remain deferred.

## 2. Scope & Philosophy Alignment

- Implements the caller-facing boundary of `SPEC-STUDY`.
- Makes provider scope and exact plan identity visible before execution.
- Requires explicit selection and approval; no bare command means “run all.”
- Keeps inspect/validate free of Player construction and provider calls.
- Uses stable JSON output for automation and concise human output by default.

## 3. Command Contract

### Inspect

```text
agentdeck study inspect STUDY [--json]
```

Behavior:

- load and prepare the Study;
- perform no AgentDeck-orchestrated Player construction or provider calls;
- print question, intent, phases, ExecutionGroups, Cells, Conditions, Assembly
  runs, match counts, providers/models, declared lineage, and plan hash;
- show unknown or unavailable execution-envelope values explicitly;
- write no Study execution artifacts.

### Validate

```text
agentdeck study validate STUDY [--json]
```

Behavior:

- perform every structural, reference, identity, portability, and no-call
  validation available before execution;
- print all independent diagnostics discovered in one pass when safe;
- return success only when the Study can be prepared into a valid plan;
- write no Study execution artifacts.

### Run

```text
agentdeck study run STUDY \
  (--phase PHASE... | --group GROUP... | --all) \
  --approve PLAN_SHA256 \
  --output-root PATH \
  [--json]
```

Behavior:

- prepare the complete Study again;
- require the supplied full plan hash to match exactly;
- require exactly one selection mode;
- display the selected groups, phases, matches, and provider/model requirements;
- persist prepared plan and selection before Player construction;
- execute selected groups through `execute_prepared_study()`;
- print the execution id, status, Record count, usage, and receipt path.

This version has no interactive approval prompt. Automation and humans use the
same explicit `--approve` contract.

### Analyze

```text
agentdeck study analyze STUDY \
  --cell CELL... \
  --measure MEASURE... \
  (--execution RECEIPT... | --import-manifest PATH) \
  --output-root PATH \
  [--assumption TEXT...] \
  [--json]
```

Behavior:

- prepare the current Study and every explicitly named Measure;
- require non-empty explicit Cell and Measure selections;
- construct one exact RecordCorpus from either current non-overlapping
  StudyExecution receipts or one pinned imported manifest;
- derive one Evidence artifact per selected Measure;
- persist PreparedStudy, RecordCorpus, PreparedMeasures, Evidence artifacts,
  and one content-addressed analysis receipt outside authored source;
- never choose a Measure from a Game Research Profile automatically;
- never author a Finding or modify source Records.

### Report

```text
agentdeck study report FINDINGS \
  --finding FINDING_ID \
  --evidence EVIDENCE... \
  --output PATH \
  [--json]
```

Behavior:

- load one authored Finding declaration and every explicitly supplied Evidence
  artifact;
- resolve each citation to one exact EvidenceResult;
- write the canonical Finding JSON and a deterministic Markdown projection;
- never infer, rewrite, strengthen, or validate the authored claim.

## 4. Human Output

Human output MUST use this information order:

```text
Study
Question / intent
Plan identity
Selected scope (run only)
Phases and ExecutionGroups
Cells and Conditions
Total Matches
Providers / models
Known limits and unknowns
Output location (run only)
Status / diagnostics
```

`inspect` and `validate` MUST state:

```text
AgentDeck constructed no Players and invoked no providers.
Assembly preparation executed trusted authored Python.
```

The CLI MUST NOT label a Study, Evidence, or Finding “scientifically valid.”
Validation means only that the current structural and execution contracts pass.

## 5. JSON Output

`--json` emits exactly one JSON document to stdout. Logs and progress MUST go to
stderr.

Envelope:

```json
{
  "command": "study.inspect",
  "ok": true,
  "study_id": "information-grounding",
  "plan_sha256": "...",
  "data": {},
  "diagnostics": []
}
```

- `command`: stable command id.
- `ok`: command contract success, not scientific validity.
- `study_id`: present when parsing identifies it.
- `plan_sha256`: present only after successful preparation.
- `data`: command-specific structured output.
- `diagnostics`: ordered `{code, severity, location, message}` objects.

JSON artifact paths (`receipt_path`, `finding_path`, `report_path`) MUST be relative to `data.output_root`. That field identifies the resolved host output directory and MAY be absolute outside hashed artifacts. Success and partial-failure envelopes MUST provide this base whenever they provide an artifact path. Logs from trusted authored preparation and default runtime monitors MUST also remain on stderr in JSON mode.

## 6. Invariants & Guarantees

1. **SC1 — One namespace:** all current and future Study commands live under
   `agentdeck study`; no new `agentdeck-research-*` executable is introduced.
2. **SC2 — Scoped no-call inspection:** AgentDeck orchestration in inspect and
   validate MUST NOT construct Players, resolve credentials, or invoke
   providers. Preparation executes trusted Assembly Python, whose arbitrary side
   effects are outside this assurance.
3. **SC3 — No implicit execution:** `run` MUST require exactly one of `--phase`,
   `--group`, or `--all`.
4. **SC4 — Hash approval:** `run` MUST require the full current plan SHA-256;
   prefixes, stale hashes, and approval of only a selection hash MUST fail.
5. **SC5 — Fail before calls:** parse, validation, selection, plan mismatch,
   output-root, and prepared-artifact failures MUST occur before Player
   construction.
6. **SC6 — Same plan:** equal authored inputs MUST yield the same plan hash and
   inspect/validate JSON regardless of current directory.
7. **SC7 — Honest envelope:** unavailable cost/call estimates MUST display as
   unavailable; they MUST NOT become zero.
8. **SC8 — Output discipline:** human output is concise; JSON stdout contains no
   logs, progress, ANSI codes, or multiple documents.
9. **SC9 — Partial honesty:** failed execution exits non-zero, preserves its
   receipt path, and MUST NOT print a complete status.
10. **SC10 — Explicit layer authority:** inspect, validate and run MUST NOT calculate Evidence, create Findings, or present Match outcomes as Research conclusions. Only explicit analyze and report invocations enter their respective downstream authority.
11. **SC11 — Frozen remotes:** the CLI MUST NOT upload, publish, or mutate remote
    artifacts. Remote publication is outside this spec.
12. **SC12 — Explicit analysis authority:** `analyze` MUST require Cells,
    Measures, and exactly one corpus origin. A Game Research Profile MAY aid
    discovery outside this command but MUST NOT select a Measure implicitly.
13. **SC13 — Immutable derivation output:** `analyze` and `report` MUST create
    new output and fail rather than overwrite an existing canonical artifact.
14. **SC14 — No claim synthesis:** `analyze` stops at Evidence. `report` renders
    only an authored Finding whose granular citations resolve mechanically.

## 7. Exit Codes

| Code | Meaning |
|---:|---|
| `0` | command completed under its contract |
| `2` | authored Study/schema/reference validation failure |
| `3` | plan approval or selection identity mismatch |
| `4` | output/package preparation failure before execution |
| `5` | execution failed or completed partially; receipt preserved when possible |
| `6` | corpus, Measure, Evidence, Finding, or report derivation failed |
| `1` | unexpected internal failure |

The CLI MUST NOT return `0` for a partial execution. Scientific interpretation
never affects these exit codes.

## 8. Data Flow & Interaction

```text
inspect:  path -> prepare_study -> render
validate: path -> load + prepare + validations -> diagnostics
run:      path -> prepare -> compare approval -> select -> persist plan
          -> execute_prepared_study -> receipt -> render
analyze:  path -> prepare -> explicit corpus + Measures -> Evidence -> receipt
report:   authored Finding + Evidence -> resolve citations -> JSON + Markdown
```

Inspect and validate MAY import trusted Assembly Python because preparation must
describe its effective composition. Help text and docs MUST state this security
boundary; “AgentDeck invoked no providers” does not mean “no Python execution.”

## 9. Error Language

Errors MUST identify the failing layer and location:

- `Study schema: cells[2].execution_group references unknown group 'p9'`
- `Assembly group 'main': preparation failed: ...`
- `Selection: choose exactly one of --phase, --group, or --all`
- `Approval: expected plan <current>; received <supplied>`
- `Output: execution directory already exists; no files were overwritten`
- `Execution group 'main': failed after 12 Records; receipt: <relative path>`
- `Corpus: imported Record hash does not match manifest entry ...`
- `Finding: citation does not resolve to one EvidenceResult ...`

Errors MUST NOT use “verification failed” without naming whether schema,
identity, execution, Evidence, or review was involved.

## 10. Examples

```bash
# No AgentDeck Player/provider calls; trusted Assembly Python is loaded
agentdeck study inspect studies/information-grounding/study.yaml
agentdeck study validate studies/information-grounding/study.yaml --json

# First inspect and copy the exact plan hash, then authorize only P0
agentdeck study run studies/information-grounding/study.yaml \
  --phase p0 \
  --approve 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
  --output-root agentdeck_runs/studies

agentdeck study analyze studies/information-grounding/study.yaml \
  --cell partial --cell full \
  --measure observe-rate \
  --execution agentdeck_runs/studies/.../execution.json \
  --output-root agentdeck_runs/analysis
```

The documentation MUST NOT show `--all` as the default first execution example.

## 11. Testing Strategy

| Invariants | Behavioral proof |
|---|---|
| SC1 | packaging exposes one `agentdeck` entrypoint and `study` command tree |
| SC2, SC5 | AgentDeck provider/Player spies untouched for inspect, validate, and pre-call failures; trusted-source warning is present |
| SC3–SC4 | missing/mixed selectors and stale/partial hashes exit `3` before calls |
| SC6 | relocated fixture produces byte-equivalent JSON excluding host output echo |
| SC7–SC8 | unavailable values explicit; stdout parses as one JSON document |
| SC9 | injected group failure exits `5` and reports incomplete receipt |
| SC10–SC14 | explicit analysis selections; no auto-Measure, claim synthesis, overwrite, or remote mutation |

Acceptance requires shell-level tests for human and JSON modes plus the
single-Player orthogonal Study. All acceptance tests run without live providers.

## 12. Design Rationale

- **Inspect before run:** the user authorizes a visible content-addressed plan,
  not a mutable path.
- **Explicit selector:** prevents a large Study from turning a small intended
  smoke test into full provider execution.
- **Full hash:** avoids ambiguous approval and keeps automation deterministic.
- **No interactive prompt:** one contract works locally and in CI; a future UI
  may provide its own authorization experience over the same plan identity.
- **Stable JSON:** makes the human-first CLI usable by other systems without
  creating another execution API.

## 13. Non-Goals / Future Commands

- `study replay`, `reproduce`, `replicate`, or `extend`;
- natural-language Study creation;
- credentials, billing, or hosted execution;
- remote publication or registry integration;
- interactive TUI;
- scientific peer review or claim validation.

## 14. References

- `SPEC-RESEARCH` §5–§10
- [`SPEC-STUDY`](SPEC-STUDY.md)
- [`SPEC-STUDY-PACKAGE`](SPEC-STUDY-PACKAGE.md)
- `SPEC-ASSEMBLY` preparation/security boundary
