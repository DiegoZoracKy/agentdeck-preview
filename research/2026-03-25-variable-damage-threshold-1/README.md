# VariableDamage Threshold 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-25-variable-damage-threshold-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: VariableDamageGame
- Players: gemini-2.5-flash-lite, gemini-2.5-flash
- Seed Base: 31242
- Control Read: `Flash-AO` beat `FlashLite-RC` `16-8` (`p=0.152`)
- Risk Read: `FlashLite-RC-RISK` tied `Flash-AO` `12-12` (`p=1.0`)
- Avg Turns: `24.125`
- Total Cost: `$0.222037`
<!-- AUTO_FACTS:END -->

## Why This Exists
- `VariableDamage Controller 1` showed that `FlashLite-RC` repaired the worst under-healing failure.
- `VariableDamage Reinforcement 1` showed that turn reinforcement did not improve the matchup against plain Flash.
- The remaining failure is narrower and more actionable:
  - too much safe-zone healing in some seat-conditioned states
  - too many first lethal entries with `0` potions left
  - still too much hesitation in lower-danger and lethal states with multiple potions
- This package tests whether a direct risk-band instruction can fix that mechanism without another cadence change.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC` vs `Flash-AO`
  - `FlashLite-RC-RISK` vs `Flash-AO`
- Intervention surface:
  - same `ReasoningController`
  - no engine change
  - no game change
  - one turn-time risk-band instruction in the treatment cell
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `24` per cell
- Seed base:
  - `31242`

## Primary Endpoints
- `first_lethal_entry_inventory`
- `lower_danger_zone_potion_rate`
- `upper_danger_zone_potion_rate`
- `lethal_zone_potion_rate`
- `safe_zone_potion_rate`
- second-player wins
- `position_policy_delta`

## Secondary Endpoints
- total win rate
- `unused_potions_on_loss_rate`
- `high_roll_recovery_rate`
- cost
- latency
- strict contract rate

## Hypothesis
- Plain RC already fixed the biggest Flash-Lite VariableDamage failure.
- The remaining problem is not “reason more”; it is “use the right risk thresholds at the right time.”
- If the prompt explicitly anchors safe, lower-danger, and lethal decisions, Flash-Lite should arrive at lethal states with more potions left and become more competitive with plain Flash.

## Result
- The treatment worked directionally and competitively.
- Control: `Flash-AO` beat `FlashLite-RC` `16-8` at `N=24` (`p=0.152`, small effect).
- Treatment: `FlashLite-RC-RISK` tied `Flash-AO` `12-12` at `N=24` (`p=1.0`, negligible effect).
- The key mechanism improvement was resource timing:
  - first lethal entry inventory median improved from `0` to `1`
  - first lethal entry `zero_potions_rate` dropped from `58.3%` to `26.1%`
  - `safe_zone_potion_rate` dropped from `23.0%` to `0.0%`
  - `lower_danger_zone_potion_rate` rose from `22.2%` to `74.5%`
  - `lethal_zone_potion_rate` rose from `76.7%` to `100%`
  - `position_policy_delta` collapsed from `0.333` to `0.051`
- Tradeoff:
  - treatment cost rose from about `$0.003833` to `$0.005419` per match
  - average turns also rose slightly (`23.58 -> 24.67`)
