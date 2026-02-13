# AgentDeck TV Benchmark Matrix (2026-02-13)

**Status**: planned  
**Research Question**: How much do controller strategy (AO vs CoT), instruction cadence
(handshake-only vs per-turn reinforcement), and model tier (weak vs strong) influence
win rate, reliability, and cost across OpenAI and Anthropic in FixedDamageGame?

## Why This Package Exists
This package is the anchor for the `research -> entertainment -> research` loop:

1. Run statistically controlled benchmark cells.
2. Auto-tag notable matches (`clutch`, `comeback`, `chaos`, `dumb_decision`).
3. Curate highlights into `viewer/matches/` and agentdeck.tv.
4. Feed audience + analysis findings into the next benchmark iteration.

## Matrix Snapshot
- Models: 4 (`gpt-4o-mini`, `gpt-4o`, `claude-haiku-4.5`, `claude-sonnet-4.5`)
- Configs: 3 (`AO`, `CoT-H`, `CoT-T`)
- Cells: 22 (see `matrix.yaml`)
- Pilot: 24 matches/cell (paired seeds + side swap) => 528 matches
- Expansion: increase selected cells to 80 matches using pre-defined rules
- Campaign target: 976 matches total

## Config Definitions
- `AO`: `ActionOnlyController` + default turn template
- `CoT-H`: `ReasoningController` + turn template `{game_view}` (handshake-only reinforcement)
- `CoT-T`: `ReasoningController` + default turn template (includes `{controller_format}` per turn)

## Execution Phases
- `A1` Core CoT effects (Tracks 1-2): 8 cells
- `A2` David vs Goliath + showdowns (Tracks 3-6): 8 cells
- `A3` Baselines + raw cross-provider (Tracks 7-8): 6 cells
- `B` Google expansion in a follow-up package

Each phase should produce a viewer drop (curated highlights + research context links).

## Preflight Gate
Before full pilot, run the 4 sentinel cells from `matrix.yaml -> execution_plan.preflight`.
If parse/timeout/forfeit instability appears, fix config and rerun preflight.

## Artifacts
- `manifest.yaml`: package metadata and campaign targets
- `matrix.yaml`: schema + concrete 22-cell registry
- `analysis.md`: interpretation (to be filled after runs)
- `artifacts/`: generated exports (`cells.parquet`, `matches.parquet`, highlights)
- `logs/`: run journals
- `recordings/`: pointers only (raw recordings live outside git)

## Storage Plan
- Raw recordings: Hugging Face dataset `agentdeck/replays` under `2026-q1-benchmark-matrix/`
- Research summaries: committed in this package directory
- Curated highlights: committed in `viewer/matches/`

## Repro Notes
Freeze benchmark inputs before execution:
- git tag/commit
- prompt template version
- pricing snapshot

Populate those freeze fields in `matrix.yaml` / `manifest.yaml` before launching any cells.
