# SPEC-PROMPT-BUILDER Audit Note

Spec: [SPEC-PROMPT-BUILDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PROMPT-BUILDER.md)
Wave: 3
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Template-driven prompt composition for handshake, turn, and conclusion phases.
- Does not own renderer behavior, controller parsing, or LLM transport.

## Evidence Reviewed
- spec sections: full document, especially §§4-11
- implementation files: [prompt_builder.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/prompt_builder.py)
- tests: [test_prompt_builder.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_prompt_builder.py)
- docs/examples: in-spec examples and Player handshake usage

## Findings

### Blocker
- none

### High
- The constructor contract was stale: the spec still advertised `renderer=` and `controller=` parameters that do not exist on the shipped `PromptBuilder`.
- The biggest behavioral drift was placeholder semantics. The implementation intentionally renders missing placeholders as empty strings, but the spec still claimed undefined placeholders must raise `TemplateError`.
- The placeholder inventory was overstated by treating `game_name` as auto-bound when it is actually caller-supplied through `extras`.

### Medium
- One example used the wrong method for handshake format injection (`handshake_controller.get_format_instructions()` instead of `controller.get_handshake_format_instructions()`).

### Low
- A few migration examples still carried older framing, but they were historical context rather than live contract requirements.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 4
- test drift: 0
- doc/example drift: 2

## Required Remediation
- Trim the constructor and placeholder list to the real public surface.
- Rewrite EH1 around permissive missing-placeholder behavior.
- Refresh examples and testing guidance to the shipped prompt model.

## Beta Relevance
- required before beta: yes, because prompt composition is the basis of the release-facing FixedDamage experiments
- safe to defer: richer templating features beyond the current minimal contract

## Final Verdict
- [SPEC-PROMPT-BUILDER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PROMPT-BUILDER.md) is compliant after the Wave 3 cleanup. The spec now reflects the actual template-driven, permissive-by-default builder instead of an older stricter placeholder model.
