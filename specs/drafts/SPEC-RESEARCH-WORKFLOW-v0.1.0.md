# SPEC-RESEARCH-WORKFLOW v0.1.0

> Status: Draft
> Last Updated: 2026-03-26
> Implementation: ✅ Implemented (`scripts/research_export.py`, `research/_templates/scripts/run_experiment.py`)
> Authors: Codex
> Audience: Research engineers, experiment authors, contributors

## 1. Purpose
- Define one supported, documented workflow for matrix-based research packages.
- Reduce reliance on per-package export boilerplate while preserving the existing experiment package contract.
- Keep execution logic package-local and move only export/aggregation mechanics into shared tooling.

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC.md` reproducibility goals and `CONTRIBUTING.md` spec-first workflow.
- Builds on `SPEC-RESEARCH-EXPERIMENT.md` and `SPEC-RESEARCH-PACKAGER.md` instead of replacing them.
- Favors one coherent common-case path over a broad orchestration framework.
- Non-goals:
  - moving package-specific `run_experiment.py` logic into framework core
  - native recovery orchestration, segmented execution, or duplicate-pruning policy
  - replacing `research_package.py`, `research_validate.py`, or `research_index.py`

## 3. Responsibilities
- Support matrix-aware cell export from shared tooling.
- Support package-level aggregation from canonical cell artifacts and/or discovered session recordings.
- Keep direct recordings-dir export working unchanged for single-run or non-matrix workflows.
- Document the minimum `matrix.yaml` sections required for the shared workflow.
- Provide a minimal research-package execution template that stays package-local.

## 4. Public API

### 4.1 Shared Export Workflow
`scripts/research_export.py` MUST support two modes:

- **Direct mode**:
  - existing `--recordings-dir ... --output-dir ...` workflow
- **Matrix mode**:
  - `--experiment-dir <path>`
  - `--matrix <path>` (optional when defaulting to `<experiment-dir>/matrix.yaml`)
  - `--list-cells`
  - `--cell <id>` (repeatable)
  - `--phase <id>`
  - `--package`

### 4.2 Matrix Mode Semantics
- `--list-cells`:
  - print available cell ids with phase metadata
  - perform no export
- `--cell` / `--phase`:
  - export selected cells into `artifacts/<cell_id>/results.json` and `results.csv`
- `--package`:
  - export top-level package `results.json` and `results.csv`
  - merge canonical `source.recordings_dir(s)` from cell artifacts with discovered
    `agentdeck_runs/<cell_id>/session_*/records`
  - prefer canonical cell-artifact sources first when both exist

### 4.3 Minimal Matrix Contract
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
- **RW5**: Package export MUST prefer canonical sources from committed cell artifacts when they exist.
- **RW6**: Package export MUST preserve deterministic outputs when `--no-generated-at` is used.
- **RW7**: Shared tooling MUST NOT own or infer experiment execution policy; it only exports and aggregates outputs.
- **RW8**: The minimal template `scripts/run_experiment.py` MUST remain package-local and framework-agnostic beyond stable public AgentDeck APIs.

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
- Verify duplicate recordings dirs are deduplicated.
- Verify invalid cell selection and missing matrix files fail fast.

## 8. Examples

### Direct export
```bash
python scripts/research_export.py \
  --recordings-dir agentdeck_runs/session_x/records \
  --output-dir research/2026-03-26-demo
```

### Export one matrix cell
```bash
python scripts/research_export.py \
  --experiment-dir research/2026-03-25-variable-damage-parity-1 \
  --cell p1_c01_flash_lite_rc_risk_vs_flash_ao \
  --no-generated-at
```

### Export full package from matrix cell sources
```bash
python scripts/research_export.py \
  --experiment-dir research/2026-03-25-variable-damage-parity-1 \
  --package \
  --no-generated-at
```

## 9. Design Rationale
- The common pain point in the repo is export/aggregation duplication, not experiment execution itself.
- Keeping `run_experiment.py` package-local preserves flexibility for game/model-specific setup.
- Preferring canonical cell artifacts for package aggregation keeps top-level exports reproducible once a cell has been blessed.

## 10. References
- `CONTRIBUTING.md`
- `SPEC-RESEARCH-EXPERIMENT.md`
- `SPEC-RESEARCH-PACKAGER.md`
- `research/SCHEMA.md`
- `scripts/research_export.py`
