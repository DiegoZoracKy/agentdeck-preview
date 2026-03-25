# VariableDamage OpenAI Baseline 2

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-25-variable-damage-openai-baseline-2`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: VariableDamageGame
- Players: gpt-5-mini, gemini-2.5-flash
- Seed Base: 32242
- Pilot Read: `GPT5Mini-AO` previously beat `Flash-AO` `15-9`, `p=0.307`
- Expansion Read: `Flash-AO` edged `GPT5Mini-AO` `25-23`, `p=0.885`
- Avg Turns: `24.0625`
- Total Cost: `$0.576996`
<!-- AUTO_FACTS:END -->

## Why This Exists
- `VariableDamage OpenAI Baseline 1` showed the most interesting top-tier pilot cell was `GPT5Mini-AO` vs `Flash-AO`.
- That pilot came back `15-9` for `GPT5Mini-AO`, but it stayed null at `N=24`.
- The behavioral gap was clearer than the win gap:
  - `GPT5Mini-AO` preserved far more inventory into lethal states
  - converted second-player starts better
  - and almost never healed in the safe zone
- This package expands only that one cell to decide whether the top of the VariableDamage baseline graph is a real ordering or just near-parity.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers:
  - `gpt-5-mini`
  - `gemini-2.5-flash`
- Strategy condition:
  - `GPT5Mini-AO` vs `Flash-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `48`
- Seed base:
  - `32242`

## Primary Endpoints
- decisive win rate
- second-player win split
- `first_lethal_entry_inventory`
- `safe_zone_potion_rate`
- `lower_danger_zone_potion_rate`
- `upper_danger_zone_potion_rate`
- `lethal_zone_potion_rate`

## Secondary Endpoints
- `unused_potions_on_loss_rate`
- `high_roll_recovery_rate`
- cost
- latency
- strict contract rate

## Hypothesis
- `GPT5Mini-AO` should remain cleaner on inventory timing than `Flash-AO`.
- If that advantage is structurally important, it should hold up as an `N=48` edge.
- If the cell stays near-parity, the right read will be that Flash and GPT-5 Mini are both top-tier VariableDamage baselines with different policy styles.

## Result
- The pilot edge did not hold up.
- `Flash-AO` edged `GPT5Mini-AO` `25-23` at `N=48` with exact-binomial `p=0.885` and negligible effect.
- The headline read is near-parity, not a premium-model separation.
- The behavioral split still matters:
  - `GPT5Mini-AO` kept a much stronger inventory margin into lethal states
    - first lethal entry inventory median `2` vs `0`
    - first lethal entry `zero_potions_rate` `25.5%` vs `65.2%`
    - `lethal_zone_potion_rate` `1.0` vs `0.739`
    - `safe_zone_potion_rate` `0.0` vs `0.102`
  - `Flash-AO` kept the slight outcome edge anyway
    - `25-23` overall
    - `6` second-player wins vs `5`
    - `19` wins as first player vs `18`
- Cost remained materially different:
  - `Flash-AO`: about `$0.002350` per match
  - `GPT5Mini-AO`: about `$0.009671` per match
  - `gpt-5-mini` cost about `4.1x` as much in this cell
