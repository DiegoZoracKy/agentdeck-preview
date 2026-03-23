# FixedDamage FlashLite Exit 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-23-fixed-damage-exit-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `google:gemini-2.5-flash`
- Seed Base: `20242`
- Topline Read:
  - `FlashLite-RC-TR-HP-exit` beat `Flash-AO` `35-13` at `N=48`
  - the no-potion exit clause turned the old near-significant Flash parity result into a significant win (`p=0.0021`)
  - the prompt repair removed the worst low-HP tail behavior without reopening the old threshold bug
- Avg Turns: `22.31`
- Avg Duration (s): `63.41`
- Total Cost: `0.21875`
<!-- AUTO_FACTS:END -->

## Why This Exists
- Parity 3 showed that the full Flash-Lite stack could become genuinely
  competitive with plain Flash, but the raw recordings also exposed a prompt
  defect.
- In low-HP / no-potion states, the HP instruction could tell the model not to
  attack when `ATTACK` was the only legal move left.
- That deadlock produced the largest reasoning-cost outliers in the full stack,
  especially near `10 HP / 0 potions`.
- This package repairs that prompt gap directly without touching the engine or
  the game.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC-TR-HP-exit` vs `Flash-AO`
- Turn-time prompt:
  - same as Parity 3 full stack except for one repair
  - if the HP check fails and no potions remain, the prompt now tells the model
    to `ATTACK anyway`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `48`
- Seed base:
  - `20242`

## Primary Endpoints
- second-player win split
- total win rate
- tail-cost reduction
- `position_policy_delta`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`
- state-level evidence at `10 HP / 0 potions`, `20 HP / 3 potions`, and `20 HP / 1 potion`

## Secondary Endpoints
- latency
- strict contract rate
- parse failure rate

## Hypothesis
- If the worst reasoning tail comes from the prompt deadlock rather than from
  inherently hard states, then this repair should remove the `10 HP / 0
  potions` loop, reduce tail cost, and preserve or improve the full-stack
  behavior against plain Flash.

## Result
- `FlashLite-RC-TR-HP-exit` finished `35-13` over `Flash-AO` at `N=48`.
- Statistical read:
  - exact binomial `p=0.0021`
  - effect size `0.476` (`small`)
- Position read:
  - first player won `37/48`
  - `FlashLite-RC-TR-HP-exit` won `24/24` as first player and `11/24` as second
  - `Flash-AO` won `13/24` as first player and `0/24` as second

## What Changed
- The exit clause fixed the known low-HP prompt defect.
  - in Parity 3, Flash-Lite's worst `10 HP / 0 potions` turn was `13,126` chars
  - in Exit 1, the same state averaged about `263` chars with max `358`
- The long tail shrank materially.
  - Parity 3 had `45` Flash-Lite turns over `500` chars
  - Exit 1 had `19`, despite slightly more total Flash-Lite turns (`541` vs `525`)
- The fix improved behavior, not just verbosity.
  - `all_attack_match_rate`: `2.1%`
  - `unused_potions_on_loss_rate`: `7.7%`
  - `state_action_consistency`: `0.981`
  - `position_policy_delta`: `0.014`
  - `error_recovery_rate`: `0.597`

## Cost Read
- The prompt repair reduced pathological tail cost, but it did not lower average spend.
  - `FlashLite-RC-TR-HP-exit`: about `$0.002379` per player-match
  - `Flash-AO`: about `$0.002178` per player-match
- Why average cost rose anyway:
  - Flash-Lite won more often and pushed more matches deep
  - package average turns increased from Parity 3's `21.73` to `22.31`

## Execution Status
- Canonical run used:
  - `VERTEX_LOCATION=global`
  - same Flash retry/backoff profile as the recent Gemini packages
  - no gameplay change beyond the prompt exit clause
