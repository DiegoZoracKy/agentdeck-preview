# FixedDamage OpenAI Parity 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-21-fixed-damage-openai-parity-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `96/96`
- Game: `FixedDamageGame`
- Players: `openai:gpt-4o-mini`, `openai:gpt-5-mini`
- Seed Base: `16242`
- Baseline Read: `GPT5Mini-AO` beat `GPT4oMini-AO` `29-19`
- Baseline Statistics: `p=0.193`, small effect, not significant at `alpha=0.05`
- RC Read: `GPT5Mini-AO` beat `GPT4oMini-RC` `40-8`
- RC Statistics: `p=3.31e-06`, medium effect, significant at `alpha=0.05`
- Position Read:
  - baseline first player won `41/48`
  - RC cell first player won `32/48`, but `GPT4oMini-RC` still went `0/24` as second player
- Total Cost: `1.57631`
<!-- AUTO_FACTS:END -->

## Why This Exists
- We already know three things in FixedDamage:
  - tuned `FlashLite` beats plain `gpt-4o-mini`
  - tuned `FlashLite` stays competitive with plain Flash
  - tuned `FlashLite` loses directionally to plain `gpt-5-mini`
- The missing OpenAI-only ladder is:
  - plain `gpt-4o-mini` vs plain `gpt-5-mini`
  - then `gpt-4o-mini` with `ReasoningController` vs plain `gpt-5-mini`
- This package asks whether RC alone is enough to move the cheaper OpenAI mini meaningfully toward the stronger plain OpenAI mini baseline.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
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
  - `48` per cell
- Seed base:
  - `16242`

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
- If the main `gpt-4o-mini` failure is policy-shaped rather than capability-shaped, then `ReasoningController` alone should close meaningful ground against plain `gpt-5-mini`.

## Results
- Baseline:
  - `GPT5Mini-AO` beat `GPT4oMini-AO` `29-19` at `N=48`
  - exact binomial `p=0.193`
  - effect size `0.210` (`small`)
  - this is a directional edge for `gpt-5-mini`, not a formal outcome gap claim
- RC-only:
  - `GPT5Mini-AO` beat `GPT4oMini-RC` `40-8` at `N=48`
  - exact binomial `p=3.31e-06`
  - effect size `0.730` (`medium`)
  - this is a clear failure for the RC-only intervention

### Confirmed Findings
- Plain `gpt-4o-mini` was closer to plain `gpt-5-mini` than the RC-only variant:
  - `19` wins for `GPT4oMini-AO`
  - only `8` wins for `GPT4oMini-RC`
- The baseline weakness was the expected seat-conditioned early-heal rule:
  - at shared `80 HP / 3 potions`, `GPT4oMini-AO` attacked `24/24` as first player
  - in that same state as second player, it healed `24/24`
- `ReasoningController` partially fixed that high-HP seat bug:
  - at shared `80 HP / 3 potions`, `GPT4oMini-RC` attacked `24/25` as first player and `15/24` as second
- But RC introduced a much worse survival policy:
  - `all_attack_match_rate`: `0.0%` -> `18.75%`
  - `unused_potions_on_loss_rate`: `17.2%` -> `60.0%`
  - `critical_potion_response_rate`: `0.550` -> `0.363`
  - `error_recovery_rate`: `0.531` -> `0.336`
- RC also failed completely in the harder seat:
  - `GPT4oMini-RC` won `8/24` as first player
  - `0/24` as second player

### Cost and Reliability
- Baseline costs:
  - `GPT4oMini-AO`: `$0.06009` total, `$0.001252` per player-match
  - `GPT5Mini-AO`: `$0.70033` total, `$0.014590` per player-match
  - plain `gpt-5-mini` cost about `11.7x` as much as plain `gpt-4o-mini`
- RC-only costs:
  - `GPT4oMini-RC`: `$0.09907` total, `$0.002064` per player-match
  - `GPT5Mini-AO`: `$0.71682` total, `$0.014934` per player-match
  - plain `gpt-5-mini` still cost about `7.2x` as much as RC-only `gpt-4o-mini`
- Reliability:
  - AO baseline: `100%` strict overall, `1` parse failure total
  - RC cell: `99.9%` strict overall, `1` parse failure total

### What AgentDeck Made Visible
- The headline results alone would suggest a simple story:
  - plain `gpt-5-mini` is somewhat better than plain `gpt-4o-mini`
  - RC-only `gpt-4o-mini` is much worse
- The behavioral layer shows why:
  - the baseline `gpt-4o-mini` problem was an obvious seat-conditioned threshold bug at high HP
  - RC softened that exact bug
  - but replaced it with a worse pattern of low-HP indecision, all-attack/no-heal collapses, and poor recovery after missed defensive turns
- That is the load-bearing insight from this package:
  - the intervention did move the policy
  - it just moved it in the wrong direction for this game
