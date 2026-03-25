# FixedDamage Baseline Completion 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-24-fixed-damage-baseline-completion-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: completed
- Matches: `192/192`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `google:gemini-2.5-flash`, `openai:gpt-4o-mini`, `anthropic:claude-haiku-4-5-20251001`
- Seed Base: `26242`
- Topline Winner: `Haiku-AO` (pooled package summary; interpret per cell)
- Avg Turns: `21.81`
- Avg Duration (s): `38.64`
- Total Cost: `$1.4289`
<!-- AUTO_FACTS:END -->

## Why This Exists
- The FixedDamage arc is behaviorally complete, but its plain-model ordering is
  not fully symmetric with the later VariableDamage round-robin.
- We already ran:
  - `FlashLite-AO` vs `Flash-AO`
  - `FlashLite-AO` vs `Mini-AO`
- We did not yet run the remaining four plain-model edges:
  - `FlashLite-AO` vs `Haiku-AO`
  - `Flash-AO` vs `Mini-AO`
  - `Flash-AO` vs `Haiku-AO`
  - `Mini-AO` vs `Haiku-AO`
- This package fills that gap without reopening the FixedDamage intervention
  ladder.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
  - `gpt-4o-mini`
  - `claude-haiku-4-5-20251001`
- Strategy conditions:
  - AO-only plain-model head-to-heads
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini models
  - `Flash-AO` uses `max_retries=12`, `retry_delay=4.0`
- Matches planned:
  - `48` per cell
  - `192` total
- Seed base:
  - `26242`

## Primary Endpoints
- decisive win rate
- position-controlled split
- `first_potion_profile`
- `all_attack_match_rate`
- `unused_potions_on_loss_rate`
- `critical_potion_response_rate`
- `position_policy_delta`
- state-level evidence at `80 HP / 3 potions` and `20 HP / 1 potion`

## Secondary Endpoints
- cost
- latency
- strict contract rate

## Hypothesis
- Haiku should look much stranger in FixedDamage than it did in VariableDamage
  because its seat-conditioned inversion was already visible in the original
  release package.
- Mini should remain stable and early-healing.
- Flash should remain the cleanest plain Gemini baseline.

## Results
- `Haiku-AO` beat `FlashLite-AO` `44-4` (`p=1.51e-09`, large effect).
- `Flash-AO` beat `Mini-AO` `36-12` (`p=7.17e-04`, medium effect).
- `Flash-AO` edged `Haiku-AO` `26-22`, but this stayed null (`p=0.665`, negligible effect).
- `Haiku-AO` beat `Mini-AO` `35-13` (`p=0.00209`, small effect).
- The completed plain-model FixedDamage ordering is therefore:
  - `Flash-AO ≈ Haiku-AO > Mini-AO > FlashLite-AO`
- The most important behavioral finding is that `Haiku-AO` remains bizarre in `FixedDamage`, not just strong:
  - it kept `position_policy_delta = 1.0` against both `FlashLite-AO` and `Mini-AO`
  - it still won `23/24` as second player against `FlashLite-AO`
  - but against `Flash-AO` the seat distortion narrowed sharply and the matchup became near parity
- `Mini-AO` stayed stable and early-healing:
  - first potion median `80 HP` against both `Flash-AO` and `Haiku-AO`
- `FlashLite-AO` stayed the weakest untuned model:
  - `unused_potions_on_loss_rate = 97.7%` against `Haiku-AO`
  - `critical_potion_response_rate = 0.221`

## Artifacts
- `matrix.yaml`
- `manifest.yaml`
- `results.json` / `results.csv`
- `analysis.md`
- `artifacts/`
- `notes/`
- `recordings/`
- `scripts/`
