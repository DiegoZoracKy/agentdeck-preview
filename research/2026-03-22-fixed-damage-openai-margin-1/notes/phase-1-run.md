# Phase 1 Run Notes

## Purpose
- Run the final FixedDamage OpenAI mechanism probe with a within-package control:
  - `GPT4oMini-RC-TR-HP` vs `GPT5Mini-AO`
  - `GPT4oMini-RC-TR-MARGIN` vs `GPT5Mini-AO`
- Primary question:
  - can a forward-projected HP-margin reminder fix the residual `30 HP / 2 potions` aggression and create any second-player wins for the `gpt-4o-mini` side?

## Execution
- Phase: `P1`
- Cells:
  - `p1_c01_gpt4omini_rc_tr_hp_vs_gpt5mini_ao`
  - `p1_c02_gpt4omini_rc_tr_margin_vs_gpt5mini_ao`
- Seed base:
  - `18242`
- Canonical sessions:
  - control: `session_20260322_090435_f13de0`
  - margin: `session_20260322_093318_3b3913`
- Runtime note:
  - `concurrency=4` was used again because `gpt-5-mini` remained the pacing model
  - the package started from the prior OpenAI parity template, so export cleanup was required before finalizing the control artifact
  - duplicate zero-match session directories were discarded before the final package export so the canonical artifacts reflect only the two completed `48`-match runs

## Outcome
- Completed matches: `96`
- Control cell:
  - `GPT5Mini-AO` `27-21` over `GPT4oMini-RC-TR-HP`
  - exact binomial `p=0.4709`
  - effect size `negligible`
- Margin cell:
  - `GPT5Mini-AO` `30-18` over `GPT4oMini-RC-TR-MARGIN`
  - exact binomial `p=0.1114`
  - effect size `small`
- Neither cell was significant at `alpha=0.05`, and the new prompt worsened the competitive result.

## Position Diagnostic
- Control cell:
  - first player won `45/48`
  - `GPT4oMini-RC-TR-HP` won `21/24` as first player and `0/24` as second
  - `GPT5Mini-AO` won `24/24` as first player and `3/24` as second
- Margin cell:
  - first player won `42/48`
  - `GPT4oMini-RC-TR-MARGIN` won `18/24` as first player and `0/24` as second
  - `GPT5Mini-AO` won `24/24` as first player and `6/24` as second
- Primary endpoint read:
  - the `gpt-4o-mini` side stayed at `0/24` second-player wins in both cells

## Mechanism Notes
- Control reproduced the prior full-stack state cleanly:
  - `80 HP / 3 potions` stayed fixed:
    - first player `ATTACK` `24/24`
    - second player `ATTACK` `23/24`
  - `30 HP / 2 potions` remained the key residual mistake:
    - first player `ATTACK` `20/26`
    - second player `ATTACK` `36/41`
- The margin prompt fixed that target bucket directly:
  - `30 HP / 2 potions` under MARGIN:
    - first player `ATTACK` `5/23`
    - second player `ATTACK` `1/23`
- But the broader policy did not improve enough:
  - second-player wins stayed `0/24`
  - `unused_potions_on_loss_rate` worsened `0.185 -> 0.233`
  - `error_recovery_rate` slipped `0.601 -> 0.573`
  - first-player `20 HP / 3 potions` attacks increased `2/15 -> 5/21`
- Conclusion:
  - the prompt solved the exact local forward-projection failure
  - but it did not solve the overall second-player conversion problem

## Cost Notes
- Control:
  - `GPT4oMini-RC-TR-HP`: `$0.17447` total, `$0.003635` per player-match
  - `GPT5Mini-AO`: `$0.79330` total, `$0.016527` per player-match
- Margin:
  - `GPT4oMini-RC-TR-MARGIN`: `$0.18742` total, `$0.003905` per player-match
  - `GPT5Mini-AO`: `$0.74950` total, `$0.015615` per player-match
- The new prompt cost slightly more than the existing full stack and still stayed about `4x` cheaper than plain `gpt-5-mini`.
