# SPEC-PARALLEL Implementation Compliance Report

**Spec Version**: 0.1.0
**Spec Status**: Draft
**Review Date**: 2026-01-21
**Reviewer**: Codex (automated review)
**Implementation**: `src/agentdeck/core/console.py`, `src/agentdeck/core/session.py`, `src/agentdeck/core/types.py`, `README.md`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 11 |
| Compliant | 8 |
| Partial | 3 |
| Non-Compliant | 0 |
| N/A | 0 |

**Overall Compliance**: 72.7% (8/11 fully compliant)

---

## Invariant Compliance Matrix

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| BC1 | concurrency==1 preserves legacy sequential behavior | Yes | `console.py:1171-1181` | Uses legacy direct path when concurrency==1 |
| DS1 | Per-match seed derivation uses base_seed + match_index | Yes | `console.py:1192-1194`, `console.py:1519-1524`, `console.py:2515-2518` | _derive_match_seed implements base_seed+index |
| EO1 | Replay events in match_index order | Yes | `console.py:1621-1628` | Replays artifacts in ordered list |
| SI1 | Single session/batch lifecycle events preserved | Yes | `console.py:1156-1165`, `console.py:1299-1308`, `console.py:1657-1678` | BATCH_START/END emitted once; events replayed via main bus |
| PO1 | Parallel-incompatible get_player_order falls back sequentially with warning | Partial | `console.py:1257-1268` | Falls back, but logs debug (not warning) |
| IS1 | Worker isolation via deep-copied game/players and dedicated RNG | Yes | `console.py:162-199`, `console.py:551-567` | Deep copies and isolated match runtime |
| FP1 | Worker failure cancels remaining work, emits partial BATCH_END, raises | Partial | `console.py:1546-1619`, `console.py:1286-1296` | Raises on failure, but does not cancel in-flight futures |
| CF1 | Cloning failure raises ParallelExecutionError before worker launch | Yes | `console.py:42-54`, `console.py:162-191` | ParallelExecutionError raised during cloning |
| MP1 | Aggregate player metrics synchronized back to originals | Yes | `console.py:1395-1397`, `console.py:1627-1632`, `console.py:1706-1721` | Syncs totals and response_times |
| RC1 | Recorder parity via sanitized snapshots + replay events | Yes | `console.py:954-1026`, `console.py:1657-1678` | Captures sanitized events and replays originals |
| PC1 | Performance guidance encourages benchmarking concurrency | Partial | `README.md:295-321` | Mentions speedup but not explicit benchmarking guidance |

---

## Drift Issues

1. **PO1**: Fallback warning uses debug level
   - **Description**: Parallel-incompatible `get_player_order` fallback logs at DEBUG.
   - **Impact**: Users may miss the fallback and assume parallel execution.
   - **Recommended Fix**: Raise to warning level and include effective concurrency.

2. **FP1**: Parallel failures do not cancel remaining workers
   - **Description**: On worker failure, executor continues running other futures.
   - **Impact**: Extra work can run after a failure, diverging from spec behavior.
   - **Recommended Fix**: Cancel outstanding futures on first failure and stop scheduling.

3. **PC1**: Benchmarking guidance not explicitly documented
   - **Description**: README highlights speedup but does not advise benchmarking workload.
   - **Impact**: Users may over-allocate concurrency for rate-limited providers.
   - **Recommended Fix**: Add explicit guidance to benchmark concurrency for workload/provider.

---

## Action Items

- [ ] Log a warning when falling back to sequential due to get_player_order override
- [ ] Cancel outstanding futures on first worker failure
- [ ] Document benchmarking guidance for concurrency selection

