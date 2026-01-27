# SPEC-LLM Implementation Compliance Report

**Spec Version**: 1.1.0
**Spec Status**: Draft
**Review Date**: 2026-01-21
**Reviewer**: Codex (automated review)
**Implementation**: `src/agentdeck/players/llm_player.py`, `src/agentdeck/players/openai_player.py`, `src/agentdeck/players/anthropic_player.py`, `src/agentdeck/players/google_player.py`, `src/agentdeck/utils/pricing.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 21 |
| Compliant | 11 |
| Partial | 8 |
| Non-Compliant | 2 |
| N/A | 0 |

**Overall Compliance**: 52.4% (11/21 fully compliant)

---

## Invariant Compliance Matrix

### Credentials and Configuration (CC1-CC3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| CC1 | Resolve api_key from constructor > env var > raise ValueError if missing | Partial | `llm_player.py:78-79`, `llm_player.py:146-156`, `google_player.py:41-43` | Gemini bypasses env key requirement by returning empty string; spec does not mention ADC exception |
| CC2 | Ensure model is set or raise ValueError | Yes | `llm_player.py:57-63` | Raises on missing model/default_model |
| CC3 | Call _initialize_client during construction; surface ImportError/ValueError | Yes | `llm_player.py:104-105`, `openai_player.py:16-24`, `anthropic_player.py:16-24`, `google_player.py:45-54` | Provider clients initialized in __init__ |

### Request Execution (RE1-RE3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| RE1 | Retry loop with exponential backoff up to max_retries | Yes | `llm_player.py:201-261` | Backoff uses retry_delay * 2**attempt |
| RE2 | Log request/response metadata with phase | Partial | `llm_player.py:188-236` | Logger calls exist but no phase is passed |
| RE3 | Exhausted retries raise RuntimeError with provider/model context | Partial | `llm_player.py:252-254` | Error mentions model, not provider |

### Metadata and Accounting (MA1-MA4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| MA1 | usage_info includes tokens, prompt/completion tokens, cost, latency_ms, model, provider identifiers | Partial | `llm_player.py:214-223` | Provider identifier missing; optional provider_model only |
| MA2 | Accumulate total_tokens/total_cost/response_times | Yes | `llm_player.py:208-210`, `llm_player.py:300-309` | Totals and averages tracked |
| MA3 | Attach retries, retry_durations, attempt_durations in metadata | Yes | `llm_player.py:240-245` | Returned from _invoke_model |
| MA4 | Flag estimated metrics when provider approximates | Partial | `google_player.py:95-123`, `llm_player.py:214-247` | Gemini sets estimated, but _invoke_model drops it from usage_info/metadata |

### Conversation and History (CH1-CH3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| CH1 | Delegate history logging to ConversationManager when bound | Yes | `player.py:466-478` | _record_exchange delegates when manager exists |
| CH2 | When no manager, append to _local_history and include handshake | Partial | `llm_player.py:274-278`, `player.py:480-482` | History recorded twice (LLMPlayer + Player), causing duplicated turns |
| CH3 | reset_conversation clears local history | Yes | `llm_player.py:265-267`, `player.py:420-434` | Calls Player.reset_conversation |

### Pricing Integration (PI1-PI3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| PI1 | Subclasses define PROVIDER constant | Yes | `openai_player.py:12`, `anthropic_player.py:12`, `google_player.py:16` | All built-in providers set PROVIDER |
| PI2 | Use calculate_cost(provider, model, prompt_tokens, completion_tokens) | Yes | `openai_player.py:55-60`, `anthropic_player.py:57-62`, `google_player.py:108-113` | Cost calculation centralized |
| PI3 | Log warning and default cost to $0 when pricing missing | Partial | `pricing.py:202-210` | Defaults to $0 but logs ERROR, not warning |

### Prompt Metadata Capture (PM1-PM4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| PM1 | _invoke_model returns metadata with usage_info for ActionResult/HandshakeResult | Partial | `llm_player.py:240-247`, `llm_player.py:280-284`, `player.py:231`, `player.py:327-336` | _invoke_model returns usage_info but get_response drops metadata; handshake/turn usage_info is None |
| PM2 | Metadata includes response_text (raw LLM output) | No | `llm_player.py:240-242`, `player.py:318` | Uses raw_response key; no response_text in metadata |
| PM3 | Metadata includes phase context | No | `llm_player.py:240-247` | Phase not included in returned metadata |
| PM4 | Metadata values are JSON-serializable | Yes | `llm_player.py:240-247` | Uses simple types and lists/dicts |

### Cloning and Parallel Execution (CL1)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| CL1 | Override clone to recreate client and preserve config/metrics | Yes | `llm_player.py:107-143` | New instance created; metrics preserved |

---

## Drift Issues

1. **CC1**: Gemini bypasses api_key enforcement
   - **Description**: Spec requires ValueError when api_key/env var missing. Gemini overrides `_get_api_key_from_env()` to return an empty string for ADC use.
   - **Impact**: Spec does not document ADC exception; behavior diverges for one provider.
   - **Recommended Fix**: Update SPEC-LLM to allow ADC/credential-less providers or add explicit validation for non-ADC providers only.

2. **RE2**: Logger calls omit phase context
   - **Description**: Logger calls in `_invoke_model` do not include lifecycle phase.
   - **Impact**: Logs cannot distinguish handshake/turn/conclusion calls.
   - **Recommended Fix**: Add `phase` parameter to logger calls and pass through `_invoke_model`.

3. **RE3**: RuntimeError missing provider identifier
   - **Description**: Final failure includes model but not provider.
   - **Impact**: Harder to diagnose multi-provider runs.
   - **Recommended Fix**: Include `self.PROVIDER` or provider metadata in error message.

4. **MA1**: usage_info lacks provider identifier
   - **Description**: usage_info includes model and tokens but not provider.
   - **Impact**: Recorder cannot attribute usage to provider consistently.
   - **Recommended Fix**: Add `provider` (and optionally `provider_model`) to usage_info.

5. **MA4**: Estimated usage flag dropped
   - **Description**: Gemini sets `estimated` in metadata, but `_invoke_model` does not propagate it.
   - **Impact**: Recorder cannot distinguish estimated usage.
   - **Recommended Fix**: Add `estimated` to usage_info and returned metadata when present.

6. **CH2**: Local history duplicated
   - **Description**: `_invoke_model` appends to `_local_history` and Player._record_exchange also appends, duplicating turns.
   - **Impact**: Prompt history grows with repeated entries, skewing context.
   - **Recommended Fix**: Centralize history writes in one path (prefer Player._record_exchange).

7. **PI3**: Cost fallback logs ERROR instead of warning
   - **Description**: calculate_cost logs ERROR when pricing unavailable.
   - **Impact**: Spec requires warning-level log for missing pricing.
   - **Recommended Fix**: Downgrade to warning or update spec to allow error-level logging.

8. **PM1**: usage_info not wired into handshake/turn metadata
   - **Description**: get_response drops metadata from `_invoke_model`, so handshake/turn usage_info is None.
   - **Impact**: Recorder lacks usage metadata for main lifecycle events.
   - **Recommended Fix**: Return metadata from get_response or override Player.handshake/decide to use _invoke_model metadata.

9. **PM2**: response_text key missing from metadata
   - **Description**: Metadata uses `raw_response` instead of `response_text`.
   - **Impact**: Recorder expects response_text per spec.
   - **Recommended Fix**: Add `response_text` to metadata (or rename consistently across pipeline).

10. **PM3**: Phase context missing from metadata
    - **Description**: `_invoke_model` does not include `phase` in metadata.
    - **Impact**: Recorder cannot categorize LLM calls by phase.
    - **Recommended Fix**: Add `phase` to metadata payload.

---

## Action Items

- [ ] Define spec-compliant behavior for ADC providers like Gemini (update spec or enforce CC1 for non-ADC providers)
- [ ] Add phase context to logger calls and metadata payloads
- [ ] Include provider identifiers in usage_info and error messages
- [ ] Propagate estimated token flags into usage_info/metadata
- [ ] Remove duplicate local history appends
- [ ] Align pricing fallback logging level with spec
- [ ] Wire usage_info into handshake/turn metadata and add response_text/phase fields

