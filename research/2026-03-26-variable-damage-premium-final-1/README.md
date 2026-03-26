# VariableDamage Premium Final 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-26-variable-damage-premium-final-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 24/24
- Game: VariableDamageGame
- Players: gemini-2.5-flash-lite, gpt-5-mini
- Seed Base: 34242
- Carry-Forward Read: `FlashLite-RC-RISK` previously beat `Flash-AO` `26-22`, `p=0.665`
- Premium Read: `GPT5Mini-AO` beat `FlashLite-RC-RISK` `13-11`, `p=0.839`
- Avg Turns: `24.63`
- Total Cost: `$0.3082`
<!-- AUTO_FACTS:END -->

## Why This Exists
- `VariableDamage Parity 1` showed that the risk-grounded Flash-Lite condition survived expansion and held near parity with the practical `Flash-AO` baseline.
- The main remaining release-facing question is not another tuning rung.
- It is whether the tuned cheap-model condition can stay behaviorally respectable against the premium clean-policy baseline `GPT5Mini-AO`.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gpt-5-mini`
- Strategy condition:
  - `FlashLite-RC-RISK` vs `GPT5Mini-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `24`
- Seed base:
  - `34242`

## Primary Endpoints
- decisive win rate
- second-player win split
- `first_lethal_entry_inventory`
- `safe_zone_potion_rate`
- `lower_danger_zone_potion_rate`
- `upper_danger_zone_potion_rate`
- `lethal_zone_potion_rate`
- `risk_band_potion_rate_by_scarcity`

## Secondary Endpoints
- `unused_potions_on_loss_rate`
- `position_policy_delta`
- cost
- latency
- strict contract rate

## Result
- `GPT5Mini-AO` beat `FlashLite-RC-RISK` `13-11` at `N=24`, but the result stayed fully non-significant.
- The useful part is that the carried-forward Flash-Lite condition stayed behaviorally clean:
  - `safe_zone_potion_rate = 1.3%`
  - `lethal_zone_potion_rate = 100%`
  - `unused_potions_on_loss_rate = 0.0%`
  - `position_policy_delta = 0.0`
- `GPT5Mini-AO` was still cleaner in the remaining narrow weakness:
  - lower danger-zone potion rate overall (`30.4%` vs `41.7%`)
  - much lower zero-potions first-lethal entry (`12.5%` vs `34.8%`)

## Practical Read
- This is the right stopping point for the main VariableDamage research arc.
- The tuned weak-model condition did not beat the premium baseline, but it stayed close enough and clean enough to prove the main AgentDeck point.
- What remains is synthesis, not more package branching:
  - `VariableDamage Arc 1`
  - cross-game comparison
  - release-facing `v0.1.0` docs
