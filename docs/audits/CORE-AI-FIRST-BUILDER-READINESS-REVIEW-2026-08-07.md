# AgentDeck Core: AI-First Builder Readiness Review

Date: 2026-08-07

Status: Final assessment; no implementation changes are included in this review

Repository: `agentdeck-core` at `5c5a7ec`

## 1. Decision

`agentdeck-builder` is a sufficient name for the future standalone builder.

The Core should remain consumer-agnostic. It should not know whether its caller is a
human, an AI agent, the AgentDeck product, a CLI, or another service. Its responsibility
is to publish precise contracts, execute conforming components, preserve complete
evidence, and reject invalid artifacts early.

The current Core is architecturally sound and already unusually legible to coding
agents. It is not yet ready to be the unquestioned authority behind an autonomous
instrument builder. The blocker is not a weak engine. The blocker is the missing
contract between "a Game that runs" and "a complete, reproducible research instrument
that can be certified and promoted."

The recommended order is:

1. Fix the confirmed Core correctness and security defects.
2. Specify a versioned Instrument Package Contract and conformance protocol.
3. Make active specs and invariant evidence mechanically discoverable in this repo.
4. Certify one external reference instrument without changing Core internals.
5. Create `agentdeck-builder` and make that certification gate its definition of done.

Starting the Builder before steps 1-4 would encode repository conventions and tacit
knowledge into prompts. It could generate code that works while still losing method
configuration, weakening replay, or omitting the behavioral and presentation layers.

## 2. Scope

This review covers the current source repository only:

- architecture and dependency direction
- execution, recording, replay, and research packaging
- security boundaries relevant to generated components and untrusted artifacts
- specification lifecycle and spec-to-code traceability
- AI legibility for an agent operating from a source checkout
- tests, type contracts, and CI gates
- readiness to support a separate autonomous Builder

The published PyPI artifact and its packaging contents are explicitly outside scope.

## 3. Evidence Collected

### Repository baseline

- Local `main` and `origin/main` are synchronized (`0 0`).
- Worktree was clean before this report was added; the report is the only new file.
- Current GitHub CI run for `5c5a7ec` is green.
- Public root exports: 49 declared, 49 resolvable.
- Public research exports: 34 declared, 34 resolvable.

### Executed gates

- Core CI: 585 collected, 583 passed, 2 skipped.
- Coverage: 80.59% line coverage.
- Black: 140 files unchanged.
- Pylint: 10.00/10 under the repository gate.
- mypy: 198 errors across 37 files; currently non-blocking in CI.
- Bandit: no medium- or high-severity findings; 17 low-severity findings.
- A clean resolution of the dependencies declared by the current repo reported no
  known vulnerability. The CI job named `Dependency Audit` does not currently perform
  this check.

### Direct behavioral proofs

The review did not rely only on text search.

1. A Game returning a `set` inside canonical state completed successfully. Recorder
   converted the set to a string through `json.dump(..., default=str)`. The resulting
   record was JSON, but it no longer represented the original state type.
2. A non-default `FixedDamageGame` run recorded only Game name/module. It lost
   `max_health`, damage, potion settings, and `information_level`. Player records also
   omitted the full Controller, Renderer, and template descriptions required by the
   Recorder spec.
3. A Match Surface document with `match_id="../escaped"` wrote outside its configured
   output directory.
4. An experiment ID containing enough parent segments resolved outside
   `research_dir` after `normalize_research_experiment_id()`.
5. Importing a package-local behavioral scorer executed an import-time filesystem side
   effect. This confirms that scorer loading is arbitrary Python execution, not data
   loading.

## 4. What Is Strong

### 4.1 The component model is real

The central architecture is not cosmetic:

- Game owns rules, state transitions, views, actions, and lifecycle hooks.
- Player owns handshake, decision, and conclusion behavior.
- Controller owns response contracts and parsing.
- Renderer transforms player-visible state into model input.
- Spectator observes without participating in Game semantics.
- Recorder persists canonical lifecycle and gameplay artifacts.
- Replay re-emits recorded evidence without invoking providers.
- Research derives objective results, statistics, behavioral profiles, and packages.

There is no second hidden Game engine inside research or product-oriented code. This is
the right foundation for generated instruments.

### 4.2 Policy and mechanism are mostly separated

The Core does not know about product Questions, wallets, catalog promotion, or UI
workflows. Provider integrations remain Players; presentation remains Renderer/
Spectator territory; research calculations consume records. This boundary should be
preserved.

### 4.3 Determinism and lifecycle are first-class

Seed derivation, ordered replay, handshake, gameplay, conclusion, batch lifecycle,
parallel isolation, and event projection all have concrete implementations and broad
test coverage. The direct lifecycle replay tests are particularly valuable for a
Builder because they make generated Games observable through the same canonical path.

### 4.4 The source repo is already AI-friendly

The repo has the right raw materials:

- explicit component specs
- a strict spec-first contribution process
- numbered invariants
- runnable examples
- deterministic mock Players
- official Game examples with tests
- research packages showing real usage
- a spec bundling script

The previous blind authoring tests succeeded for a reason. A strong coding agent can
infer the framework and produce compatible code. The remaining work is to make success
defined and mechanically certified rather than dependent on the agent's judgment.

## 5. Confirmed Findings

### F1. Path traversal in artifact output and research package IDs

Severity: P0 security

Evidence:

- `src/agentdeck/spectators/match_surface.py:66-78` derives an output path directly
  from `document.match.match_id`.
- `src/agentdeck/research/packager.py:23-32` adds a prefix but does not reject path
  separators or parent segments.
- `src/agentdeck/research/packager.py:497-504` joins the resulting ID to
  `research_dir` without a containment check.

Observed behavior:

- `../escaped` escaped `JsonArtifactSink.output_dir`.
- `../../../outside` escaped the intended `research_dir` boundary after normalization.

Why it matters:

`SECURITY.md` explicitly includes path traversal and untrusted replay JSON in scope. A
generated or imported artifact must never select a filesystem destination.

Required outcome:

- One shared identifier/path policy for match, session, batch, experiment, package,
  and artifact IDs.
- Reject separators, parent segments, absolute paths, control characters, and empty
  normalized IDs.
- Resolve every write target and assert containment before creating files.
- Add adversarial tests through public APIs, including replay-to-Match-Surface paths.

### F2. Canonical Game state is not globally enforced as JSON-serializable

Severity: P0 evidence correctness

Evidence:

- `SPEC-GAME` GS1/GS3 requires JSON-serializable canonical state.
- `Game.validate_state()` is a no-op by default at
  `src/agentdeck/core/base/game.py:323-347`.
- `MatchRuntime.validate_state()` only delegates to the Game at
  `src/agentdeck/core/match_runtime.py:379-406`.
- Recorder masks violations with `default=str` at
  `src/agentdeck/core/recorder.py:765-770`.

Observed behavior:

A state containing a Python `set` ran to completion and was persisted as a string.
Replay then received a different type from the one the Game executed.

Why it matters:

This breaks the meaning of exact recording/replay and lets a generated Game pass while
silently corrupting its evidence.

Required outcome:

- Runtime performs a strict JSON serialization check after setup and every update,
  independently of optional domain validation.
- The check includes a useful path to the invalid value.
- Recorder removes `default=str` for canonical artifacts.
- Domain `Game.validate_state()` remains additive and side-effect free.

### F3. Recorder does not preserve the configuration promised by its Final spec

Severity: P0 reproducibility and spec compliance

Evidence:

- `SPEC-RECORDER` MC3/MC4 requires complete Player configuration/templates and Game
  name/module/information level/allowed actions.
- `src/agentdeck/core/recorder.py:323-349` stores reduced summaries.
- `_get_player_configs()` at `src/agentdeck/core/recorder.py:859-877` omits full
  Controller, Renderer, PromptBuilder, and template descriptions.
- Game configuration records only name and module.
- `Player.describe()` already exposes substantially richer data at
  `src/agentdeck/core/base/player.py:626-653`, but Recorder does not use it.

Observed behavior:

A run with non-default FixedDamage settings could not reconstruct those settings from
its record. The Research Packager accepts an explicit `game_config`, but the recording
does not provide it automatically.

Why it matters:

An autonomous Builder can produce a logically valid instrument and still create
evidence that cannot reconstruct which instrument was run.

Required outcome:

- Define a JSON-serializable component description contract for Game as well as the
  existing Player/Controller/Renderer descriptions.
- Recorder stores immutable snapshots of effective Game, Player, Controller, Renderer,
  PromptBuilder, templates, provider/model parameters, and relevant policies.
- Research packaging derives effective configuration from records by default; explicit
  caller context is an override or compatibility path, not the normal source.
- Add round-trip tests using non-default nested configurations.

### F4. Executable extensions are treated as data without an explicit trust contract

Severity: P0 for generated/self-serve instruments; accepted local behavior today

Evidence:

- `src/agentdeck/research/score.py:78-96` imports and executes package-local Python
  using `exec_module()`.
- Generated Games, Players, Renderers, and Spectators are also Python code by design.
- The scorer spec says import-time side effects must not occur, but an in-process loader
  cannot enforce that statement.

Observed behavior:

A scorer created a file during module import before any scorer method was called.

Why it matters:

The future Builder will create executable code. Correct architecture requires saying
where trust begins, not pretending code loading is safe because the manifest is valid.

Required outcome:

- Document two distinct operations: structural validation of a package and execution
  of trusted package code.
- Core may provide conformance APIs, but must not claim to sandbox Python.
- Conformance output declares the trust assumption used.
- The Builder or its runner executes generated packages in an isolated process/
  container with constrained filesystem, network, credentials, time, and memory.
- Package-local scorer documentation explicitly states that loading executes code.

### F5. There is no complete Instrument Package Contract

Severity: P0 Builder readiness

The existing specs describe individual components well, but no contract answers:

- What files make one generated instrument complete?
- Which class is its Game entry point?
- What is its machine-readable configuration schema?
- Which actions, participant counts, and lifecycle phases does it support?
- Which fields are oracle/hidden and how is player visibility tested?
- What deterministic Players or fixtures calibrate its rules?
- Which behavioral profile is available and what does each metric mean?
- Which evidence paths support each metric?
- Is a Match Surface projection available?
- Are viewer assets optional, and how are they located?
- Which package/spec versions produced the artifact?
- What does "runnable", "evidence-ready", and "presentable" mean?

This missing aggregate contract explains the prior FixedDamage reconstruction result:
the generated code was compatible with the engine, but productization details had to
be supplied later through assembly and local knowledge.

Required outcome:

Create a minimal, versioned `SPEC-INSTRUMENT-PACKAGE` with capability tiers:

1. Runnable
   - Game entry point
   - configuration schema and effective config snapshot
   - participant/action/lifecycle contract
   - deterministic smoke fixture
   - visibility and JSON-state checks
2. Evidence-ready
   - behavioral profile ID/version
   - metric definitions and evidence paths
   - deterministic calibration Players/fixtures
   - package/result validation
3. Presentable
   - Match Surface compatibility
   - redaction policy
   - optional viewer/stage assets and their declared entry points

The tiers avoid making a custom viewer or scorer mandatory for every experimental Game
while preventing a merely runnable Game from being presented as a research-ready one.

### F6. Spec lifecycle and traceability are not mechanically trustworthy

Severity: P1 spec-first integrity

Evidence:

- 32 specification documents are present.
- The main spec table has stale versions for Player, Controller, Renderer,
  PromptBuilder, Research, Research Experiment, Research Packager, Match Surface, and
  Viewer.
- Several implemented v2 contracts still say `Implementation: Planned`.
- `SPEC-RESEARCH-SCORE` uses an implementation state in the Status field rather than a
  lifecycle state.
- The main Public API example names `progressive_comparison`, `parameter_sweep`, and
  `EloLeague`; none exists. The actual progressive function is
  `compare_models_progressive`.
- 467 invariant-like IDs were found. Ninety-four IDs are reused across specs.
- Only 127 of 467 IDs appear textually in tests. This is not proof that 340 behaviors
  are untested, but it proves the repo cannot currently derive compliance from direct
  evidence.

Why it matters:

An AI agent follows declared truth literally. Stale versions, false API examples, and
ambiguous invariant IDs create deterministic implementation errors.

Required outcome:

- Add canonical front matter to every spec: `spec_id`, `version`, `status`,
  `supersedes`, `implementation`, `audience`, and dependencies.
- Add a machine-readable spec registry generated from and validated against those
  headers.
- Key invariants by `(spec_id, invariant_id)`; do not assume IDs are global.
- Add a compliance matrix with evidence type: `mapped`, `automated`, `semantic`.
- CI rejects stale index versions, nonexistent public API symbols, invalid lifecycle
  transitions, missing referenced files, and `automated` claims without direct tests.
- Keep semantic review distinct from automated evidence.

### F7. AI context exists, but selection and task guidance remain implicit

Severity: P1 AI legibility

Evidence:

- `scripts/bundle_specs.py` concatenates all specs, includes a wall-clock timestamp,
  and does not distinguish active, superseded, legacy, or task-relevant contracts.
- There is no concise machine-readable map from authoring task to required specs,
  examples, public symbols, and conformance commands.
- Built-in Games expose constructor signatures and `allowed_actions`, but no common
  `describe()`, `config_schema`, capability descriptor, behavioral profile pointer, or
  viewer pointer.

Why it matters:

More context is not the same as better context. A Builder needs the smallest complete
contract set for its task and a deterministic way to prove it satisfied that set.

Required outcome:

- Make the spec bundle deterministic; remove the current-time field or derive it from
  source control metadata.
- Bundle active specs only by default and retain explicit flags for legacy/history.
- Add an authoring manifest such as `contracts/authoring.json` that maps tasks to
  specs, examples, public imports, outputs, and validation commands.
- Add JSON output to all conformance commands.
- Add a repo-root AI orientation file only after the contracts above exist; it should
  point, not duplicate.

### F8. Game-specific research completeness is inconsistent

Severity: P1 Builder reference quality

Evidence:

- VariableDamage has a Game spec and a detailed behavioral profile spec.
- Archivist Choice has a behavioral profile spec.
- FixedDamage has a Game spec, calibration bots, and a large behavioral scorer, but no
  dedicated FixedDamage behavioral profile spec.
- Hangman has visibility tests and a Game implementation, but no Game-specific spec or
  promoted behavioral profile.
- Built-in scorer discovery is a hardcoded registry of three implementations.

Why it matters:

FixedDamage is the likely golden reconstruction target, yet part of its intended
instrument semantics lives only in code and research history. A Builder should not be
required to reverse-engineer metric meaning from a 600-line scorer.

Required outcome:

- Complete the FixedDamage behavioral profile spec before using it as the golden
  Builder acceptance target.
- Declare each built-in Game's capability tier explicitly.
- Keep Hangman unpromoted unless/until it satisfies the selected tier.
- Replace implicit built-in scorer discovery with the Instrument Package declaration,
  while preserving explicit Core allowlists where trust requires them.

### F9. MatchRuntime is not yet the exclusive mechanics gateway

Severity: P2 architecture

Evidence:

- `TurnLoop` accesses `runtime._console` for event bus, first-player metadata, logging,
  and `get_player_action()`.
- `src/agentdeck/core/mechanics/turn_based.py:513-526` documents this as a future
  refactor.
- `Console` and `_MatchWorker` both retain implementations of handshake, decision,
  parse failure, and conclusion behavior.
- Normal sequential and parallel runs use `_MatchWorker`, so the duplicate Console path
  is largely compatibility residue rather than two equally active engines.

Why it matters:

The current engine works, but another mechanic would either repeat protected access or
depend on behavior not published by MatchRuntime.

Required outcome:

- Complete the MatchRuntime public gateway for decisions, lifecycle emission, metadata,
  and logging.
- Move shared lifecycle behavior into one implementation used by workers and Console.
- Remove or explicitly deprecate compatibility paths after call-site proof.
- Add a minimal non-turn-based test mechanic to prove the boundary, not a full product
  feature.

### F10. The typing marker is ahead of the source contract

Severity: P2 public API quality

Evidence:

- `py.typed` is present.
- mypy reports 198 errors across 37 files under the repo's already permissive config.
- CI displays mypy output but always succeeds.

Required outcome:

- Define the typed public surface first rather than demanding strict typing for every
  internal module at once.
- Add a small strict consumer fixture that imports and composes public extension APIs.
- Ratchet errors down by module; do not use a global all-or-nothing migration.
- Keep `py.typed` only if the supported public surface is covered by the strict fixture.

### F11. CI names a dependency audit that does not audit vulnerabilities

Severity: P2 security operations

Evidence:

The GitHub job named `Dependency Audit` installs the project, imports it, installs dev
dependencies, and performs smoke imports. It does not run an advisory scanner.

Required outcome:

- Rename it to `Dependency Install Smoke` or add a real locked/declarative audit.
- Add Bandit or an equivalent static security check with an explicit reviewed baseline.
- Keep generated-code isolation tests separate; static scanning cannot certify trust.

## 6. Spec-Compliance Verdict

The Core is not 100% spec-compliant today.

Confirmed violations include:

- Recorder MC3/MC4 configuration fidelity.
- Game GS1/GS3 enforcement at the generic runtime boundary.
- The main spec's Public API listing.
- Spec index versions and implementation states.

The broader compliance percentage is unknown. The repository has strong adjacent tests,
but no mechanically defensible invariant-by-invariant matrix. It would be misleading to
turn textual ID counts into a compliance score.

The correct current claim is:

> Core behavior is broadly tested and current CI is green, but complete spec compliance
> has not yet been demonstrated. Several direct violations were reproduced.

## 7. Security Verdict

For trusted local research code, the Core has a reasonable security posture:

- safe YAML loading
- no `eval()` or shell interpolation in the reviewed runtime paths
- explicit provider credential handling
- canonical event and replay checks
- no medium/high generic static-analysis findings

For generated or externally supplied instruments, it is not ready:

- confirmed path traversal in two write boundaries
- arbitrary Python execution by design for Games and package scorers
- no declared trust/execution model
- no process/container isolation contract
- untrusted replay data can influence an artifact filename

This does not mean the Core should implement a container runtime. It means the Core must
state exactly what it validates and what remains executable trust, while the Builder
runner supplies isolation.

## 8. Proposed Core Evolution

### Wave C0: Correctness and path safety

Specs first:

- Amend Game/MatchRuntime/Recorder contracts for strict canonical JSON enforcement.
- Amend Recorder configuration snapshot requirements with exact schemas.
- Add a common safe artifact identifier/path contract.
- Clarify trusted-code execution for package-local Python.

Implementation:

- enforce strict JSON state at runtime
- remove `default=str` from canonical recording
- record complete effective component configurations
- validate IDs and output containment everywhere
- add adversarial replay/package tests

Exit gate:

- all four direct proofs in F1-F4 fail safely
- old valid records and official Games still pass compatibility tests

### Wave C1: Instrument Package Contract

Specs first:

- define package manifest and capability tiers
- define component entry points and effective config descriptors
- define calibration and visibility fixtures
- define behavioral profile and Match Surface declarations
- define trust metadata and conformance result schema

Implementation:

- one package loader for explicitly selected packages
- `inspect`, `validate`, and `certify` APIs with deterministic JSON output
- a conformance suite that runs against an external fixture package

Exit gate:

- a package outside `src/agentdeck` reaches `runnable` without Core edits
- evidence-ready and presentable capabilities are independently testable
- no Game name is hardcoded in the conformance engine

### Wave C2: Machine-verifiable spec system

Specs first:

- define spec metadata and lifecycle
- define compliance evidence states

Implementation:

- normalize all headers
- correct stale index/API claims
- generate deterministic active-spec registry/bundle
- validate links, versions, symbols, invariant keys, and evidence files in CI
- establish the initial honest compliance matrix

Exit gate:

- an agent can query the active contracts for "author a turn-based instrument" without
  reading superseded or irrelevant material
- CI cannot call a contract automated without a direct executable mapping

### Wave C3: Golden instrument certification

- Write the missing FixedDamage behavioral profile spec.
- Express official FixedDamage as the first complete Instrument Package.
- Preserve its current semantics, fixtures, scorer, and viewer declarations.
- Build a second tiny external instrument solely to prove generality.
- Run both through the same certifier.

Exit gate:

- the certifier distinguishes runnable, evidence-ready, and presentable
- a deliberate oracle leak, missing config, nondeterministic fixture, malformed metric,
  invalid state, or path escape is rejected

### Wave C4: Runtime boundary and typed extension surface

- Complete MatchRuntime as the public mechanics gateway.
- Remove duplicated lifecycle implementations where behavior is proven equivalent.
- Add strict type checks for the public authoring surface.
- Add real dependency/security jobs with reviewed baselines.

This wave may overlap C2/C3 where changes are local, but it should not delay the first
external package proof unless a duplicated path affects certification.

## 9. Builder Definition of Ready

Create the `agentdeck-builder` repo only when:

- C0 is complete.
- The Instrument Package spec is Final.
- Core exposes deterministic inspect/validate/certify commands or APIs.
- At least one instrument outside Core passes the runnable tier.
- FixedDamage's intended behavioral semantics are fully specified.
- Generated code has a documented isolated execution environment.
- The active authoring contract set can be selected mechanically.

## 10. Builder First Mission

The first serious Builder acceptance mission should remain the clean reconstruction of
FixedDamage from intent and active contracts, but the expected output changes.

The Builder must not merely produce a winning Game class. It must produce an isolated
Instrument Package that:

- extends the documented Core bases rather than reimplementing the engine
- declares every effective Game parameter
- defines player-visible state and proves oracle fields do not leak
- exposes allowed actions and lifecycle instructions
- includes deterministic calibration Players/fixtures
- records instructions in handshake evidence
- produces strict JSON canonical state
- passes seeded execution and replay parity
- declares and validates a behavioral profile if targeting evidence-ready
- projects a Match Surface without hardcoded product logic if targeting presentable
- preserves provenance and exact package version in the Research Package
- passes Core certification in isolation

Only after that succeeds should the Builder be connected to the magic product flow:

`idea -> generated instrument -> certified package -> isolated run -> evidence`

## 11. Explicit Non-Goals

The Core hardening should not add:

- product Questions or research agendas
- user/account/funding concepts
- Builder-specific prompts or model providers
- UI workflows
- autonomous approval policy
- MCP
- a universal ontology of Games
- a requirement that every Game have custom behavioral metrics or a viewer

Those belong to consumers or to optional capability tiers. The Core remains the neutral
execution and evidence authority.

## 12. Final Assessment

The architecture does not need a rewrite. The component boundaries, lifecycle, event
model, replay discipline, and research artifacts are strong enough to justify building
on them.

The required change is a shift from conventions that a capable AI can infer to
contracts that any Builder output must prove. That is the right AI-first evolution:

- less tacit repository knowledge
- more machine-readable authority
- earlier rejection of invalid instruments
- complete evidence of what actually ran
- explicit trust boundaries for executable code
- conformance independent of official Games

Once those conditions hold, `agentdeck-builder` can remain genuinely separate and the
Core will not need to know who is using it or why.
