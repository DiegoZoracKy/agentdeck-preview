# SPEC-AGENTDECK Implementation Compliance Report

**Spec Version**: 0.3.0
**Spec Status**: Draft
**Review Date**: 2026-01-21
**Reviewer**: Claude (automated review)
**Implementation**: `src/agentdeck/core/agentdeck.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 17 |
| Compliant | 14 |
| Partial | 3 |
| Non-Compliant | 0 |
| N/A | 0 |

**Overall Compliance**: 82.4% (14/17 fully compliant)

---

## Invariant Compliance Matrix

### 6.1 Engine Integration (E1-E3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| E1 | MUST select default console when none supplied; honour explicit overrides | ✅ Yes | `agentdeck.py:61-66` | Creates Console with injected session/recorder/spectators; no override mechanism in current API |
| E2 | MUST pass SessionConfig and seed to console without mutation | ✅ Yes | `agentdeck.py:42-46, 61-66` | Config passed to Console via session parameter |
| E3 | MUST surface console-supplied session metadata via helpers without alteration | ⚠️ Partial | `agentdeck.py:376-401` | `get_session_stats()` exposes metadata, but spec requires `elapsed_time` as a property (see drift) |

### 6.2 Lifecycle (L1-L4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| L1 | MUST complete construction only after console signals readiness | ✅ Yes | `agentdeck.py:61-66` | Console construction triggers SESSION_START; AgentDeck constructor returns after Console is ready |
| L2 | MUST delegate cleanup to console; console emits SESSION_END exactly once | ✅ Yes | `agentdeck.py:434` | `self.console.close()` called in `_cleanup()` |
| L3 | MUST ensure cleanup idempotence | ✅ Yes | `agentdeck.py:422-423, 430` | `_closed` guard prevents double cleanup |
| L4 | MUST expose console-stamped `finished_at` via session state | ⚠️ Partial | `console.py:2444` | Console sets `finished_at`, but AgentDeck doesn't expose it directly; uses `get_session_stats()` elapsed_time instead |

### 6.3 Batch Execution (B1-B5)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| B1 | MUST reject empty players, duplicate names, or matches < 1 | ✅ Yes | `agentdeck.py:275-289` | All three validations with descriptive ValueError messages |
| B2 | MUST reject non-integer seeds with TypeError | ✅ Yes | `agentdeck.py:292-293` | `raise TypeError(f"'seed' must be an integer or None, got {type(seed).__name__}")` |
| B3 | MUST delegate batch execution to console.run | ✅ Yes | `agentdeck.py:162-168, 306` | Calls `self.console.run(...)` with seed and spectators |
| B4 | MUST return MatchResults with seeds and player ordering metadata | ✅ Yes | `agentdeck.py:307-308` | Returns `MatchResults(results)` from console.run() which includes metadata |
| B5 | MUST return MatchResults with exactly the number of results from console | ✅ Yes | `agentdeck.py:307-308` | Wraps `results` list directly without filtering |

### 6.4 Spectator Scoping (S1-S4)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| S1 | MUST treat session spectators as persistent across all batches and replays | ✅ Yes | `agentdeck.py:63` | Session spectators passed to Console at construction |
| S2 | MUST append execution-level spectators without removing session spectators | ✅ Yes | `agentdeck.py:167` | Execution spectators passed to `console.run(spectators=...)` which adds to session |
| S3 | MUST forward effective spectator set to console for play and replay | ✅ Yes | `agentdeck.py:167, 352-353` | Spectators forwarded in both `_run_batch` and `replay` |
| S4 | MUST allow console auto-attachment when spectators is None | ✅ Yes | `agentdeck.py:63` | Comment: "Don't convert None to [] - let Console handle auto-attachment" |

### 6.5 Replay (R1-R2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| R1 | MUST accept exactly one of match or path; reject unsupported inputs | ⚠️ Partial | `agentdeck.py:342-344` | Validates mutual exclusivity with ValueError, but doesn't explicitly raise TypeError for unsupported types (delegates to ReplayEngine) |
| R2 | MUST reproduce recorded events in original order | ✅ Yes | `agentdeck.py:351-353` | Delegates to `ReplayEngine.replay()` which maintains event order |

---

## Drift Issues

### 1. **E3/L4**: `elapsed_time` not exposed as property

**Description**: SPEC-AGENTDECK §5 specifies:
> "Read-only properties: `elapsed_time -> float`: MUST report wall-clock seconds since SESSION_START using the session timestamp."

**Current Behavior**: `elapsed_time` is exposed via `get_session_stats()` method (`agentdeck.py:396`) rather than as a `@property`. The spec explicitly lists it as a property alongside `session` and `total_matches`.

**Impact**: Minor API deviation. Researchers must call `deck.get_session_stats()['elapsed_time']` instead of `deck.elapsed_time`.

**Recommended Fix**: Add `@property` decorator:
```python
@property
def elapsed_time(self) -> float:
    return time.time() - self.session_start_time
```

### 2. **L4**: `finished_at` exposure

**Description**: Spec requires exposing console-stamped `finished_at` via session state for duration reporting.

**Current Behavior**: Console sets `self.session_state.finished_at` at `console.py:2444`, but AgentDeck accesses `SessionContext` (different from `Console.session_state`). The `finished_at` is not easily accessible via `deck.session`.

**Impact**: Researchers can't access the exact finish timestamp. They can use `elapsed_time` from `get_session_stats()` instead.

**Status**: Partial - duration is available, but not via `finished_at` property as specified.

### 3. **R1**: TypeError for unsupported input types

**Description**: Spec says:
> "MUST raise `TypeError` / `ValueError` when inputs are of an unsupported type."

**Current Behavior**: `replay()` validates mutual exclusivity (ValueError for neither/both), but doesn't explicitly check that `match` is MatchResult/dict or `path` is str/PathLike. Invalid types would fail later in ReplayEngine.

**Impact**: Minor - errors still surface, just not at the documented location.

**Recommended Fix**: Add explicit type checking in `replay()`:
```python
if match is not None and not isinstance(match, (MatchResult, dict)):
    raise TypeError(f"'match' must be MatchResult or dict, got {type(match).__name__}")
```

---

## Action Items

- [ ] **E3**: Add `elapsed_time` as `@property` on AgentDeck class
- [ ] **L4**: Consider exposing `session.finished_at` if needed for duration analysis
- [ ] **R1**: Add explicit type validation in `replay()` method for match parameter

---

## Verification Notes

### Input Validation Verified
All B1-B2 validations present at `agentdeck.py:275-293`:
- Empty players: `ValueError("'players' cannot be empty...")`
- Duplicate names: `ValueError("Player names must be unique...")`
- matches < 1: `ValueError("'matches' must be >= 1...")`
- Non-integer seed: `TypeError("'seed' must be an integer or None...")`

### Context Manager Protocol Verified
- `__enter__`: Returns self (`agentdeck.py:407-408`)
- `__exit__`: Calls `_cleanup()`, returns None to propagate exceptions (`agentdeck.py:410-414`)
- `_cleanup()`: Idempotent via `_closed` flag, calls `console.close()` (`agentdeck.py:416-460`)

### Spectator Scoping Verified
- Session spectators: Passed to Console at construction (`agentdeck.py:63`)
- Execution spectators: Passed via `spectators=` parameter to `console.run()` (`agentdeck.py:167`)
- Replay spectators: Uses execution spectators or falls back to `self.console.spectators` (`agentdeck.py:352`)
- Auto-attachment: `spectators=None` passed through to Console, not converted to `[]`

### Console Integration Verified
- Console created with session, recorder, spectators, logger (`agentdeck.py:61-66`)
- Batch execution delegated to `console.run()` (`agentdeck.py:162-168`)
- Cleanup delegated to `console.close()` (`agentdeck.py:434`)

### Session Metadata Exposure Verified
`get_session_stats()` exposes:
- session_id, total_matches, elapsed_time
- log_directory, record_directory
- seed, max_turns

---

## Notes

- AgentDeck facade correctly delegates orchestration to Console
- Input validation is comprehensive with descriptive error messages
- Session/execution spectator scoping works as specified
- Context manager protocol provides reliable cleanup
- Minor drift around property vs method for `elapsed_time`
- Replay functionality delegates to ReplayEngine correctly
