# SPEC-RESEARCH-PACKAGER: Session to Experiment Packager

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-01-27
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
- Implement core logic in `src/agentdeck/research/packager.py` with a thin CLI wrapper in `scripts/research_package.py`.

## 4. Data Structures
- **manifest.yaml**: MUST follow `research/SCHEMA.md` and `SPEC-RESEARCH-EXPERIMENT.md`.
- **recordings/README.md**: MUST include `session_id` and the absolute or repo-relative source path.

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
- `--run-dir` (Path, default: `agentdeck_runs`): Base directory for session lookup.
- `--research-dir` (Path, default: `research`): Destination root for experiment packages.
- `--experiment-id` (str, optional): Defaults to `session_id`.
- `--question` (str, required): Research question to store in manifest.
- `--status` (planned|running|complete|archived, optional): Overrides derived status.
- `--title` (str, optional): Title stored in manifest and experiment README.
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

## 7. Data Flow & Interaction
- Package: CLI → resolve session records → copy templates → write manifest → run export → update index.
- Validation: CLI → `scripts/research_validate.py` (optional follow-up, not required by tool).
- References: `SPEC-RECORDER.md` for batch metadata, `SPEC-RESEARCH-EXPERIMENT.md` for schema.

## 8. Error Handling & Edge Cases
- Missing session directory or `records/`: raise `FileNotFoundError` with guidance.
- No `batch_*.json` or `match_*.json`: fail fast with clear error.
- Missing required manifest fields after inference: raise `ValueError` and print missing keys.
- Existing experiment directory: raise `FileExistsError` with the path.
- `--dry-run`: perform validation and print inferred manifest without writing files.

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

## 11. Design Rationale
- Keeps research packages intentional and tidy (opt-in, no automatic writes).
- Reuses existing scripts to avoid schema drift and duplicated logic.
- Fails loudly when required manifest fields cannot be inferred, preserving standards.

## 12. Open Questions / Future Work
- Should the tool update the experiment `README.md` with inferred fields?
- Should we support packaging from non-session recordings directories (e.g., `agentdeck_records/`)?

## 13. References
- `SPEC-RESEARCH-EXPERIMENT.md`
- `SPEC-RECORDER.md`
- `SPEC-RESEARCH.md`
- `research/SCHEMA.md`
- `research/README.md`
- `scripts/research_export.py`
- `scripts/research_index.py`
