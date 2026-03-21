# FixedDamage Ablation 2

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-21-fixed-damage-ablation-2`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `google:gemini-2.5-flash`
- Seed Base: `14242`
- Topline Read:
  - `Flash-AO` beat `FlashLite-AO-HP` `24-0`
  - `Flash-AO` beat `FlashLite-AO-TR-HP` `18-6`
- Package Cost: `0.10078`
- Avg Turns: `16.83`
- Avg Duration (s): `14.46`
<!-- AUTO_FACTS:END -->

## Why This Exists
- The full Flash-Lite stack (`RC + TR + HP`) became competitive with plain Flash, but it was much more expensive than plain Flash-Lite.
- This package asks the cheaper strategy question:
  - can ActionOnly prompting overlays recover most of the same gains?
- The two ablations isolate that:
  - HP-threshold grounding without turn reinforcement
  - HP-threshold grounding with turn-time ActionOnly reinforcement

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-AO-HP` vs `Flash-AO`
  - `FlashLite-AO-TR-HP` vs `Flash-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini models
- Matches planned:
  - `24` per cell
- Seed base:
  - `14242`

## Primary Endpoints
- second-player win split
- `position_policy_delta`
- state-level evidence at `80 HP / 3 potions`, `20 HP / 3 potions`, and `20 HP / 1 potion`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`

## Secondary Endpoints
- total win rate
- cost
- latency
- strict contract rate

## Results
- `Flash-AO` beat `FlashLite-AO-HP` `24-0` at `N=24`.
  - exact binomial `p=1.19e-07`
  - effect size `1.571` (`large`)
- `Flash-AO` beat `FlashLite-AO-TR-HP` `18-6` at `N=24`.
  - exact binomial `p=0.0227`
  - effect size `0.524` (`medium`)

## Confirmed Findings
- HP-threshold grounding alone failed completely.
  - `FlashLite-AO-HP` lost from both seats: `0/12` as first player, `0/12` as second.
  - It regressed into a mixed but still pathological policy:
    - `all_attack_match_rate`: `66.7%`
    - first potion median: `80 HP`
    - `never_used_rate`: `66.7%`
    - `unused_potions_on_loss_rate`: `87.5%`
    - `critical_potion_response_rate`: `0.082`
    - `error_recovery_rate`: `0.123`
- Turn reinforcement on top of HP-grounding helped, but not enough.
  - `FlashLite-AO-TR-HP` improved to `6/24` wins overall and `6/12` wins as first player, but still `0/12` as second player.
  - Behavioral gains over HP-only were real:
    - `all_attack_match_rate`: `66.7%` -> `29.2%`
    - first potion median: `80 HP` -> `20 HP`
    - `position_policy_delta`: `0.183` -> `0.079`
    - `critical_potion_response_rate`: `0.082` -> `0.241`
    - `error_recovery_rate`: `0.123` -> `0.392`
- The cheap overlays still fell far short of the full stack.
  - Best known full stack (`FlashLite-RC-TR-HP`) from Parity 3:
    - beat `Flash-AO` `31-17`
    - `all_attack_match_rate`: `10.4%`
    - `unused_potions_on_loss_rate`: `35.3%`
    - `critical_potion_response_rate`: `0.434`
    - `error_recovery_rate`: `0.563`
  - So `ActionOnly + TR + HP` recovered part of the behavior, but not the competitive result.

## Concrete State Evidence
- At `80 HP / 3 potions`, HP-only still made the old healthy-state second-player mistake:
  - `FlashLite-AO-HP` as second player: `POTION` `5/12`
  - `FlashLite-AO-TR-HP` as second player: `POTION` `2/12`
- At `20 HP / 3 potions`, the cheap overlays still failed the real low-HP test:
  - `FlashLite-AO-HP` first player: `ATTACK` `17/17`
  - `FlashLite-AO-HP` second player: `ATTACK` `7/9`
  - `FlashLite-AO-TR-HP` first player: `ATTACK` `7/14`, `POTION` `7/14`
  - `FlashLite-AO-TR-HP` second player: `ATTACK` `10/15`, `POTION` `5/15`
- At `20 HP / 1 potion`, the reinforced ActionOnly cell was still far from the full stack:
  - `FlashLite-AO-TR-HP` first player: `ATTACK` `9/9`
  - `FlashLite-AO-TR-HP` second player: `ATTACK` `6/8`, `POTION` `2/8`

## Cost and Reliability
- Cost:
  - `FlashLite-AO-HP`: `$0.01170` total, `$0.000488` per player-match
  - `FlashLite-AO-TR-HP`: `$0.01841` total, `$0.000767` per player-match
  - `FlashLite-RC-TR-HP` from Parity 3: `$0.10190` total, `$0.002123` per player-match
  - So `FlashLite-AO-TR-HP` kept only about `36%` of the full-stack cost, but it also lost most of the full-stack performance.
- Reliability:
  - both Flash-Lite ablations stayed `100%` strict with `0` parse failures
  - `Flash-AO` remained fully parseable but not fully strict:
    - `89.2%` strict in the HP-only cell
    - `89.9%` strict in the reinforced cell

## What AgentDeck Made Visible
- The cheap ActionOnly overlays were not just “weaker versions” of the full stack.
- The behavioral layer shows a more precise story:
  - HP-only preserved some healthy-state aggression but never formed a reliable critical-state healing policy
  - turn reinforcement helped keep the HP hint active, but still did not produce the same low-HP threshold discipline as ReasoningController
- So in this task class, `ReasoningController` is carrying real policy value, not just formatting overhead.
