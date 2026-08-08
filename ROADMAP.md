# AgentDeck Core Roadmap

> Status: Active
> Updated: 2026-08-07
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
| C1 | Instrument Package Contract | Pending | An external package reaches `runnable` through deterministic `inspect`, `validate`, and `certify` APIs |
| C2 | Machine-verifiable spec system | Pending | Active authoring contracts and compliance evidence are selected and validated mechanically |
| C3 | Golden instrument certification | Pending | FixedDamage and an external fixture pass the same tiered certifier; adversarial mutations fail |
| C4 | Runtime boundary and typed authoring API | Pending | Extensions use public runtime mechanics, strict public typing, and real security gates |
| B0 | AgentDeck Builder bootstrap | Pending | A separate Builder invokes Codex CLI and produces a certified isolated package from intent |

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

- [ ] Approve the versioned manifest and capability tiers.
- [ ] Define structural inspection separately from trusted execution.
- [ ] Implement deterministic `inspect`, `validate`, and `certify` APIs and CLI.
- [ ] Declare config schemas, entry points, fixtures, visibility, metrics, and presentation.
- [ ] Prove that certification contains no Game-name branches.

## C2: Machine-Verifiable Specs

- [ ] Define canonical spec metadata, lifecycle, and compliance evidence states.
- [ ] Correct stale versions, implementation states, and public API claims.
- [ ] Generate deterministic active-spec and authoring-context registries.
- [ ] Validate links, public symbols, invariant keys, and evidence mappings in CI.
- [ ] Publish an honest initial compliance matrix without grouped assurance shortcuts.

## C3: Golden Instruments

- [ ] Specify the FixedDamage behavioral profile.
- [ ] Package FixedDamage without changing its current semantics.
- [ ] Add a tiny external instrument fixture outside `src/agentdeck`.
- [ ] Certify runnable, evidence-ready, and presentable capabilities independently.
- [ ] Reject oracle leaks, nondeterminism, malformed metrics, invalid state, and path escapes.

## C4: Runtime And Public Authoring Surface

- [ ] Complete `MatchRuntime` as the public mechanics gateway.
- [ ] Remove direct private Console access from the turn loop.
- [ ] Consolidate lifecycle paths where equivalence is proven by tests.
- [ ] Add strict typing gates for public extension examples.
- [ ] Add real dependency and security audit jobs with reviewed baselines.

## B0: AgentDeck Builder

The separate `agentdeck-builder` repository begins only after C0 and C1 gates pass.
Its first strategy is intentionally direct: run Codex CLI against the mechanically
selected Core authoring contracts, write into an isolated workspace, certify the result,
and feed certification failures back into a bounded repair loop.

First acceptance mission:

`intent -> isolated FixedDamage reconstruction -> Core certification -> seeded run -> replay -> evidence`

The Builder may choose implementation details inside the package. It may not modify the
Core, bypass certification, silently repair evidence after execution, or claim a higher
capability tier than the certifier awards.

## Definition Of Done

- Core CI passes from a clean checkout without provider credentials.
- Every new invariant has a named direct test.
- The source tree and generated artifacts remain inside declared roots.
- Certification output is deterministic JSON and records trust mode and provenance.
- A Codex-built external package runs through the real Core and produces replayable,
  packageable evidence without any Game-specific Core change.
