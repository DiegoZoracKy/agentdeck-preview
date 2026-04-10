# SPEC-RESEARCH-WORKFLOW v0.1.2

> Status: Final
> Version: 0.1.2
> Last Updated: 2026-03-27
> Implementation: ✅ Complete (`agentdeck.research.export`, `agentdeck.research.index`, thin `scripts/` wrappers)
> Audience: Research engineers, experiment authors, contributors

## 1. Purpose
- Define one supported, documented workflow for matrix-based research packages.
- Promote shared export and index mechanics into package-owned research modules.
- Keep execution logic package-local while making export, scoring, and indexing feel like first-class product surfaces.

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC.md` reproducibility goals and `CONTRIBUTING.md` spec-first workflow.
- Builds on `SPEC-RESEARCH-EXPERIMENT.md` and `SPEC-RESEARCH-PACKAGER.md` instead of replacing them.
- Favors one coherent common-case path over a broad orchestration framework.
- Keeps workflow logic in `src/agentdeck/research/` and treats `scripts/` as compatibility wrappers.
- Non-goals:
  - moving package-specific `run_experiment.py` logic into framework core
  - native recovery orchestration, segmented execution, or duplicate-pruning policy
  - replacing package-local execution scripts

## 3. Responsibilities
- Support matrix-aware cell export from shared package-owned tooling.
- Support package-level aggregation from canonical cell artifacts and/or discovered session recordings.
- Keep direct recordings-dir export working unchanged for single-run or non-matrix workflows.
- Provide installable research CLI entry points for export and index generation.
- Retain backward-compatible `scripts/research_export.py` and `scripts/research_index.py` wrappers.
- Document the minimum `matrix.yaml` sections required for the shared workflow.
- Provide a minimal research-package execution template that stays package-local.

## 4. Public API

### 4.1 Shared Export Surface
The shared export surface MUST be implemented in `agentdeck.research.export` and exposed through:

- **Package API**:
  - `export_results(...)`
- **CLI entry point**:
  - `agentdeck-research-export ...`
- **Module execution**:
  - `python -m agentdeck.research.export ...`
- **Compatibility wrapper**:
  - `python scripts/research_export.py ...`

All supported entry paths MUST provide the same behavior.

### 4.2 Shared Export Workflow
The export surface MUST support two modes:

- **Direct mode**:
  - existing `--recordings-dir ... --output-dir ...` workflow
- **Matrix mode**:
  - `--experiment-dir <path>`
  - `--matrix <path>` (optional when defaulting to `<experiment-dir>/matrix.yaml`)
  - `--list-cells`
  - `--cell <id>` (repeatable)
  - `--phase <id>`
  - `--package`

### 4.3 Matrix Mode Semantics
- `--list-cells`:
  - print available cell ids with phase metadata
  - perform no export
- `--cell` / `--phase`:
  - export selected cells into `artifacts/<cell_id>/results.json` and `results.csv`
- `--package`:
  - export top-level package `results.json` and `results.csv`
  - refresh factual marker blocks in top-level `README.md` and `analysis.md`
  - merge canonical `source.recordings_dir(s)` from cell artifacts with discovered
    `agentdeck_runs/<cell_id>/session_*/records`
  - prefer canonical cell-artifact sources first when both exist and remain usable
  - ignore canonical sources that do not exist, are not directories, or contain no
    `match_*.json` files

### 4.4 Shared Index Surface
The shared index surface MUST be implemented in `agentdeck.research.index` and exposed through:

- **Package API**:
  - `generate_index(...)`
- **CLI entry point**:
  - `agentdeck-research-index ...`
- **Module execution**:
  - `python -m agentdeck.research.index ...`
- **Compatibility wrapper**:
  - `python scripts/research_index.py ...`

### 4.5 Minimal Matrix Contract
The supported shared workflow assumes these `matrix.yaml` sections exist:
- `experiment_id`
- `cells`
- `execution_plan.phases` (optional but required when `--phase` is used)

Each cell MUST define:
- `id`
- `phase`

The workflow MUST NOT require model/config registries for export-only operations.

## 5. Invariants
- **RW1**: Direct mode and matrix mode MUST remain separate entry paths; direct mode behavior MUST stay backward-compatible.
- **RW2**: Matrix mode MUST deduplicate recordings directories by resolved path.
- **RW3**: Cell export MUST fail fast when the selected cell ids do not exist.
- **RW4**: Cell export MUST skip cells with no discovered recordings rather than fabricate empty artifacts.
- **RW5**: Package export MUST prefer usable canonical sources from committed cell
  artifacts when they exist.
- **RW5a**: Package export MUST ignore unusable canonical sources from committed cell
  artifacts and continue with discovered session recordings when available. A canonical
  source is unusable when the path does not exist, is not a directory, or contains no
  `match_*.json` files.
- **RW6**: Package export MUST preserve deterministic outputs when `--no-generated-at` is used.
- **RW6a**: Package export MUST refresh top-level factual marker blocks when
  `README.md` / `analysis.md` contain `AUTO_FACTS` markers.
- **RW7**: Shared tooling MUST NOT own or infer experiment execution policy; it only exports, scores, aggregates, and indexes outputs.
- **RW8**: The minimal template `scripts/run_experiment.py` MUST remain package-local and framework-agnostic beyond stable public AgentDeck APIs.
- **RW9**: Workflow logic MUST live in `src/agentdeck/research/`; any `scripts/` entry file for export or index MUST be a thin wrapper over the package-owned implementation.
- **RW10**: The shared export surface MUST remain the supported path for behavioral scoring in matrix/package workflows; experiment packages MUST NOT require custom scorer scripts for common-case export.

## 6. Error Handling
- Missing `matrix.yaml` in matrix mode: raise `FileNotFoundError` with the expected path.
- Missing selected cells: exit with a clear selection error.
- `--package` with no usable cell recordings: fail fast with clear provenance guidance.
- Invalid mixed mode (for example, `--recordings-dir` plus `--package`): reject early with a clear CLI error.

## 7. Testing Strategy
- Verify direct export mode remains unchanged.
- Verify matrix mode can:
  - list cells
  - export a selected cell from discovered session recordings
  - export a package from canonical cell artifacts
  - merge canonical and discovered sources, and still export from discovered
    session recordings when cell artifacts are absent
  - ignore dead or empty canonical artifact sources and still export from discovered
    session recordings
- Verify duplicate recordings dirs are deduplicated.
- Verify invalid cell selection and missing matrix files fail fast.
- Verify the package-owned module and the `scripts/` wrapper share the same behavior.
- Verify the index CLI and package API remain aligned.

## 8. Examples

### Direct export
```bash
agentdeck-research-export \
  --recordings-dir agentdeck_runs/session_x/records \
  --output-dir research/2026-03-26-demo
```

### Export one matrix cell
```bash
agentdeck-research-export \
  --experiment-dir research/2026-03-25-variable-damage-parity-1 \
  --cell p1_c01_flash_lite_rc_risk_vs_flash_ao \
  --no-generated-at
```

### Export full package from matrix cell sources
```bash
agentdeck-research-export \
  --experiment-dir research/2026-03-25-variable-damage-parity-1 \
  --package \
  --no-generated-at
```

## 9. Design Rationale
- The common pain point in the repo is export/aggregation duplication, not experiment execution itself.
- Keeping `run_experiment.py` package-local preserves flexibility for game/model-specific setup.
- Moving workflow logic into `src/agentdeck/research/` makes the supported surface feel like product functionality rather than repo plumbing.
- Preferring canonical cell artifacts for package aggregation keeps top-level exports reproducible once a cell has been blessed.

## 10. References
- `CONTRIBUTING.md`
- `SPEC-RESEARCH-EXPERIMENT.md`
- `SPEC-RESEARCH-PACKAGER.md`
- `research/SCHEMA.md`
- `agentdeck.research.export`
- `agentdeck.research.index`
