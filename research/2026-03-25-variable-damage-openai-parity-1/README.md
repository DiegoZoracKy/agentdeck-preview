# VariableDamage OpenAI Parity 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-25-variable-damage-openai-parity-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: planned
- Matches: 48/48
- Game: VariableDamageGame
- Players: gpt-4o-mini, gpt-5-mini
- Seed Base: 29242
- Baseline Read: `GPT5Mini-AO` beat `GPT4oMini-AO` `16-8`, `p=0.152`
- RC Read: `GPT5Mini-AO` beat `GPT4oMini-RC` `15-9`, `p=0.307`
- Avg Turns: `23.52`
- Total Cost: `$0.5330`
<!-- AUTO_FACTS:END -->

## Why This Exists
- `VariableDamage OpenAI Baseline 1` placed plain `GPT5Mini-AO` into the current baseline graph.
- The missing OpenAI-only ladder is now:
  - plain `GPT4oMini-AO` vs plain `GPT5Mini-AO`
  - `GPT4oMini-RC` vs plain `GPT5Mini-AO`
- This package asks whether RC alone helps the cheaper OpenAI mini under uncertainty, or repeats the FixedDamage pattern where RC moved the policy in the wrong direction.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers:
  - `gpt-4o-mini`
  - `gpt-5-mini`
- Strategy conditions:
  - `GPT4oMini-AO` vs `GPT5Mini-AO`
  - `GPT4oMini-RC` vs `GPT5Mini-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `24` per cell
- Seed base:
  - `29242`

## Primary Endpoints
- second-player win split
- `safe_zone_potion_rate`
- `danger_zone_potion_rate`
- `lower_danger_zone_potion_rate`
- `upper_danger_zone_potion_rate`
- `lethal_zone_potion_rate`
- `first_lethal_entry_inventory`
- `unused_potions_on_loss_rate`
- `high_roll_recovery_rate`
- `position_policy_delta`

## Secondary Endpoints
- total win rate
- cost
- latency
- strict contract rate

## Result
- Plain `GPT4oMini-AO` was already within pilot-range striking distance of `GPT5Mini-AO`, but still lost `8-16`.
- `GPT4oMini-RC` improved only marginally to `9-15`; this was still null and did not justify an RC continuation by itself.
- The main shift under RC was behavioral:
  - first potion moved from `78 HP` to `39 HP`
  - first lethal entry improved from median `0` potions left to median `1`
  - but RC also overshot in the other direction:
    - `danger_zone_potion_rate` fell from `0.810` to `0.292`
    - `lethal_zone_potion_rate` reached only `0.581`
    - `unused_potions_on_loss_rate` rose from `0.0` to `0.40`
- `GPT5Mini-AO` stayed the cleaner policy in both cells:
  - essentially `0%` safe-zone healing
  - `1.0` lethal-zone healing
  - stronger second-player conversion (`6/12` in both cells)
