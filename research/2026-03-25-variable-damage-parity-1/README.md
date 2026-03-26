# VariableDamage Parity 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-25-variable-damage-parity-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: VariableDamageGame
- Players: gemini-2.5-flash-lite, gemini-2.5-flash
- Seed Base: 33242
- Carry-Forward Read: `FlashLite-RC-RISK` previously tied `Flash-AO` `12-12`, `p=1.0`
- Expansion Read: `FlashLite-RC-RISK` beat `Flash-AO` `26-22`, but this stayed null (`p=0.665`, negligible effect)
- Avg Turns: `24.42`
- Total Cost: `$0.2613`
<!-- AUTO_FACTS:END -->

## Why This Exists
- `VariableDamage Threshold 1` identified the first Flash-Lite treatment that helped both behavior and outcome.
- That treatment:
  - eliminated safe-zone healing
  - cut empty-at-lethal entries sharply
  - fixed seat-conditioned drift
  - moved the matchup from `8-16` to `12-12`
- This package tests whether that pilot tie survives at the first real parity sample.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy condition:
  - `FlashLite-RC-RISK` vs `Flash-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `48`
- Seed base:
  - `33242`

## Primary Endpoints
- decisive win rate
- second-player win split
- `first_lethal_entry_inventory`
- `safe_zone_potion_rate`
- `lower_danger_zone_potion_rate`
- `upper_danger_zone_potion_rate`
- `lethal_zone_potion_rate`
- `position_policy_delta`

## Secondary Endpoints
- `unused_potions_on_loss_rate`
- `high_roll_recovery_rate`
- cost
- latency
- strict contract rate

## Result
- The Threshold 1 treatment held up at expansion size.
- `FlashLite-RC-RISK` finished `26-22` over `Flash-AO` at `N=48`, which is still non-significant but directionally favorable.
- The behavioral profile stayed strong where it mattered:
  - `safe_zone_potion_rate`: `0.0%`
  - `lethal_zone_potion_rate`: `100%`
  - `unused_potions_on_loss_rate`: `0.0%`
  - `position_policy_delta`: `0.0667`
- The treatment still enters first lethal with `0` potions too often (`39.6%`), but that remains much better than the RC-only Threshold 1 control (`58.3%`).

## Practical Read
- This was not a statistical win over Flash, but it was enough to keep the Flash-Lite VariableDamage line alive.
- The treatment now looks like a real near-parity condition against the practical reference baseline.
- The remaining weakness is not safe-zone waste or lethal-zone failure anymore; it is danger-zone behavior once only `1` potion remains.
