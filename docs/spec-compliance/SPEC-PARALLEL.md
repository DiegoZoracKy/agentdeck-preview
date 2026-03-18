# SPEC-PARALLEL Audit Note

Spec: [SPEC-PARALLEL.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PARALLEL.md)
Wave: 2
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Parallel match-execution contract for worker isolation, seed determinism, replay parity, and fallback behavior.
- Does not own the base sequential execution contract or player/controller semantics.

## Evidence Reviewed
- spec sections: full document
- implementation files: [console.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/console.py), [types.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/types.py)
- tests: [test_parallel_execution.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_parallel_execution.py)
- docs/examples: in-spec examples and adjacent Console/Game specs

## Findings

### Blocker
- none

### High
- The spec header version had drifted from the hub spec and test references.
- The fallback wording was narrower than the implementation: the shipped beta conservatively falls back to sequential execution for any `get_player_order` override, not only proven `previous_match_result` users.

### Medium
- One example still relied on older provider-facing player setup where a simple cloned mock-player example is sufficient to express the contract.

### Low
- none

## Drift Classification Summary
- implementation drift: 0
- spec drift: 2
- test drift: 0
- doc/example drift: 1

## Required Remediation
- Align the version header with the active spec set.
- Make the fallback semantics match the conservative beta implementation.
- Refresh the example to a minimal AgentDeck-native setup.

## Beta Relevance
- required before beta: yes, because reproducibility and fallback semantics matter for large experiment batches
- safe to defer: future refinement that distinguishes harmless `get_player_order` overrides from stateful ones

## Final Verdict
- [SPEC-PARALLEL.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PARALLEL.md) is compliant after cleanup. The contract now reflects the current conservative parallel-execution behavior.
