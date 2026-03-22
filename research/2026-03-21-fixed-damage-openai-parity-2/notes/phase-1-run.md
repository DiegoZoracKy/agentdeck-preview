# Phase 1 Run Notes

## Purpose
- Run the last meaningful FixedDamage OpenAI rung:
  - `GPT4oMini-RC-TR-HP` vs `GPT5Mini-AO`
- Primary question:
  - can the full stack recover `gpt-4o-mini` after RC-only failed and make it truly competitive with plain `gpt-5-mini`?

## Execution
- Phase: `P1`
- Cell:
  - `p1_c01_gpt4omini_rc_tr_hp_vs_gpt5mini_ao`
- Seed base:
  - `17242`
- Session:
  - `session_20260321_225728_dfd5b7`
- Runtime note:
  - `concurrency=4` was used again because `gpt-5-mini` remained the pacing model
  - the run completed cleanly in about `25` minutes, but several `gpt-5-mini` turns stretched well past normal weak-tier latency

## Outcome
- Completed matches: `48`
- Result: `GPT5Mini-AO` `27-21` over `GPT4oMini-RC-TR-HP`
- Statistical read:
  - exact binomial `p=0.4709`
  - effect size `negligible`
  - not significant at `alpha=0.05`

## Position Diagnostic
- first player won `45/48`
- `GPT4oMini-RC-TR-HP` won `21/24` as first player and `0/24` as second
- `GPT5Mini-AO` won `24/24` as first player and `3/24` as second

## Mechanism Notes
- The full stack fixed the obvious opening-seat threshold bug:
  - at `80 HP / 3 potions`, `GPT4oMini-RC-TR-HP` attacked `24/25` as first player and `24/24` as second
- It also restored sane critical healing:
  - at `20 HP / 3 potions`, it healed `15/15` as first player and `17/18` as second
- The remaining weakness is medium/low-HP aggression after the obvious threshold check:
  - at `20 HP / 1 potion`, second player still attacked `6/22`
  - at `30 HP / 2 potions`, second player attacked `41/49`
- Behavioral deltas versus OpenAI Parity 1:
  - vs AO baseline:
    - wins `19 -> 21`
    - first potion median `60 -> 20`
    - `position_policy_delta` `0.324 -> 0.060`
  - vs RC-only:
    - wins `8 -> 21`
    - `critical_potion_response_rate` `0.363 -> 0.444`
    - `error_recovery_rate` `0.336 -> 0.494`
    - `unused_potions_on_loss_rate` `0.600 -> 0.185`

## Cost Notes
- `GPT4oMini-RC-TR-HP`: `$0.17777` total, `$0.003703` per player-match
- `GPT5Mini-AO`: `$0.75017` total, `$0.015629` per player-match
- So the full stack kept `gpt-4o-mini` about `4.2x` cheaper than plain `gpt-5-mini`, but the cheaper stack still lost directionally.
