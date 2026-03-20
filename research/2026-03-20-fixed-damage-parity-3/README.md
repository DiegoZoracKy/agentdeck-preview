# FixedDamage Parity 3

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-parity-3`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `google:gemini-2.5-flash`
- Seed Base: `9242`
- Topline Winner: `FlashLite-RC-TR-HP` finished `31-17` over `Flash-AO`
- Statistical Read: `p=0.059`, small effect, not significant at `alpha=0.05`
- Position Read: first player won `35/48`; `FlashLite-RC-TR-HP` won `10/24` as second player vs `Flash-AO` `3/24`
- Avg Turns: `21.73`
- Avg Duration (s): `19.78`
- Total Cost: `0.20162`
<!-- AUTO_FACTS:END -->

## Why This Exists
- Threshold 1 showed that HP-threshold grounding fixed the residual seat-conditioned healing bug in Flash-Lite.
- That answered the mechanism question.
- This package asks only the competitive question:
  - can the full Flash-Lite strategy stack (`RC + TR + HP-grounding`) match plain Flash at a larger `N`?
- The key diagnostic is not only total wins, but whether Flash-Lite can improve its **second-player** win rate.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC-TR-HP` vs `Flash-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini 2.5 models
- Matches planned:
  - `48`
- Seed base:
  - `9242` to keep this package on a fresh schedule family

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

## Hypothesis
- The full Flash-Lite strategy stack should remain much more behaviorally coherent than the earlier reinforced-only condition.
- If that coherence is strong enough to lift second-player performance, the parity claim may become competitive rather than just behavioral.

## Results
- `FlashLite-RC-TR-HP` finished `31-17` over `Flash-AO` at `N=48`.
- This is the strongest competitive showing in the FixedDamage series so far, but it still stops just short of the pre-registered significance cutoff:
  - exact binomial `p=0.059`
  - effect size: `small`
- The primary diagnostic moved in the right direction.
  - `FlashLite-RC-TR-HP` won `21/24` as first player and `10/24` as second
  - `Flash-AO` won `14/24` as first player and only `3/24` as second
  - so the full stack did not erase position, but it materially improved the weaker model's second-player competitiveness

### Confirmed Findings
- The HP-threshold grounding fix held up at larger `N`.
  - `position_policy_delta` stayed low for `FlashLite-RC-TR-HP`: `0.043`
  - `state_action_consistency` stayed high: `0.947`
  - `all_attack_match_rate` stayed low: `10.4%`
  - `unused_potions_on_loss_rate` stayed below `Flash-AO`: `35.3%` vs `41.9%`
  - `error_recovery_rate` stayed well above `Flash-AO`: `0.563` vs `0.327`
- The healthy-state second-player bug stayed mostly fixed.
  - at shared `80 HP / 3 potions`, `FlashLite-RC-TR-HP` attacked `28/28` as first player and `23/24` as second
  - the old second-player panic-heal did not return at scale
- The critical-state behavior stayed much better than earlier reinforced-only runs, but some second-player hesitation remains.
  - at shared `20 HP / 3 potions`, `FlashLite-RC-TR-HP` used `POTION` `19/21` as first player and `18/26` as second
  - at shared `20 HP / 1 potion`, it used `POTION` `19/20` as first player and `17/19` as second
  - so the threshold is no longer inverted, but it is not perfectly symmetric yet
- `Flash-AO` remained more position-sensitive and less behaviorally stable in this cell.
  - `position_policy_delta`: `0.153`
  - `state_action_consistency`: `0.875`
  - `all_attack_match_rate`: `18.8%`
  - second-player wins: `3/24`

### Cost and Reliability
- The full Flash-Lite stack no longer kept a cost edge in this cell.
  - `FlashLite-RC-TR-HP`: about `$0.002123` per player-match
  - `Flash-AO`: about `$0.002078` per player-match
- Reliability still favored the full-stack Lite condition.
  - `FlashLite-RC-TR-HP`: `100%` strict, `0` parse failures
  - `Flash-AO`: `94.98%` strict, `26` recoverable non-strict turns, `0` parse failures

### What AgentDeck Made Visible
- Without the behavioral layer, this package would read as a near-significant `31-17` result and little more.
- The state-level evidence shows the more useful story:
  - the healthy-state seat bug stayed fixed
  - the critical-state hesitation shrank but did not fully disappear
  - second-player wins improved enough to make the competitive claim plausible, but not enough to remove position as the main remaining obstacle
- That is the practical value of the platform here:
  - not only whether the full strategy stack improved a cheaper model
  - but where the remaining gap still lives
