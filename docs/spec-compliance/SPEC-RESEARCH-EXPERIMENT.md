# SPEC-RESEARCH-EXPERIMENT Audit Note

Spec: [SPEC-RESEARCH-EXPERIMENT.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-EXPERIMENT.md)
Wave: 5
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Experiment package layout, manifest/results/index contracts, and validation/export script responsibilities.
- Does not own the live execution or post-hoc analysis implementation details beyond the generated artifact contract.

## Evidence Reviewed
- spec sections: full document, especially §§4-6
- implementation files: [research_export.py](/home/diegozoracky/dev/agentdeck-preview/scripts/research_export.py), [research_validate.py](/home/diegozoracky/dev/agentdeck-preview/scripts/research_validate.py), [research_index.py](/home/diegozoracky/dev/agentdeck-preview/scripts/research_index.py), [artifact_validation.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/artifact_validation.py)
- tests: [test_recording_metrics.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_recording_metrics.py), [test_research_validate.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_research_validate.py)
- docs/examples: [SCHEMA.md](/home/diegozoracky/dev/agentdeck-preview/research/SCHEMA.md), [results.json](/home/diegozoracky/dev/agentdeck-preview/research/_templates/results.json), [README.md](/home/diegozoracky/dev/agentdeck-preview/research/README.md)

## Findings

### Blocker
- none

### High
- none

### Medium
- The earlier spec treated `generated_at` as always required even though the export tool intentionally supports deterministic exports without it.
- Source provenance wording still carried backward-compatibility framing that no longer fits the pre-release cleanup direction.
- The schema/template docs still mentioned a `forfeit_rate` summary field that the export tool does not generate.

### Low
- The repeated `--recordings-dir` aggregation behavior existed in code but was under-described in the public API section.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 1
- doc/example drift: 2

## Required Remediation
- Make the spec and schema explicit about deterministic exports without `generated_at`.
- Define `source.recordings_dir` as the primary source pointer and `recordings_dirs` as the optional full provenance list for aggregated exports.
- Remove unsupported summary-field examples from schema docs/templates.

## Beta Relevance
- required before beta: yes, because experiment packages are a public release surface
- safe to defer: richer optional matrix conventions and future artifact types

## Final Verdict
- [SPEC-RESEARCH-EXPERIMENT.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-EXPERIMENT.md) is compliant after Wave 5 cleanup. The remaining contract is now honest about deterministic exports and aligned with the generated research artifacts.
