# VariableDamage Reinforcement 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-24-variable-damage-reinforcement-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: VariableDamageGame
- Players: gemini-2.5-flash-lite, gemini-2.5-flash
- Seed Base: 24242
- Topline Winner: Flash-AO over both FlashLite-RC and FlashLite-RC-TR (14-10 in each cell)
- Avg Turns: 23.21
- Avg Duration (s): 94.11
- Total Cost: $0.1892
<!-- AUTO_FACTS:END -->

## Why This Exists
- `VariableDamage Controller 1` showed that `FlashLite-RC` repaired the core under-healing failure, but introduced more policy variance than `FlashLite-AO`.
- In FixedDamage, turn reinforcement was the next successful stabilizer after RC.
- This package asked whether the same next-step intervention helps in the stochastic VariableDamage setting.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers: `gemini-2.5-flash-lite`, `gemini-2.5-flash`
- Configs:
  - `FlashLite-RC` vs `Flash-AO`
  - `FlashLite-RC-TR` vs `Flash-AO`
- Matches Planned: `48`
- Matches Completed: `48`
- Seed Base: `24242`
- Turn cap: `40`

## Outcome
- `FlashLite-RC` vs `Flash-AO`: `10-14`, exact-binomial `p=0.541`, negligible effect.
- `FlashLite-RC-TR` vs `Flash-AO`: `10-14`, exact-binomial `p=0.541`, negligible effect.
- So TR did not improve the headline result against Flash on this seed family.

## Behavioral Read
- Both RC variants stayed materially better than the old `FlashLite-AO` VariableDamage baseline on resource use and lethal-state defense.
- TR helped some specific behaviors:
  - second-player wins improved from `1/12` to `3/12`
  - lethal-zone potion rate improved from `75.0%` to `82.1%`
  - safe-zone potion rate fell slightly from `21.5%` to `19.0%`
  - zero-potion first lethal entry rate fell from `58.3%` to `41.7%`
- But the tradeoff was real:
  - first-player wins fell from `9/12` to `7/12`
  - first potion median moved later from `40 HP` to `49 HP`
  - danger-zone potion rate fell from `37.5%` to `33.3%`
  - position policy delta worsened from `0.333` to `0.750`
- The clean read is that TR made Flash-Lite a bit more coherent in some places, but not more competitive overall.

## Practical Read
- `FlashLite-RC` remains the meaningful VariableDamage repair over plain `FlashLite-AO`.
- `FlashLite-RC-TR` is not a good next default. It costs a bit more and did not outperform RC against plain Flash.
- The next intervention, if we stay on this branch, should be a targeted instruction layer rather than more cadence work.

## Primary Readout
- Outcome:
  - decisive win rate
  - exact-binomial significance
  - first-player win rate
  - position-controlled split
- Behavior:
  - `safe_zone_potion_rate`
  - `danger_zone_potion_rate`
  - `lower_danger_zone_potion_rate`
  - `upper_danger_zone_potion_rate`
  - `risk_band_potion_rate_by_scarcity`
  - `first_lethal_entry_inventory`
  - `unused_potions_on_loss_rate`
  - `risk_band_policy_delta`
  - `high_roll_recovery_rate`

## Artifacts
- `matrix.yaml` (benchmark grid definition)
- `manifest.yaml` (repro metadata)
- `analysis.md` (interpretation plan and hypotheses)
- `results.json` / `results.csv` (exported package summary)
- `artifacts/` (derived tables/plots/highlights)
- `notes/` (human run notes)
- `recordings/` (external pointers only)
- `scripts/` (execution helpers / notes)

## Storage
- Raw recordings will live under `research/2026-03-24-variable-damage-reinforcement-1/agentdeck_runs`
- Repo keeps the package contract and later lightweight derived artifacts
