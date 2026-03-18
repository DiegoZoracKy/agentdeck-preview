# SPEC-GAME Audit Note

Spec: [SPEC-GAME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME.md)
Wave: 2
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Game author contract for instructions, setup/update/status/get_view, hooks, and state ownership.
- Does not own turn-mechanic execution details or recorder schema.

## Evidence Reviewed
- spec sections: full document, especially §§3-8
- implementation files: [game.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/base/game.py), [console.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/console.py)
- tests: [test_game.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_game.py), [test_game_hooks.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_game_hooks.py)
- docs/examples: in-spec examples and base-class docstrings

## Findings

### Blocker
- none

### High
- The spec incorrectly said Console never reads or delivers `instructions`, but handshake composition now legitimately consumes that property through `{game_instructions}`.
- The `setup(...)` signature and multiple examples had drifted from the actual seeded contract.

### Medium
- The data-flow description no longer reflected that setup may happen before handshake so the initial state can inform onboarding.

### Low
- Base-class docstrings had older wording and examples that drifted with the old contract.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Update the `instructions` and `setup` sections to the real handshake-aware contract.
- Refresh examples and base-class docs to use the seeded setup API.
- Clarify the setup/handshake interaction in data flow.

## Beta Relevance
- required before beta: yes, because game authors need a trustworthy contract for setup and onboarding
- safe to defer: additional authoring examples beyond the corrected seeded pattern

## Final Verdict
- [SPEC-GAME.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME.md) is compliant after cleanup. The game contract now matches how Console actually builds and uses initial state.
