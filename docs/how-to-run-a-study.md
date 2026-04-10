# How To Run A Study

This is the supported common-case workflow for turning a research question into
an AgentDeck experiment package.

## What This Guide Covers

Use this flow when you want to:
- define a benchmark question
- run matrix-based cells under `research/`
- export cell and package artifacts
- validate the package before committing it

It assumes:
- you are working inside this repo
- runtime recordings stay outside git
- `matrix.yaml` is the source of truth for multi-cell benchmark packages
- preferred commands come from the installed `agentdeck-research-*` entry points
- the `scripts/` commands remain available as compatibility fallbacks inside the repo

If the `agentdeck-research-*` commands are not yet available in your shell, use
the equivalent `python scripts/...` command from the repo root.

## The Workflow

### 1. Start a Package

For a fresh package:

```bash
cp -R research/_templates research/YYYY-MM-DD-your-experiment
```

If you already have a finished session and want to package it quickly:

```bash
agentdeck-research-package \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here"
```

### 2. Fill The Package Contract

At minimum:
- set `manifest.yaml`
- set `README.md`
- define `matrix.yaml` if the package has benchmark cells/phases

For matrix-based studies, use:
- `player_registry` for reusable player/model definitions
- `player_ref` inside each cell side (`player_a`, `player_b`)

For matrix-based studies, keep these sections stable:
- `experiment_id`
- `cells`
- `execution_plan.phases`

Each cell should define at minimum:
- `id`
- `phase`

### 3. Add The Package-Local Runner

For matrix-based studies, start from the template runner:

```bash
python research/YYYY-MM-DD-your-experiment/scripts/run_experiment.py --list-cells
```

The template is intentionally package-local. Keep experiment execution logic in
the package, not in framework core.

If the study introduces a brand-new repo-local game, put the importable game
implementation under `src/agentdeck/games/examples/<slug>/` so the package can
import it cleanly without promoting it to the core built-in game surface.

For game-specific metrics, add a package-local analysis script under
`research/YYYY-MM-DD-your-experiment/scripts/` that reads `results.json` or raw
recordings and writes package-local artifacts. Do not modify the central
behavioral scorer registry unless the metric is generic across many studies.

If the study needs a formal `behavioral_profile` for a package-owned game, add
`research/YYYY-MM-DD-your-experiment/scripts/behavioral_scorer.py`. The scorer
must follow `SPEC-RESEARCH-BEHAVIORAL.md`, and `agentdeck-research-score` will
load it for that package without framework edits.

### 4. Run Cells

Typical patterns:

```bash
python research/YYYY-MM-DD-your-experiment/scripts/run_experiment.py --phase P1
python research/YYYY-MM-DD-your-experiment/scripts/run_experiment.py --cell p1_c01_example
python research/YYYY-MM-DD-your-experiment/scripts/run_experiment.py --cell p1_c01_example --dry-run
```

Recordings should land under:

```text
research/YYYY-MM-DD-your-experiment/agentdeck_runs/<cell_id>/session_*/records/
```

### 5. Export Cell Artifacts

Use the shared exporter instead of package-local export helpers:

```bash
agentdeck-research-export \
  --experiment-dir research/YYYY-MM-DD-your-experiment \
  --phase P1 \
  --no-generated-at
```

Or export a single cell:

```bash
agentdeck-research-export \
  --experiment-dir research/YYYY-MM-DD-your-experiment \
  --cell p1_c01_example \
  --no-generated-at
```

This writes canonical cell artifacts under:

```text
research/YYYY-MM-DD-your-experiment/artifacts/<cell_id>/
```

### 6. Export The Top-Level Package

After cell artifacts exist, aggregate the package:

```bash
agentdeck-research-export \
  --experiment-dir research/YYYY-MM-DD-your-experiment \
  --package \
  --no-generated-at
```

Package aggregation merges canonical `source.recordings_dir(s)` from cell
artifacts with discovered session recordings, while preferring canonical
sources first when both exist.

This step also refreshes the `AUTO_FACTS` blocks in the top-level
`README.md` and `analysis.md` from the exported package results.

Package-local behavioral scorers are a separate step. After export, run:

```bash
agentdeck-research-score \
  --experiment-dir research/YYYY-MM-DD-your-experiment
```

That updates only `results.json.behavioral_profile`. Export does not apply
package-local scorers automatically.

### 7. Validate And Index

Before committing:

```bash
agentdeck-research-validate --research-dir research --write-index
```

This validates:
- manifest structure
- generated results artifacts
- index consistency
- completed-package factual block expectations

For completed or archived packages with matches:
- keep the `AUTO_FACTS` markers in `README.md` and `analysis.md`
- do not leave placeholder values like `TBD` inside those blocks

### 8. Write Analysis And Recordings Pointers

Keep the narrative human-owned:
- update `analysis.md`
- update `notes/`
- update `recordings/README.md` with external storage pointers

Do not commit raw match recordings into git.

## Common Guardrails

- `matrix.yaml` should be the source of truth for cells/phases in benchmark grids.
- Use `--no-generated-at` when you want deterministic diffs.
- Keep `run_experiment.py` package-local even when the export path is shared.
- Prefer cell artifacts as the canonical source before top-level package export.
- Validate before committing.

## See Also

- [Research Guide](../research/README.md)
- [Research Schema](../research/SCHEMA.md)
- [Scripts README](../scripts/README.md)
- [Research Templates](../research/_templates/)
