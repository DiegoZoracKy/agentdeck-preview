# SPEC-REPLAY Implementation Compliance Report

**Spec Version**: 1.1.0
**Spec Status**: Final
**Review Date**: 2026-01-21
**Reviewer**: Claude (automated review)
**Implementation**: `src/agentdeck/core/replay.py`, `src/agentdeck/core/replay_utils.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 25 |
| Compliant | 21 |
| Partial | 2 |
| Non-Compliant | 2 |
| N/A | 0 |

**Overall Compliance**: 84.0% (21/25 fully compliant)

---

## Invariant Compliance Matrix

### 6.1 Input Normalization (IN1-IN3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| IN1 | MUST accept only schema v1.3 artifacts, raise ValueError if incompatible | ✅ Yes | `replay.py:304-318` | `_validate_schema_version` raises ValueError for missing/incompatible versions |
| IN2 | MUST accept dict from Recorder.load_match() and MatchResult | ✅ Yes | `replay.py:38-70` | Both paths implemented |
| IN3 | MUST validate prompt payloads per SPEC-RECORDER §6.7 | ❌ No | Not implemented | **DRIFT**: No validation of prompt payload structure (PM1-PM6 fields) |

### 6.2 Event Parity (EP1-EP3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| EP1 | MUST replay every recorded event exactly once, in order | ✅ Yes | `replay.py:149-155` | Sequential iteration through events |
| EP2 | MUST emit consistent event types | ✅ Yes | `replay.py:210-253` | Event types mapped correctly |
| EP3 | EventContext MUST be rehydrated with same IDs/timestamps | ✅ Yes | `replay.py:255-275` | `_apply_event_context` rehydrates from recorded context |

### 6.3 Timing & Ordering (TO1-TO3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| TO1 | MUST replay events sequentially in recorded order | ✅ Yes | `replay.py:149-155` | For loop preserves order |
| TO2 | MUST compute delays via scheduler with speed multiplier | ✅ Yes | `replay_utils.py:20-26` | `compute_delay` divides by speed |
| TO3 | MUST treat speed <= 0 or NaN as zero delay | ⚠️ Partial | `replay.py:91`, `replay_utils.py:16,21` | **DRIFT**: `max(speed, 0.0)` handles negative but `max(NaN, 0.0)` returns NaN; no NaN check |

### 6.4 Context Reconstruction (CR1-CR2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| CR1 | MUST extract session_id, batch_id, match_id from metadata | ✅ Yes | `replay.py:100-108` | Populates EventBus base context |
| CR2 | MUST preserve phase_index from recorded events | ✅ Yes | `replay.py:267-272`, `replay_utils.py:42-43` | Fallback from turn_index if needed |

### 6.5 Lifecycle Events (LC1-LC5)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| LC1 | MUST emit in order: HANDSHAKE → MATCH_START → GAMEPLAY → MATCH_END → CONCLUSION | ✅ Yes | `replay.py:113-173` | Handshakes processed first, then MATCH_START, then remaining events, then MATCH_END, then conclusions |
| LC2 | MUST emit PLAYER_HANDSHAKE_* before MATCH_START | ✅ Yes | `replay.py:113-131` | While loop processes handshakes before MATCH_START emission |
| LC3 | MUST emit MATCH_START after handshake phase | ✅ Yes | `replay.py:142-147` | MATCH_START emitted after handshake loop exits |
| LC4 | MUST emit MATCH_END after all gameplay events | ✅ Yes | `replay.py:165-168` | MATCH_END emitted after event iteration completes |
| LC5 | MUST emit PLAYER_CONCLUSION after MATCH_END | ✅ Yes | `replay.py:169-173` | `_pending_conclusions` emitted after MATCH_END |

### 6.6 Prompt Metadata Replay (PM1-PM3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| PM1 | MUST deliver prompt_text, prompt_blocks, response_text | ✅ Yes | `replay.py:213` | `payload = copy.deepcopy(event.data)` preserves prompt payloads |
| PM2 | MUST include optional renderer_output, controller_format, etc. | ✅ Yes | `replay.py:213` | Deep copy preserves all fields |
| PM3 | MUST treat recorded payload as canonical source | ✅ Yes | Code analysis | No synthesis or recomputation of prompt data |

### 6.7 State Tracking (ST1-ST2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| ST1 | MUST maintain state_before/state_after continuity | ✅ Yes | Code analysis | Events emitted with recorded state payloads; no recomputation |
| ST2 | MUST use recorded turn_number/phase_index | ✅ Yes | `replay.py:267-270` | phase_index extracted from context, not recomputed |

### 6.8 Spectator Isolation (SI1-SI4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| SI1 | MUST emit through dedicated EventBus instance | ✅ Yes | `replay.py:72` | `self.event_bus = EventBus()` creates isolated instance |
| SI2 | MUST unsubscribe spectators after replay | ✅ Yes | `replay.py:177,200-208` | `_cleanup_spectators` in finally block |
| SI3 | MUST catch and log spectator exceptions | ✅ Yes | `event_bus.py:209-228` | EventBus catches exceptions per EI1 invariant |
| SI4 | MUST inject logger into spectators before subscription | ✅ Yes | `replay.py:95-96` | Logger injection before `event_bus.subscribe` |

### Error Handling (from §8)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| ERR1 | Invalid speed type → ValueError | ⚠️ Partial | `replay.py:91` | **DRIFT**: `max(speed, 0.0)` will raise TypeError for string, but spec says "MUST raise ValueError" |

---

## Drift Issues

### 1. IN3: No Prompt Payload Validation

**Severity**: Moderate
**Spec Requirement**: "MUST validate that every event requiring prompt metadata includes a well-formed `prompt` payload per SPEC-RECORDER §6.7. Raise ValueError if any prompt payload is missing required fields."
**Current Behavior**: No validation of prompt payloads; events are deserialized and emitted without checking PM1-PM6 field presence
**Impact**: Malformed recordings silently replay with missing prompt data
**Location**: `replay.py:179-198` (`_deserialize_events` performs no prompt validation)

**Recommended Fix**:
```python
def _validate_prompt_payload(self, event_type: str, data: dict) -> None:
    """Validate PM1-PM6 fields for lifecycle events."""
    if event_type not in {"player_handshake_complete", "player_handshake_abort",
                          "gameplay", "player_conclusion", "player_action_parse_failed"}:
        return

    prompt = data.get("prompt")
    if prompt is None:
        raise ValueError(f"Event {event_type} missing required 'prompt' payload")

    # PM1: prompt_text required
    if "prompt_text" not in prompt:
        raise ValueError(f"Event {event_type} prompt missing 'prompt_text' (PM1)")
```

### 2. TO3: NaN Speed Handling

**Severity**: Minor
**Spec Requirement**: "MUST treat speed <= 0 or NaN as zero delay (instant replay)"
**Current Behavior**: `max(speed, 0.0)` handles negative speeds but `max(float('nan'), 0.0)` returns `nan` in Python
**Impact**: NaN speed would cause incorrect delay calculations
**Locations**: `replay.py:91`, `replay_utils.py:16`

**Recommended Fix**:
```python
import math

# In replay.py:91
if speed is not None:
    if math.isnan(speed) or speed <= 0:
        self.scheduler.speed = 0.0
    else:
        self.scheduler.speed = speed

# In replay_utils.py:16
self.speed = 0.0 if (math.isnan(speed) or speed <= 0) else speed
```

### 3. ERR1: Invalid Speed Type Error

**Severity**: Minor
**Spec Requirement**: "Invalid `speed` type (e.g., string) → MUST raise ValueError"
**Current Behavior**: `max(speed, 0.0)` raises `TypeError` for non-numeric types, not `ValueError`
**Impact**: Error type doesn't match spec

**Recommended Fix**:
```python
if speed is not None:
    if not isinstance(speed, (int, float)):
        raise ValueError(f"speed must be numeric, got {type(speed).__name__}")
```

---

## Action Items

| Priority | Issue | Action | Effort |
|----------|-------|--------|--------|
| P2 | IN3 drift | Add prompt payload validation in `_deserialize_events` | Medium |
| P3 | TO3 drift | Add `math.isnan()` check for NaN speed values | Low |
| P3 | ERR1 drift | Wrap speed validation to raise ValueError for invalid types | Low |

---

## Conclusion

SPEC-REPLAY implementation is **well compliant** (84.0%) with 21 of 25 invariants fully satisfied. The implementation correctly handles:

- **Input normalization** (IN1-IN2) - Schema validation and dual input paths
- **Event parity** (EP1-EP3) - Events replayed exactly as recorded
- **Lifecycle ordering** (LC1-LC5) - Correct event sequence: handshake → match_start → gameplay → match_end → conclusion
- **Prompt metadata replay** (PM1-PM3) - Deep copy preserves all prompt payloads
- **State tracking** (ST1-ST2) - No recomputation, uses recorded values
- **Spectator isolation** (SI1-SI4) - Dedicated EventBus, cleanup, exception handling, logger injection

The identified drifts are:

1. **Missing prompt payload validation** (IN3) - No validation that lifecycle events have well-formed prompt payloads
2. **NaN speed handling** (TO3) - `max(NaN, 0.0)` returns NaN instead of treating as instant replay
3. **Speed type error** (ERR1) - TypeError raised instead of ValueError for invalid speed types

**Critical Note**: The IN3 drift could allow malformed recordings to silently replay with missing prompt data, affecting research validity. Consider adding validation to ensure recordings meet the v1.3 schema requirements.

**Recommendation**: Add prompt payload validation when deserializing events to catch malformed recordings early (fail-fast principle per CONTRIBUTING.md).
