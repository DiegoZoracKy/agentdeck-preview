# FixedDamage Baseline Completion 2

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-25-fixed-damage-baseline-completion-2`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `96/96`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash`, `anthropic:claude-haiku-4-5-20251001`, `openai:gpt-5-mini`
- Seed Base: `27242`
- Topline Winner: `GPT5Mini-AO` (pooled package summary; interpret per cell)
- Avg Turns: `23.48`
- Avg Duration (s): `118.96`
- Total Cost: `$2.1301`
<!-- AUTO_FACTS:END -->

## Why This Exists
- `FixedDamage Baseline Completion 1` closed the weak-tier AO graph among:
  - `FlashLite-AO`
  - `Flash-AO`
  - `Mini-AO`
  - `Haiku-AO`
- The only plain AO edges still missing in the broader FixedDamage model graph are:
  - `Flash-AO` vs `GPT5Mini-AO`
  - `Haiku-AO` vs `GPT5Mini-AO`
- This package closes those last direct head-to-heads without reopening any FixedDamage intervention branches.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash`
  - `claude-haiku-4-5-20251001`
  - `gpt-5-mini`
- Strategy conditions:
  - AO-only plain-model head-to-heads
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Runtime settings:
  - `thinking_budget=0` for `Flash-AO`
  - `Flash-AO` uses `max_retries=12`, `retry_delay=4.0`
- Matches planned:
  - `48` per cell
  - `96` total
- Seed base:
  - `27242`

## Primary Endpoints
- decisive win rate
- position-controlled split
- `first_potion_profile`
- `all_attack_match_rate`
- `unused_potions_on_loss_rate`
- `critical_potion_response_rate`
- `position_policy_delta`

## Hypothesis
- `GPT5Mini-AO` should remain the strongest plain OpenAI baseline in FixedDamage.
- `Flash-AO` should have the best chance to stay competitive with it.
- `Haiku-AO` may still be strong on outcome, but its FixedDamage seat distortion should stay visible.

## Results
- `GPT5Mini-AO` beat `Flash-AO` `36-12` (`p=7.17e-04`, medium effect).
- `GPT5Mini-AO` crushed `Haiku-AO` `46-2` (`p=8.36e-12`, large effect).
- With these last two edges closed, the broader plain-model FixedDamage ordering is:
  - `GPT5Mini-AO > Flash-AO ≈ Haiku-AO > Mini-AO > FlashLite-AO`
- `GPT5Mini-AO` is therefore the clear strongest plain FixedDamage baseline we ran:
  - it went `24/24` as first player and `12/24` as second against `Flash-AO`
  - it went `23/24` from both seats against `Haiku-AO`
- `Haiku-AO` stayed behaviorally bizarre even in a heavy loss:
  - first potion median `70 HP`
  - `critical_potion_response_rate = 1.0`
  - `position_policy_delta = 1.0`
  - but only `2/48` wins overall against `GPT5Mini-AO`
- `Flash-AO` remained the strongest non-OpenAI plain baseline:
  - materially better than `Mini-AO` and near-parity with `Haiku-AO` from Baseline Completion 1
  - but still clearly below `GPT5Mini-AO`
