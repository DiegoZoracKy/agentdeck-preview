# SPEC-RESEARCH Audit Note

Spec: [SPEC-RESEARCH.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH.md)
Wave: 5
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Research helper layer for live comparisons, post-hoc session analysis, and lightweight cross-session comparison.
- Does not own experiment package schema, recorder integrity validation, or the core execution lifecycle.

## Evidence Reviewed
- spec sections: full document, especially public API and invariants
- implementation files: [analysis.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/analysis.py), [comparison.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/comparison.py), [statistical.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/statistical.py), [statistical_analysis.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/statistical_analysis.py), [performance_analysis.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/performance_analysis.py), [cost_analysis.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/cost_analysis.py), [multi_session.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/multi_session.py), [research_spectators.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/spectators/research_spectators.py)
- tests: [test_results_analyzer.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_results_analyzer.py), [test_research_costs.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_research_costs.py), [test_research_posthoc.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_research_posthoc.py)
- docs/examples: [__init__.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/__init__.py)

## Findings

### Blocker
- none

### High
- The prior spec overpromised several cross-session capabilities that are not part of the shipped beta surface, especially cost/performance comparison tables and generalized model-comparison matrices.

### Medium
- The prior spec described post-hoc analysis as validating full recording completeness from batch and match JSON files, while the current beta implementation primarily reads recorder-produced batch summaries under `records/`.
- The previous version mixed stable public contract with internal ambition notes, making the document heavier than needed for a spec-first repo.

### Low
- Module-level docs still carried older “Kaggle-inspired” framing and version-specific notes that were less precise than the actual public contract.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 0
- doc/example drift: 1

## Required Remediation
- Trim the spec to the real beta contract instead of expanding code toward older ambitions.
- Keep the research layer focused on live comparisons, post-hoc session analysis, and lightweight cross-session summaries.

## Beta Relevance
- required before beta: yes, because this spec informs the research story and exported API surface
- safe to defer: richer benchmark-management ambitions and broader cross-session tables

## Final Verdict
- [SPEC-RESEARCH.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH.md) is compliant after Wave 5 cleanup. The spec now matches the actual research API instead of promising a larger framework than the beta intends to ship.
