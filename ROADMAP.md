# AgentDeck Roadmap

Last updated: 2026-03-17
Owner: Diego + Codex + Claude

## Goal
Prepare AgentDeck for a disciplined public beta release by:
- validating the codebase against the full spec suite
- resolving release-relevant spec drifts
- producing a clean release-facing FixedDamage research package

## Release Position
- AgentDeck should be released as a public beta / preview, not `1.0`.
- The recent pre-release blocker sweep is complete and part of the current branch baseline.
- The next release risks are no longer just implementation bugs; they are spec-governance and contract-coherence risks.

## Baseline Already Landed
- Core fairness, recorder, artifact-validation, and metadata fixes
- Viewer beta baseline
- Research export, packaging, validation, and reset templates
- Cleaner release docs and spec wording around recent blocker fixes

## Current Release Workstreams

### 1. Spec Governance And Compliance
- [ ] Run a full spec-compliance assessment across `specs/*`, starting with the navigation hub and cross-spec coherence.
- [ ] For every spec, classify findings as one of:
  - implementation drift
  - spec drift
  - test drift
  - doc/example drift
- [ ] Resolve all blocker/high-severity drifts on release-critical surfaces before the public showcase.
- [ ] Produce a durable audit ledger so future work can be checked spec-first instead of rediscovering drift ad hoc.

### 2. Release Research Showcase
- [ ] Finalize the new FixedDamage release plan around AgentDeck-native features only.
- [ ] Keep the public study causally clean and behavior-first.
- [ ] Package one human-written public report with viewer-supported replay highlights.
- [ ] Use that package as the public proof of AgentDeck's research value.

## Release Gates

### Beta Gate
- No unresolved blocker-level spec drifts in core execution, player pipeline, observability, replay, or research packaging.
- `SPEC.md` and component specs agree on versions, statuses, and ownership boundaries.
- README/spec/docs/examples tell the same product story.
- One polished FixedDamage experiment package is ready for public viewing.

### `1.0` Gate
- Stronger methodological defaults for benchmark fairness
- At least one robust public benchmark package beyond a single showcase study
- Ongoing spec-compliance discipline built into normal development, not only pre-release cleanup

## Audit Order
1. Hub and cross-spec coherence
2. Core execution kernel
3. Player pipeline and prompt contracts
4. Observability, recorder, replay, and viewer
5. Research stack and package contracts
6. Public docs, examples, and release narrative alignment

## Immediate Next Steps
1. Execute the spec-compliance assessment plan in [docs/spec-compliance-audit-plan.md](/home/diegozoracky/dev/agentdeck-preview/docs/spec-compliance-audit-plan.md).
2. Fix any blocker/high-severity drifts discovered in the first audit wave.
3. Only then lock the release-facing FixedDamage matrix and start the new experiment runs.
