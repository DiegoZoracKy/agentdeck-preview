# FixedDamage Mini Parity 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-mini-parity-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `openai:gpt-4o-mini`
- Seed Base: `12242`
- Topline Winner: `FlashLite-RC-TR-HP` by `41-7`
- Statistical Read: `p=6.24e-07`, medium effect, significant at `alpha=0.05`
- Position Read: first player won `27/48`; `FlashLite-RC-TR-HP` went `22/24` as first player and `19/24` as second
- Avg Turns: `22.40`
- Avg Duration (s): `23.97`
- Total Cost: `0.16189`
<!-- AUTO_FACTS:END -->

## Why This Exists
- Parity 3 showed that the full Flash-Lite strategy stack could beat plain Flash `31-17`, but still stopped just short of formal significance.
- The mechanism question is already answered well enough to keep this package single-cell.
- This package asks the cross-provider question:
  - does the same full Flash-Lite stack stay competitive against a stable Mini baseline?
- The key diagnostic is whether Flash-Lite's lower seat drift and better threshold behavior transfer outside the Gemini family.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gpt-4o-mini`
- Strategy conditions:
  - `FlashLite-RC-TR-HP` vs `Mini-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for `FlashLite-RC-TR-HP`
- Matches planned:
  - `48`
- Seed base:
  - `12242` to keep this package on a fresh schedule family

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
- If the Flash-Lite strategy advantages are general rather than opponent-specific, the full stack should stay competitive with Mini here too.
- The main diagnostic is whether Flash-Lite can keep its cleaner policy shape against a stronger cross-provider baseline.

## Results
- `FlashLite-RC-TR-HP` beat `Mini-AO` `41-7` at `N=48`.
- This is the strongest competitive result in the arc so far:
  - exact binomial `p=6.24e-07`
  - effect size `0.787` (`medium`)
- The result was not driven mainly by seat:
  - first player won `27/48`
  - `FlashLite-RC-TR-HP` still won `19/24` as second player
  - `Mini-AO` won only `2/24` as second player

### Confirmed Findings
- The full Flash-Lite stack decisively outperformed Mini on outcomes while keeping a cleaner, lower-drift policy:
  - `position_policy_delta`: `0.044` vs `0.077`
  - `state_action_consistency`: `0.961` vs `0.975`
  - `all_attack_match_rate`: `12.5%` vs `0.0%`
  - `error_recovery_rate`: `0.730` for `FlashLite-RC-TR-HP`
- The mechanism is visible in the state buckets:
  - at shared `80 HP / 3 potions`, `Mini-AO` used `POTION` `24/24` as first player and `24/24` as second
  - at the same state, `FlashLite-RC-TR-HP` attacked `48/48` as first player and `46/47` as second
- Flash-Lite kept its later, survival-grounded threshold:
  - at shared `20 HP / 3 potions`, it healed `19/23` as first player and `17/20` as second
  - at shared `20 HP / 1 potion`, it healed `17/20` as first player and `17/17` as second
- Mini almost never reached comparable critical-with-potions states because it spent potions much earlier:
  - first potion median `80 HP`
  - `0` critical-potion support turns in the exported profile

### Cost and Reliability
- Cost:
  - `FlashLite-RC-TR-HP`: `$0.10861` total, `$0.002263` per player-match
  - `Mini-AO`: `$0.05328` total, `$0.001110` per player-match
  - the Flash-Lite full stack cost about `2.04x` as much as plain Mini in this package
- Reliability:
  - both players were `100%` strict with `0` parse failures

### What AgentDeck Made Visible
- The headline `41-7` result says Lite crushed Mini.
- The behavioral layer shows why:
  - Mini's baseline policy spent potions immediately at `80 HP`, in both seats
  - Flash-Lite held potions until genuinely dangerous states and then healed consistently enough to stay alive through long exchanges
- So this package is not just “Lite beat Mini.”
  - it is “a tuned weaker model beat a plain cross-provider baseline because its action threshold was much better aligned to the game.”
