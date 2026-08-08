# SPEC-RESEARCH-SCORE: Standalone Behavioral Rescore CLI

> Status: Final
> Version: 0.2.0
> Last Updated: 2026-04-09
> Implementation: Complete (`src/agentdeck/research/score.py`, `scripts/research_score.py`)
> Review State: Legacy-approved
> Audience: Research engineers, contributors

## 1. Purpose

Researchers need to recompute the behavioral profile of a packaged experiment independently of a full re-export. Two concrete triggers:

1. Raw recordings are available for a new run, but the researcher wants to score behavior without regenerating all statistics.
2. A behavioral profile definition changed — the researcher wants to rescore existing recordings against the updated profile without rerunning the experiment.

`agentdeck-research-score` provides this as a first-class CLI entry point backed by the same `BehavioralScorer` contract defined in `SPEC-RESEARCH-BEHAVIORAL.md`. It writes only the `behavioral_profile` key in the targeted `results.json`; it does not touch match results, statistics, or any other package artifact.

## 2. Terminology

- **Experiment dir**: a packaged experiment directory containing `manifest.yaml` and `results.json`.
- **Targeted results file**: the `results.json` file that rescoring will update.
  - for direct/non-matrix packages: `<experiment-dir>/results.json`
  - for matrix packages: `<experiment-dir>/artifacts/<cell>/results.json`
- **Recordings dir**: the directory containing raw `match_*.json` payloads produced by the recorder.
- **Behavioral profile**: the `behavioral_profile` key in `results.json`, defined by `SPEC-RESEARCH-BEHAVIORAL.md §4.2`.
- **Profile ID**: the scorer identity string used to select a specific `BehavioralScorer`; `auto` selects the first scorer that reports `supports() == True` for the supplied payloads.
- **Package-local scorer**: an optional scorer defined at `{experiment_dir}/scripts/behavioral_scorer.py` and loaded only for that experiment.

## 3. Architecture

```
manifest.yaml (game config + recordings path)
      ↓
agentdeck-research-score
      ↓
BehavioralScorer.score(players, match_payloads, config)   ← SPEC-RESEARCH-BEHAVIORAL
      ↓
targeted results.json  [behavioral_profile key updated in place]
```

The scorer reads recordings via the same path-resolution logic used by the research export surface (`SPEC-RESEARCH-WORKFLOW.md`). All other keys in the targeted `results.json` are preserved byte-for-byte.

Resolution order:
1. package-local scorer at `{experiment_dir}/scripts/behavioral_scorer.py`
2. built-in scorer registry
3. no scorer matched

Adjacent ownership:
- Scorer contract: `SPEC-RESEARCH-BEHAVIORAL.md`
- Experiment package schema: `SPEC-RESEARCH-EXPERIMENT.md`
- Recording discovery: `SPEC-RESEARCH-WORKFLOW.md`

## 4. CLI Contract

### 4.1 Entry Points

Installed:
```
agentdeck-research-score
```

Script wrapper:
```
python scripts/research_score.py
```

Package-local scorer convention:
```text
research/research_YYYY-MM-DD-your-experiment/scripts/behavioral_scorer.py
```

That module MAY expose either:
- `SCORER`, a module-global `BehavioralScorer` instance
- exactly one concrete `BehavioralScorer` subclass

If both exist, `SCORER` wins.

### 4.2 Arguments

| Flag | Type | Default | Description |
|---|---|---|---|
| `--experiment-dir` | path | required | Packaged experiment directory |
| `--cell` | string | `None` | Matrix cell selector (for matrix experiments) |
| `--recordings-dir` | path | `None` | Override recordings path from manifest |
| `--profile-id` | string | `auto` | Scorer profile ID; `none` disables scoring |
| `--dry-run` | flag | `False` | Print resolved scorer and coverage; do not write |

### 4.3 Exit Codes

| Code | Meaning |
|---|---|
| `0` | Scoring complete, or no scorer matched (`auto` with no supported scorer) |
| `1` | Required argument missing, path not found, or scorer error |

## 5. Invariants

- **RS1**: The scorer MUST read match payloads from raw recordings (`match_*.json` files). It MUST NOT attempt to reconstruct payloads from the existing `results.json` matches array.
- **RS2**: On success, the scorer MUST write only the `behavioral_profile` key in the targeted `results.json`. All other keys MUST remain unchanged.
- **RS3**: The scorer MUST be idempotent: running it twice on the same inputs MUST produce the same `behavioral_profile` output.
- **RS4**: If `profile_id=auto` resolves to no supported scorer for the experiment's game, the scorer MUST exit with code `0` and leave `results.json` unmodified.
- **RS5**: The scorer MUST read `game.config` from `manifest.yaml` as the behavioral config, matching the behavior of the research export surface.
- **RS6**: If `--recordings-dir` is supplied, it MUST override the path resolved from `manifest.yaml`. If neither is available, the scorer MUST fail with a clear error.
- **RS7**: For matrix experiments, `--cell` MUST scope both recordings discovery and results.json update to that cell's artifact. If omitted on a matrix experiment, the scorer MUST require explicit confirmation or fail with a clear error rather than silently scoring all cells.
- **RS8**: `--dry-run` MUST print: resolved scorer `profile_id`, `profile_version`, recordings path used, and match count. It MUST NOT write any files.
- **RS9**: The scorer MUST delegate all behavioral computation to the `BehavioralScorer.score(...)` contract. It MUST NOT implement game-specific logic directly.
- **RS10**: If `{experiment_dir}/scripts/behavioral_scorer.py` exists, the scorer MUST attempt package-local resolution before consulting the built-in registry.
- **RS11**: If a package-local scorer module exists but does not expose a valid, unambiguous scorer, the scorer MUST fail with exit code `1` and leave `results.json` unchanged.
- **RS12**: If a package-local scorer resolves successfully but `supports(...)` returns `False` for the supplied payloads, the scorer MUST fail with exit code `1` rather than silently falling back to a built-in scorer.
- **RS13**: Package-local scorer modules MUST NOT produce side effects at import time beyond defining the scorer.
- **RS14**: `--dry-run` MUST report whether the resolved scorer source is `package_local` or `builtin`.

## 6. Error Handling

- `--experiment-dir` not found → `FileNotFoundError`, exit 1
- targeted `results.json` not found → `FileNotFoundError`, exit 1
- Recordings dir not found (from manifest or override) → `FileNotFoundError`, exit 1
- No `match_*.json` files in recordings dir → `FileNotFoundError`, exit 1
- `--profile-id` names a specific scorer that does not match the experiment's game → `ValueError`, exit 1
- Scorer raises during `score()` → propagate with exit 1
- Matrix experiment, `--cell` omitted → `ValueError` with message listing available cells, exit 1
- Package-local scorer module exists but exposes invalid `SCORER` → `ValueError`, exit 1
- Package-local scorer module exists but exposes multiple concrete subclasses without `SCORER` → `ValueError`, exit 1
- Package-local scorer resolves but `supports(...)` returns `False` → `ValueError`, exit 1

## 7. Testing Strategy

- Verify RS2: targeted `results.json` keys other than `behavioral_profile` are byte-identical before and after scoring.
- Verify RS3: running twice produces the same `behavioral_profile` output.
- Verify RS4: no-op exit on auto with no matching scorer; results.json untouched.
- Verify RS6: `--recordings-dir` override is used when supplied.
- Verify RS8: `--dry-run` emits required fields and writes nothing.
- Verify error paths: missing experiment dir, missing results.json, missing recordings, unknown explicit profile ID.
- Verify RS9: scorer computation is delegated; the CLI adds no game-specific logic.
- Verify RS10/RS11: valid package-local scorer is loaded; invalid or ambiguous package-local module fails loudly.
- Verify RS12: package-local scorer with `supports(...) == False` fails with exit code `1`.
- Verify RS14: `--dry-run` reports `package_local` vs `builtin`.

## 8. Examples

```bash
# Auto-detect scorer and rescore
agentdeck-research-score --experiment-dir research/research_2026-03-26-variable-damage-premium-final-1

# Rescore a specific cell in a matrix experiment
agentdeck-research-score \
  --experiment-dir research/research_2026-03-26-variable-damage-arc-1 \
  --cell flash_lite_rc_risk

# Preview without writing
agentdeck-research-score \
  --experiment-dir research/research_2026-03-25-fixed-damage-baseline-completion-2 \
  --dry-run

# Package-local scorer inside the experiment package
agentdeck-research-score \
  --experiment-dir research/research_2026-04-09-signal-cache-controller-2

# Matrix package: rescore one cell artifact
agentdeck-research-score \
  --experiment-dir research/research_2026-04-10-your-matrix-study \
  --cell p1_c01_example

# Override recordings path (e.g., after moving runs to a new location)
agentdeck-research-score \
  --experiment-dir research/research_2026-03-23-fixed-damage-exit-1 \
  --recordings-dir /mnt/recovered/agentdeck_runs/session-abc123/records
```

## 9. Design Rationale

- **Write only `behavioral_profile`**: the rest of the targeted `results.json` is stable and audit-relevant. Updating only the profile key makes the scorer a surgical tool rather than a re-export alias.
- **Requires raw recordings (RS1)**: behavioral scorers consume recorder match payloads, not the derived `matches` array in `results.json`. The raw payloads carry event-level detail that the summarized array strips out.
- **No-op on no match (RS4)**: games without a registered scorer are valid. Failing loudly would make the scorer unusable in mixed-game pipelines or automation.
- **RS7 explicit cell requirement**: silently scoring all cells of a matrix experiment would produce multiple writes to different result files without feedback. An explicit cell flag keeps each invocation unambiguous.
- **Matrix cell ownership**: matrix rescoring is intentionally cell-scoped. It updates `artifacts/<cell>/results.json`, not the top-level package `results.json`.
- **Package-local convention over manifest fields**: a conventional `scripts/behavioral_scorer.py` path is the smallest non-breaking extension for new games and keeps scorer ownership inside the experiment package.
- **Fail loudly on package-local mismatch**: the presence of a package-local scorer file signals author intent. Silent fallback would hide scorer bugs and make Round 8-style benchmark authoring harder to audit.

## 10. References

- `SPEC-RESEARCH-BEHAVIORAL.md` — scorer contract
- `SPEC-RESEARCH-EXPERIMENT.md` — experiment package schema and `results.json` ownership
- `SPEC-RESEARCH-WORKFLOW.md` — recordings discovery and path resolution
- `src/agentdeck/research/behavioral.py` — `compute_behavioral_profile`, `get_behavioral_scorer`
- `src/agentdeck/research/export.py` — `_behavioral_config_from_manifest`, `_canonical_recordings_dirs_from_artifact`
