# SPEC-PRICING Implementation Compliance Report

**Spec Version**: 1.0.0
**Spec Status**: Final
**Review Date**: 2026-01-21
**Reviewer**: Claude (automated review)
**Implementation**: `src/agentdeck/utils/pricing.py`, `src/agentdeck/config/pricing.yaml`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 16 |
| Compliant | 14 |
| Partial | 1 |
| Non-Compliant | 1 |
| N/A | 0 |

**Overall Compliance**: 87.5% (14/16 fully compliant)

---

## Invariant Compliance Matrix

### YAML Validation (V0-V6)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| V0 | Root structure MUST be dict; MUST check isinstance() BEFORE calling .items() | ❌ No | `pricing.py:23-26` | Missing explicit `isinstance(data, dict)` check before `data.items()` |
| V1 | Required fields (input_cost_per_million, output_cost_per_million) | ✅ Yes | `pricing.py:46-49` | Checks for both required keys |
| V2 | Type safety (costs are numeric) | ✅ Yes | `pricing.py:51-56` | `isinstance(value, (int, float))` check |
| V3 | Non-negative costs | ✅ Yes | `pricing.py:58-59` | `if value < 0` raises ValueError |
| V4 | Provider structure (providers are dicts) | ✅ Yes | `pricing.py:30-34` | `isinstance(models, dict)` check |
| V5 | Metadata exclusion | ✅ Yes | `pricing.py:27-28` | `if provider == "metadata": continue` |
| V6 | Special keys skip validation | ✅ Yes | `pricing.py:37-38` | `if model.startswith("_"): continue` |

### Python API Functions

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| L1 | load_pricing_data() caches globally | ✅ Yes | `pricing.py:73-76` | `global _pricing_data` with `if _pricing_data is not None: return` |
| L2 | load_pricing_data() validates before caching | ✅ Yes | `pricing.py:91-94` | Calls `_validate_pricing_structure(data)` before setting `_pricing_data` |
| L3 | load_pricing_data() returns {} on missing file | ✅ Yes | `pricing.py:82-85` | `if not pricing_file.exists(): return {}` |
| L4 | load_pricing_data() raises ValueError on validation failure | ✅ Yes | `pricing.py:96-99` | `raise` preserves ValueError |
| G1 | get_model_pricing() exact match first | ✅ Yes | `pricing.py:143-148` | `if model in provider_pricing` |
| G2 | get_model_pricing() fallback to _default | ✅ Yes | `pricing.py:150-161` | `if "_default" in provider_pricing` |
| G3 | get_model_pricing() allow_missing=False raises ValueError | ✅ Yes | `pricing.py:171-179` | Raises ValueError with helpful message |
| G4 | get_model_pricing() allow_missing=True returns (0.0, 0.0) | ✅ Yes | `pricing.py:164-170` | Returns tuple with warning |
| C1 | calculate_cost() catches ValueError, returns 0.0, logs ERROR | ⚠️ Partial | `pricing.py:202-212` | Catches and returns 0.0 but uses `logging.error()` not AgentDeckLogger |

---

## Drift Issues

### 1. **V0**: Missing root structure validation

**Description**: SPEC-PRICING §4.3 V0 (critical) states:
> "The YAML root MUST be a dict/mapping. If pricing.yaml contains a list, scalar, or null at the top level, validation MUST raise ValueError BEFORE attempting to iterate. This prevents AttributeError and ensures 'fail fast & loudly' behavior."

**Current Behavior**: `_validate_pricing_structure()` at `pricing.py:23-26`:
```python
if not data:
    return  # Empty dict is valid
for provider, models in data.items():  # <-- Will AttributeError if data is list/None
```

The function calls `data.items()` without first checking `isinstance(data, dict)`. If YAML root is a list, this causes AttributeError (not ValueError), which is caught by the broad `except Exception` in `load_pricing_data()` and returns `{}` silently.

**Impact**: Malformed YAML (list root) fails silently with `{}` instead of raising ValueError. This violates the "fail fast & loudly" principle.

**Recommended Fix**:
```python
def _validate_pricing_structure(data) -> None:
    if not isinstance(data, dict):
        raise ValueError(f"pricing.yaml root must be a dict, got {type(data).__name__}")
    if not data:
        return
    for provider, models in data.items():
        ...
```

### 2. **C1**: Logger not using AgentDeckLogger

**Description**: The spec notes costs should be logged to AgentDeckLogger for consistency with the rest of the framework.

**Current Behavior**: Uses standard library `logging.error()`, `logging.warning()`, etc.

**Impact**: Minor - logs still work but don't integrate with AgentDeck's structured logging infrastructure.

**Status**: Partial compliance - functional but not integrated with AgentDeckLogger.

---

## Action Items

- [ ] **V0**: Add explicit `isinstance(data, dict)` check at start of `_validate_pricing_structure()` (critical)
- [ ] **C1**: Consider using AgentDeckLogger for consistent logging integration (optional)

---

## Verification Notes

### pricing.yaml File Exists
File located at `src/agentdeck/config/pricing.yaml` with proper structure:
- OpenAI models with pricing
- Metadata section
- _default fallback for unknown models
- Uses YAML anchors for repeated values

### Caching Verified
`load_pricing_data()` uses global `_pricing_data` variable with None check to avoid repeated file loads.

### Validation Pipeline Verified
1. Check file exists (return `{}` if not)
2. Load YAML
3. Call `_validate_pricing_structure(data)`
4. Cache on success, raise on validation failure

### Cost Calculation Verified
```python
input_cost = (prompt_tokens / 1_000_000) * input_cost_per_million
output_cost = (completion_tokens / 1_000_000) * output_cost_per_million
return input_cost + output_cost
```

### Error Messages Verified
`get_model_pricing()` provides helpful error messages:
```python
f"Available providers: {available_providers}. "
f"Available models for '{provider}': {available_models}. "
```

### Fallback Behavior Verified
- Missing file: `{}` returned, WARNING logged
- Unknown provider/model: ValueError or (0.0, 0.0) depending on allow_missing
- calculate_cost(): Always returns float (0.0 on error)

---

## Notes

- Core pricing calculation logic is correct
- YAML structure supports multi-provider configuration
- _default fallback provides reasonable behavior for new models
- Critical gap in V0 validation could allow malformed YAML to fail silently
- Pricing YAML includes OpenAI models with accurate tiered pricing
