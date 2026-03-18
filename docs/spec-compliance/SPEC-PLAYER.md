# SPEC-PLAYER Audit Note

Spec: [SPEC-PLAYER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PLAYER.md)
Wave: 3
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Player lifecycle contract for handshake, turn decisions, conclusion handling, conversation recording, and introspection.
- Does not own provider transport details, recorder schema internals, or console orchestration.

## Evidence Reviewed
- spec sections: full document, especially §§3-11
- implementation files: [player.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/base/player.py), [llm_player.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/players/llm_player.py)
- tests: [test_llm_player.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_llm_player.py)
- docs/examples: in-spec examples and adjacent controller/prompt specs

## Findings

### Blocker
- none

### High
- The public constructor contract had drifted: it still advertised `prompt=` on the base `Player` API even though that belongs to provider-backed subclasses via `LLMPlayer` config.
- The conclusion section overstated the base contract by requiring LLM invocation/reflection generation for all players; the shipped base `Player.conclude()` only records prompt metadata and returns `None`.
- The decision semantics still described fallback-era parsing even though the controller stack now surfaces `ActionParseError`.

### Medium
- Introspection helpers were blurred together: `describe()` and `get_summary()` belong to base `Player`, while `get_stats()` is provider-specific.
- One example omitted the required `controller=` argument.

### Low
- Several version-pinned references pointed at older controller wording rather than the current generic cross-spec contract.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 5
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Trim the base Player API to the real public surface.
- Make the base-vs-provider conclusion contract explicit.
- Update no-fallback semantics and refresh the example code.

## Beta Relevance
- required before beta: yes, because player lifecycle and prompt metadata are central to every public experiment
- safe to defer: richer ergonomics beyond the current public player surface

## Final Verdict
- [SPEC-PLAYER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PLAYER.md) is compliant after the Wave 3 cleanup. The spec now matches the shipped player lifecycle instead of mixing base-player guarantees with LLM-specific behavior.
