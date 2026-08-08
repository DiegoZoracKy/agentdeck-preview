# SPEC-RESEARCH-INTERVENTION-COMPARISON

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-04
> Implementation: Complete (`agentdeck.research.intervention`)
> Review State: Legacy-approved
> Audience: research engineers, product integrators

## 1. Purpose

Define a deterministic Core artifact for comparing one completed baseline run
with one completed intervention run. The artifact answers what direction was
observed and how uncertain the difference is. It does not infer lineage,
declare that a method changed, or create a causal finding.

## 2. Inputs

`compare_intervention_results(...)` consumes two Core `results.json` mappings,
the focal player identity in each result, exact source hashes, and a product-
verified design declaration. Version 0.1 supports independent binary outcomes
only. Separate sessions MUST NOT be described as paired without a future paired
comparison contract.

The design declaration contains the baseline and intervention run identifiers,
the declared changed paths, preserved-path parity status, execution profiles,
and whether each profile supports a finding.

## 3. Artifact

The returned `InterventionComparisonArtifact` contains:

- schema, version, kind, generated timestamp, and test name;
- exact baseline and intervention run IDs and results SHA-256 values;
- focal player identity, wins, decisive matches, total matches, win rate, and
  package-provided marginal Wilson interval for each side;
- observed win-rate difference (`intervention - baseline`);
- Newcombe confidence interval for the difference of independent proportions;
- two-sided Fisher exact p-value and significance state;
- evidence classification and explicit limitations.

## 4. Invariants

1. **RIC1 Exact sources:** both results hashes MUST be valid SHA-256 values and
   MUST be retained verbatim in the artifact.
2. **RIC2 No lineage inference:** Core MUST accept declared lineage and method
   parity as inputs; it MUST NOT infer them from outcomes or labels.
3. **RIC3 Focal identity:** the focal player MUST resolve unambiguously in both
   results mappings.
4. **RIC4 Binary outcome:** wins and decisive-match counts MUST be non-negative,
   internally consistent, and contain at least one decisive match per side.
5. **RIC5 Independent test:** v0.1 MUST use a Newcombe difference interval and
   two-sided Fisher exact test and MUST label the design `independent_binary`.
6. **RIC6 No finding from preview:** if either execution profile does not
   support a finding, the evidence classification MUST be
   `observational_direction_only` regardless of point estimate or p-value.
7. **RIC7 Method parity gate:** an artifact MUST NOT be generated unless the
   caller declares preserved-path parity and at least one changed path.
8. **RIC8 Null parity:** a null, contrary, or uncertain result MUST receive the
   same complete artifact as a positive direction.
9. **RIC9 No causal prose:** the artifact MUST NOT state that the intervention
   caused, improved, fixed, or harmed behavior.
10. **RIC10 Immutable value object:** inputs MUST NOT be mutated and the
    serialized artifact MUST be stable except for its generated timestamp.

## 5. Errors

Missing statistics, unknown focal players, malformed hashes, zero decisive
matches, missing changed paths, failed parity, and invalid confidence levels
fail explicitly before an artifact is returned.

## 6. Testing

Tests cover null, positive, and contrary directions; one-match previews;
evidence-grade profiles; malformed inputs; parity refusal; exact source
retention; and the canonical `1/1 versus 0/1` case whose interval crosses zero
and whose Fisher p-value is `1.0`.

## 7. Non-Goals

Paired cross-run inference, sequential analysis, multiple interventions,
meta-analysis, behavioral-metric differences, lineage creation, Study curation,
or natural-language interpretation.

## 8. Rationale

Two individually honest result cards can create an inflated claim when placed
side by side. Core therefore owns the direct numerical comparison while the
product owns why those two runs are related. Keeping those authorities separate
preserves both statistical rigor and declared research intent.
