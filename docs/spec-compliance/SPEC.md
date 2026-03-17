# SPEC.md Audit Note

Spec: [SPEC.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC.md)
Wave: 1
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Navigation hub for AgentDeck architecture, component inventory, and high-level philosophy.
- Does not own low-level component contracts; it must accurately point to them.

## Evidence Reviewed
- spec sections: full document, especially §§2-5
- implementation files: [__init__.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/__init__.py), [agentdeck.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/agentdeck.py)
- tests: none required for the hub itself
- docs/examples: [README.md](/home/diegozoracky/dev/agentdeck-preview/README.md), component spec headers

## Findings

### Blocker
- none

### High
- The component inventory table was stale across multiple versions and statuses. `SPEC.md` claimed several core specs were older or still draft when their component specs were already final.
- The quick start example no longer matched the current public API or game contract. It showed an outdated custom game shape and provider-backed player usage without the now-required explicit model configuration.
- The “games require only 4 methods” hub claim had drifted from [SPEC-GAME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME.md), which now includes required descriptive properties as part of the author contract.

### Medium
- The hub omitted the viewer from the component inventory despite [SPEC-VIEWER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-VIEWER.md) now being part of the active spec surface.
- Lifecycle/version references in the narrative were behind the current component versions.

### Low
- Hub metadata (`Last Updated`) was stale.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 4
- test drift: 0
- doc/example drift: 1

## Required Remediation
- Update the hub inventory to match the current component spec headers.
- Update the high-level game-authoring description to match the current contract.
- Replace the quick start with a valid, current public API example.
- Add the viewer to the navigable component inventory.

## Beta Relevance
- required before beta: yes, because the hub is the first spec entry point and sets expectations for the rest of the suite
- safe to defer: deeper content tuning beyond inventory/contract accuracy

## Final Verdict
- [SPEC.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC.md) is compliant after the Wave 1 cleanup. It is now a trustworthy navigation hub again.
