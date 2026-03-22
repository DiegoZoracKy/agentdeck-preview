# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): `48` total matches in one cell
- Decisive matches: `48`
- Draws: `0`
- Win rates: `GPT5Mini-AO` finished `27-21` over `GPT4oMini-RC-TR-HP`
- Statistical read: `p=0.4709`, negligible effect, not significant at `alpha=0.05`
- Position read: first player won `45/48`; `GPT4oMini-RC-TR-HP` won `21/24` as first player and `0/24` as second
- Strict contract rate: `1.0000` overall
- Artifact validation: all exported matches passed
- Average turns: `24.60`
- Average duration (s): `114.45`
- Total cost: `0.92794`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: the full `gpt-4o-mini` stack recovered dramatically from the RC-only failure, but it still lost directionally to plain `gpt-5-mini`, `21-27`, without reaching parity.
- Statistical finding: the outcome stayed non-significant (`p=0.4709`), so this is not evidence that plain `gpt-5-mini` is decisively better in this seed family.
- Mechanism finding: the full stack fixed the obvious high-HP second-player heal bug and restored sane critical healing, but it still produced `0/24` second-player wins because medium-to-low HP aggression remained too high in the harder seat.
- Practical read: this is a strong recovery result, not a win result. The full stack made `gpt-4o-mini` competitive again and kept it much cheaper than `gpt-5-mini`, but it did not cross into true parity.

## Outcome Readout
- `GPT5Mini-AO` beat `GPT4oMini-RC-TR-HP` `27-21` at `N=48`.
- The inferential read is null:
  - exact binomial `p=0.4709`
  - effect size `0.125` (`negligible`)
- The important comparison is to the earlier OpenAI ladder:
  - AO baseline: `19-29`
  - RC-only: `8-40`
  - full stack: `21-27`
- So the full stack recovered the matchup from the RC collapse and slightly improved over the plain baseline, but not enough to flip the result.

## Position-Controlled Results
- This package was extremely first-player dominated:
  - first player won `45/48`
  - upset rate: `3/48`
- `GPT4oMini-RC-TR-HP` was strong only from the advantaged seat:
  - `21/24` as first player
  - `0/24` as second player
- `GPT5Mini-AO` was perfect as first player and still converted a few second-player games:
  - `24/24` as first player
  - `3/24` as second player
- So the remaining gap is not broad policy collapse. It is second-player conversion.

## Behavioral Endpoints
- The full stack made `gpt-4o-mini` much cleaner than RC-only:
  - `all_attack_match_rate`: `18.75% -> 0.0%`
  - `first_potion_profile.median_first_potion_hp`: `40 -> 20`
  - `critical_potion_response_rate`: `0.363 -> 0.444`
  - `error_recovery_rate`: `0.336 -> 0.494`
  - `unused_potions_on_loss_rate`: `0.600 -> 0.185`
  - `position_policy_delta`: `0.149 -> 0.060`
- It also improved over the plain baseline on the metrics that matter most for this game:
  - first potion median `60 -> 20`
  - `position_policy_delta` `0.324 -> 0.060`
- The remaining weakness is that plain `gpt-5-mini` still has the better survival policy:
  - `critical_potion_response_rate`: `0.631` vs `0.444`
  - `error_recovery_rate`: `0.563` vs `0.494`
  - `unused_potions_on_loss_rate`: `0.0%` vs `18.5%`
- So the full stack repaired `gpt-4o-mini` enough to be competitive again, but not enough to become the stronger defender.

## Threshold-State Evidence
- The original high-HP seat bug is effectively gone:
  - at `80 HP / 3 potions`, `GPT4oMini-RC-TR-HP`:
    - first player: `ATTACK` `24/25`
    - second player: `ATTACK` `24/24`
  - compare that with the plain baseline:
    - `GPT4oMini-AO` first player: `ATTACK` `24/24`
    - `GPT4oMini-AO` second player: `POTION` `24/24`
- Critical low-HP healing is also much better:
  - at `20 HP / 3 potions`, `GPT4oMini-RC-TR-HP`:
    - first player: `POTION` `15/15`
    - second player: `POTION` `17/18`
- The remaining error is subtler:
  - at `20 HP / 1 potion` as second player:
    - `ATTACK` `6/22`
    - `POTION` `16/22`
  - at `30 HP / 2 potions`:
    - first player: `ATTACK` `21/29`
    - second player: `ATTACK` `41/49`
- That makes the failure mode much narrower than before:
  - not “heal at 80”
  - but “stay too aggressive after the obvious one-hit check has already been passed”

## Cost, Latency, and Reliability
- Cost:
  - `GPT4oMini-RC-TR-HP`: `$0.17777` total, `$0.003703` per player-match
  - `GPT5Mini-AO`: `$0.75017` total, `$0.015629` per player-match
  - plain `gpt-5-mini` cost about `4.2x` as much as the full `gpt-4o-mini` stack
- Relative to OpenAI Parity 1:
  - AO baseline `gpt-4o-mini`: `$0.001252` per player-match
  - RC-only `gpt-4o-mini`: `$0.002064` per player-match
  - full stack `gpt-4o-mini`: `$0.003703` per player-match
- So the full stack is materially more expensive than AO or RC-only, but still far cheaper than plain `gpt-5-mini`.
- Latency:
  - average duration: `114.45s` per match
  - this is roughly in line with the other `gpt-5-mini` packages and still materially slower than weak-tier baselines
- Reliability:
  - both players were `100%` strict with `0` parse failures
- So once again, the limiting factor is not formatting or parseability. It is policy quality.

## Interpretation
- This package closes the OpenAI FixedDamage ladder cleanly.
- The honest conclusion is:
  - full-stack `gpt-4o-mini` is far better than RC-only `gpt-4o-mini`
  - it is slightly better than plain `gpt-4o-mini`
  - it is still not enough to beat plain `gpt-5-mini`
- The most useful claim is not the null win-rate result.
- It is that AgentDeck localized the intervention boundary:
  - RC-only changed the policy in the wrong direction
  - RC+TR+HP repaired that and made the cheaper model competitive again
  - but the last remaining obstacle is second-player endgame aggression, not the old opening-seat threshold bug

## Limitations
- This is still one seed family.
- First-player dominance was extreme (`45/48`), which makes the second-player split more informative than the headline total.
- The package compares one full-stack condition to one plain baseline. It does not test whether a narrower, cheaper reminder could preserve most of the gains.
- FixedDamage remains a local sequential decision task, so transfer claims are strongest for similar task classes.

## Next Steps
- For FixedDamage specifically, this OpenAI branch is probably done.
- The package answered the important question:
  - the full stack helps a lot
  - but not enough to beat plain `gpt-5-mini`
- If we keep pushing in FixedDamage, the next intervention would have to target the residual second-player `30 HP / 2 potions` aggression directly.
- My recommendation is to stop the OpenAI ladder here and move on once the remaining FixedDamage controls are complete.
