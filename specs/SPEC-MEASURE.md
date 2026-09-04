# SPEC-MEASURE v0.1.0

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented
> Review State: approved by maintainer for the Research-axis wave
> Audience: Study authors, Measure authors, Research-layer implementers, reviewers

## 1. Purpose

Let a caller declare one deterministic transformation over an identified Record
corpus and obtain small, traceable results without turning AgentDeck into a
generic analytics framework or allowing hidden inference after execution.

A Measure answers one mechanical question about Records. It does not select an
undeclared corpus, execute an AI judge, alter a Study execution plan, create
Evidence authority, or write a Finding.

## 2. Scope & Philosophy Alignment

- Implements `SPEC-RESEARCH` RE2–RE5, RE8, RE13, and RE17.
- Consumes immutable current-schema Records through a prepared corpus contract.
- Keeps Measure identity independent from Study execution-plan identity.
- Makes implementation, parameters, and material environment part of identity.
- Keeps assumptions and application scope explicit without misrepresenting them
  as properties of the analysis implementation.
- Produces flat, addressable results rather than an unrestricted `results.json`.
- Does not define corpus admissibility, Evidence identity, Findings, reports,
  statistical test selection, or domain-specific metrics.

## 3. Terminology

- **MeasureDeclaration**: authored Measure id, implementation, parameters,
  source artifacts, and material dependencies.
- **PreparedMeasure**: immutable declaration bound to exact implementation,
  artifacts, parameters, and material-environment identities.
- **RecordCorpus**: immutable ordered collection of identified Records plus
  semantic Study bindings, defined by `SPEC-EVIDENCE` independently of any
  Measure.
- **MeasureInput**: read-only view of one RecordCorpus plus the PreparedMeasure
  parameters supplied to Measure code.
- **SourceLocator**: optional exact Record hash plus RFC 6901 JSON Pointer used
  for direct navigation to source material.
- **MeasureResult**: one flat, available or unavailable derived value identified
  by metric and dimensions.
- **MeasureOutput**: deterministic tuple of MeasureResults and mechanical
  diagnostics returned by one Measure evaluation.

## 4. Architecture

```text
authored MeasureDeclaration
  -> prepare implementation + artifacts + material environment
  -> PreparedMeasure

PreparedMeasure + independent immutable RecordCorpus
  -> trusted deterministic Measure code
  -> validate values and any declared SourceLocators
  -> MeasureOutput
  -> SPEC-EVIDENCE binds Study scope + corpus + Measure + assumptions
```

Research MAY import Recorder loading contracts. Recorder and the execution
kernel MUST NOT import Measure types.

Study execution identity and Measure identity are orthogonal:

```text
execution_plan_sha256 = what was authorized to execute
measure_sha256        = how identified Records are transformed
corpus_sha256         = which identified Records are analyzed
evidence_sha256       = the binding of all relevant identities and outputs
```

Changing a Measure MUST NOT change `PreparedStudy.plan_sha256`. A future
pre-registration or protocol artifact MAY pin an execution plan, Measures, and
analysis scope together; v0.1 MUST NOT overload execution-plan identity to model
that future contract.

## 5. Authored Declaration

Measure declarations live separately from `study.yaml` and are location-neutral.
A declaration MAY be referenced by a Game Research Profile, a Study package, a
built-in catalog, or an explicit caller path. A Study package MAY contain an
explicit `measures.yaml`; loading or preparing it is not part of `load_study()`
or `prepare_study()` and does not alter Study definition or plan identity.

Built-in implementation:

```yaml
schema_version: 1
measures:
  - id: total-cost
    implementation: {builtin: total-cost}
    parameters: {}
```

Custom implementation:

```yaml
schema_version: 1
measures:
  - id: observe-rate
    implementation:
      entrypoint: measures.py:observe_rate
      artifacts: []
    parameters: {action: OBSERVE}
    material_distributions: []
```

Contract:

- `id`: unique portable id matching `[a-z0-9][a-z0-9._-]*`.
- `implementation`: exactly one explicit built-in id or package-relative Python
  `entrypoint`; automatic Game/scorer discovery is forbidden.
- `parameters`: canonical JSON with finite numbers and no paths, credentials, or
  ambient values.
- `artifacts`: package-relative source files needed by custom code. Every local
  module, helper, template, data file, or other package-local source whose
  change can affect output MUST be declared; importing undeclared local source
  is a contract violation even though AgentDeck cannot prove arbitrary Python
  declared every dependency.
- `material_distributions`: exact Python distribution names whose resolved
  versions can affect output. Custom code MUST declare every material
  third-party dependency; built-ins declare theirs in AgentDeck.

AgentDeck resolves and records the declared material environment. It MUST NOT
represent that as mechanical proof that arbitrary custom Python declared every
dependency it actually imports or consults.

Cell scope and authored assumptions do not belong to a MeasureDeclaration.
Corpus construction chooses exact Cells; Evidence derivation records assumptions
and binds both to the PreparedMeasure. This permits the same Measure and corpus
to be reused without duplicating either artifact.

A Measure declaration MUST NOT define Game, Player, Controller, provider, model,
prompt, match count, seed, Study phase, Cell selection, Finding semantics, or
another executable value.

## 6. Data Structures

### PreparedMeasure

Contains:

- Measure id and contract version;
- parameters;
- implementation kind, logical id/entrypoint, and source SHA-256;
- declared source-artifact SHA-256 values;
- Python, AgentDeck, and resolved material-distribution versions;
- optional declared platform properties when output is platform-sensitive;
- final `measure_sha256`.

`measure_sha256` covers only the transformation and everything materially
required to reproduce it. It MUST NOT cover Study id, execution plan, corpus,
Cell scope, assumptions, output location, or timestamps.

Local source paths MAY exist on the Python object but MUST serialize relatively
or be omitted. Every value reachable from PreparedMeasure MUST be immutable or a
detached copy.

### MeasureInput

Contains:

- exact `corpus_sha256`;
- ordered immutable CorpusRecords;
- Cell, phase, ExecutionGroup, and AssemblyRun binding for every Record;
- immutable PreparedMeasure parameters.

Measure code receives no credential resolver, provider client, output directory,
network client, clock, mutable Study object, assumptions, or Finding context from
AgentDeck.

### SourceLocator

```json
{
  "record_sha256": "...",
  "pointer": "/events/3/data/action/value"
}
```

- `record_sha256` MUST name exactly one Record in MeasureInput.
- `pointer` MUST be a valid RFC 6901 pointer resolving inside that exact Record.
- Empty pointer MAY cite the complete Record.
- SourceLocators are optional direct-navigation aids. If present, every locator
  MUST resolve mechanically.
- AgentDeck MUST NOT claim that an arbitrary custom Measure enumerated every
  materially contributing field merely because its declared locators resolve.
  Exact corpus identity and Measure identity are the exhaustive provenance
  boundary in v0.1.

### MeasureResult

Contains:

- `metric`: stable portable metric id;
- `dimensions`: canonical flat mapping from dimension names to JSON scalar
  values; empty for a scalar result without dimensions;
- `status`: `available` or `unavailable`;
- `value`: required only when available; JSON scalar or finite list of JSON
  scalars, never an unrestricted mapping;
- `unit`: optional stable unit such as `count`, `proportion`, `usd`, or `seconds`;
- `support`: optional `{count, unit}` describing the evaluated denominator;
- `sources`: optional exact SourceLocators;
- `diagnostic`: required code and message when unavailable;
- `result_sha256`: AgentDeck-derived stable identity over the canonical result.

The `(metric, dimensions)` pair MUST be unique within one MeasureOutput.
Dimensions MUST remain data, not be encoded into brittle metric names. An
interval MAY be represented as a two-value finite list. Related estimates,
p-values, effect sizes, and quality checks SHOULD remain separate metric and
dimension pairs rather than fields in a nested result tree.

### MeasureOutput

Contains:

- Measure and corpus hashes;
- canonically ordered unique MeasureResults;
- stable diagnostics concerning mechanical evaluation only.

It contains no Study-completeness claim, assumptions, Evidence hash, narrative
claim, scientific-validity flag, report content, or current timestamp.

## 7. Public API

```python
load_measure(path: str | Path, measure_id: str) -> MeasureDeclaration
prepare_measure(declaration: MeasureDeclaration) -> PreparedMeasure
evaluate_measure(prepared: PreparedMeasure, corpus: RecordCorpus) -> MeasureOutput
```

### `load_measure`

- MUST parse one explicit declaration without loading a Study or Records.
- MUST reject duplicate or ambiguous ids and undeclared implementation fields.

### `prepare_measure`

- MUST resolve the exact implementation and source artifacts.
- MUST import custom Python as trusted authored code without creating caches in
  the Study package.
- AgentDeck orchestration MUST NOT construct Players, resolve credentials,
  invoke providers, or make network calls.
- MUST fail when a declared material distribution cannot be resolved.

### `evaluate_measure`

- MUST require exact corpus and Measure identities.
- MUST expose deeply immutable Record payloads and parameters to Measure code.
- MUST validate every result, finite value, support count, dimension, and any
  SourceLocator that the Measure returns.
- MUST return unavailable results explicitly; it MUST NOT substitute zero,
  `false`, `1.0`, an empty available list, or another neutral value.
- MUST NOT write Evidence directly. `SPEC-EVIDENCE` owns that authority.

Custom Measure Python is trusted executable analysis code, not a sandbox.
AgentDeck validates identity, inputs, and outputs; it does not claim to prove
that arbitrary authored Python is deterministic, exhaustive, complete in its
dependency declaration, or scientifically correct.

## 8. Invariants & Guarantees

1. **ME1 — Explicit selection:** every Measure is loaded from one explicit
   declaration; no Game-name, schema, filename, or registry heuristic selects it.
2. **ME2 — Exact corpus:** Measure code receives only the content-addressed
   Records and semantic bindings in the supplied RecordCorpus.
3. **ME3 — No hidden observation:** a Measure MUST NOT call a model, judge,
   network, current time, entropy source, provider, or ambient mutable service.
4. **ME4 — Deterministic output:** equal PreparedMeasure and RecordCorpus
   identities MUST produce byte-equivalent canonical MeasureOutput.
5. **ME5 — Material identity:** implementation source, declared artifacts,
   parameters, Python, AgentDeck, and every material distribution version MUST
   enter `measure_sha256`; Study scope and assumptions MUST NOT.
6. **ME6 — Explicit seeded analysis:** a pseudorandom algorithm MAY run only
   when its algorithm/version and seed are explicit parameters covered by
   identity; ambient entropy is forbidden.
7. **ME7 — Immutable inputs:** Measure evaluation MUST NOT mutate canonical
   Records, corpus metadata, Study source, or PreparedMeasure.
8. **ME8 — Flat results:** every result is addressed by metric and flat
   dimensions; MeasureResult values MUST NOT become an arbitrary nested report
   schema.
9. **ME9 — Honest traceability:** available results always identify their exact
   corpus and Measure through MeasureOutput. Optional granular SourceLocators
   MUST resolve, but their presence is not an exhaustiveness certificate.
10. **ME10 — No auto-statistics:** method choice, null, confidence level,
    sidedness, corrections, and seed MUST be explicit parameters when relevant.
    AgentDeck MUST NOT auto-select a statistical test from observed data.
11. **ME11 — No fallback method:** a missing dependency or unsupported method
    MUST fail or yield explicit unavailability; it MUST NOT silently use another
    algorithm or omit uncertainty.
12. **ME12 — No domain leakage:** the protocol MUST NOT contain winner,
    opponent, position, health, action, strategy-tier, or win-rate fields.
13. **ME13 — No interpretation:** outputs MUST NOT include natural-language
    conclusions, assumptions, significance labels, actionability, or Finding
    lifecycle state.
14. **ME14 — Deep immutability:** PreparedMeasure, MeasureInput, and returned
    MeasureOutput representations MUST NOT change while their identities remain
    unchanged.
15. **ME15 — Orthogonal identity:** preparing or changing a Measure MUST NOT
    change Study definition or execution-plan identity.
16. **ME16 — Corpus independence:** one RecordCorpus MAY be supplied to multiple
    Measures without changing corpus identity.
17. **ME17 — Location neutrality:** the same declaration and artifacts MUST
    prepare to the same Measure identity whether selected directly, referenced
    by a Game Research Profile, or stored beside a Study.

## 9. Data Flow & Interaction

```text
MeasureDeclaration
  -> PreparedMeasure
  -> independent exact RecordCorpus
  -> MeasureOutput
  -> Evidence builder binds Study scope, assumptions, and completeness
```

LLM-assisted evaluation remains:

```text
Source Records -> Judge Assembly -> Judge Records -> Measure -> MeasureOutput
```

The Measure never receives a hidden judge callback.

## 10. Error Handling & Edge Cases

| Condition | Required outcome |
|---|---|
| Unknown/ambiguous Measure id | fail loading before Records |
| Missing/unresolvable material distribution | fail preparation |
| Source/artifact changed | new Measure identity; stale identity fails |
| Study plan changed | no change to Measure identity; Evidence must bind the new corpus/plan |
| Invalid or duplicate metric/dimensions | reject MeasureOutput |
| NaN/Infinity or nested result mapping | reject MeasureOutput |
| Non-resolving declared SourceLocator | reject MeasureOutput with result identity |
| Missing input | unavailable result, never neutral substitution |
| Measure raises | preserve diagnostic context; do not create available Evidence |

## 11. Contract Examples

### Single-Player action rate

```json
{
  "metric": "action_rate",
  "dimensions": {"action": "OBSERVE", "condition": "partial_information"},
  "status": "available",
  "value": 0.625,
  "unit": "proportion",
  "support": {"count": 40, "unit": "gameplay_events"},
  "sources": [{"record_sha256": "...", "pointer": "/events/2/data/action/value"}],
  "result_sha256": "..."
}
```

No winner, opponent, or competitive field is required by the protocol.

### Missing action field

The Measure emits `status=unavailable` with `measure.input_missing`; it MUST NOT
emit `value=0.0`.

### Exact binomial method

The declaration names the method, null probability, sidedness, confidence level,
seed when applicable, and material SciPy version. `auto` is not permitted.

## 12. Testing Strategy

| Invariants | Behavioral proof |
|---|---|
| ME1–ME2 | explicit declaration and exact corpus required; no auto scorer path |
| ME3–ME4, ME6 | byte-equal repeat; no network/time/entropy; seeded method repeats |
| ME5, ME15 | source/parameter/environment changes alter Measure identity; Study plan does not |
| ME7, ME14 | deep mutation attempts fail; canonical Records hash unchanged |
| ME8 | nested mappings and duplicate metric/dimensions fail |
| ME9 | corpus/Measure hashes always present; declared invalid locators fail |
| ME10–ME11 | `auto`, missing methods, and dependency fallback fail explicitly |
| ME12 | competitive and single-Player/no-winner fixtures use identical public types |
| ME13 | interpretation/actionability fields rejected from MeasureOutput |
| ME16 | two Measures consume one corpus without changing its identity |
| ME17 | direct and Game-Research-Profile references resolve to the same PreparedMeasure |

Acceptance requires:

- a The Agentic Edge fixture Measure that derives a headline outcome from the
  exact hashed corpus and offers direct source navigation where practical;
- a single-Player/no-winner Measure deriving a non-outcome behavioral rate;
- changed source Record -> changed corpus/Evidence, never stale MeasureOutput;
- one execution plan analyzed by a changed Measure without changing plan identity;
- no optional scientific dependency in the base `agentdeck-ai` import path.

## 13. Design Rationale

- **Analysis outside Study identity:** post-hoc analysis and reanalysis must not
  rewrite what was authorized to execute. A future pre-registration contract can
  explicitly bind both without corrupting either identity.
- **Corpus independent from Measure:** the same exact Records can support several
  derivations without duplicate manifests or measure-specific corpus hashes.
- **Flat dimensional results:** preserves stable machine structure without
  encoding every comparison into metric names or recreating a nested behavioral
  profile.
- **Optional exact SourceLocators:** enables result-to-turn navigation without
  pretending arbitrary Python proved exhaustive field-level causality.
- **Trusted custom Python:** matches Assembly's inspectable extensibility without
  pretending arbitrary local code can be proven pure by a library.
- **No generic statistics layer:** explicit Measures may use established
  libraries; AgentDeck records method and environment instead of wrapping every
  scientific procedure.

## 14. Non-Goals / Future Work

- pre-registration or protocol snapshots binding execution and analysis plans;
- Measure composition or Measure-to-Measure dependencies;
- automatic metric/scorer selection;
- semantic judges inside Measure code;
- hostile-code sandboxing;
- exhaustive field-level provenance for arbitrary custom code;
- streaming/incremental Measure evaluation;
- dataframe, SQL, notebook, or plotting APIs;
- adaptive/sequential analysis;
- a universal statistical result taxonomy.

## 15. References

- `SPEC-RESEARCH` §4–§10
- `SPEC-STUDY` authored Study and Cell contracts
- `SPEC-RECORDER` canonical Record schema
- `SPEC-STUDY-PACKAGE` source/output separation
- [`SPEC-EVIDENCE`](SPEC-EVIDENCE.md)
- [`SPEC-GAME-RESEARCH-PROFILE`](SPEC-GAME-RESEARCH-PROFILE.md)
