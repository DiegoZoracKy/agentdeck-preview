# Scripts

> **Historical Study scripts:** the shared export command and repository wrapper
> below belong to the `0.2` workflow preserved at the
> `agentic-edge-research` tag. They are not available on current `main`.

Place experiment-specific runners and helpers here.

Default expectation:
- keep execution package-local in `run_experiment.py`
- use the shared `agentdeck-research-export` workflow for cell/package export
- fall back to `python scripts/research_export.py` only when you need the repo-local wrapper

Examples:
- `run_experiment.py`
- `export_highlights.py`
