# SPEC-RESEARCH-PACKAGER Audit Note

Spec: [SPEC-RESEARCH-PACKAGER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-PACKAGER.md)
Wave: 5
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Session-to-experiment promotion flow, manifest inference, export/index invocation, and research-template hydration.
- Does not own the downstream experiment schema beyond delegating to the export/index scripts and templates.

## Evidence Reviewed
- spec sections: full document, especially responsibilities, invariants, and CLI
- implementation files: [packager.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/research/packager.py), [research_package.py](/home/diegozoracky/dev/agentdeck-preview/scripts/research_package.py)
- tests: [test_research_packager.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_research_packager.py)
- docs/examples: [research/README.md](/home/diegozoracky/dev/agentdeck-preview/research/README.md), [manifest.yaml](/home/diegozoracky/dev/agentdeck-preview/research/_templates/manifest.yaml)

## Findings

### Blocker
- none

### High
- none

### Medium
- The multi-session checkpoint path was implemented but previously lacked direct RP13/RP14 coverage.

### Low
- The provider-inference invariant referenced an internal helper name in `research_export.py` instead of the shared provider utility actually used by both surfaces.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 1
- test drift: 2
- doc/example drift: 0

## Required Remediation
- Add direct tests for successful multi-session packaging and compatibility failure.
- Point the provider-inference contract at the shared helper instead of an internal script alias.

## Beta Relevance
- required before beta: yes, because this tool is the main path from sessions to curated experiment packages
- safe to defer: broader packaging sources beyond session directories

## Final Verdict
- [SPEC-RESEARCH-PACKAGER.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-RESEARCH-PACKAGER.md) is compliant after Wave 5 cleanup. The packager surface was already close to correct; the main remaining work was filling the missing multi-session test coverage.
