# Phase 1 Run Notes

## Purpose
- Run the dedicated fresh-seed `N=48` cross-provider parity package for the full Flash-Lite stack:
  - `FlashLite-RC-TR-HP` vs `GPT5Mini-AO`
- Primary diagnostic:
  - whether the stronger threshold-grounded Flash-Lite policy stays competitive against a stronger plain OpenAI mini baseline

## Execution
- Phase: `P1`
- Cell: `p1_c01_flash_lite_rc_tr_hp_vs_gpt5mini_ao`
- Seed base: `15242`
- Session:
  - `session_20260321_103701_549980`
- Runtime note:
  - `concurrency=4` override used because `gpt-5-mini` response latency was materially higher than earlier baselines

## Outcome
- Completed matches: `48`
- Result: `GPT5Mini-AO` `28-20` over `FlashLite-RC-TR-HP`
- Statistical read: `p=0.312`, negligible effect, not significant at `alpha=0.05`

## Position Diagnostic
- first player won `44/48`
- `FlashLite-RC-TR-HP` won `20/24` as first player and `0/24` as second
- `GPT5Mini-AO` won `24/24` as first player and `4/24` as second

## Mechanism Notes
- `GPT5Mini-AO` did not share the old `gpt-4o-mini` early-heal pathology:
  - at shared `80 HP / 3 potions`, it attacked `24/24` as first player and `23/24` as second
- Flash-Lite remained much cleaner on policy stability:
  - `position_policy_delta`: `0.0159`
  - `state_action_consistency`: `0.9680`
- GPT-5 Mini still outperformed it on survival behavior:
  - `critical_potion_response_rate`: `0.5571` vs Flash-Lite `0.3958`
  - `error_recovery_rate`: `0.6304` vs Flash-Lite `0.5122`

