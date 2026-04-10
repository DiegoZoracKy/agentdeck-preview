# Scripts

Place experiment-specific runners and helpers here.

Default expectation:
- keep execution package-local in `run_experiment.py`
- use the shared `agentdeck-research-export` workflow for cell/package export
- add `behavioral_scorer.py` only when the package needs a formal
  `behavioral_profile`
- fall back to `python scripts/research_export.py` only when you need the repo-local wrapper

Examples:
- `run_experiment.py`
- `behavioral_scorer.py`
- `export_highlights.py`
