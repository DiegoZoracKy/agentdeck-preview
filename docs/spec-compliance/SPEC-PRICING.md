# SPEC-PRICING Audit Note

Spec: [SPEC-PRICING.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PRICING.md)
Wave: 3
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Central pricing data/schema contract and utility behavior for provider/model cost calculation.
- Does not own provider SDK usage capture beyond the metadata it consumes.

## Evidence Reviewed
- spec sections: full document, especially §§4-9
- implementation files: [pricing.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/utils/pricing.py), [pricing.yaml](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/config/pricing.yaml)
- tests: [test_pricing.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_pricing.py)
- docs/examples: in-spec utility examples and LLM/pricing integration references

## Findings

### Blocker
- none

### High
- The YAML metadata schema had drifted. The shipped file exposes `updated_at`, `last_updated`, and `sources`, while the spec still documented a simpler singular `source`.
- Error semantics were overstated: validation failures do raise `ValueError`, but generic load/parsing failures fall back to `{}` with logging.
- `calculate_cost()` logging severity was stale in the spec; the shipped helper logs warnings, not errors, on missing pricing.

### Medium
- This surface had no dedicated unit coverage before Wave 3, which made spec drift harder to spot and easier to reintroduce.

### Low
- A few example assertions hard-coded older messaging around error severity.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 4
- test drift: 1
- doc/example drift: 1

## Required Remediation
- Rewrite metadata and error-handling sections to the real utility behavior.
- Add focused pricing tests for packaged data, validation, provider defaults, and zero-cost fallback.

## Beta Relevance
- required before beta: yes, because public beta research claims include cost observability
- safe to defer: richer pricing-source provenance beyond the current packaged snapshot

## Final Verdict
- [SPEC-PRICING.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-PRICING.md) is compliant after the Wave 3 cleanup. The spec now matches the packaged pricing schema and the real fallback/validation behavior, and the surface finally has direct unit coverage.
