# Performance Methods Benchmark Matrix (2026-02-13)

**Status**: planned  
**Research Question**: How much can strategy tuning (AO vs CoT-H vs CoT-T) close or overturn
model-tier gaps by making `gpt-4o-mini` cost-efficient against stronger OpenAI, Anthropic,
and Google models in FixedDamageGame?

## Why This Package Exists
This package is built around a narrative-first benchmark:

1. Establish mini baselines (`AOxAO`, `CoT-HxCoT-H`, `CoT-TxCoT-T`) to control first-player/variance effects.
2. Tune `gpt-4o-mini` for the task (`AO` vs `CoT-H`, `AO` vs `CoT-T`, `CoT-H` vs `CoT-T`).
3. Measure whether tuning beats raw model-tier advantage (`gpt-4o`, `gpt-5.2`).
4. Test if the same tuned strategy transfers against Anthropic and Google weak/strong tiers.
5. Quantify the cost-efficiency story with statistically stronger headline cells.

## Primary Matrix
- Primary file: `matrix.yaml` (v2 OpenAI-anchor grid)

## Matrix Snapshot (v2)
- Models: 7 (`gpt-4o-mini`, `gpt-4o`, `gpt-5.2`, `claude-haiku-4.5`, `claude-sonnet-4.5`, `gemini-2.5-flash-lite`, `gemini-2.5-pro`)
- Configs: 3 (`AO`, `CoT-H`, `CoT-T`)
- Cells: 28
- Pilot: 24 matches/cell => 672 matches
- Expansion targets: 80 per cell by default; 120 for headline `gpt-5.2` cells (`c15-c17`)
- Full-expansion ceiling: 2360 matches

## Config Definitions
- `AO`: `ActionOnlyController` + default turn template
- `CoT-H`: `ReasoningController` + turn template `{game_view}` (handshake-only reinforcement)
- `CoT-T`: `ReasoningController` + default turn template (includes `{controller_format}` per turn)

## Execution Phases (v2)
- `A1` OpenAI Strategy Discovery + Baselines (Tracks 0-3): 10 cells
- `A2` Opponent Strategy Calibration (Track 4): 4 cells
- `A3` OpenAI Cost-Efficiency Showcase (Track 5): 6 cells
- `A4` Cross-Provider Challenge (Track 6): 8 cells

Each phase should produce an analysis update and optional qualitative match curation.

## Preflight Gate
Before full pilot, run the 4 sentinel cells from `matrix.yaml -> execution_plan.preflight`.
If parse/timeout/forfeit instability appears, fix config and rerun preflight.

## Artifacts
- `manifest.yaml`: package metadata and campaign targets
- `matrix.yaml`: schema + concrete 25-cell registry (primary)
- `OUT_OF_THE_BOX_REQUIREMENTS.md`: execution requirements checklist using only AgentDeck-native capabilities
- `analysis.md`: interpretation (to be filled after runs)
- `artifacts/`: generated exports (`cells.parquet`, `matches.parquet`, highlights)
- `logs/`: run journals
- `recordings/`: pointers only (raw recordings live outside git)

## Storage Plan
- Raw recordings: Hugging Face dataset `agentdeck/replays` under `2026-q1-performance-methods-matrix-v2/`
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

Single-match out-of-the-box smoke test:
```bash
python3 research/2026-02-13-performance-methods-benchmark-matrix/scripts/run_one_match_openai_mini.py
```
