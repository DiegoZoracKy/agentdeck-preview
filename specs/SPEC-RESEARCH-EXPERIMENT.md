# SPEC-RESEARCH-EXPERIMENT: Experiment Package Contract

> Status: Final
> Version: 1.7.0
> Last Updated: 2026-04-27
> Implementation: Complete (`research/SCHEMA.md`, `agentdeck.research.export`, `agentdeck.research.index`, `agentdeck.research.validate`, compatibility `scripts/` wrappers)
> Review State: Legacy-approved
> Audience: Research engineers, contributors, experiment authors

## 1. Purpose
- Standardize experiment packages so results are comparable, reproducible, and machine-readable.
- Provide a single contract for manifest metadata, generated results, and the global index.
- Prevent drift between narratives, recordings, and reported metrics.

## 2. Scope & Philosophy Alignment
- Supports `SPEC.md` §2.4 (reproducibility) and §3.2 (separation of concerns).
- Aligns with research-first framing: experiment artifacts are data-first, not prose-first.
- Keeps outputs deterministic: the shared research surfaces are the source of truth for results, validation, and index generation.

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
├── results.md         # Human-readable factual report (generated)
├── analysis/          # Authored human/AI interpretation workspace (optional)
├── artifacts/         # Plots/tables (optional)
├── logs/              # Narrative logs (optional)
├── recordings/        # External pointers only (no raw JSON)
└── scripts/           # Experiment scripts (optional)
```

AgentDeck uses the timestamp core `YYYYMMDD_HHMMSS` for instanced artifacts.
Runtime sessions use `session_YYYYMMDD_HHMMSS_<suffix>`. Authored analysis
directories SHOULD use `analysis_YYYYMMDD_HHMMSS_<author>_<topic_slug>` under
`analysis/`, so independent human and AI reports sort chronologically, remain
attributable, avoid same-day collisions, and remain grep-friendly. Process-created
research package folders MUST use the `research_` prefix. Human-named packages
SHOULD use `research_YYYY-MM-DD-<kebab-slug>`; packages derived from sessions
SHOULD rewrite `session_YYYYMMDD_HHMMSS_<suffix>` to
`research_YYYYMMDD_HHMMSS_<suffix>`.

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
- `phase_model` (when a package has multiple execution phases and no `matrix.yaml`)
- `analysis_plan` (ci_method, alpha, effect_size)
- `artifacts` (paths for results.json/results.csv/results.md/plots/analysis)
- `notes`

The canonical schema and examples live in `research/SCHEMA.md`.

### 4.2a matrix.yaml Phase Model (Optional)
Matrix packages MAY declare phase scope for export and validation.

Recommended fields:
- `phase_model.study_phases` (list[str]): phases included in default package aggregation.
- `phase_model.preflight_phases` (list[str]): smoke/setup phases excluded from default package aggregation.
- `phase_model.main_phases` (list[str]): scaled phases, when distinct from pilot phases.
- `phase_model.excluded_phases` (list[str]): phases intentionally excluded from default package aggregation.

When both `matrix.yaml` and `manifest.yaml` declare `phase_model`, `matrix.yaml` is authoritative.
Multi-phase matrices SHOULD declare `study_phases` before top-level package export.

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
- `source.aggregation_scope` (`cell|study_phases|explicit_phase|explicit_cells|all_phases`)
- `source.phase` (string) for cell exports when known.
- `source.cell_id` (string) for cell exports.
- `source.phases_included` (array of strings) for matrix package exports.
- `source.cells_included` (array of strings) for matrix package exports.
- `generated_at` (ISO-8601) unless export was run with `--no-generated-at` for deterministic output.
- `behavioral_profile` (object; optional game-specific behavioral scorer output following `SPEC-RESEARCH-BEHAVIORAL.md`)

Extended required fields for `schema_version >= 2`:
- `statistics` (object; inferential statistics)
- `format_strictness` (object; response format compliance metrics)
- `position_effect` (object; first-player and upset metrics)

Extended required fields for `schema_version >= 3`:
- `artifact_validation` (object; game-agnostic recording invariant summary)

### 4.3a results.md (Generated)
Exports MUST write `results.md` next to `results.json`.

`results.md` is a deterministic human-readable factual report generated from
`results.json`. For matrix package exports, it SHOULD also read sibling cell
artifacts under `artifacts/<cell_id>/results.json` when
`source.cells_included` is present, so users can inspect per-cell outcomes and
seat splits without opening JSON.

`results.md` SHOULD include:
- source scope and included phases/cells
- aggregate summary metrics
- player results and direct head-to-head comparisons
- position effects and seat splits by player
- per-cell outcome, p-value/effect, and seat-split tables for matrix packages
- format strictness
- costs
- behavioral profile summary when present
- artifact validation status

The report MUST remain factual and deterministic. It MUST NOT call an LLM and
MUST NOT include authored interpretation beyond warnings derived mechanically
from exported metrics, such as high first-player skew, non-significant direct
comparisons, or heterogeneous package aggregation.

### 4.3b Authored Analysis Namespace
New packages SHOULD use `analysis/` as the authored interpretation namespace
instead of a single `analysis.md` file. The package root `README.md` SHOULD
point analysts to `analysis/README.md`. `analysis/README.md` SHOULD explain how
humans and AI agents write independent analysis subdirectories:

```text
analysis/analysis_YYYYMMDD_HHMMSS_<author>_<topic_slug>/
├── analysis.md
├── provenance.yaml
└── support/
```

Each analysis subdirectory SHOULD include provenance describing author identity
(`human` or `ai`), model/tool when relevant, date, source artifacts, review
status, and whether LLM assistance was used. Quantitative claims SHOULD cite
generated artifacts.

Legacy `analysis.md` remains valid for existing packages but is no longer the
preferred canonical analysis shape.

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

Pairwise comparison is RECOMMENDED for direct 2-player experiments and MAY be omitted for larger setups.
When present, `statistics.pairwise_comparisons` MUST contain only direct
head-to-head comparisons derived from matches where both named players appear in
the same `results.json.matches[*].players` array. It MUST NOT compare players
using package-level aggregate wins from unrelated cells or pools.

Pairwise entry fields:
- `player_a` (string)
- `player_b` (string)
- `comparison_scope` (`direct_head_to_head`)
- `wins_a` (int; direct wins by `player_a` against `player_b`)
- `wins_b` (int; direct wins by `player_b` against `player_a`)
- `head_to_head_matches` (int; all direct matches containing both players)
- `head_to_head_decisive` (int; `wins_a + wins_b`)
- `win_rate_a` (float; `wins_a / head_to_head_decisive` when decisive > 0)
- `ci_a` (2-float array)
- `p_value` (float)
- `effect_size` (float)
- `effect_label` (`negligible|small|medium|large`)
- `is_significant` (bool)

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

### 4.8 behavioral_profile (Optional Extension)
When present, `behavioral_profile` MUST follow the global scorer contract defined in
`SPEC-RESEARCH-BEHAVIORAL.md`.

Minimum required fields:
- `schema_version` (int)
- `game_id` (string)
- `profile_id` (string)
- `profile_version` (string)
- `coverage` (object)
- `aggregate_metrics` (mapping)
- `per_player` (mapping)
- `state_metrics` (mapping)
- `evidence` (mapping)
- `quality_flags` (object)

`behavioral_profile` remains optional because behavioral scorers are game-specific.
When omitted, the baseline research package still consists of the game-agnostic
metrics above.

### 4.9 results.csv (Generated)
Minimum columns:
`match_id`, `winner`, `turns`, `outcome`, `seed`, `duration`, `cost`,
`player_order_source`, `first_player`, `players`, `player_costs`.

### 4.10 research/INDEX.md (Generated)
A registry table for all experiments. It is generated from manifests using the
shared research index surface and MUST match its generated output.

Minimum table shape:

```markdown
| Experiment | Status | Game | Players | Matches | Results |
|---|---|---|---|---|---|
| 2026-03-17-example | complete | FixedDamageGame | gpt-4o-mini vs claude-haiku-4.5 | 80/80 | A 57.5% |
```

## 5. Public API

### 5.1 Export Results
Preferred surfaces:
- `agentdeck-research-export ...`
- `python -m agentdeck.research.export ...`
- compatibility: `python scripts/research_export.py ...`

- `--recordings-dir` (Path, required)
  - Repeat the flag to aggregate multiple source directories into one export.
- `--output-dir` (Path, required)
- `--experiment-id` (string, optional; defaults to output-dir name)
- `--no-generated-at` (flag, optional; omit timestamp for deterministic exports)
- Output: `results.json` and `results.csv` in `--output-dir`

### 5.2 Generate Index
Preferred surfaces:
- `agentdeck-research-index ...`
- `python -m agentdeck.research.index ...`
- compatibility: `python scripts/research_index.py ...`

- `--research-dir` (Path, default `research`)
- `--output` (Path, default `research/INDEX.md`)
- Output: `research/INDEX.md`

### 5.3 Validate Research Tree
Preferred surfaces:
- `agentdeck-research-validate ...`
- `python -m agentdeck.research.validate ...`
- compatibility: `python scripts/research_validate.py ...`

- `--research-dir` (Path, default `research`)
- `--index` (Path, default `research/INDEX.md`)
- `--write-index` (bool; regenerate index if out of date)
- Output: non-zero exit code on validation failure

## 6. Invariants & Guarantees
- **RE1**: Committed experiment directories MUST contain `manifest.yaml`. `README.md` is RECOMMENDED for curated experiments. Ad-hoc/local experiments may omit README.
- **RE2**: When using the shared research validation surface, `results.json` and `results.csv` MUST be present for completed experiments (`status: complete`) or whenever results files exist, and MUST conform to the schema produced by the shared export surface (provenance/shape check).
- **RE3**: `manifest.yaml` MUST include all required fields in §4.2.
- **RE4**: `experiment_id` MUST match the experiment folder name.
- **RE5**: `schema_version` MUST be an integer >= 1 for manifests. Results files SHOULD include schema_version for forward compatibility.
- **RE6**: Raw recordings SHOULD NOT be committed to version control; `recordings/` should contain pointers or be gitignored. (This is a repository policy, enforced by `.gitignore`, not runtime validation.)
- **RE7**: `research/INDEX.md` MUST match the output of the shared research index surface.
- **RE8**: Export scripts MUST produce deterministic output for identical recordings, excluding `generated_at` timestamps. Use `--no-generated-at` to omit the timestamp for diff-sensitive checks.
- **RE9**: Status-gated markdown completeness MUST be enforced by validation:
  - `planned`/`running`: placeholders allowed.
  - `complete`/`archived` with `run.matches_completed > 0`: factual markdown blocks in `README.md` MUST be populated. Legacy `analysis.md` factual blocks MUST be populated when the file exists or is declared.
- **RE10**: Auto-written markdown content in `README.md` and legacy `analysis.md` MUST be limited to the factual marker block (`<!-- AUTO_FACTS:BEGIN -->` ... `<!-- AUTO_FACTS:END -->`). Authored analysis belongs under `analysis/`.
- **RE11**: For `results.json.schema_version >= 2`, `results.json.statistics` MUST be produced by the shared export surface for every exported dataset with one or more matches.
- **RE12**: For `results.json.schema_version >= 2`, `results.json.format_strictness` MUST be produced by the shared export surface for every exported dataset with one or more matches and MUST be derived from recorder events only (game-agnostic).
- **RE13**: For `results.json.schema_version >= 2`, `results.json.position_effect` MUST be produced by the shared export surface for every exported dataset with one or more matches and MUST be derived from first-player metadata and winners only (game-agnostic).
- **RE14**: `results.json.source.recordings_dir` MUST be a non-empty primary source string. When aggregating multiple source directories, `results.json.source.recordings_dirs` MUST be a non-empty array and `recordings_dir` MUST equal its first entry.
- **RE15**: For `results.json.schema_version >= 3`, `results.json.artifact_validation` MUST be produced by the shared export surface for every exported dataset with one or more matches.
- **RE16**: `artifact_validation` MUST cover monotonic gameplay timeline, top-level timing consistency, prompt payload turn-number coherence, and winner/final-state consistency using only recorder payloads (game-agnostic).
- **RE17**: Matrix package exports that include source-scope metadata MUST keep
  `source.phases_included` and `source.cells_included` consistent with `matrix.yaml`.
- **RE18**: When a phase model declares `study_phases`, top-level package exports
  with `source.aggregation_scope: study_phases` MUST NOT include preflight,
  excluded, or otherwise non-study phases.
- **RE19**: Validation MUST reject phase-contaminated package results when a phase
  model exists or source-scope metadata is present.
- **RE20**: `statistics.pairwise_comparisons` MUST be direct-head-to-head only.
  Validation MUST reject pairwise entries whose wins, direct match count, or
  decisive count do not match the subset of `results.json.matches` containing
  both compared players.
- **RE21**: The shared export surface MUST fail fast when artifact invariants fail rather than writing partially valid `results.json`.
- **RE22**: The shared export surface MUST generate `results.md` from exported artifacts without LLM calls or handwritten interpretation. Validation MUST require it when declared in `manifest.artifacts.results_md` for completed or archived packages.
- **RE23**: New templates SHOULD provide `analysis/README.md` as the authored analysis policy surface. Validation MUST accept legacy `analysis.md` for existing packages.

## 7. Data Flow & Interaction
- Export: `recordings/ -> agentdeck.research.export -> results.json + results.csv + results.md`
- Index: `manifest.yaml -> agentdeck.research.index -> research/INDEX.md`
- Validation: `manifest.yaml + INDEX.md -> agentdeck.research.validate -> pass/fail`

## 8. Error Handling & Edge Cases
- Missing recordings directory or no `match_*.json` files → fail fast with
  `FileNotFoundError` (export).
- Missing required manifest fields → validator exits non-zero with detail.
- Out-of-date index → validator exits non-zero unless `--write-index` used.
- Completed experiment with placeholder factual block in README or legacy analysis.md → validator exits non-zero with detail.
- Completed experiment declaring `artifacts.results_md` but missing `results.md` → validator exits non-zero with detail.

## 9. Examples

### 9.1 Create a New Experiment
```bash
cp -R research/_templates research/research_2026-01-19-example
```

### 9.2 Export Results
```bash
agentdeck-research-export \
  --recordings-dir recordings \
  --output-dir research/research_2026-01-19-example
```

### 9.3 Validate Research Tree
```bash
agentdeck-research-validate --research-dir research
```

## 10. Testing Strategy
- Run the shared research validation surface before committing research changes.
- Validator MUST cover RE3, RE4, and RE7 at minimum.

## 11. Design Rationale
- Shared package-owned research surfaces prevent drift between recordings and reported metrics while keeping `scripts/` available as compatibility wrappers.
- Generated index avoids manual registry errors and keeps status consistent.

## 12. Open Questions / Future Work
- Add optional JSON schema validation for results.json.
- CI enforcement for the shared research validation surface.

## 13. References
- [SPEC.md](./SPEC.md) §2.4, §3.2
- [SPEC-RESEARCH.md](./SPEC-RESEARCH.md)
- [SPEC-RESEARCH-BEHAVIORAL.md](./SPEC-RESEARCH-BEHAVIORAL.md)
- [research/SCHEMA.md](../research/SCHEMA.md)
- [research/README.md](../research/README.md)
- [agentdeck.research.export](../src/agentdeck/research/export.py)
- [agentdeck.research.index](../src/agentdeck/research/index.py)
- [agentdeck.research.validate](../src/agentdeck/research/validate.py)
- [scripts/research_export.py](../scripts/research_export.py)
- [scripts/research_index.py](../scripts/research_index.py)
- [scripts/research_validate.py](../scripts/research_validate.py)
