# FixedDamage Mini Baseline 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-mini-baseline-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `openai:gpt-4o-mini`
- Seed Base: `13242`
- Topline Winner: `Mini-AO` by `44-4`
- Statistical Read: `p=1.51e-09`, large effect, significant at `alpha=0.05`
- Position Read: first player won `28/48`; `FlashLite-AO` went `4/24` as first player and `0/24` as second
- Avg Turns: `18.17`
- Avg Duration (s): `13.47`
- Total Cost: `0.06281`
<!-- AUTO_FACTS:END -->

## Why This Exists
- Mini Parity 1 showed that the full Flash-Lite stack beat plain Mini `41-7`.
- That result still lacks the missing baseline control:
  - how would plain Flash-Lite have done against plain Mini?
- This package isolates that question before attributing the Mini result to tuning.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gpt-4o-mini`
- Strategy conditions:
  - `FlashLite-AO` vs `Mini-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for `FlashLite-AO`
- Matches planned:
  - `48`
- Seed base:
  - `13242` to keep this package on a fresh schedule family

## Primary Endpoints
- second-player win split
- `position_policy_delta`
- `first_potion_profile`
- state-level evidence at `80 HP / 3 potions`
- `unused_potions_on_loss_rate`
- `state_action_consistency`

## Secondary Endpoints
- total win rate
- cost
- latency
- strict contract rate

## Hypothesis
- If Mini's default policy is simply bad in this game, plain Flash-Lite may already beat it comfortably.
- If plain Flash-Lite does not beat Mini clearly, the `41-7` tuned result can be attributed much more strongly to the Flash-Lite strategy stack.

## Results
- `Mini-AO` beat `FlashLite-AO` `44-4` at `N=48`.
- This is the opposite of the tuned Mini result and it is statistically clean:
  - exact binomial `p=1.51e-09`
  - effect size `0.985` (`large`)
- The control result means the tuned `41-7` Mini package was not just Mini being weak against any opponent.
  - plain Flash-Lite lost badly
  - tuned Flash-Lite then won decisively against the same plain Mini baseline

### Confirmed Findings
- Plain Flash-Lite was far too aggressive and inconsistent against Mini:
  - `all_attack_match_rate`: `45.8%`
  - `never_used_rate`: `45.8%`
  - `unused_potions_on_loss_rate`: `93.2%`
  - `critical_potion_response_rate`: `0.203`
  - `error_recovery_rate`: `0.259`
- Mini was not simply unbeatable or intrinsically stronger in this game.
  - its own policy still showed the same early-heal tendency
  - first potion median stayed at `80 HP`
  - at shared `80 HP / 3 potions`, Mini healed in `14/28` first-player turns and `24/24` second-player turns
- The tuned stack changed the matchup completely:
  - outcome swing from `4-44` to `41-7`
  - Flash-Lite second-player wins from `0/24` to `19/24`
  - Flash-Lite `position_policy_delta` from `0.169` to `0.044`
  - Flash-Lite `critical_potion_response_rate` from `0.203` to `0.513`

### Cost and Reliability
- Cost:
  - `FlashLite-AO`: `$0.02266` total, `$0.000472` per player-match
  - `Mini-AO`: `$0.04014` total, `$0.000836` per player-match
  - plain Flash-Lite was cheaper than plain Mini, but much worse
- Reliability:
  - both players were `100%` strict with `0` parse failures

### What AgentDeck Made Visible
- The baseline package closes the causal gap in the Mini story.
- Without it, `41-7` could be read as “Mini is just bad.”
- With it, the interpretation is sharper:
  - plain Flash-Lite loses badly because it attacks through critical states and often dies holding potions
  - the tuned Flash-Lite stack reverses that exact failure mode and flips the matchup completely
