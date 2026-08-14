# AgentDeck Scripts

Utility scripts for Core validation, schema migration, spec bundling, and viewer
support. Research packaging and analysis are intentionally outside the current
AgentDeck package boundary. The historical workflow remains available at the
`agentic-edge-research` tag.

## Viewer Support

- `update_match_manifest.js` refreshes `viewer/matches/manifest.json`.
- `viewer_smoke_check.js` performs a lightweight replay-viewer sanity check.
- `viewer_test_match.py` generates a small local match for viewer testing.

## Validation Utilities

- `validate_schema_v1_3.py` validates existing schema v1.3 match recordings offline.
- `live_schema_check_v1_3.py` runs the OpenAI-backed schema/replay validation flow.
- `bundle_specs.py` packages spec files for review or export.
- `ci.sh` runs the repository CI script locally.

One-off experiment runners are intentionally not part of the baseline branch.
