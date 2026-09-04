# How the AgentDeck Research Arc Works

AgentDeck turns an AI behavior observed inside a Game into a traceable Research
artifact without confusing execution facts, derived measurements, and authored
interpretation.

Its two governing questions are:

- **Execution contract:** what exactly happened?
- **Research contract:** what exactly supports this conclusion?

The complete arc is:

```text
Game or behavioral Question
  -> Game Research Profile
  -> Study
  -> Prepared Assembly
  -> Runs
  -> canonical Records
  -> closed RecordCorpus
  -> deterministic Measures
  -> Evidence
  -> authored Finding
  -> deterministic human-readable report
```

This document explains what each layer owns, how generic the architecture is,
what a new Game must provide, where LLMs may participate, and what final value a
user receives.

## The user outcome

The final outcome is not merely a score, CSV, replay, or AI-generated summary.
It is a navigable claim with an explicit assurance boundary:

```text
Finding
  -> exact Evidence result
  -> exact Measure and parameters
  -> exact Record corpus
  -> exact Match Records
  -> optional direct source anchors to specific fields/turns
  -> actions, state, prompts, responses, and execution provenance
```

A user should be able to answer:

- What question did we ask?
- What stayed constant and what changed?
- What executable composition was authorized?
- Which Runs actually completed?
- Which exact Records entered the analysis?
- How was each value calculated?
- Which value supports each sentence in the conclusion?
- What assumptions, missing observations, phases, and limitations apply?
- Was any AI judgment involved, and if so, where is its execution Record?

AgentDeck can also deliver an honest negative outcome: an incomplete corpus,
unsupported Measure, missing observation, or unresolved citation becomes an
explicit failure or `unavailable` result rather than a plausible-looking zero.

## Two ways into the same arc

### Game-first

```text
Choose or create a Game
  -> inspect what its mechanics make observable
  -> notice behavior
  -> formulate a Question
  -> create a Study
  -> run, measure, and interpret
```

This path supports exploration. A person may first see an interesting Match and
only later decide to test whether the behavior holds.

### Question-first

```text
State a behavioral Question
  -> choose or create a Game that makes it observable
  -> materialize Conditions as exact Assemblies
  -> create a Study
  -> run, measure, and interpret
```

This path supports a planned investigation. The same execution and Research
contracts serve both paths; the architecture does not require a separate
experiment runtime.

## The layers and their authority

| Layer | Primary responsibility | What it must not do |
|---|---|---|
| Game | Define the world, rules, state, actions, and consequences | Claim that its mechanics prove a behavioral construct |
| Game Research Profile | Explain Research opportunities, supported operationalizations, and boundaries | Select a Measure, create a Study, or alter execution |
| Study | State the Question and semantic design; map Conditions and Cells to exact Assembly Runs | Duplicate model, prompt, seed, Player, or Game configuration |
| Prepared Assembly | Authoritatively define the executable Game, Players, Controllers, prompts, provider options, schedule, and seeds | Contain Research interpretation |
| StudyExecution | Preserve what selected scope ran and bind each Record to group, run, match slot, seed, phase, and Cell | Infer membership from filenames or expected counts |
| Record | Preserve the canonical execution facts | Contain Research annotations or conclusions |
| RecordCorpus | Close and identify the exact Records selected for analysis | Select itself implicitly or mix phases/origins silently |
| Measure | Deterministically transform the identified corpus into small, addressable results | Call a model, network, clock, judge, or mutable service |
| Evidence | Bind Study scope, corpus, Measure, environment, assumptions, and derived results | Claim scientific or causal truth |
| Finding | Express an authored interpretation with exact Evidence-result citations and limitations | Become true merely because hashes and citations resolve |
| Report | Project Finding and Evidence into a human-readable form | Replace the canonical machine artifacts |

The dependency direction is intentionally one-way:

```text
Research layer -> public execution contracts
execution kernel -X-> Research layer
```

AgentDeck therefore contains Research as a first-class product capability while
keeping the execution kernel independently reusable.

## How each stage works

### 1. The Game makes behavior observable

A Game creates an explicit environment in which an AI receives information,
chooses actions, and experiences consequences. AgentDeck records structural
gameplay events, including action and state transitions, plus lifecycle,
provider, cost, error, and configuration provenance where available.

A Game may emit additional JSON-serializable domain events when its Research
questions require observations beyond the structural gameplay event.

The Game owns mechanics only. `FixedDamageGame` does not “measure reasoning” or
“prove risk preference.” It creates repeated, inspectable decisions involving
health, attacks, and a scarce recovery resource.

### 2. The Game Research Profile explains what is investigable

A Game Research Profile (GRP) is versioned Research metadata associated with a
Game identity. It answers:

- Which pressures or affordances do the mechanics create?
- Which behaviors may become observable?
- Which questions are plausible Research Opportunities?
- Which exact Measures are already supported operationalizations?
- Which observations do those Measures require?
- What does this Game explicitly not establish?

The distinction is important:

- A **Research Opportunity** is a plausible question exposed by mechanics.
- A **supported operationalization** is a prepared, content-addressed Measure
  that can mechanically calculate a declared result from suitable Records.

Preparation proves that references and identities resolve. It does not prove
that a metric is scientifically valid or calibrated.

A GRP is not required by the Study or analysis APIs. It is the recommended
discovery contract that makes the system usable by someone who does not already
know what to measure.

### 3. The Study states intent without duplicating execution

`study.yaml` contains the human Research semantics:

- id, title, Question, and exploratory or confirmatory intent;
- optional hypotheses and lineage;
- phases such as preflight, pilot, study, and supplemental;
- semantic Conditions;
- Cells that map those Conditions to exact Assembly Runs.

It deliberately does not contain model, provider, prompt, Controller, Game
parameter, seed, or match count. Those values already belong to Assembly.

This prevents two competing descriptions of the experiment:

```text
Study says what is being investigated.
Assembly says exactly what will execute.
```

`prepare_study()` loads and content-addresses every declared Assembly, validates
all references, and produces a stable `plan_sha256`. Equal authored content and
equal Assembly identities produce the same plan identity after relocation.

### 4. The user explicitly authorizes execution

Inspection and validation show the complete plan, Players, models, phases,
Cells, match counts, and provider requirements without AgentDeck constructing a
Player or invoking a provider.

Execution requires:

- an explicit phase, group, or all-groups selection;
- the full inspected `plan_sha256` as approval;
- a separate output root.

Before any Player construction, AgentDeck prepares the Study again and rejects
changed source or composition. A completed execution records the exact mapping:

```text
Study -> ExecutionGroup -> AssemblyRun -> match_index -> effective_seed
      -> Match id -> Record path -> Record SHA-256 -> Cell and phase
```

Partial execution preserves emitted Records and an incomplete receipt. It never
becomes a complete Study by implication.

### 5. Records preserve execution truth

Canonical Records answer what happened. Depending on the Player and provider,
they can preserve:

- effective Game and Player configuration;
- Game implementation fingerprint;
- prompts and model-visible context;
- provider-native request arguments and response metadata;
- parsed and resolved actions;
- retries, parse failures, stop reasons, and errors;
- state before and after each gameplay action;
- costs, usage, latency, lifecycle, and outcome;
- recorded or stated reasoning when the model emitted it.

Recorded reasoning remains model testimony. AgentDeck never represents it as
privileged access to hidden internal thought.

Research never modifies a Record. Derived labels, metrics, Evidence, and claims
live in separate artifacts.

### 6. RecordCorpus closes the analysis input

A `RecordCorpus` is an immutable, ordered, content-addressed set of Records plus
their exact Study bindings. It can originate from:

- one or more non-overlapping `StudyExecution` receipts for the same plan; or
- an explicitly pinned imported manifest.

Imported Records retain their original provenance and are labeled `imported`.
An authored mapping to current Cells does not pretend that a historical Record
was produced by the current Assembly.

Corpus completeness means every planned match slot for every selected Cell is
present exactly once. It does not mean every Record necessarily contains the
observation required by every possible Measure.

In v0.1, an incomplete corpus blocks derivation instead of silently calculating
over an accidental subset.

### 7. Measures derive values mechanically

A Measure is a small deterministic transformation:

```text
PreparedMeasure + RecordCorpus -> MeasureResults
```

Its identity includes:

- implementation source;
- parameters;
- declared local artifacts;
- materially relevant Python distributions and versions;
- other declared environment properties that can change the result.

Each result is deliberately flat and addressable:

```json
{
  "metric": "potion-rate-by-risk-band",
  "dimensions": {"cell": "variable-s3", "player": "candidate", "risk-band": "danger"},
  "status": "available",
  "value": 0.625,
  "unit": "proportion",
  "support": {"count": 16, "unit": "turns"}
}
```

When the denominator or observation does not exist, the result is
`unavailable` with a diagnostic. It is never converted to `0`, `false`, `1.0`,
an empty successful value, or a default confidence interval.

AgentDeck currently includes only narrow generic built-ins such as
`record-count` and `total-cost`. Behavioral Measures are normally authored for
the Game's observable mechanics. This is intentional: the framework does not
pretend that “cooperation,” “deception,” or “risk” has a universal definition
across arbitrary worlds.

A Measure may optionally return exact Record-hash and JSON-Pointer source
anchors for direct navigation to contributing fields. AgentDeck validates that
those anchors resolve. It does not claim that arbitrary custom Python declared
every field it read; the exhaustive provenance boundary in v0.1 is the complete
identified corpus plus the complete declared Measure identity.

Determinism is a contract for trusted Measure code, not hostile-code proof.
AgentDeck does not supply a network client, clock, provider, or credentials to a
Measure and records its declared implementation and environment. It cannot
prove that arbitrary authored Python did not reach undeclared ambient state or
import an undeclared helper. Such access is a contract violation, not a
sandboxed impossibility.

### 8. Evidence binds the derivation to its scope

Evidence is an immutable envelope created by AgentDeck, not by custom Measure
code. It binds:

- Study id, intent, plan, Cells, and phases;
- corpus origin, identity, membership, and completeness;
- Measure identity, parameters, and material environment;
- authored assumptions;
- derived results and diagnostics.

Evidence answers:

> What do these exact Records support under this declared Measure and Study
> scope?

It does not answer whether the design was unbiased, the metric was the best
choice, the relationship was causal, or the result generalizes outside the
declared conditions.

### 9. Finding closes the human Research journey

A Finding contains:

- an authored natural-language claim;
- authorship kind: `human`, `ai_assisted`, or `ai`;
- at least one exact supporting Evidence-result citation;
- optional qualifying, challenging, and contextualizing citations;
- at least one explicit limitation.

AgentDeck mechanically verifies that every citation resolves. It does not
certify the claim as scientifically true.

The deterministic Markdown report shows the claim, authorship, result value,
dimensions, phase, corpus origin, hashes, limitations, and assurance boundary.

## What is deterministic and what may use an LLM

The architectural rule is:

> Every intelligence-mediated or externally non-deterministic observation that
> can affect Evidence must become a canonical Record before deterministic
> measurement begins.

| Operation | Deterministic? | May use an LLM? | Where provenance lives |
|---|---:|---:|---|
| Author a Game, GRP, Study, Measure, or Finding | Not inherently | Yes, as authoring assistance | Authored source and content identity; Finding records authorship kind |
| Prepare Game/Assembly/Study/Profile/Measure | Yes for equal declared inputs | No provider calls by AgentDeck | Prepared artifact hashes and declared environment |
| Select and approve a Study scope | Yes | No | Selection and plan hashes |
| Execute deterministic local Players/Game logic | Yes when contracts and seeded RNG are respected | No | canonical Records and execution receipts |
| Execute provider-backed Players | Not guaranteed | Yes | model, provider, prompt/context, parameters, raw interaction, retries, cost, errors, Records |
| Execute a semantic LLM judge | Not guaranteed | Yes, but only as a new Judge Assembly | Judge Records, then deterministic Measure |
| Construct a RecordCorpus | Yes | No | corpus manifest and SHA-256 |
| Evaluate a Measure | Required to be deterministic | No | Measure, corpus, environment, output hashes |
| Use bootstrap/permutation/Monte Carlo analysis | Yes when algorithm and seed are identified | No | Measure parameters and material environment |
| Build Evidence | Yes | No | Evidence identity and exact results |
| Author a Finding claim | Not mechanical interpretation | Yes, if labeled `ai_assisted` or `ai` | Finding authorship, citations, limitations, hash |
| Resolve citations and render the report | Yes | No | Finding and Evidence identities |

For local execution, “deterministic” means the same declared gameplay logic and
seeded inputs produce the same framework decisions and outcomes. It does not
mean separately generated Record files are byte-identical: execution ids,
timestamps, durations, and other runtime observations may differ and do not
enter the prepared plan identity.

Provider-backed execution may vary even with the same model id, prompt, and
seed because remote models and serving infrastructure can change. AgentDeck's
guarantee is not that an LLM will repeat itself forever. The guarantee is that
the authorized composition and resulting interaction are inspectable and that
replay never fabricates a new provider call.

## How generic is the arc?

### Generic at the framework level

The Research primitives contain no built-in concept of:

- winner or loser;
- opponent;
- two-player topology;
- turn-order comparison;
- health, potion, card, mana, or score;
- strategy tier;
- win rate;
- LLM provider or model family.

The same public types have been exercised by:

- The Agentic Edge: competitive, two-player, multi-phase, 19 Cells, 540 planned
  Matches, two Games, outcome statistics, and behavioral Measures;
- an orthogonal acceptance Study: single Player, no opponent, no winner, two
  information Conditions, and a non-win-rate Measure.

The flagship Study is expressed through normal Study, Measure, Evidence, and
Finding contracts. There is no Agentic-Edge-specific analysis engine in the
framework.

### Game-specific at the semantic edge

No generic framework can infer what a domain-specific behavior means merely by
looking at arbitrary state fields. A new Game may require authored knowledge in
three places:

1. a GRP explaining why its mechanics make a question plausible;
2. sufficient observability in canonical Records;
3. one or more deterministic Measures implementing the chosen
   operationalization.

This is intended domain extension, not coupling in the Research kernel.

### The precise readiness claim

AgentDeck is structurally ready for any Game that:

- can run through the AgentDeck execution contracts;
- produces current canonical Records;
- records every observation required by the intended Measure;
- can express its planned executions as fixed PreparedAssembly Runs and Study
  Cells;
- uses deterministic post-Record derivation.

It is not accurate to say that any arbitrary external Game becomes a complete
Research instrument with no authored work. External engines first need an
AgentDeck Game/Record integration, and domain behavior still needs an explicit
operationalization.

The best shorthand is:

> The Research arc is Game-agnostic, not Game-semantic-free.

## What a new Game needs

There are four useful readiness levels.

### Level 1: executable Game

Required:

- implement or adapt the Game to AgentDeck's Game/mechanic contracts;
- expose JSON-serializable state and actions;
- use framework-provided RNG for stochastic mechanics when reproducibility is
  required;
- run through an Assembly with declared Players and schedule.

Research dependency: **none**. The Game package does not import Research.

Result: Matches, canonical Records, and replay.

### Level 2: Research-ready Game

Additionally required:

- ensure the behavior of interest is present in structural gameplay events or
  explicit domain events;
- create `study.yaml` mapping semantic Conditions and Cells to exact Assembly
  Runs;
- use built-in Measures where sufficient or declare a custom deterministic
  Measure in `measures.yaml`.

Research dependency in Game code: **none**. Study and Measures live downstream.

Result: identified corpus and Evidence.

### Level 3: Research-discoverable Game

Recommended addition:

- author a Game Research Profile with Opportunities, mechanisms, required
  observables, supported operationalizations, and explicit boundaries.

The profile remains separate from Game execution and can evolve independently.

Result: a non-expert can understand what is worth asking and which methods are
already executable.

### Level 4: interpreted Study

Additionally required:

- author a Finding that cites exact Evidence results and states limitations;
- optionally render the deterministic Markdown report.

Result: a human-readable conclusion that remains navigable to execution truth.

## Runtime and package dependencies

The base package requires Python 3.10+ and PyYAML. The Research arc itself adds
no mandatory NumPy, SciPy, Statsmodels, Matplotlib, notebook, database, or LLM
SDK dependency.

- Provider SDK extras are needed only for the provider-backed Players selected
  by an Assembly.
- A custom Measure may use a third-party statistical library, but every
  materially relevant distribution must be declared so its resolved version
  enters Measure identity.
- Custom Assembly and Measure Python is trusted authored code. Portability and
  content-addressing are not a hostile-code sandbox.
- Credentials may be resolved for execution but must not enter portable
  Research artifacts.

This keeps a deterministic local Study possible without provider credentials or
scientific Python packages, while allowing a specific Study to opt into the
dependencies it actually needs.

## End-to-end files for a new Game

A small complete package can remain compact:

```text
my-behavior-study/
|-- study.yaml              # Question, phases, Conditions, Cells
|-- assembly.py             # exact Game, Players, Controllers, Runs
|-- measures.yaml           # explicit Measure declarations
|-- measures.py             # custom deterministic Measures, if needed
|-- research-profile.yaml   # recommended discovery metadata
`-- findings.yaml           # authored claims and exact citations
```

A complex Study may split Assemblies and declared artifacts into subdirectories.
Generated execution, analysis, and report output always lives outside authored
source.

## Command journey

```bash
# Understand and validate the complete plan without AgentDeck provider calls
agentdeck study inspect my-behavior-study
agentdeck study validate my-behavior-study

# Execute only an explicit approved scope
agentdeck study run my-behavior-study \
  --phase p0 \
  --approve <full-plan-sha256> \
  --output-root agentdeck_runs/studies

# Select exact Cells, Measures, and corpus origin
agentdeck study analyze my-behavior-study \
  --cell control --cell treatment \
  --measure behavior-rate \
  --execution agentdeck_runs/studies/.../execution.json \
  --output-root agentdeck_runs/analysis

# Render one authored claim from exact Evidence artifacts
agentdeck study report my-behavior-study/findings.yaml \
  --finding declared-behavior-change \
  --evidence agentdeck_runs/analysis/.../evidence/behavior-rate.json \
  --output agentdeck_runs/reports/declared-behavior-change
```

There is no implicit “run everything,” automatic Measure selection, or
automatic claim synthesis.

## Generated output

### Execution output

```text
<output-root>/<study-id>/<execution-id>/
|-- prepared-study.json
|-- selection.json
|-- execution.json
`-- execution-groups/<group-id>/
    |-- prepared-assembly.json
    |-- execution.json
    `-- assembly-output/.../records/match_*.json
```

This layer provides the inspected plan, authorization, exact execution receipts,
usage, failures, canonical Records, and replay source.

### Analysis output

```text
<output-root>/<study-id>/<analysis-id>/
|-- prepared-study.json
|-- corpus.json
|-- analysis.json
|-- measures/<measure-id>.json
`-- evidence/<measure-id>.json
```

This layer provides exact corpus membership, transformation identities,
material environment, assumptions, flat results, diagnostics, and Evidence
hashes.

### Finding output

```text
<finding-output>/
|-- finding.json
`-- report.md
```

`finding.json` is the canonical authored interpretation with exact citations.
`report.md` is a deterministic human representation showing values, dimensions,
phase, corpus origin, hashes, limitations, and the assurance boundary.

## What The Agentic Edge proves

The current architecture materializes The Agentic Edge as:

- one normal `study.yaml` with 19 Cells and four phases;
- ordinary Prepared Assemblies describing 540 planned Matches;
- two independent Game Research Profiles;
- one imported, checksum-verified historical corpus;
- two ordinary Measures: outcome/statistics and combat behavior;
- normal Evidence artifacts;
- normal authored Findings and deterministic reports.

The current reproducer:

- verifies all 540 frozen source Records;
- preserves every `source_sha256 -> adapted_sha256` mapping;
- derives Evidence over the 432 primary/supplemental Records;
- reproduces 99 of 99 frozen outcome/statistical values exactly;
- also derives the promoted behavioral Measure over the same identified corpus;
- leaves the frozen Hugging Face source untouched.

This validates the complete architecture against a real historical Study. The
orthogonal single-Player/no-winner acceptance Study is the separate proof that
the framework did not encode the flagship's competitive topology as a generic
concept.

## Current limits

The v0.1 arc deliberately does not provide:

- automatic natural-language Study or experimental-design generation;
- automatic Measure discovery or selection from a Game;
- a universal behavioral metric ontology;
- automatic calibration or scientific validation of an operationalization;
- proof that `intent: confirmatory` was preregistered before outcomes were seen;
- causal-inference guarantees;
- adaptive or sequential sampling; execution plans are fixed;
- automatic early stopping;
- automatic Finding or claim generation;
- peer review, publication, collaboration, or a knowledge graph;
- hostile-code sandboxing for custom Assembly or Measure Python;
- a completed human-annotation provenance contract;
- byte-identical repetition of mutable remote LLM behavior.

These limits are not gaps hidden behind generic words. They preserve the core
assurance model: execution facts are recorded, derivations are deterministic,
and interpretation remains explicit.

## Practical assessment

The arc is generic and decoupled enough to be used with any current or future
AgentDeck Game without modifying the Research framework. A new Game does not
need to inherit a Research base class, register a scorer, expose a winner, or
adopt a domain ontology.

What cannot be generic is the intellectual act of deciding which mechanics make
a behavior observable and how to operationalize that behavior honestly. The GRP
and Measure contracts give that domain knowledge a precise place without
letting it leak into Game execution, corpus identity, Evidence provenance, or
Finding assurance.

The delivered product value is therefore larger than “run agents and export
data”:

> Put AI inside an explicit world, observe what it does, determine what the
> observations support, and preserve the exact path from conclusion back to
> execution truth.

## Related contracts and working example

- [Research Constitution](../specs/SPEC-RESEARCH.md)
- [Game Research Profile](../specs/SPEC-GAME-RESEARCH-PROFILE.md)
- [Study](../specs/SPEC-STUDY.md)
- [Measure](../specs/SPEC-MEASURE.md)
- [Evidence](../specs/SPEC-EVIDENCE.md)
- [Finding](../specs/SPEC-FINDING.md)
- [Study package](../specs/SPEC-STUDY-PACKAGE.md)
- [Study CLI](../specs/SPEC-STUDY-CLI.md)
- [The Agentic Edge](../research/2026-04-27-agentic-edge-strategy-stack/README.md)
- [End-to-end reproduction](../research/2026-04-27-agentic-edge-strategy-stack/reproduction.md)
