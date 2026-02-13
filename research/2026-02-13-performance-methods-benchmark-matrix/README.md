# Performance Methods Benchmark Matrix (2026-02-13)

**Status**: planned  
**Research Question**: How much do controller strategy (AO vs CoT), instruction cadence
(handshake-only vs per-turn reinforcement), and model tier (weak vs strong) influence
win rate, reliability, and cost across OpenAI and Anthropic in FixedDamageGame?

## Why This Package Exists
This package exists to measure performance gains from:

1. Controller strategy (`ActionOnly` vs `Reasoning`).
2. Prompt cadence (`handshake-only` vs per-turn reinforcement).
3. Model tier tradeoffs (weak/strong, intra/inter-provider).
4. Reliability and cost behavior under the same game conditions.

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

Each phase should produce an analysis update and optional qualitative match curation.

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
- Optional curated qualitative matches: committed in `viewer/matches/`

## Repro Notes
Freeze benchmark inputs before execution:
- git tag/commit
- prompt template version
- pricing snapshot

Populate those freeze fields in `matrix.yaml` / `manifest.yaml` before launching any cells.

Turn-budget helper for this package:
```bash
python3 research/2026-02-13-performance-methods-benchmark-matrix/scripts/turn_budget.py
```
