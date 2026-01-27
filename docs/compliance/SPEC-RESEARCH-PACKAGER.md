# SPEC-RESEARCH-PACKAGER Implementation Compliance Report

**Spec Version**: 0.1.0
**Spec Status**: Draft
**Review Date**: 2026-01-21
**Reviewer**: Codex (automated review)
**Implementation**: `src/agentdeck/research/packager.py`, `scripts/research_package.py`, `scripts/research_export.py`, `scripts/research_index.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 8 |
| Compliant | 8 |
| Partial | 0 |
| Non-Compliant | 0 |
| N/A | 0 |

**Overall Compliance**: 100% (8/8 fully compliant)

---

## Invariant Compliance Matrix

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| RP1 | Tool is opt-in (no automatic execution) | Yes | `research_package.py:1-6`, `packager.py:349-361` | Only runs via CLI entrypoint |
| RP2 | Does not copy raw recordings into research/ | Yes | `packager.py:309-319` | Writes recordings README and invokes export instead of copying |
| RP3 | Writes manifest with required fields | Yes | `packager.py:198-228`, `packager.py:149-157` | build_manifest sets required fields; validates players |
| RP4 | Generates results via research_export.py | Yes | `packager.py:317-318` | Calls export_results from script |
| RP5 | Updates research/INDEX.md via research_index.py | Yes | `packager.py:320-322` | Calls generate_index and writes INDEX.md |
| RP6 | Fails if experiment dir exists | Yes | `packager.py:286-288` | Raises FileExistsError |
| RP7 | Fails fast when required fields cannot be inferred | Yes | `packager.py:198-212`, `packager.py:149-157`, `packager.py:269-271` | Raises ValueError on missing game/seed/provider/model/question |
| RP8 | Provider inference matches research_export mapping | Yes | `packager.py:13`, `research_export.py:13-26` | Uses shared provider_from_module mapping |

---

## Drift Issues

None.

---

## Action Items

None.

