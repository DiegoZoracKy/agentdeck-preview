# VariableDamage OpenAI Parity 2

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-25-variable-damage-openai-parity-2`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: VariableDamageGame
- Players: gpt-4o, gpt-5-mini
- Seed Base: 30242
- Baseline Read: `GPT4o-AO` beat `GPT5Mini-AO` `13-11`, `p=0.839`
- RC Read: `GPT4o-RC` beat `GPT5Mini-AO` `13-11`, `p=0.839`
- Avg Turns: `24.50`
- Total Cost: `$1.8360`
<!-- AUTO_FACTS:END -->

## Why This Exists
- `VariableDamage OpenAI Parity 1` showed that `gpt-4o-mini` plus RC-only did not close much ground against plain `gpt-5-mini`.
- The next clean rung is premium `gpt-4o`:
  - plain `GPT4o-AO` vs plain `GPT5Mini-AO`
  - `GPT4o-RC` vs plain `GPT5Mini-AO`
- This asks whether the better base model changes the RC story, or whether RC still fails to create useful uplift against `gpt-5-mini`.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers:
  - `gpt-4o`
  - `gpt-5-mini`
- Strategy conditions:
  - `GPT4o-AO` vs `GPT5Mini-AO`
  - `GPT4o-RC` vs `GPT5Mini-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `24` per cell
- Seed base:
  - `30242`

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

## Hypothesis
- If premium `gpt-4o` is already close to or above plain `gpt-5-mini`, RC may add little.
- If `gpt-4o` is still behind on VariableDamage risk calibration, RC may either help modestly or repeat the same policy reorganization failure seen on `gpt-4o-mini`.

## Result
- Premium `GPT4o-AO` was already near-parity with plain `GPT5Mini-AO` and edged the pilot `13-11`.
- `GPT4o-RC` produced the exact same `13-11` outcome, so RC added no headline improvement at all.
- RC did make `gpt-4o` behavior somewhat cleaner:
  - `safe_zone_potion_rate` fell from `0.116` to `0.066`
  - first lethal-entry `zero_potions_rate` improved from `0.727` to `0.565`
  - `position_policy_delta` fell from `0.182` to `0.044`
- But that cleanup came without better results and at a much higher price:
  - AO cell total cost: `$0.7403`
  - RC cell total cost: `$1.0957`
- `GPT5Mini-AO` remained the cleaner endgame policy in both cells:
  - lethal-zone healing stayed at `1.0`
  - first lethal entry median stayed at `2` potions left
  - but that cleaner policy did not translate into a pilot-size win edge against premium `gpt-4o`
