# Phase 1 Run Notes

## Purpose
- Run the OpenAI-only ladder in one package:
  - `GPT4oMini-AO` vs `GPT5Mini-AO`
  - `GPT4oMini-RC` vs `GPT5Mini-AO`
- Primary question:
  - is `ReasoningController` alone enough to move `gpt-4o-mini` meaningfully toward plain `gpt-5-mini` in FixedDamage?

## Execution
- Phase: `P1`
- Seed base: `16242`
- Sessions:
  - baseline cell:
    - `p1_c01_gpt4omini_ao_vs_gpt5mini_ao`
    - `session_20260321_174935_df8c56`
  - RC cell:
    - `p1_c02_gpt4omini_rc_vs_gpt5mini_ao`
    - `session_20260321_180944_a4c489`
- Runtime note:
  - `concurrency=4` was used because `gpt-5-mini` latency was materially higher than the weak-tier baselines
  - one `gpt-5-mini` turn in the RC cell took about `606s`, but the process remained healthy and completed cleanly

## Outcomes
- Baseline:
  - `GPT5Mini-AO` beat `GPT4oMini-AO` `29-19`
  - exact binomial `p=0.193`
  - effect size `small`
- RC-only:
  - `GPT5Mini-AO` beat `GPT4oMini-RC` `40-8`
  - exact binomial `p=3.31e-06`
  - effect size `medium`

## Mechanism Notes
- Plain `gpt-4o-mini` showed the known seat-conditioned early-heal pathology:
  - at `80 HP / 3 potions`, it attacked `24/24` as first player but healed `24/24` as second
- `ReasoningController` softened that high-HP error:
  - at `80 HP / 3 potions`, it attacked `24/25` as first player and `15/24` as second
- But RC introduced a worse low-HP failure mode:
  - `all_attack_match_rate` rose from `0.0%` to `18.75%`
  - `unused_potions_on_loss_rate` rose from `17.2%` to `60.0%`
  - `critical_potion_response_rate` fell from `0.550` to `0.363`
  - `error_recovery_rate` fell from `0.531` to `0.336`

## Cost Notes
- `GPT4oMini-AO`: `$0.001252` per player-match
- `GPT4oMini-RC`: `$0.002064` per player-match
- `GPT5Mini-AO`:
  - baseline cell: `$0.014590` per player-match
  - RC cell: `$0.014934` per player-match
- So RC raised `gpt-4o-mini` cost by about `65%` while making the outcome much worse.
