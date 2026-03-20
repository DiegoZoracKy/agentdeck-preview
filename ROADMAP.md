# AgentDeck Roadmap

Last updated: 2026-03-20
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
- [x] Wave 0. Audit framework
- [x] Wave 1. Hub and cross-spec coherence
- [x] Wave 2. Core execution kernel
- [x] Wave 3. Player pipeline and prompt contracts
- [x] Wave 4. Observability, recorder, replay, and viewer
- [x] Wave 5. Research stack and package contracts
- [x] Wave 6. Public docs, examples, and release narrative alignment

## Immediate Next Steps
1. Lock the release-facing FixedDamage plan and encode it as an AgentDeck-native experiment package.
2. Run the new calibration and baseline cells on the audited codebase.
3. Package the first public showcase experiment and viewer-supported replay set.

## After Current Experiments
- [ ] Promote matrix-aware multi-session cell aggregation into the core research CLI so checkpoint expansions do not require package-local export logic.
  - Scope:
    - discover and retain full session history per `matrix.yaml` cell
    - export cell artifacts with canonical `source.recordings_dirs`
    - refresh package-level exports from aggregated cell history
  - Non-goal:
    - moving one-off experiment runners like `run_experiment.py` into the framework baseline
