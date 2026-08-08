# AgentDeck Core Roadmap

> Status: Active
> Updated: 2026-08-08
> Branch: `codex/ai-first-builder-readiness`
> Authority: specifications in `specs/` remain the source of truth

## Objective

Make AgentDeck Core a deterministic, secure, machine-legible certifier for externally
authored Instrument Packages without coupling the Core to any Builder, product workflow,
model provider, or research agenda.

The implementation rationale and verified baseline are recorded in
[`docs/audits/CORE-AI-FIRST-BUILDER-READINESS-REVIEW-2026-08-07.md`](docs/audits/CORE-AI-FIRST-BUILDER-READINESS-REVIEW-2026-08-07.md).

## Delivery Rules

- Specs are committed before the implementation they govern.
- Each completed wave receives its own validation and commit.
- Invariant IDs map to direct tests; adjacent coverage is not sufficient.
- Official Games and external packages pass through the same public certifier.
- Generated Python is always treated as executable code, never as inert package data.
- The Builder remains a separate consumer with its own repository and lifecycle.

## Waves

| Wave | Outcome | Status | Exit gate |
|---|---|---|---|
| C0 | Canonical evidence and artifact safety | Complete | Path escapes, lossy JSON, incomplete configuration snapshots, and undeclared trust fail safely |
| C1 | Instrument Package Contract | Complete | An external package reaches `runnable` through deterministic `inspect`, `validate`, and `certify` APIs |
| C2 | Machine-verifiable spec system | Complete | Active authoring contracts and compliance evidence are selected and validated mechanically |
| C3 | Golden instrument certification | Complete | FixedDamage and an external fixture pass the same tiered certifier; adversarial mutations fail |
| C4 | Runtime boundary and typed authoring API | Complete | Extensions use public runtime mechanics, strict public typing, and real security gates |
| C5 | Honest compliance and artifact publication | In progress | Assurance is non-vacuous; canonical writes and package publication fail atomically |
| B0 | AgentDeck Builder bootstrap | Complete | A separate Builder invokes Codex CLI and produces a certified contained package from intent |

## C0: Canonical Evidence And Artifact Safety

- [x] Approve strict JSON, complete snapshot, safe path, and trusted-code contracts.
- [x] Reject unsafe artifact identifiers and prove output containment.
- [x] Enforce strict JSON state and visible views at the runtime boundary.
- [x] Remove coercive serialization from canonical Recorder artifacts.
- [x] Record effective Game, Player, Controller, Renderer, prompt, and lifecycle config.
- [x] Preserve compatibility with official Games and valid historical records.
- [x] Add adversarial tests for all corrected paths.

Validation: Core CI passed with `620 passed, 2 skipped` on 2026-08-07.

## C1: Instrument Package Contract

- [x] Approve the versioned manifest and capability tiers.
- [x] Define structural inspection separately from trusted execution.
- [x] Implement deterministic `inspect`, `validate`, and `certify` APIs and CLI.
- [x] Declare config schemas, entry points, fixtures, visibility, metrics, and presentation.
- [x] Prove that certification contains no Game-name branches.

Validation: the external `NumberDuel` fixture reaches `runnable` through the public
certifier with deterministic execution, replay parity, and no built-in registry.

## C2: Machine-Verifiable Specs

- [x] Define canonical spec metadata, lifecycle, and compliance evidence states.
- [x] Correct stale versions, implementation states, and public API claims.
- [x] Generate deterministic active-spec and authoring-context registries.
- [x] Validate links, invariant keys, profile sources, and evidence mappings in CI.
- [x] Publish an honest initial compliance matrix without grouped assurance shortcuts.

Validation: 33 Final contracts are registered; one deprecated viewer remains
discoverable but inactive. The initial matrix deliberately reports legacy contracts as
partial, while SR1-SR10 have direct automated evidence. The `instrument-builder`
profile is a closed, ordered, deterministic context rather than an all-spec glob.

## C3: Golden Instruments

- [x] Specify the FixedDamage behavioral profile.
- [x] Package FixedDamage without changing its current semantics.
- [x] Add a tiny external instrument fixture outside `src/agentdeck`.
- [x] Certify runnable, evidence-ready, and presentable capabilities independently.
- [x] Reject oracle leaks, nondeterminism, malformed metrics, invalid state, and path escapes.

Validation: canonical FixedDamage and external NumberDuel both receive `runnable`,
`evidence_ready`, and `presentable` from the same public certifier. The evidence tier
resolves exact scorer and record pointers; the presentation tier rebuilds Match Surfaces
from Player-visible state and rejects declared oracle paths.

## C4: Runtime And Public Authoring Surface

- [x] Complete `MatchRuntime` as the public mechanics gateway.
- [x] Remove direct private Console access from the turn loop.
- [x] Consolidate lifecycle paths where equivalence is proven by tests.
- [x] Add strict typing gates for public extension examples.
- [x] Add real dependency and security audit jobs with reviewed baselines.

Validation: stock mechanics contain zero private Console access; the complete external
NumberDuel package passes strict consumer typing and the production certifier. Local and
hosted CI now block on Bandit medium/high findings and the pinned runtime vulnerability
audit. Whole-Core legacy mypy debt remains explicitly outside this gate.

## B0: AgentDeck Builder

The separate `agentdeck-builder` repository began after the C0 and C1 gates passed.
Its first strategy is intentionally direct: run Codex CLI against the mechanically
selected Core authoring contracts, write into a contained `workspace-write` sandbox,
certify the result, and feed certification failures back into a bounded repair loop.

First acceptance mission:

`intent -> isolated FixedDamage reconstruction -> Core certification -> seeded run -> replay -> evidence`

The Builder may choose implementation details inside the package. It may not modify the
Core, bypass certification, silently repair evidence after execution, or claim a higher
capability tier than the certifier awards.

Validation: on 2026-08-08, Builder request
`fixed-damage-reconstruction-20260808T032849Z` used `gpt-5.5` with `xhigh` reasoning
against Core commit `091565a`. The independently generated package imported only the
public `agentdeck` API, passed strict consumer typing, and received `runnable`,
`evidence_ready`, and `presentable` from the real Core certifier. Certification produced
two deterministic seeded executions, replay parity, calibrated behavioral evidence,
and oracle-safe Match Surfaces without any Game-specific Core change.

The live acceptance also exposed a quality boundary outside current IP6: generated
instructions can describe default values while a constructor accepts alternate config.
The Builder records a config-variant instruction probe as its next promotion gate; Core
does not silently broaden the meaning of the already-awarded tiers.

## C5: Honest Compliance And Artifact Publication

- [x] Specify exact test-function evidence and non-vacuous verification.
- [x] Expose unregistered legacy invariants as migration debt.
- [x] Correct the trusted-local fixture boundary without claiming OS isolation.
- [x] Define strict atomic single-file writes and staged package publication.
- [x] Replace impossible byte-preservation language with semantic JSON preservation.
- [x] Implement exact registry evidence and public authoring imports.
- [ ] Implement the writer, packager, rescore, and certification changes.
- [ ] Add adversarial tests and regenerate the compliance projections.

This wave intentionally adds no research-quality gate and no semantic judgment about a
Game's instructions, metrics, or hypotheses. It strengthens only claims the Core can
verify mechanically while preserving the freedom to build and run unconventional
instruments.

## Definition Of Done

- Core CI passes from a clean checkout without provider credentials.
- Every new invariant has a named direct test.
- The source tree and generated artifacts remain inside declared roots.
- Certification output is deterministic JSON and records trust mode and provenance.
- A Codex-built external package runs through the real Core and produces replayable,
  packageable evidence without any Game-specific Core change.
