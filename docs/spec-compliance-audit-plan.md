# AgentDeck Spec-Compliance Audit Plan

Last updated: 2026-03-17
Status: Historical audit plan

## Purpose
Run a deep, systematic compliance assessment across the full AgentDeck spec suite so the release is grounded in the actual source of truth, not only in passing code reads or spot fixes.

This plan exists because recent work surfaced real drift in:
- prompt defaults
- handshake contract wiring
- test expectations that had drifted with implementation

The goal is to prevent more of that from hiding in other surfaces.

## Scope

### In Scope
- [SPEC.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC.md)
- [SPEC-AGENTDECK.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-AGENTDECK.md)
- [SPEC-CONSOLE.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONSOLE.md)
- [SPEC-GAME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME.md)
- [SPEC-GAME-MECHANIC-TURN-BASED.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME-MECHANIC-TURN-BASED.md)
- [SPEC-MATCH-RUNTIME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MATCH-RUNTIME.md)
- [SPEC-PARALLEL.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PARALLEL.md)
- [SPEC-PLAYER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PLAYER.md)
- [SPEC-CONTROLLER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONTROLLER.md)
- [SPEC-PROMPT-BUILDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PROMPT-BUILDER.md)
- [SPEC-RENDERER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RENDERER.md)
- [SPEC-LLM.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-LLM.md)
- [SPEC-PRICING.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PRICING.md)
- [SPEC-OBSERVABILITY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-OBSERVABILITY.md)
- [SPEC-SPECTATOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-SPECTATOR.md)
- [SPEC-MONITOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MONITOR.md)
- [SPEC-RECORDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RECORDER.md)
- [SPEC-REPLAY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-REPLAY.md)
- [SPEC-VIEWER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-VIEWER.md)
- [SPEC-RESEARCH.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH.md)
- [SPEC-RESEARCH-EXPERIMENT.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-EXPERIMENT.md)
- [SPEC-RESEARCH-PACKAGER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-PACKAGER.md)

### Reference Inputs
- [GUIDELINES.md](/home/diegozoracky/dev/agentdeck-preview/specs/GUIDELINES.md)
- [README.md](/home/diegozoracky/dev/agentdeck-preview/README.md)
- [CONTRIBUTING.md](/home/diegozoracky/dev/agentdeck-preview/CONTRIBUTING.md)
- public examples, viewer docs, research templates, and targeted test suites

### Out Of Scope
- New benchmark design itself
- New product features that are not required to restore compliance
- Polishing every example unless it affects a spec-backed contract

## Audit Principles
- Spec is the source of truth unless the spec itself is internally inconsistent.
- Every finding must be classified before it is fixed.
- Tests are evidence, not truth. Tests can drift too.
- Prefer narrow, contract-based fixes over opportunistic refactors.
- Do not blur implementation drift and spec drift into the same bucket.
- Keep audited specs contract-focused. Do not add rolling in-spec changelog blocks during remediation; use git history and the audit notes for change narrative.

## Finding Taxonomy

### By Drift Type
- `implementation drift`: code behavior does not match the spec
- `spec drift`: spec no longer reflects the intended or shipped contract
- `test drift`: tests encode behavior that conflicts with the spec
- `doc/example drift`: README, examples, or viewer/docs contradict the spec or code

### By Severity
- `blocker`: release-critical contract is wrong, missing, or misleading
- `high`: important inconsistency that undermines confidence or expected usage
- `medium`: bounded inconsistency with workarounds
- `low`: wording, examples, stale metadata, or cleanup-only issues

## Deliverables

### 1. Audit Ledger
Create a durable ledger under `docs/spec-compliance/` with:
- one `INDEX.md` summarizing overall status
- one note per audited spec

Each spec note should capture:
- scope of the component
- verdict: `compliant`, `mostly compliant`, `partial`, `drifted`, or `blocked`
- findings list with severity and drift type
- evidence: code paths, tests, docs
- required remediation
- whether the remediation is required for beta

### 2. Remediation PRs / Commits
For each audit wave:
- fix blocker/high items immediately
- either fix medium items or backlog them explicitly
- never leave ambiguous status after a wave ends

### 3. Release Summary
Before beta:
- concise summary of remaining accepted drifts
- rationale for anything intentionally deferred

## Per-Spec Assessment Method
For each spec, perform the same sequence:

1. Read the spec end-to-end.
2. Extract:
   - purpose and scope
   - public API / data structures
   - invariants and guarantees
   - interaction rules with adjacent components
   - testing strategy claims
3. Map the spec to implementation surfaces:
   - source files
   - relevant tests
   - relevant docs/examples
4. Check four classes of coherence:
   - spec vs implementation
   - spec vs tests
   - spec vs docs/examples
   - spec vs adjacent specs
5. Record findings before making fixes.
6. Fix blocker/high issues.
7. Add or tighten targeted tests where a contract was previously unguarded.
8. Update the ledger with the final verdict for that spec.

## Audit Order

### Wave 0. Audit Framework
- Create the ledger structure
- Define note template and severity labels
- Freeze the audit method so all waves use the same criteria

### Wave 1. Hub And Cross-Spec Coherence
Audit:
- [SPEC.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC.md)

Focus:
- component list, versions, statuses
- missing or stale cross-references
- product framing consistency
- contradictions between hub language and component specs

Exit criteria:
- hub accurately reflects the current component spec set
- no misleading status/version mismatches remain

### Wave 2. Core Execution Kernel
Audit:
- [SPEC-AGENTDECK.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-AGENTDECK.md)
- [SPEC-CONSOLE.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONSOLE.md)
- [SPEC-GAME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME.md)
- [SPEC-GAME-MECHANIC-TURN-BASED.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME-MECHANIC-TURN-BASED.md)
- [SPEC-MATCH-RUNTIME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MATCH-RUNTIME.md)
- [SPEC-PARALLEL.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PARALLEL.md)

Focus:
- lifecycle ordering
- fairness and player-order semantics
- handshake/conclusion flow ownership
- runtime bindings
- deep-copy / isolation expectations
- determinism and seed propagation

Exit criteria:
- no blocker/high drift in match execution contracts

### Wave 3. Player Pipeline And Prompt Contracts
Audit:
- [SPEC-PLAYER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PLAYER.md)
- [SPEC-CONTROLLER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONTROLLER.md)
- [SPEC-PROMPT-BUILDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PROMPT-BUILDER.md)
- [SPEC-RENDERER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RENDERER.md)
- [SPEC-LLM.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-LLM.md)
- [SPEC-PRICING.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PRICING.md)

Focus:
- handshake vs turn vs conclusion contracts
- prompt placeholders and default templates
- controller binding semantics
- provider metadata, retries, costs, and history
- default behavior for out-of-the-box users

Exit criteria:
- no blocker/high drift in the player prompt/response pipeline

### Wave 4. Observability, Replay, And Viewer
Audit:
- [SPEC-OBSERVABILITY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-OBSERVABILITY.md)
- [SPEC-SPECTATOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-SPECTATOR.md)
- [SPEC-MONITOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MONITOR.md)
- [SPEC-RECORDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RECORDER.md)
- [SPEC-REPLAY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-REPLAY.md)
- [SPEC-VIEWER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-VIEWER.md)

Focus:
- event ordering and payload completeness
- prompt metadata capture
- replay parity
- viewer schema assumptions
- monitor vs spectator role split

Exit criteria:
- no blocker/high drift in observability or replay artifacts

### Wave 5. Research Stack
Audit:
- [SPEC-RESEARCH.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH.md)
- [SPEC-RESEARCH-EXPERIMENT.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-EXPERIMENT.md)
- [SPEC-RESEARCH-PACKAGER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-PACKAGER.md)

Focus:
- package schema, manifest/results contracts, and index generation
- artifact validation requirements
- metric definitions
- public-package expectations

Exit criteria:
- the release-facing research package can be trusted as spec-backed output

### Wave 6. Public Surface Alignment
Audit:
- [README.md](/home/diegozoracky/dev/agentdeck-preview/README.md)
- [viewer/README.md](/home/diegozoracky/dev/agentdeck-preview/viewer/README.md)
- [examples/README.md](/home/diegozoracky/dev/agentdeck-preview/examples/README.md)
- research templates and public docs

Focus:
- product framing consistency
- install/use flows
- defaults users actually experience
- example narratives matching the real contract

Exit criteria:
- docs no longer advertise behavior that the specs or code do not support

## Definition Of Done Per Spec
A spec is considered fully assessed only when:
- its own wording is internally coherent
- adjacent specs do not contradict it
- implementation behavior is mapped and verified
- targeted tests cover the most important invariants
- examples/docs do not undermine the contract
- the ledger records a clear verdict and any remaining accepted gaps

## Beta Exit Criteria For The Whole Audit
- All specs have an audit note and final verdict
- No unresolved blocker-level drifts remain on release-critical surfaces
- Any accepted high/medium drifts are explicitly documented with rationale
- The product and research release story uses only behavior that has passed the audit

## Practical Notes
- Start with the hub and the player pipeline because recent drift already appeared there.
- Keep each wave narrow enough that fixes can be landed before moving on.
- Do not start new public experiments until Wave 1 and Wave 3 are complete, because those waves define the default user-facing contract.
