# SPEC-CONTROLLER Implementation Compliance Report

**Spec Version**: 1.3.0
**Spec Status**: Draft (Pending Review)
**Review Date**: 2026-01-21
**Reviewer**: Claude (automated review)
**Implementation**: `src/agentdeck/core/base/controller.py`, `src/agentdeck/controllers/action_only.py`, `src/agentdeck/controllers/reasoning.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 29 |
| Compliant | 26 |
| Partial | 2 |
| Non-Compliant | 1 |
| N/A | 0 |

**Overall Compliance**: 89.7% (26/29 fully compliant)

---

## Invariant Compliance Matrix

### 5.1 Handshake Validation (HV1-HV5)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| HV1 | `validate_handshake()` MUST be deterministic and side-effect free | ✅ Yes | `controller.py:148-167` | Pure function, no mutations, deterministic output |
| HV2 | MUST normalize whitespace/punctuation, preserve raw response, return upper-cased normalized_response | ✅ Yes | `controller.py:149-150` | `raw.upper().rstrip("!.")` for normalization |
| HV3 | Rejection MUST set `accepted=False` and populate `reason` | ✅ Yes | `controller.py:155` | `reason = f"Expected one of {sorted(allowed)}, got '{raw}'"` |
| HV4 | Accepted acknowledgements SHOULD populate metadata | ✅ Yes | `controller.py:157-159` | Populates `allowed` and optionally `player` |
| HV5 | Default MUST accept {"OK", "READY", "YES"} (case-insensitive, punctuation-tolerant) | ✅ Yes | `controller.py:150-153` | `allowed = {"OK", "READY", "YES"}`, normalized via `.upper().rstrip("!.")` |

### 5.2 Format Instructions (FI1-FI3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| FI1 | `get_format_instructions()` MUST align with parsing expectations | ✅ Yes | `action_only.py:87-93`, `reasoning.py:61-75` | Instructions mention ACTION: prefix, match parse() expectations |
| FI2 | Format instructions MUST be deterministic text | ✅ Yes | `controller.py:195`, `action_only.py:76-93` | No randomness, pure string generation |
| FI3 | `get_handshake_format_instructions()` MUST match `validate_handshake()` expectations | ✅ Yes | `controller.py:195` | Returns "Reply with 'OK'..." matching accepted tokens |

### 5.3 Action Parsing (AP1-AP3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| AP1 | `parse()` MUST populate `raw_response` with trimmed input | ✅ Yes | `action_only.py:120`, `reasoning.py:93` | `cleaned = response.strip()` stored in ParseResult |
| AP2 | On success: `success=True`, `action` contains normalized action, `error` MUST be None | ✅ Yes | `action_only.py:131-143`, `reasoning.py:111-124` | Success path sets all fields correctly |
| AP3 | On failure: `success=False`, `error` explains failure, `normalized_action` SHOULD be None | ✅ Yes | `action_only.py:145-161`, `reasoning.py:126-143` | Failure path with descriptive error messages |

### 5.4 Validation & Error Propagation (VF1-VF4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| VF1 | Controllers with allowed sets MUST use casefold semantics, include allowed set in metadata | ✅ Yes | `action_only.py:238-240`, `reasoning.py:237` | Uses `.upper()` for case-insensitive comparison |
| VF2 | `to_action_result()` MUST raise `ActionParseError` when `success=False` | ✅ Yes | `types.py:503-504` | `raise ActionParseError(self)` on failure |
| VF3 | Controllers MUST NOT return fallback actions; `ParseResult.action` MUST be None on failure | ✅ Yes | `action_only.py:151-153`, `reasoning.py:133-134` | `action=None` on all failure paths |
| VF4 | `ParseResult.metadata` SHOULD contain diagnostic fields | ✅ Yes | `action_only.py:138-142, 157-160` | Includes `validated`, `allowed_actions`, `candidates` |

### 5.5 Metadata Integrity (MI1-MI2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| MI1 | `ParseResult.metadata` and `HandshakeResult.metadata` MUST be JSON-serializable | ✅ Yes | All implementations | Only uses lists, dicts, strings, bools |
| MI2 | Controllers SHOULD include candidate lists, reasoning text, and debug aids | ✅ Yes | `action_only.py:141`, `reasoning.py:122` | Includes `candidates`, `reasoning_extracted` |

### 5.6 Determinism & Safety (DS1-DS2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| DS1 | Controllers MUST NOT mutate inputs or global state | ✅ Yes | All implementations | No mutations observed; response trimmed to local variable |
| DS2 | Repeat calls with identical input/configuration MUST yield identical outputs | ✅ Yes | All implementations | Pure functions, no state dependency |

### 5.7 Game Binding (GB1-GB6)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| GB1 | Console MUST call `bind_game()` once per batch before match starts | ✅ Yes | `console.py:636-639, 2663-2666` | Called before handshake for each player |
| GB2 | `bind_game()` MUST be idempotent | ✅ Yes | `action_only.py:64-74`, `reasoning.py:45-52` | Re-assigns `_allowed_actions` set, idempotent |
| GB3 | Controllers SHOULD extract `game.allowed_actions` during binding | ✅ Yes | `action_only.py:74`, `reasoning.py:52` | Extracts and uppercases allowed actions |
| GB4 | Controllers MUST NOT require `bind_game()` before `get_format_instructions()` | ✅ Yes | `action_only.py:91-93`, `reasoning.py:69-75` | Returns generic instructions when unbound |
| GB5 | Controllers SHOULD return game-specific instructions when bound | ✅ Yes | `action_only.py:87-90`, `reasoning.py:61-68` | Shows allowed actions when bound |
| GB6 | Controllers requiring allowed_actions MUST raise RuntimeError if unbound | ❌ No | Not implemented | **DRIFT**: Neither ActionOnlyController nor ReasoningController raises RuntimeError when unbound and validation needed; they silently accept any action |

### 5.8 Prompt Metadata Capture (PM1-PM4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| PM1 | `ParseResult.metadata` MUST be available for Player to include in ActionResult | ✅ Yes | `types.py:512-513` | `to_action_result()` copies metadata to ActionResult |
| PM2 | `HandshakeResult.metadata` MUST be available for Console events | ✅ Yes | `controller.py:161-167` | metadata field populated and returned |
| PM3 | Controllers SHOULD populate metadata with parsing-specific context | ✅ Yes | All implementations | Includes `allowed_actions`, `candidates`, `validated`, `reasoning_extracted` |
| PM4 | All metadata fields MUST be JSON-serializable | ✅ Yes | All implementations | Only primitive types used |

### Additional: Conclusion Parsing

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| CP1 | `parse_conclusion()` MUST be deterministic and side-effect free | ✅ Yes | `controller.py:345` | `return response.strip()` - pure function |
| CP2 | Default returns trimmed response (passthrough) | ⚠️ Partial | `controller.py:345` | **DRIFT**: Spec §4.1 says default returns `{"reflection_text": response.strip()}` (dict), but implementation returns `response.strip()` (str) |

---

## Drift Issues

### 1. **GB6**: Missing RuntimeError for unbound validation

**Description**: SPEC-CONTROLLER §5.7 GB6 states:
> "Controllers that require `allowed_actions` for validation MUST raise `RuntimeError` during `parse()` if `bind_game()` was not called (fail-fast, catch configuration errors early)."

**Current Behavior**: Both `ActionOnlyController` and `ReasoningController` silently accept any action when unbound (no validation occurs). The code path at `action_only.py:162-173` and `reasoning.py:144-172` returns success for any parsed action without raising an error.

**Impact**: Configuration errors (forgetting to call `bind_game()`) go undetected. Research results may include invalid actions that passed silently.

**Recommended Fix**: Add a check in `parse()` to raise `RuntimeError` if `_allowed_actions is None` and the controller is designed to validate. Alternatively, update spec if current behavior is intentional.

### 2. **CP2**: parse_conclusion return type mismatch

**Description**: SPEC-CONTROLLER §4.1 specifies `parse_conclusion()` returns:
```python
def parse_conclusion(self, response: str) -> dict:
    """Default implementation: {"reflection_text": response.strip()}"""
```

**Current Behavior**: Implementation at `controller.py:312` returns `str`:
```python
def parse_conclusion(self, response: str, ...) -> str:
    return response.strip()
```

**Impact**: Callers expecting a dict with `reflection_text` key will fail. Spec and implementation are out of sync.

**Recommended Fix**: Either update implementation to return `{"reflection_text": response.strip()}` or update spec to document string return type.

---

## Action Items

- [ ] **GB6**: Add RuntimeError check in ActionOnlyController.parse() and ReasoningController.parse() when unbound and validation is expected, OR clarify in spec that validation-optional controllers don't need this check
- [ ] **CP2**: Align parse_conclusion() return type between spec (dict) and implementation (str)

---

## Notes

- The unified single-controller architecture (v1.3.0) is fully implemented
- Default handshake validation works correctly (HV1-HV5)
- Game binding lifecycle is correctly orchestrated by Console (GB1-GB5)
- Metadata capture for observability is comprehensive (PM1-PM4)
- ActionParseError propagation works as specified (VF2-VF3)
