# AgentDeck Scripts

Utility scripts for validation, packaging, and viewer support.

## Research Workflow

- `research_package.py` promotes one or more `agentdeck_runs/<session>/` folders into a standardized package under `research/`.
- `research_export.py` generates `results.json` and `results.csv` from one or more recordings directories and fails fast on recording invariant violations.
- `research_index.py` regenerates `research/INDEX.md` from experiment manifests.
- `research_validate.py` validates package structure, generated artifacts, exported invariant summaries, and index consistency.

### Typical flow

```bash
python scripts/research_package.py \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here"

python scripts/research_export.py \
  --recordings-dir agentdeck_runs/session_YYYYMMDD_HHMMSS_xxxxxx/records \
  --output-dir research/YYYY-MM-DD-your-experiment \
  --no-generated-at

python scripts/research_validate.py --research-dir research --write-index
```

## Viewer Support

- `update_match_manifest.js` refreshes `viewer/matches/manifest.json`.
- `viewer_smoke_check.js` performs a lightweight replay-viewer sanity check.
- `viewer_test_match.py` generates a small local match for viewer testing.

## Validation Utilities

- `validate_schema_v1_3.py` runs a schema/replay validation flow.
- `validate_baseline.py` checks baseline assumptions used by local workflows.
- `bundle_specs.py` packages spec files for review or export.
- `ci.sh` runs the repository CI script locally.

One-off experiment runners are intentionally not part of the baseline branch.
