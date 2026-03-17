# SPEC-RESEARCH-PACKAGER: Session to Experiment Packager

> Status: Final
> Version: 0.3.0
> Last Updated: 2026-03-05
> Implementation: ✅ Complete (packager module + CLI wrapper)
> Authors: Codex, Diego ZoracKy
> Audience: Research engineers, contributors, experiment owners

## 1. Purpose
- Provide a one-command way to promote an AgentDeck session into a standardized research package.
- Reduce manual boilerplate while preserving the research experiment contract.
- Ensure experiment artifacts are reproducible, indexed, and ready for review.

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC.md` research-first focus and reproducibility guarantees.
- Composes existing tooling (`research/_templates`, `scripts/research_export.py`, `scripts/research_index.py`) rather than reimplementing it.
- Keeps the tool opt-in to avoid polluting the repo with unintentional experiments.
- Enforces "recordings external" policy from `research/README.md` and `SPEC-RESEARCH-EXPERIMENT.md`.

## 3. Responsibilities
- Create a new experiment directory under `research/` using `_templates/`.
- Pre-fill `manifest.yaml` with required fields using session metadata and CLI inputs.
- Generate `results.json` and `results.csv` by invoking `scripts/research_export.py`.
- Update `research/INDEX.md` by invoking `scripts/research_index.py`.
- Create or update `recordings/README.md` with a pointer to the source session.
- Auto-populate factual markdown blocks in `README.md` and `analysis.md`.
- Support checkpoint-style aggregation from multiple compatible sessions in one package.
- Implement core logic in `src/agentdeck/research/packager.py` with a thin CLI wrapper in `scripts/research_package.py`.

## 4. Data Structures
- **manifest.yaml**: MUST follow `research/SCHEMA.md` and `SPEC-RESEARCH-EXPERIMENT.md`.
- **recordings/README.md**: MUST include `session_id` and the absolute or repo-relative source path.
- **README.md / analysis.md factual blocks**: MUST use `<!-- AUTO_FACTS:BEGIN --> ... <!-- AUTO_FACTS:END -->`
  markers; only this block is auto-written by tooling.

### Manifest Field Mapping (Minimum)
- `schema_version`: 1
- `experiment_id`: CLI `--experiment-id` or default to `session_id`
- `question`: CLI `--question` (required)
- `status`: CLI `--status` or derived from matches planned vs completed
- `game.name`: batch metadata `metadata.game` or `metadata.configuration.game.name`
- `players[].provider`: derived from `metadata.configuration.players[].module`
- `players[].model`: derived from match refs `player_summaries[].model`
- `run.matches_planned`: batch metadata `metadata.matches_planned` or match count
- `run.matches_completed`: batch metadata `metadata.matches_completed` or match count
- `run.seed_base`: first entry in `metadata.seeds_used`, else first match `seed`

## 5. Public API

### CLI
```
python scripts/research_package.py \
  --session-dir agentdeck_runs/session_20260119_215606_7e095e \
  --experiment-id 2026-01-19-walkthrough-demo \
  --question "Does Alice beat Bob in TinyBattleGame?"
```

#### Arguments
- `--session-dir` (Path, required unless `--session-id`): Session root containing `records/`.
- `--session-id` (str, optional): Session identifier resolved under `--run-dir`.
- `--session-dirs` (Path list, optional): Multiple session roots for checkpoint aggregation.
- `--session-ids` (str list, optional): Multiple session identifiers resolved under `--run-dir`.
- `--run-dir` (Path, default: `agentdeck_runs`): Base directory for session lookup.
- `--research-dir` (Path, default: `research`): Destination root for experiment packages.
- `--experiment-id` (str, optional): Defaults to `session_id`.
- `--question` (str, required): Research question to store in manifest.
- `--status` (planned|running|complete|archived, optional): Overrides derived status.
- `--title` (str, optional): Title stored in manifest and experiment README.
- `--include-matrix` (flag, optional): Include `matrix.yaml` scaffold for benchmark grids.
- `--dry-run` (flag, optional): Validate inputs and print planned actions without writing files.

## 6. Invariants & Guarantees
1. **RP1**: Tool MUST be opt-in; it MUST NOT run automatically after sessions.
2. **RP2**: Tool MUST NOT copy raw recordings into `research/`.
3. **RP3**: Tool MUST write a manifest that satisfies required fields in `research/SCHEMA.md`.
4. **RP4**: Tool MUST generate `results.json`/`results.csv` by calling `scripts/research_export.py`.
5. **RP5**: Tool MUST update `research/INDEX.md` by calling `scripts/research_index.py`.
6. **RP6**: Tool MUST fail if the experiment directory already exists (no implicit overwrite).
7. **RP7**: Tool MUST fail fast if required fields cannot be inferred and no CLI override is supplied.
8. **RP8**: Provider inference MUST reuse the same mapping as `scripts/research_export.py` (`_provider_from_module`).
9. **RP9**: `matrix.yaml` MUST be optional by default; it is included only when explicitly requested.
10. **RP10**: If `matrix.yaml` is not included, manifest MUST omit `run.matrix_source` and `artifacts.matrix_yaml`.
11. **RP11**: Tool MUST auto-populate factual markdown blocks in `README.md` and `analysis.md`, and MUST NOT overwrite narrative sections outside marker blocks.
12. **RP12**: When a session contains multiple `batch_*.json` files (e.g., side-swap split runs), tool MUST aggregate them into a single packaging view for `match_refs`, `matches_planned`, `matches_completed`, `seeds_used`, and time window (`started_at`/`ended_at`).
13. **RP13**: Tool MUST support checkpoint packaging from multiple sessions. When multiple sessions are supplied, tool MUST aggregate all compatible `match_*.json` into one experiment export and MUST record all source sessions in `recordings/README.md`.
14. **RP14**: Multi-session packaging MUST fail fast when compatibility checks fail (mismatched game name or mismatched player identity/model/controller tuple).

## 7. Data Flow & Interaction
- Package: CLI → resolve session records → copy templates → write manifest → run export → update index.
- Markdown hydration: after export, fill factual blocks in `README.md` and `analysis.md`.
- Validation: CLI → `scripts/research_validate.py` (optional follow-up, not required by tool).
- References: `SPEC-RECORDER.md` for batch metadata, `SPEC-RESEARCH-EXPERIMENT.md` for schema.

## 8. Error Handling & Edge Cases
- Missing session directory or `records/`: raise `FileNotFoundError` with guidance.
- No `batch_*.json` or `match_*.json`: fail fast with clear error.
- Missing required manifest fields after inference: raise `ValueError` and print missing keys.
- Existing experiment directory: raise `FileExistsError` with the path.
- `--dry-run`: perform validation and print inferred manifest without writing files.
- Missing auto-facts markers: skip markdown hydration (non-fatal), preserving manual docs.

## 9. Examples

### Minimal (session dir)
```bash
python scripts/research_package.py \
  --session-dir agentdeck_runs/session_20260119_215606_7e095e \
  --question "Does Alice beat Bob in TinyBattleGame?"
```

### With explicit experiment id + title
```bash
python scripts/research_package.py \
  --session-id session_20260119_215606_7e095e \
  --experiment-id 2026-01-19-walkthrough-demo \
  --title "Walkthrough Demo" \
  --question "Does Alice beat Bob in TinyBattleGame?"
```

### Checkpoint aggregation from multiple sessions
```bash
python scripts/research_package.py \
  --session-ids session_20260304_181345_92ec64 session_20260305_010000_ab12cd \
  --experiment-id fixed-damage-mini-vs-haiku-ao__n80 \
  --question "Does gpt-4o-mini beat Haiku in FixedDamage AO at N=80?"
```

### Dry run
```bash
python scripts/research_package.py \
  --session-id session_20260119_215606_7e095e \
  --question "Does Alice beat Bob in TinyBattleGame?" \
  --dry-run
```

## 10. Testing Strategy
- **RP3**: Unit test manifest inference from a fixture `batch_*.json`.
- **RP4**: Integration test writes results via `research_export.py`.
- **RP5**: Integration test updates `research/INDEX.md` deterministically.
- **RP6**: Unit test fails on existing experiment directory.
- **RP7**: Unit test fails when provider/model cannot be inferred.
- **RP9/RP10**: Unit tests for default matrix omission and `--include-matrix` opt-in behavior.
- **RP11**: Unit test verifies factual block is populated while template narrative remains untouched.
- **RP12**: Unit test verifies multi-batch sessions are aggregated deterministically.
- **RP13**: Unit test verifies multi-session packaging aggregates match files and emits `source.recordings_dirs`.
- **RP14**: Unit test verifies multi-session packaging fails on incompatible sessions.

## 11. Design Rationale
- Keeps research packages intentional and tidy (opt-in, no automatic writes).
- Reuses existing scripts to avoid schema drift and duplicated logic.
- Fails loudly when required manifest fields cannot be inferred, preserving standards.

## 12. Open Questions / Future Work
- Should markdown hydration support custom marker names for non-default templates?
- Should we support packaging from non-session recordings directories (e.g., `agentdeck_records/`)?

## 13. References
- `SPEC-RESEARCH-EXPERIMENT.md`
- `SPEC-RECORDER.md`
- `SPEC-RESEARCH.md`
- `research/SCHEMA.md`
- `research/README.md`
- `scripts/research_export.py`
- `scripts/research_index.py`
