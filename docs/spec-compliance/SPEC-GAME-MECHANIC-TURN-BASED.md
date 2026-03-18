# SPEC-GAME-MECHANIC-TURN-BASED Audit Note

Spec: [SPEC-GAME-MECHANIC-TURN-BASED.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME-MECHANIC-TURN-BASED.md)
Wave: 2
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Default turn-based mechanic contract for `TurnBasedGame`, `TurnLoop`, and turn/result invariants.
- Does not own the higher-level session/batch lifecycle or non-turn-based mechanics.

## Evidence Reviewed
- spec sections: full document
- implementation files: [turn_based.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/mechanics/turn_based.py), [console.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/console.py)
- tests: [test_turn_based_mechanic.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_turn_based_mechanic.py), [test_game_hooks.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_game_hooks.py)
- docs/examples: in-spec examples and mechanic docstrings

## Findings

### Blocker
- none

### High
- The spec still implied TurnLoop always owns setup, but the current execution path may receive `runtime.initial_state` after Console performs setup + handshake first.
- The execution steps overstated a separate `runtime.emit_event` gameplay call; in the shipped contract `runtime.record_turn` emits the canonical `GAMEPLAY` event.

### Medium
- Example wording around deterministic setup still assumed the older setup-only path.

### Low
- Mechanic docstrings had one stale `setup(players)` example.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 0
- doc/example drift: 1

## Required Remediation
- Document the `runtime.initial_state` handoff explicitly.
- Make `record_turn` the canonical gameplay-event emission path in the spec text.
- Refresh the stale setup example.

## Beta Relevance
- required before beta: yes, because turn-based execution is the default mechanic underpinning the release experiments
- safe to defer: broader custom-mechanic guidance beyond the corrected default path

## Final Verdict
- [SPEC-GAME-MECHANIC-TURN-BASED.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-GAME-MECHANIC-TURN-BASED.md) is compliant after cleanup. The spec now reflects the real setup/handshake split and gameplay recording path.
