# SPEC-CONSOLE Audit Note

Spec: [SPEC-CONSOLE.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONSOLE.md)
Wave: 2
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Execution engine contract for session lifecycle, batch orchestration, fairness policies, handshakes, conclusion flow, and cleanup.
- Does not own researcher-facing facade concerns or recorder payload schema details.

## Evidence Reviewed
- spec sections: full document, especially §§3-10
- implementation files: [console.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/console.py), [session.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/session.py)
- tests: [test_player_ordering.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_player_ordering.py), [test_parallel_execution.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_parallel_execution.py), [test_auto_reporter.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_auto_reporter.py)
- docs/examples: in-spec examples and adjacent execution specs

## Findings

### Blocker
- none

### High
- The public constructor contract was stale: it omitted `session=...`, used the wrong `session_factory` shape, and claimed `console.session` rather than `console.session_state`.
- The spec still described a Null-object logger/recorder contract that the current implementation does not enforce for direct Console usage.

### Medium
- The close contract and examples implied flush/default behavior that is not part of the current implementation.
- A few examples still pointed to outdated imports and non-exported example classes.

### Low
- Design-rationale wording still referenced an old console-size target rather than an actual contract.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 4
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Rewrite the public API section to the real constructor/session-state shape.
- Make the logger/recorder contract honest for both direct Console users and the higher-level AgentDeck facade.
- Refresh examples and cleanup semantics.

## Beta Relevance
- required before beta: yes, because Console owns the execution contracts that every experiment depends on
- safe to defer: deeper architectural cleanup that does not change the external contract

## Final Verdict
- [SPEC-CONSOLE.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONSOLE.md) is compliant after the Wave 2 cleanup. The spec now describes the actual execution engine rather than an older idealized Null-object variant.
