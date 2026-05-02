# AgentDeck Scripts

Utility scripts for validation, packaging, and viewer support.

The preferred research workflow now lives in package-owned entry points:
- `agentdeck-research-export`
- `agentdeck-research-index`
- `agentdeck-research-package`
- `agentdeck-research-validate`

The `scripts/` files remain as backward-compatible wrappers for repo-local use.

## Research Workflow

- `research_package.py` wraps the package-owned packager surface and promotes one or more `agentdeck_runs/<session>/` folders into a standardized package under `research/`.
- `research_export.py` wraps the package-owned export surface and generates `results.json`, `results.csv`, and deterministic `results.md` from one or more recordings directories while failing fast on recording invariant violations.
  It also supports matrix-based cell export and package aggregation for benchmark-grid studies.
- `research_index.py` wraps the package-owned index surface and regenerates `research/INDEX.md` from experiment manifests.
- `research_validate.py` wraps the package-owned validation surface and validates package structure, generated artifacts, exported invariant summaries, and index consistency.

### Typical flow

```bash
agentdeck-research-package \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here"

agentdeck-research-export \
  --recordings-dir agentdeck_runs/session_YYYYMMDD_HHMMSS_xxxxxx/records \
  --output-dir research/research_YYYY-MM-DD-your-experiment \
  --no-generated-at

agentdeck-research-validate --research-dir research --write-index
```

### Matrix-Based Benchmark Flow

Export one selected cell from a benchmark package:

```bash
agentdeck-research-export \
  --experiment-dir research/research_YYYY-MM-DD-your-experiment \
  --cell p1_c01_example \
  --no-generated-at
```

Export all cells from one phase:

```bash
agentdeck-research-export \
  --experiment-dir research/research_YYYY-MM-DD-your-experiment \
  --phase P1 \
  --no-generated-at
```

Aggregate the top-level package from canonical cell artifacts and/or discovered
session recordings:

```bash
agentdeck-research-export \
  --experiment-dir research/research_YYYY-MM-DD-your-experiment \
  --package \
  --no-generated-at
```

## Viewer Support

- `update_match_manifest.js` refreshes `viewer/matches/manifest.json`.
- `viewer_smoke_check.js` performs a lightweight replay-viewer sanity check.
- `viewer_test_match.py` generates a small local match for viewer testing.

## Validation Utilities

- `validate_schema_v1_3.py` validates existing schema v1.3 match recordings offline.
- `live_schema_check_v1_3.py` runs the OpenAI-backed schema/replay validation flow.
- `validate_baseline.py` checks baseline assumptions used by local workflows.
- `bundle_specs.py` packages spec files for review or export.
- `ci.sh` runs the repository CI script locally.

One-off experiment runners are intentionally not part of the baseline branch.
