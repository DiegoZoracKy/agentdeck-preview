# SPEC-PROMPT-BUILDER Implementation Compliance Report

**Spec Version**: 0.4.0
**Spec Status**: Draft
**Review Date**: 2026-01-21
**Reviewer**: Claude (automated review)
**Implementation**: `src/agentdeck/core/prompt_builder.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Invariants | 15 |
| Compliant | 15 |
| Partial | 0 |
| Non-Compliant | 0 |
| N/A | 0 |

**Overall Compliance**: 100.0% (15/15 fully compliant)

---

## Invariant Compliance Matrix

### 5.1 Template Control (TC1-TC3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| TC1 | Templates are ONLY source of truth for prompt content | ✅ Yes | `prompt_builder.py:317-373` | `compose()` uses template.format_map() - only placeholders in template appear in output |
| TC2 | Researchers control what appears by choosing placeholders | ✅ Yes | `prompt_builder.py:348-349` | Template string directly controls output via str.format() |
| TC3 | No hidden filtering or automatic block suppression | ✅ Yes | `prompt_builder.py:340-346` | DefaultEmptyDict renders missing keys as empty string, no filtering |

### 5.2 Composition Determinism (CD1-CD3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| CD1 | Identical inputs MUST produce identical PromptBundle | ✅ Yes | `prompt_builder.py:241-373` | Pure function: same phase + templates + inputs → same output |
| CD2 | Renderer output MUST be inserted without alteration | ✅ Yes | `prompt_builder.py:449` | `substitutions["game_view"] = ctx.render_result.text` - verbatim |
| CD3 | Template selection based on phase MUST be deterministic | ✅ Yes | `prompt_builder.py:375-395` | `_select_template()` uses simple if/elif based on LifecyclePhase enum |

### 5.3 Metadata Capture (MC1-MC3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| MC1 | metadata MUST contain template_id, phase, turn_number, blocks_rendered | ✅ Yes | `prompt_builder.py:366-371` | All four fields populated in compose() |
| MC2 | blocks MUST contain ordered PromptBlock entries for each placeholder | ✅ Yes | `prompt_builder.py:497-530` | `_build_blocks()` creates PromptBlock for every placeholder in order |
| MC3 | When RenderResult has metadata, MUST preserve in corresponding PromptBlock | ✅ Yes | `prompt_builder.py:525-527` | `if name == "game_view" and render_result.metadata: metadata = render_result.metadata` |

### 5.4 Provider Safety (PS1-PS3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| PS1 | Custom providers MUST receive immutable PromptContext | ✅ Yes | `prompt_builder.py:414-416` | `immutable_extras = MappingProxyType(extras)` in `_build_context()` |
| PS2 | Builder MUST memoize provider output per composition call | ✅ Yes | `prompt_builder.py:459-472` | `if name not in provider_cache:` check before evaluation |
| PS3 | Provider exceptions MUST surface as TemplateError | ✅ Yes | `prompt_builder.py:464-471` | `except Exception as e: raise TemplateError(...)` |

### 5.5 Error Handling (EH1-EH3)

| ID | Description | Status | Evidence | Notes |
|----|-------------|--------|----------|-------|
| EH1 | Undefined placeholder MUST raise TemplateError; missing extras render empty | ✅ Yes | `prompt_builder.py:340-358` | DefaultEmptyDict returns "" for missing keys; KeyError (if any) raises TemplateError |
| EH2 | Missing template for phase MUST fall back to minimal default | ✅ Yes | `prompt_builder.py:87-97, 130-134` | DEFAULT_HANDSHAKE, DEFAULT_TURN, DEFAULT_CONCLUSION defined and used in `_load_template()` |
| EH3 | Provider exceptions MUST be wrapped in TemplateError | ✅ Yes | `prompt_builder.py:464-471` | Same as PS3 |

---

## Drift Issues

None identified. Implementation fully complies with spec.

---

## Action Items

None required.

---

## Verification Notes

### Template Control Verified
- Templates use Python str.format() syntax
- `compose()` calls `template.format_map(format_dict)`
- No hidden filtering - DefaultEmptyDict returns "" for missing keys
- Only placeholders in template appear in final output

### Determinism Verified
- `compose()` is a pure function with no side effects
- Template selection via `_select_template()` uses simple phase mapping
- Same inputs (phase, templates, render_result, controller_format, extras) produce identical output

### Metadata Capture Verified
PromptBundle metadata at `prompt_builder.py:366-371`:
```python
metadata = {
    "template_id": template_id,
    "phase": phase.value,
    "turn_number": turn_number,
    "blocks_rendered": [block.key for block in blocks],
}
```

### PromptBlock Construction Verified
`_build_blocks()` at `prompt_builder.py:497-530`:
- Iterates placeholder_names in order of appearance
- Creates PromptBlock for every placeholder (even if content is empty)
- Preserves render_result.metadata for game_view block (MC3)

### Provider Safety Verified
- Context wrapped in MappingProxyType for immutability (PS1)
- Provider cache prevents double evaluation (PS2)
- Exceptions wrapped in TemplateError with context (PS3)

### Default Templates Verified
```python
DEFAULT_HANDSHAKE = "You are playing {game_name}...{handshake_controller_format}"
DEFAULT_TURN = "{game_view}\n\n{controller_format}"
DEFAULT_CONCLUSION = "=== Match Concluded ===\n\n{outcome}\n\nFinal state:\n{game_view}"
```

### Factory Methods Verified
- `from_template(template)` - creates turn-only builder
- `from_file(path)` - loads template from file
- `from_function(compose_fn)` - escape hatch for custom logic

---

## Notes

- Implementation is clean and fully compliant with spec
- DefaultEmptyDict pattern elegantly handles optional extras keys
- MappingProxyType ensures true immutability for providers
- Memoization prevents provider double-evaluation
- All 15 invariants pass without issues
