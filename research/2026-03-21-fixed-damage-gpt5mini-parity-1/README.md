# FixedDamage GPT-5 Mini Parity 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-21-fixed-damage-gpt5mini-parity-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `openai:gpt-5-mini`
- Seed Base: `15242`
- Topline Winner: `GPT5Mini-AO` by `28-20`
- Statistical Read: `p=0.312`, negligible effect, not significant at `alpha=0.05`
- Position Read: first player won `44/48`; `FlashLite-RC-TR-HP` went `20/24` as first player and `0/24` as second
- Avg Turns: `22.42`
- Avg Duration (s): `105.82`
- Total Cost: `0.80113`
<!-- AUTO_FACTS:END -->

## Why This Exists
- The full Flash-Lite stack already did two important things in FixedDamage:
  - it beat plain `gpt-4o-mini` decisively
  - it stayed competitive with plain `gemini-2.5-flash`
- This package asks the next rung question:
  - can the same tuned Flash-Lite stack stay competitive against plain `gpt-5-mini`?
- The broader goal is to test whether strategy stack can offset base-model differences against a stronger plain OpenAI mini baseline that does not share `gpt-4o-mini`'s early-heal pathology.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gpt-5-mini`
- Strategy conditions:
  - `FlashLite-RC-TR-HP` vs `GPT5Mini-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for `FlashLite-RC-TR-HP`
- Matches planned:
  - `48`
- Seed base:
  - `15242` to keep this package on a fresh schedule family

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
- If the Flash-Lite strategy stack is general enough, it should stay competitive with plain `gpt-5-mini`.
- The key diagnostic is whether Flash-Lite keeps the cleaner threshold behavior and lower seat drift that made it strong in the earlier parity packages.

## Results
- `GPT5Mini-AO` beat `FlashLite-RC-TR-HP` `28-20` at `N=48`.
- This is a directional loss for Flash-Lite, not a clean inferential result:
  - exact binomial `p=0.312`
  - effect size `0.167` (`negligible`)
- The matchup was heavily position-dominated:
  - first player won `44/48`
  - `FlashLite-RC-TR-HP` won `20/24` as first player and `0/24` as second
  - `GPT5Mini-AO` won `24/24` as first player and `4/24` as second

### Confirmed Findings
- `gpt-5-mini` is a much stronger plain baseline than `gpt-4o-mini` in this game:
  - at shared `80 HP / 3 potions`, `GPT5Mini-AO` attacked `24/24` as first player and `23/24` as second
  - this is not another “Mini heals immediately at 80 HP” matchup
- Flash-Lite remained the cleaner, lower-drift policy:
  - `position_policy_delta`: `0.0159` vs `0.1403`
  - `state_action_consistency`: `0.9680` vs `0.8677`
  - both players were `100%` strict with `0` parse failures
- GPT-5 Mini still had the stronger survival behavior:
  - `critical_potion_response_rate`: `0.5571` vs `0.3958`
  - `error_recovery_rate`: `0.6304` vs `0.5122`
  - `all_attack_match_rate`: `6.25%` vs `20.83%`
- Flash-Lite's threshold fix held, but it did not produce second-player wins:
  - at shared `20 HP / 1 potion`, Flash-Lite healed `20/20` as first player and `18/19` as second
  - at shared `20 HP / 3 potions`, Flash-Lite healed `20/30` as first player and `18/28` as second
  - despite that, it still went `0/24` as second player in the package

### Cost and Reliability
- Cost:
  - `FlashLite-RC-TR-HP`: `$0.11202` total, `$0.002334` per player-match
  - `GPT5Mini-AO`: `$0.68911` total, `$0.014356` per player-match
  - plain `gpt-5-mini` cost about `6.15x` as much as the full Flash-Lite stack in this package
- Reliability:
  - both players were `100%` strict with `0` parse failures

### What AgentDeck Made Visible
- The headline `28-20` result alone says Flash-Lite lost directionally to `gpt-5-mini`.
- The behavioral layer shows the more important distinction:
  - Flash-Lite is now a cleaner policy than the opponent
  - but `gpt-5-mini` is still the stronger survival policy in this game
- That matters because it is not the same failure mode as the earlier `gpt-4o-mini` baseline.
  - the old early-heal bug is gone
  - the remaining gap is about converting low-HP states and second-player games against a stronger defender

