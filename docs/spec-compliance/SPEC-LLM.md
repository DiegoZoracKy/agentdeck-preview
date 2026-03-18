# SPEC-LLM Audit Note

Spec: [SPEC-LLM.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-LLM.md)
Wave: 3
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Provider integration contract for LLM-backed players: credentials, retries, usage/cost metadata, stats, and provider-specific normalization.
- Does not own prompt composition, controller parsing, or console orchestration.

## Evidence Reviewed
- spec sections: full document, especially §§3-9
- implementation files: [llm_player.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/players/llm_player.py), [openai_player.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/players/openai_player.py), [anthropic_player.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/players/anthropic_player.py), [google_player.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/players/google_player.py)
- tests: [test_llm_player.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_llm_player.py), [test_openai_player.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_openai_player.py), [test_google_player.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_google_player.py)
- docs/examples: in-spec examples and adjacent pricing/player specs

## Findings

### Blocker
- none

### High
- The public constructor contract still treated `prompt` as a first-class declared parameter and claimed null prompt defaults instead of the real PromptBuilder defaults plus provider kwargs behavior.
- `_invoke_model` was described with an explicit `phase=` parameter even though the shipped helper derives phase from active lifecycle state or turn context.
- The stats contract was stale: the implementation returns `avg_response_time`, not raw `response_times`.
- The data-flow section incorrectly assigned history recording to `_invoke_model()` itself; in the shipped design, lifecycle methods call `_record_exchange()` after provider invocation.

### Medium
- Provider-specific release-relevant behavior was under-specified: Anthropic's required `max_tokens` fallback and Gemini's base64 credential path were both real but undocumented.

### Low
- Several example snippets still called the older `_invoke_model(..., phase=...)` shape directly.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 6
- test drift: 0
- doc/example drift: 3

## Required Remediation
- Trim the public API to the real constructor/helper signatures.
- Align stats and history-flow wording with the shipped implementation.
- Document the concrete Anthropic and Gemini provider paths already in the codebase.

## Beta Relevance
- required before beta: yes, because public experiments depend on reproducible provider behavior, retries, and cost accounting
- safe to defer: provider-specific optimizations that are not part of the current stable contract

## Final Verdict
- [SPEC-LLM.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-LLM.md) is compliant after the Wave 3 cleanup. The spec now describes the actual provider surface instead of an older idealized helper/stats model.
