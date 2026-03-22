# FixedDamage OpenAI Margin 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-22-fixed-damage-openai-margin-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `96/96`
- Game: `FixedDamageGame`
- Players: `openai:gpt-4o-mini`, `openai:gpt-5-mini`
- Seed Base: `18242`
- Topline Read:
  - control cell: `GPT5Mini-AO` beat `GPT4oMini-RC-TR-HP` `27-21`
  - margin cell: `GPT5Mini-AO` beat `GPT4oMini-RC-TR-MARGIN` `30-18`
- Avg Turns: `24.07`
- Avg Duration (s): `129.02`
- Total Cost: `1.90469`
<!-- AUTO_FACTS:END -->

## Why This Exists
- OpenAI Parity 2 had already narrowed the `gpt-4o-mini` problem:
  - the obvious `80 HP / 3 potions` second-player bug was gone
  - but the full stack still stayed too aggressive at `30 HP / 2 potions`
  - and it still converted `0/24` second-player wins against plain `gpt-5-mini`
- This package is the final FixedDamage mechanism probe for that ladder.
- It tests one last targeted idea with a within-package control:
  - existing `GPT4oMini-RC-TR-HP` vs `GPT5Mini-AO`
  - new `GPT4oMini-RC-TR-MARGIN` vs `GPT5Mini-AO`

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gpt-4o-mini`
  - `gpt-5-mini`
- Strategy conditions:
  - `GPT4oMini-RC-TR-HP` vs `GPT5Mini-AO`
  - `GPT4oMini-RC-TR-MARGIN` vs `GPT5Mini-AO`
- Turn-time prompt difference:
  - control: existing HP-grounding reminder
  - margin variant: forward-projected exchange check, replacing the old HP reminder rather than stacking on top of it
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `48` per cell, `96` total
- Seed base:
  - `18242`

## Primary Endpoints
- second-player win split
- `position_policy_delta`
- state-level evidence at `80 HP / 3 potions`, `30 HP / 2 potions`, `20 HP / 3 potions`, and `20 HP / 1 potion`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`

## Secondary Endpoints
- total win rate
- cost
- latency
- strict contract rate

## Hypothesis
- If the last real failure in the full stack is the `30 HP / 2 potions` exchange-margin mistake, then a forward-projected calculation should improve second-player conversion without reintroducing the old healthy-state over-heal bug.

## Results
- Control cell:
  - `GPT5Mini-AO` beat `GPT4oMini-RC-TR-HP` `27-21` at `N=48`
  - exact binomial `p=0.4709`
  - effect size `0.125` (`negligible`)
- Margin cell:
  - `GPT5Mini-AO` beat `GPT4oMini-RC-TR-MARGIN` `30-18` at `N=48`
  - exact binomial `p=0.1114`
  - effect size `0.253` (`small`)
- So the new prompt did not improve the competitive result. It made it worse.

### Confirmed Findings
- The within-package control cleanly reproduced the prior full-stack result on a fresh seed family.
  - prior full stack: `27-21`
  - this control cell: `27-21`
  - `GPT4oMini-RC-TR-HP` again won `0/24` as second player
- The margin prompt fixed the exact local state it was designed to target.
  - at `30 HP / 2 potions`, control `gpt-4o-mini` attacked:
    - `20/26` as first player
    - `36/41` as second player
  - with the margin prompt, those became:
    - `5/23` as first player
    - `1/23` as second player
- The prompt also preserved the already-fixed healthy-state behavior.
  - at `80 HP / 3 potions`, control second player attacked `23/24`
  - margin second player attacked `24/24`
- But the primary endpoint did not move:
  - `GPT4oMini-RC-TR-HP` won `0/24` as second player
  - `GPT4oMini-RC-TR-MARGIN` also won `0/24` as second player
- And some broader behavioral metrics got worse even while the target bucket improved.
  - `position_policy_delta`: `0.048 -> 0.077`
  - `unused_potions_on_loss_rate`: `18.5% -> 23.3%`
  - `error_recovery_rate`: `0.601 -> 0.573`
  - first-player `20 HP / 3 potions` attacks increased `2/15 -> 5/21`
- The clean read is:
  - the new prompt fixed a real local mistake
  - but it over-corrected the policy and did not solve second-player conversion

### Cost and Reliability
- Cost:
  - control cell:
    - `GPT4oMini-RC-TR-HP`: `$0.17447` total, `$0.003635` per player-match
    - `GPT5Mini-AO`: `$0.79330` total, `$0.016527` per player-match
  - margin cell:
    - `GPT4oMini-RC-TR-MARGIN`: `$0.18742` total, `$0.003905` per player-match
    - `GPT5Mini-AO`: `$0.74950` total, `$0.015615` per player-match
  - both `gpt-4o-mini` stacks stayed about `4x` cheaper than plain `gpt-5-mini`
- Reliability:
  - both cells were `100%` strict with `0` parse failures

### What AgentDeck Made Visible
- Without the behavioral layer, this package would look like a simple “new prompt did not help” result.
- The state buckets show something more useful:
  - the prompt worked exactly where it was aimed
  - but fixing one bucket was not enough to improve the whole policy
  - the limiting factor in this ladder is no longer formatting, high-HP panic healing, or obvious one-hit lethality checks
  - it is the model’s ability to convert the harder seat into wins under broader medium-to-low HP pressure
- That makes this package a real stopping point:
  - the OpenAI FixedDamage branch is now saturated enough to move on
  - the next useful game should add more uncertainty, not more prompt micro-variants to the same deterministic threshold problem
