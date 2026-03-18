# SPEC-VIEWER Audit Note

Spec: [SPEC-VIEWER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-VIEWER.md)
Wave: 4
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Browser-side offline replay viewer contract: record loading, timeline playback, renderer interface, and renderer registry behavior.
- Does not own the record schema itself or Python replay semantics.

## Evidence Reviewed
- spec sections: full document, especially §§4-6 and examples
- implementation files: [record-loader.js](/home/diegozoracky/dev/agentdeck-preview/viewer/js/record-loader.js), [timeline.js](/home/diegozoracky/dev/agentdeck-preview/viewer/js/timeline.js), [index.js](/home/diegozoracky/dev/agentdeck-preview/viewer/js/renderers/index.js), [app.js](/home/diegozoracky/dev/agentdeck-preview/viewer/js/app.js)
- tests: [viewer_smoke_check.js](/home/diegozoracky/dev/agentdeck-preview/scripts/viewer_smoke_check.js)
- docs/examples: [viewer/README.md](/home/diegozoracky/dev/agentdeck-preview/viewer/README.md), [VIEWER_STATUS.md](/home/diegozoracky/dev/agentdeck-preview/VIEWER_STATUS.md)

## Findings

### Blocker
- none

### High
- none

### Medium
- The spec under-described several shipped viewer fields and hooks: lifecycle extraction, outcome/forfeit metadata, timeline state callbacks, and the richer `renderVictory(...)` call shape used by the app shell.

### Low
- A few examples and interface snippets lagged behind the offline beta surface, but the overall direction was already correct.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 2
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Expand the interface/data-structure sections to match the shipped JS surface without turning the viewer spec into a design wish-list.

## Beta Relevance
- required before beta: yes, because the viewer is part of the public showcase even if it remains a secondary surface
- safe to defer: deeper multi-game ambitions and hosted-distribution questions

## Final Verdict
- [SPEC-VIEWER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-VIEWER.md) is compliant after Wave 4 cleanup. The viewer already worked as documented in practice; the spec now matches the actual offline-beta interface instead of a narrower earlier snapshot.
