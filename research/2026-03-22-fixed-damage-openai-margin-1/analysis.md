# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): `96` total matches across `2` cells
- Decisive matches: `96`
- Draws: `0`
- Win rates: control `GPT5Mini-AO` `27-21` over `GPT4oMini-RC-TR-HP`; margin `GPT5Mini-AO` `30-18` over `GPT4oMini-RC-TR-MARGIN`
- Topline read: the margin prompt fixed the targeted `30 HP / 2 potions` error but did not create second-player wins and worsened the outcome cell
- Strict contract rate: `1.0000` overall
- Artifact validation: all exported matches passed
- Average turns: `24.07`
- Average duration (s): `129.02`
- Total cost: `1.90469`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- This package is the final OpenAI FixedDamage mechanism probe.
- It compares the existing full-stack `gpt-4o-mini` control against one last targeted prompt variant.
- The question is narrow: can a forward-projected HP-margin reminder fix the residual `30 HP / 2 potions` aggression enough to create second-player wins against plain `gpt-5-mini`?
- The answer is no. The new prompt fixed the local state, but it did not create any second-player wins and it worsened the overall result.

## Cell Readout
- `p1_c01_gpt4omini_rc_tr_hp_vs_gpt5mini_ao`:
  - `GPT5Mini-AO` beat `GPT4oMini-RC-TR-HP` `27-21`
  - exact binomial `p=0.4709`
  - effect size `0.125` (`negligible`)
  - this exactly reproduces the prior full-stack result on a fresh seed family
- `p1_c02_gpt4omini_rc_tr_margin_vs_gpt5mini_ao`:
  - `GPT5Mini-AO` beat `GPT4oMini-RC-TR-MARGIN` `30-18`
  - exact binomial `p=0.1114`
  - effect size `0.253` (`small`)
  - so the new prompt moved the cell in the wrong direction
- The ladder therefore closes as:
  - AO baseline: `19-29`
  - RC-only: `8-40`
  - full stack: `21-27`
  - margin probe: `18-30`
- The full stack remains the best `gpt-4o-mini` condition we found for FixedDamage.

## Position-Controlled Results
- Control cell:
  - first player won `45/48`
  - `GPT4oMini-RC-TR-HP`: `21/24` as first player, `0/24` as second
  - `GPT5Mini-AO`: `24/24` as first player, `3/24` as second
- Margin cell:
  - first player won `42/48`
  - `GPT4oMini-RC-TR-MARGIN`: `18/24` as first player, `0/24` as second
  - `GPT5Mini-AO`: `24/24` as first player, `6/24` as second
- The primary endpoint therefore did not move at all:
  - second-player wins for the `gpt-4o-mini` side stayed `0/24` in both cells
- That is the real stop signal for this branch. The bottleneck is not sample size anymore. It is second-player conversion.

## Behavioral Endpoints
- Relative to RC-only, the control cell still shows why the full stack mattered:
  - `all_attack_match_rate`: `0.1875 -> 0.0417`
  - `critical_potion_response_rate`: `0.363 -> 0.471`
  - `error_recovery_rate`: `0.336 -> 0.601`
  - `unused_potions_on_loss_rate`: `0.600 -> 0.185`
- The margin probe improved the targeted aggression bucket, but not the whole policy:
  - `30 HP / 2 potions` second-player attack rate: `0.878 -> 0.043`
  - `critical_potion_response_rate`: `0.471 -> 0.508`
  - `state_action_consistency`: `0.929 -> 0.929` (effectively unchanged)
- But broader readouts moved the wrong way:
  - `position_policy_delta`: `0.048 -> 0.077`
  - `unused_potions_on_loss_rate`: `0.185 -> 0.233`
  - `error_recovery_rate`: `0.601 -> 0.573`
  - `all_attack_match_rate`: `0.042 -> 0.063`
- So the margin prompt did not produce a stronger overall survival policy. It produced a more conservative local response in one band while leaving the match-conversion problem unresolved.

## Threshold-State Evidence
- The healthy-state bug stayed fixed in both cells.
  - control at `80 HP / 3 potions`:
    - first player: `ATTACK` `24/24`
    - second player: `ATTACK` `23/24`
  - margin at `80 HP / 3 potions`:
    - first player: `ATTACK` `25/25`
    - second player: `ATTACK` `24/24`
- The prompt hit the exact target state hard.
  - control at `30 HP / 2 potions`:
    - first player: `ATTACK` `20/26`
    - second player: `ATTACK` `36/41`
  - margin at `30 HP / 2 potions`:
    - first player: `ATTACK` `5/23`
    - second player: `ATTACK` `1/23`
- But that local fix did not turn into better endgame conversion.
  - control at `20 HP / 1 potion` as second player:
    - `ATTACK` `2/22`
    - `POTION` `20/22`
  - margin in the same state:
    - `ATTACK` `3/18`
    - `POTION` `15/18`
  - control at `20 HP / 3 potions` as first player:
    - `ATTACK` `2/15`
    - `POTION` `13/15`
  - margin in the same state:
    - `ATTACK` `5/21`
    - `POTION` `16/21`
- The resulting interpretation is precise:
  - the margin instruction solved the `30 -> 10` forward-projection problem
  - but it did not solve the whole second-player policy
  - and it likely over-corrected enough medium-low HP states to hurt the total result

## Cost, Latency, and Reliability
- Cost:
  - control cell:
    - `GPT4oMini-RC-TR-HP`: `$0.17447` total, `$0.003635` per player-match
    - `GPT5Mini-AO`: `$0.79330` total, `$0.016527` per player-match
  - margin cell:
    - `GPT4oMini-RC-TR-MARGIN`: `$0.18742` total, `$0.003905` per player-match
    - `GPT5Mini-AO`: `$0.74950` total, `$0.015615` per player-match
- Relative to the earlier OpenAI ladder:
  - AO baseline `gpt-4o-mini`: `$0.001252` per player-match
  - RC-only `gpt-4o-mini`: `$0.002064` per player-match
  - full stack control: `$0.003635` per player-match
  - margin probe: `$0.003905` per player-match
- So the new prompt cost a bit more than the existing full stack and still stayed about `4x` cheaper than plain `gpt-5-mini`.
- Reliability:
  - all exported turns were parseable
  - both cells stayed `100%` strict
- The failure mode in this package is entirely behavioral, not formatting-related.

## Interpretation Notes
- Cell artifacts are the primary inferential unit in this package. Top-level pooled player win rates mix two different `gpt-4o-mini` strategy conditions and should not be read as one matchup.
- The control cell confirms the prior full-stack read on a fresh seed family.
- The margin cell answers the only remaining mechanism question:
  - yes, the targeted prompt can fix the residual `30 HP / 2 potions` bucket
  - no, that local fix is not enough to produce second-player wins or a better overall parity result

## Interpretation
- This package closes the OpenAI FixedDamage ladder cleanly.
- The honest conclusion is:
  - RC-only hurt `gpt-4o-mini`
  - RC+TR+HP repaired that and made it competitive again
  - the final targeted prompt fixed the exact `30 HP / 2 potions` state it was designed for
  - but even that fix could not produce second-player wins or a better overall result
- That makes the boundary of this game clear:
  - for `gpt-4o-mini`, FixedDamage is no longer blocked by the old high-HP seat bug
  - it is blocked by broader second-player conversion under medium-to-low HP pressure
  - more prompt micro-tuning inside this game is likely to have diminishing returns

## Limitations
- This is still one seed family.
- Both cells remain highly first-player dominated, which is why second-player conversion is the primary diagnostic here.
- The package compares two `gpt-4o-mini` strategies against one plain `gpt-5-mini` baseline. It does not test other models or other games.
- FixedDamage remains a local sequential decision task, so transfer claims are strongest for similar constrained task classes.

## Next Steps
- For FixedDamage specifically, this OpenAI branch is done.
- The package answered the last meaningful question:
  - the full stack is real value
  - the targeted margin prompt fixed a genuine local failure
  - but the branch still cannot beat plain `gpt-5-mini`
- The right next move is not another OpenAI prompt tweak in FixedDamage.
- It is to take the broader lessons from this game into the next game class, where uncertainty and non-deterministic damage can test whether the strategy-stack story transfers.
