# SPEC-RESEARCH-EXPERIMENT: Experiment Package Contract

> Status: Final
> Version: 1.6.0
> Last Updated: 2026-03-17
> Implementation: ✅ Complete (`research/SCHEMA.md`, `scripts/research_export.py`, `scripts/research_index.py`, `scripts/research_validate.py`)
> Authors: Diego ZoracKy, Codex
> Audience: Research engineers, contributors, experiment authors

## 1. Purpose
- Standardize experiment packages so results are comparable, reproducible, and machine-readable.
- Provide a single contract for manifest metadata, generated results, and the global index.
- Prevent drift between narratives, recordings, and reported metrics.

## 2. Scope & Philosophy Alignment
- Supports `SPEC.md` §2.4 (reproducibility) and §3.2 (separation of concerns).
- Aligns with research-first framing: experiment artifacts are data-first, not prose-first.
- Keeps outputs deterministic: scripts are the source of truth for results and index.

## 3. Responsibilities
- Define the required experiment package layout and required artifacts.
- Define manifest and results schemas at the contract level.
- Define script contracts for export, index generation, and validation.
- Define invariants that keep research outputs objective and reproducible.

## 4. Data Structures

### 4.1 Experiment Package Layout
```
research/<experiment-id>/
├── README.md          # Experiment card (short summary)
├── manifest.yaml      # Repro metadata (required)
├── matrix.yaml        # Benchmark grid definition (optional)
├── results.json       # Objective results (generated)
├── results.csv        # Match-level results (generated)
├── analysis.md        # Interpretation (optional)
├── artifacts/         # Plots/tables (optional)
├── logs/              # Narrative logs (optional)
├── recordings/        # External pointers only (no raw JSON)
└── scripts/           # Experiment scripts (optional)
```

### 4.2 manifest.yaml (Required)
Required fields (minimum contract):
- `schema_version` (int)
- `experiment_id` (string, MUST match folder name)
- `status` (`planned|running|complete|archived`)
- `question` (string)
- `game.name` (string)
- `players[].provider` (string)
- `players[].model` (string)
- `run.matches_planned` (int)
- `run.seed_base` (int)

Recommended fields (non-exhaustive):
- `title`, `started_at`, `completed_at`
- `game.config`
- `players[].controller`, `players[].renderer`
- `variants` (model/controller variants used across matchups)
- `run.matches_completed`, `run.concurrency`, `run.max_turns`, `run.source_sessions`
- `run.matrix_source` (when `matrix.yaml` exists)
- `analysis_plan` (ci_method, alpha, effect_size)
- `artifacts` (paths for results.json/results.csv/plots)
- `notes`

The canonical schema and examples live in `research/SCHEMA.md`.

### 4.3 results.json (Generated)
Required fields:
- `schema_version` (int)
- `experiment_id` (string)
- `source.recordings_dir` (string; primary source pointer)
- `summary` (object)
- `players` (array)
- `matches` (array)

Optional source-provenance extension:
- `source.recordings_dirs` (array of strings) for checkpoint aggregation from multiple sessions.
- `generated_at` (ISO-8601) unless export was run with `--no-generated-at` for deterministic output.

Extended required fields for `schema_version >= 2`:
- `statistics` (object; inferential statistics)
- `format_strictness` (object; response format compliance metrics)
- `position_effect` (object; first-player and upset metrics)

Extended required fields for `schema_version >= 3`:
- `artifact_validation` (object; game-agnostic recording invariant summary)

### 4.4 statistics (Generated in results.json)
Minimum contract:
- `method` (string; e.g., `exact_binomial`)
- `confidence_level` (float)
- `alpha` (float)
- `null_win_rate` (float)
- `n_total` (int)
- `n_decisive` (int)
- `players` (object keyed by player name)

Player-level required fields:
- `wins` (int)
- `win_rate` (float)
- `ci` (2-float array)
- `p_value` (float)
- `effect_size` (float)
- `effect_label` (`negligible|small|medium|large`)

Pairwise comparison is RECOMMENDED for 2-player experiments and MAY be omitted for larger setups.

### 4.5 format_strictness (Generated in results.json)
Minimum contract:
- `overall` (object)
- `by_player` (object keyed by player name)

Per-entry required fields:
- `turn_attempts` (int)
- `parse_failures` (int)
- `parse_failure_rate` (float)
- `contract_evaluable_attempts` (int)
- `strict_contract_passes` (int)
- `strict_contract_rate` (float)
- `recoverable_non_strict` (int)
- `recoverable_non_strict_rate` (float)
- `action_line_rate` (float)
- `reasoning_line_rate` (float)

Strictness MUST be computed from recorder events (`gameplay` and parse-failure events),
without relying on game-specific semantics.

### 4.6 position_effect (Generated in results.json)
Minimum contract:
- `total_matches` (int)
- `first_player_wins` (int)
- `first_player_win_rate` (float)
- `second_player_wins` (int)
- `upset_rate` (float)
- `by_player` (object keyed by player name)

Per-player required fields:
- `first_count` (int)
- `second_count` (int)
- `wins_as_first` (int)
- `wins_as_second` (int)
- `win_rate_as_first` (float)
- `win_rate_as_second` (float)

Position metrics MUST be computed from match-level first-player metadata and winner fields,
without game-specific assumptions.

### 4.7 artifact_validation (Generated in results.json)
Minimum contract:
- `matches_checked` (int)
- `all_passed` (bool)
- `checks` (object keyed by invariant name)
- `failures` (array)

Required invariant keys:
- `monotonic_gameplay_timeline`
- `top_level_timing_consistency`
- `prompt_turn_number_coherence`
- `winner_final_state_consistency`

Per-invariant summary fields:
- `passed` (int)
- `failed` (int)

Artifact validation MUST remain game-agnostic. It validates recording integrity rather
than gameplay correctness. Public committed exports SHOULD have `all_passed: true`.

### 4.8 results.csv (Generated)
Minimum columns:
`match_id`, `winner`, `turns`, `outcome`, `seed`, `duration`, `cost`,
`player_order_source`, `first_player`, `players`, `player_costs`.

### 4.9 research/INDEX.md (Generated)
A registry table for all experiments. It is generated from manifests using
`scripts/research_index.py` and MUST match the script output.

Minimum table shape:

```markdown
| Experiment | Status | Game | Players | Matches | Results |
|---|---|---|---|---|---|
| 2026-03-17-example | complete | FixedDamageGame | gpt-4o-mini vs claude-haiku-4.5 | 80/80 | A 57.5% |
```

## 5. Public API

### 5.1 Export Results
`scripts/research_export.py`
- `--recordings-dir` (Path, required)
  - Repeat the flag to aggregate multiple source directories into one export.
- `--output-dir` (Path, required)
- `--experiment-id` (string, optional; defaults to output-dir name)
- `--no-generated-at` (flag, optional; omit timestamp for deterministic exports)
- Output: `results.json` and `results.csv` in `--output-dir`

### 5.2 Generate Index
`scripts/research_index.py`
- `--research-dir` (Path, default `research`)
- `--output` (Path, default `research/INDEX.md`)
- Output: `research/INDEX.md`

### 5.3 Validate Research Tree
`scripts/research_validate.py`
- `--research-dir` (Path, default `research`)
- `--index` (Path, default `research/INDEX.md`)
- `--write-index` (bool; regenerate index if out of date)
- Output: non-zero exit code on validation failure

## 6. Invariants & Guarantees
- **RE1**: Committed experiment directories MUST contain `manifest.yaml`. `README.md` is RECOMMENDED for curated experiments. Ad-hoc/local experiments may omit README.
- **RE2**: When using `research_validate.py`, `results.json` and `results.csv` MUST be present for completed experiments (`status: complete`) or whenever results files exist, and MUST conform to the schema produced by `research_export.py` (provenance/shape check).
- **RE3**: `manifest.yaml` MUST include all required fields in §4.2.
- **RE4**: `experiment_id` MUST match the experiment folder name.
- **RE5**: `schema_version` MUST be an integer >= 1 for manifests. Results files SHOULD include schema_version for forward compatibility.
- **RE6**: Raw recordings SHOULD NOT be committed to version control; `recordings/` should contain pointers or be gitignored. (This is a repository policy, enforced by `.gitignore`, not runtime validation.)
- **RE7**: `research/INDEX.md` MUST match the output of `research_index.py`.
- **RE8**: Export scripts MUST produce deterministic output for identical recordings, excluding `generated_at` timestamps. Use `--no-generated-at` to omit the timestamp for diff-sensitive checks.
- **RE9**: Status-gated markdown completeness MUST be enforced by validation:
  - `planned`/`running`: placeholders allowed.
  - `complete`/`archived` with `run.matches_completed > 0`: factual markdown blocks in `README.md` and `analysis.md` MUST be populated.
- **RE10**: Auto-written markdown content MUST be limited to the factual marker block (`<!-- AUTO_FACTS:BEGIN -->` ... `<!-- AUTO_FACTS:END -->`). Narrative sections remain human-authored.
- **RE11**: For `results.json.schema_version >= 2`, `results.json.statistics` MUST be produced by `research_export.py` for every exported dataset with one or more matches.
- **RE12**: For `results.json.schema_version >= 2`, `results.json.format_strictness` MUST be produced by `research_export.py` for every exported dataset with one or more matches and MUST be derived from recorder events only (game-agnostic).
- **RE13**: For `results.json.schema_version >= 2`, `results.json.position_effect` MUST be produced by `research_export.py` for every exported dataset with one or more matches and MUST be derived from first-player metadata and winners only (game-agnostic).
- **RE14**: `results.json.source.recordings_dir` MUST be a non-empty primary source string. When aggregating multiple source directories, `results.json.source.recordings_dirs` MUST be a non-empty array and `recordings_dir` MUST equal its first entry.
- **RE15**: For `results.json.schema_version >= 3`, `results.json.artifact_validation` MUST be produced by `research_export.py` for every exported dataset with one or more matches.
- **RE16**: `artifact_validation` MUST cover monotonic gameplay timeline, top-level timing consistency, prompt payload turn-number coherence, and winner/final-state consistency using only recorder payloads (game-agnostic).
- **RE17**: `research_export.py` MUST fail fast when artifact invariants fail rather than writing partially valid `results.json`.

## 7. Data Flow & Interaction
- Export: `recordings/ -> research_export.py -> results.json + results.csv`
- Index: `manifest.yaml -> research_index.py -> research/INDEX.md`
- Validation: `manifest.yaml + INDEX.md -> research_validate.py -> pass/fail`

## 8. Error Handling & Edge Cases
- Missing recordings directory or no `match_*.json` files → fail fast with
  `FileNotFoundError` (export).
- Missing required manifest fields → validator exits non-zero with detail.
- Out-of-date index → validator exits non-zero unless `--write-index` used.
- Completed experiment with placeholder factual block in README/analysis → validator exits non-zero with detail.

## 9. Examples

### 9.1 Create a New Experiment
```bash
cp -R research/_templates research/2026-01-19-example
```

### 9.2 Export Results
```bash
python scripts/research_export.py \
  --recordings-dir recordings \
  --output-dir research/2026-01-19-example
```

### 9.3 Validate Research Tree
```bash
python scripts/research_validate.py --research-dir research
```

## 10. Testing Strategy
- Run `scripts/research_validate.py` before committing research changes.
- Validator MUST cover RE3, RE4, and RE7 at minimum.

## 11. Design Rationale
- Script-only results prevent drift between recordings and reported metrics.
- Generated index avoids manual registry errors and keeps status consistent.

## 12. Open Questions / Future Work
- Add optional JSON schema validation for results.json.
- CI enforcement for `scripts/research_validate.py`.

## 13. References
- [SPEC.md](./SPEC.md) §2.4, §3.2
- [SPEC-RESEARCH.md](./SPEC-RESEARCH.md)
- [research/SCHEMA.md](../research/SCHEMA.md)
- [research/README.md](../research/README.md)
- [scripts/research_export.py](../scripts/research_export.py)
- [scripts/research_index.py](../scripts/research_index.py)
- [scripts/research_validate.py](../scripts/research_validate.py)
