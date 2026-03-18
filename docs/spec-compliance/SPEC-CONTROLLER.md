# SPEC-CONTROLLER Audit Note

Spec: [SPEC-CONTROLLER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONTROLLER.md)
Wave: 3
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Unified controller contract for handshake validation, turn parsing, conclusion parsing, and game binding.
- Does not own prompt composition, provider transport, or console lifecycle policy.

## Evidence Reviewed
- spec sections: full document, especially §§3-9
- implementation files: [controller.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/base/controller.py), [action_only.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/controllers/action_only.py), [reasoning.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/controllers/reasoning.py)
- tests: [test_controller.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_controller.py)
- docs/examples: in-spec examples and adjacent player/prompt specs

## Findings

### Blocker
- none

### High
- The handshake placeholder contract had drifted: the spec implied both handshake placeholders were populated from `get_handshake_format_instructions()`, but the shipped code splits them between gameplay and acknowledgement instructions.
- The default conclusion-parsing shape was stale in the spec (`reflection_text` vs the shipped `reflection` dict).

### Medium
- One strict-handshake example still used `normalized_response=""` on rejection instead of the current `None`-style rejection semantics.

### Low
- Some surrounding prose still carried older version labels from the single-controller migration, but the actual contract text was the release-relevant part.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 1
- doc/example drift: 1

## Required Remediation
- Align handshake placeholder semantics with the player/prompt pipeline.
- Correct the default conclusion parse contract.
- Add direct coverage for default `parse_conclusion()`.

## Beta Relevance
- required before beta: yes, because controller parsing/validation semantics determine whether experiments are interpretable
- safe to defer: historical migration prose that does not affect the live contract

## Final Verdict
- [SPEC-CONTROLLER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-CONTROLLER.md) is compliant after the Wave 3 cleanup. The controller contract now matches the shipped handshake split, no-fallback parsing model, and conclusion metadata shape.
