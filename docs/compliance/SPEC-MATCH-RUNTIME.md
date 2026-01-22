# SPEC-MATCH-RUNTIME Implementation Compliance Report

**Spec Version**: 1.0.0
**Spec Status**: Draft
**Review Date**: 2026-01-21
**Reviewer**: Codex (automated review)
**Implementation**: `src/agentdeck/core/match_runtime.py`, `src/agentdeck/core/console.py`, `src/agentdeck/core/mechanics/turn_based.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 7 |
| Compliant | 3 |
| Partial | 4 |
| Non-Compliant | 0 |
| N/A | 0 |

**Overall Compliance**: 42.9% (3/7 fully compliant)

---

## Invariant Compliance Matrix

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| MR1 | One runtime per match; no shared mutable state | Yes | `console.py:2587-2621` | Console creates new MatchRuntime per match |
| MR2 | emit_event enforces lifecycle ordering and mechanic metadata | Partial | `match_runtime.py:180-206` | emit_event does not add mechanic metadata or enforce ordering |
| MR3 | record_turn emits GAMEPLAY events in execution order | Yes | `match_runtime.py:208-349` | Emits GAMEPLAY and appends to events list in-order |
| MR4 | handle_parse_failure emits event, logs, updates recorder, returns policy | Partial | `match_runtime.py:351-394`, `console.py:2133-2185` | Delegates to console but omits game argument for Console runtime |
| MR5 | RNG fork labels recorded in debug logs | Yes | `match_runtime.py:396-418` | Logs label and base seed |
| MR6 | Restore bindings even if mechanics raise | Partial | `turn_based.py:374-378` | Cleanup handled in TurnLoop, not in MatchRuntime itself |
| MR7 | Runtime extensibility remains backward compatible | Partial | `match_runtime.py:20-48` | No explicit compatibility enforcement or tests |

---

## Drift Issues

1. **MR2**: emit_event does not attach mechanic metadata or enforce ordering
   - **Description**: MatchRuntime.emit_event forwards payload without adding mechanic info or checking order.
   - **Impact**: Mechanics must remember to include mechanic metadata and ordering discipline.
   - **Recommended Fix**: Add optional mechanic parameter or inject default; validate lifecycle ordering.

2. **MR4**: handle_parse_failure delegates without game parameter in Console runtime
   - **Description**: MatchRuntime.handle_parse_failure calls Console._handle_parse_failure without game argument.
   - **Impact**: Invoking runtime.handle_parse_failure on the main Console path raises TypeError.
   - **Recommended Fix**: Pass self._game to console helper or adapt Console._handle_parse_failure signature.

3. **MR6**: Exception safety enforced in mechanic, not runtime
   - **Description**: TurnLoop handles unbinding in finally, but MatchRuntime provides no guard.
   - **Impact**: Non-turn-based mechanics could forget cleanup.
   - **Recommended Fix**: Provide a runtime-managed context or helper that restores bindings.

4. **MR7**: No explicit backward compatibility guard
   - **Description**: No tests or versioning enforce backward compatibility for runtime API.
   - **Impact**: Future runtime changes could break mechanics.
   - **Recommended Fix**: Add compatibility tests or versioned runtime interface.

---

## Action Items

- [ ] Inject mechanic metadata and enforce ordering in emit_event
- [ ] Fix handle_parse_failure to pass game context in Console runtime
- [ ] Add runtime-level cleanup helpers for mechanics
- [ ] Introduce compatibility tests/versioning for MatchRuntime API

