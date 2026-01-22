# SPEC-GAME-MECHANIC-TURN-BASED Implementation Compliance Report

**Spec Version**: 2.0.0
**Spec Status**: Draft
**Review Date**: 2026-01-21
**Reviewer**: Codex (automated review)
**Implementation**: `src/agentdeck/core/mechanics/turn_based.py`, `src/agentdeck/core/match_runtime.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 6 |
| Compliant | 2 |
| Partial | 3 |
| Non-Compliant | 1 |
| N/A | 0 |

**Overall Compliance**: 33.3% (2/6 fully compliant)

---

## Invariant Compliance Matrix

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| TL1 | Fork RNG before setup; setup uses forked RNG | Yes | `turn_based.py:312-316` | Uses runtime.fork_rng("setup") before game.setup |
| TL2 | get_current_player returns valid player; raise ValueError on invalid | Partial | `turn_based.py:436-459` | Validates unknown player but raises RuntimeError; no duplicate check |
| TL3 | Use runtime emit/record/handle_parse_failure/validate_state (no console calls) | No | `turn_based.py:486-496` | Uses runtime._console.get_player_action instead of runtime.handle_parse_failure |
| TL4 | After decide, call runtime.record_turn with prompt metadata | Yes | `turn_based.py:531-541` | record_turn invoked every successful decide |
| TL5 | Annotate exceptions with turn_number, player_name, match_id | Partial | `turn_based.py:337-343`, `turn_based.py:466-471`, `turn_based.py:555-559` | Messages include turn_number/player but not match_id consistently |
| TL6 | GAMEPLAY events include phase_index/turn_number; TurnResult events JSON-serializable | Partial | `match_runtime.py:309-339`, `turn_based.py:543-551` | phase_index injected; JSON-serializability of custom events not enforced |

---

## Drift Issues

1. **TL3**: Direct console call bypasses runtime.parse_failure pipeline
   - **Description**: TurnLoop uses runtime._console.get_player_action instead of runtime.handle_parse_failure.
   - **Impact**: Violates runtime-only gateway contract; mechanics can bypass MatchRuntime policies.
   - **Recommended Fix**: Route parse failures through runtime.handle_parse_failure or expose a runtime helper that wraps get_player_action.

2. **TL2**: Invalid player errors do not match spec
   - **Description**: Unknown player raises RuntimeError and duplicates are not validated.
   - **Impact**: Diverges from ValueError requirement and can allow invalid ordering silently.
   - **Recommended Fix**: Raise ValueError and add duplicate/unknown validation.

3. **TL5**: Exception messages missing match_id
   - **Description**: Errors include turn numbers and player but omit match_id.
   - **Impact**: Harder to correlate failures across logs and recordings.
   - **Recommended Fix**: Include runtime.match_id in raised error messages.

4. **TL6**: Custom events not validated for JSON-serializability
   - **Description**: Events returned from game.get_events are passed through without validation.
   - **Impact**: Recorder/replay can fail if events contain non-serializable objects.
   - **Recommended Fix**: Validate or sanitize custom event payloads before returning TurnResult.

---

## Action Items

- [ ] Replace console.get_player_action calls with runtime-first parse failure handling
- [ ] Validate get_current_player outputs and raise ValueError on invalid results
- [ ] Include match_id in TurnLoop exception messages
- [ ] Enforce JSON-serializable custom events

