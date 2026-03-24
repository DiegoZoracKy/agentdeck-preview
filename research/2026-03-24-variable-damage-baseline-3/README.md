# VariableDamage Baseline 3

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-24-variable-damage-baseline-3`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 144/144
- Game: VariableDamageGame
- Players: gemini-2.5-flash, gpt-4o-mini, claude-haiku-4-5-20251001
- Seed Base: 25242
- Topline Winner: Flash-AO
- Avg Turns: 23.84
- Avg Duration (s): 49.57
- Total Cost: 1.1723
<!-- AUTO_FACTS:END -->

## Why This Exists
- Complete the missing stronger-model VariableDamage AO round-robin.
- Measure how plain Flash, plain Mini, and plain Haiku compare under uncertainty before deciding whether any of those stronger baselines actually deserve controller work.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers: `gemini-2.5-flash`, `gpt-4o-mini`, `claude-haiku-4-5-20251001`
- Configs: handshake-only `ActionOnlyController`
- Matches Planned: `144`
- Seed Base: `25242`
- Turn cap: `40`

## Execution Plan
- Phase P1:
  - `Mini-AO` vs `Flash-AO`
  - `Haiku-AO` vs `Flash-AO`
  - `Mini-AO` vs `Haiku-AO`
- Expansion rule:
  - no expansion in this package; use the exported risk-band behavior to determine the plain-model ordering and whether any stronger baseline shows a specific controller-worthy failure mode

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
  - `lethal_zone_potion_rate`
  - `risk_band_potion_rate_by_scarcity`
  - `first_lethal_entry_inventory`
  - `unused_potions_on_loss_rate`
  - `high_roll_recovery_rate`

## Artifacts
- `matrix.yaml` (benchmark grid definition)
- `manifest.yaml` (repro metadata)
- `analysis.md` (interpretation plan and hypotheses)
- `artifacts/` (derived tables/plots/highlights)
- `notes/` (human run notes)
- `recordings/` (external pointers only)
- `scripts/` (execution helpers / notes)

## Storage
- Raw recordings will live under `research/2026-03-24-variable-damage-baseline-3/agentdeck_runs`
- Repo keeps the package contract and later lightweight derived artifacts

## Outcome
- `Flash-AO` beat `Mini-AO` `34-14` at `N=48` (`p=0.0055`)
- `Flash-AO` edged `Haiku-AO` `26-22` at `N=48` (`p=0.665`), effectively a null
- `Haiku-AO` beat `Mini-AO` `31-17` at `N=48` (`p=0.059`), strong directional but just short of the cutoff

## Main Finding
- The plain-model ordering in VariableDamage is now clear enough: `Flash-AO ≈ Haiku-AO > Mini-AO`
- `Mini-AO` is coherent but too conservative. It spends potions very early, then reaches lethal states already empty:
  - vs `Flash-AO`: first potion median `81 HP`, safe-zone potion rate `44.9%`, zero-potions on first lethal entry `100%`
  - vs `Haiku-AO`: first potion median `80 HP`, safe-zone potion rate `34.2%`, zero-potions on first lethal entry `100%`
- `Flash-AO` and `Haiku-AO` are both much better calibrated under uncertainty:
  - `Flash-AO` is the more pressure-oriented baseline, healing later and converting better from second player
  - `Haiku-AO` is the more conservative-but-still-strong baseline, with perfect lethal-zone healing and a near-parity result against Flash

## Practical Read
- No Mini transfer or prompt-stack claim should be imported from FixedDamage as-is. In VariableDamage, plain `Mini-AO` is already weaker than both `Flash-AO` and `Haiku-AO`.
- No Haiku controller branch is justified from this package. `Haiku-AO` already looks strong and behaviorally healthy.
- `Flash-AO` remains the practical plain-model reference point for future VariableDamage intervention work, with `Haiku-AO` as the closest alternative baseline.
