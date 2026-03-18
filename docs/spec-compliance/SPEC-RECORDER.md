# SPEC-RECORDER Audit Note

Spec: [SPEC-RECORDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RECORDER.md)
Wave: 4
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Match and batch recording, progressive persistence, schema tagging, prompt metadata embedding, and load-time normalization.
- Does not own live execution decisions, replay scheduling, or research analysis.

## Evidence Reviewed
- spec sections: full document, especially §§3-7 and references
- implementation files: [recorder.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/recorder.py)
- tests: [test_recorder_lifecycle.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_recorder_lifecycle.py)
- docs/examples: recorder/research/viewer adjacent docs

## Findings

### Blocker
- none

### High
- The spec still described a `NullRecorder` pattern that no longer exists in the shipped code.
- It also implied broader event ownership than the actual implementation, which records batch/match/gameplay/domain/lifecycle artifacts relevant to persisted recordings but does not implement session handlers.
- The documented constructor default (`output_dir="records"`) had drifted from the real default (`"agentdeck_records"`).

### Medium
- API-usage wording implied collectors handled built-in token aggregation even though that work is done by `APIUsageTracker`.
- Multiple version-pinned adjacent references added noise rather than contract clarity.

### Low
- none

## Drift Classification Summary
- implementation drift: 0
- spec drift: 5
- test drift: 0
- doc/example drift: 1

## Required Remediation
- Remove the nonexistent `NullRecorder` contract.
- Align constructor defaults and recorder responsibilities to the real implementation.
- Keep prompt-metadata and batch/match schema guarantees, which are already strongly tested.

## Beta Relevance
- required before beta: yes, because recorder schema fidelity underpins replay, viewer, research packaging, and public reproducibility claims
- safe to defer: additional helper APIs that do not change the persisted contract

## Final Verdict
- [SPEC-RECORDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RECORDER.md) is compliant after Wave 4 cleanup. The recorder implementation was already solid; the main work was removing stale Null-object assumptions and aligning the spec to the current persisted contract.
