# SPEC-MONITOR Audit Note

Spec: [SPEC-MONITOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MONITOR.md)
Wave: 4
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Console-level observation contract for progress and worker-lifecycle monitoring via the separate console EventBus.
- Does not own match narrative observation, recorder persistence, or replay behavior.

## Evidence Reviewed
- spec sections: full document, especially §§3-6, examples, and references
- implementation files: [base.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/monitors/base.py), [progress.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/monitors/progress.py), [console.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/console.py), [session.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/session.py)
- tests: [test_monitors.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_monitors.py)
- docs/examples: in-spec examples only

## Findings

### Blocker
- none

### High
- The spec mixed the shipped monitor contract with aspirational built-ins such as hardware/checkpoint monitors that are not present in the codebase.

### Medium
- Several examples and reference sections were version-pinned or too specific about hypothetical extensions rather than the current `ProgressMonitor` + custom-monitor contract.

### Low
- none

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Trim the spec back to the shipped monitor surface: console EventBus, `Monitor`, `ProgressMonitor`, and custom monitors.
- Remove or rewrite aspirational examples so they do not read like current product contract.

## Beta Relevance
- required before beta: yes, because monitor behavior affects public batch execution UX and the progress story for longer runs
- safe to defer: future built-in monitor families beyond the current core surface

## Final Verdict
- [SPEC-MONITOR.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-MONITOR.md) is compliant after Wave 4 cleanup. The code already implements the promised console-monitor pipeline; the spec needed to stop over-claiming built-ins that do not ship today.
