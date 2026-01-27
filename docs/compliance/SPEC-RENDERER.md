# SPEC-RENDERER Implementation Compliance Report

**Spec Version**: 0.3.0
**Spec Status**: Draft (In Review)
**Review Date**: 2026-01-21
**Reviewer**: Codex (automated review)
**Implementation**: `src/agentdeck/core/base/renderer.py`, `src/agentdeck/renderers/text_renderer.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 9 |
| Compliant | 7 |
| Partial | 1 |
| Non-Compliant | 1 |
| N/A | 0 |

**Overall Compliance**: 77.8% (7/9 fully compliant)

---

## Invariant Compliance Matrix

### Deterministic Formatting (DF1-DF2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| DF1 | Deterministic output for identical inputs | Yes | `text_renderer.py:71-122` | Output derived from input order and values |
| DF2 | Treat game_view/turn_context as read-only | Yes | `text_renderer.py:71-122` | No mutation of inputs |

### Mechanics-Agnostic Boundaries (MB1-MB2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| MB1 | Do not introduce hidden info absent from game_view | Yes | `text_renderer.py:88-111`, `text_renderer.py:132-155` | Renders only supplied keys/values |
| MB2 | No reliance on global state; behavior from inputs/config | Yes | `text_renderer.py:40-48`, `text_renderer.py:71-122` | Uses instance config only |

### Metadata and Observability (MO1-MO3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| MO1 | metadata JSON-serializable; include format hints/sections | Partial | `text_renderer.py:115-121` | JSON-serializable and includes sections, but no format hint |
| MO2 | describe() includes name/version/metadata | Yes | `renderer.py:98-129`, `text_renderer.py:173-183` | Default and TextRenderer describe meet schema |
| MO3 | Include turn_context fields in metadata when provided | Yes | `text_renderer.py:75-121` | Adds turn_number when turn_context present |

### Error Handling (EH1-EH2)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| EH1 | Raise descriptive ValueError when required fields missing | No | `text_renderer.py:71-122` | No validation or descriptive errors for missing keys/types |
| EH2 | Tolerate absent turn_context | Yes | `text_renderer.py:75-121` | Handles None and falls back to state["turn"] |

---

## Drift Issues

1. **MO1**: Missing format hint in metadata
   - **Description**: Metadata includes sections but omits a format marker (e.g., "format": "text").
   - **Impact**: Downstream tooling cannot quickly identify renderer output type.
   - **Recommended Fix**: Add a format hint key in metadata.

2. **EH1**: No validation for missing required fields
   - **Description**: TextRenderer does not raise descriptive ValueError when expected keys are missing or malformed.
   - **Impact**: Errors surface as generic AttributeError/KeyError instead of spec-required ValueError.
   - **Recommended Fix**: Validate required keys (if any) and raise ValueError with clear messages.

---

## Action Items

- [ ] Add a metadata format hint (e.g., "format": "text")
- [ ] Implement explicit validation and descriptive ValueError for required fields

