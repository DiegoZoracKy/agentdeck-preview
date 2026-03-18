# SPEC-RENDERER Audit Note

Spec: [SPEC-RENDERER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RENDERER.md)
Wave: 3
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Renderer contract for formatting player-visible game views into prompt-ready outputs with metadata.
- Does not own visibility filtering, prompt assembly, or controller validation.

## Evidence Reviewed
- spec sections: full document, especially §§3-10
- implementation files: [renderer.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/base/renderer.py), [text_renderer.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/renderers/text_renderer.py)
- tests: [test_text_renderer.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_text_renderer.py)
- docs/examples: in-spec `TextRenderer` example and adjacent player/game docs

## Findings

### Blocker
- none

### High
- none

### Medium
- The spec philosophy reference still pointed at `AGENTS.md` instead of the current spec suite.
- The shipped `TextRenderer` example in the spec had drifted from the actual behavior: the implementation preserves insertion order and game-provided fields rather than the older sorted/filtering/show-empty sketch.

### Low
- Base renderer docstrings still implied stricter error semantics than the generic renderer contract actually requires.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 2
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Update the top-level philosophy reference.
- Rewrite the generic renderer example to match the shipped `TextRenderer`.
- Clarify that schema-specific strictness is optional, not required for generic renderers.

## Beta Relevance
- required before beta: yes, because renderer output shapes the exact prompts used in public experiments
- safe to defer: richer renderer capabilities beyond the current generic text contract

## Final Verdict
- [SPEC-RENDERER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RENDERER.md) is compliant after the Wave 3 cleanup. Remaining changes were documentation alignment, not missing renderer features.
