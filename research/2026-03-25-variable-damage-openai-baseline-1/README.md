# VariableDamage OpenAI Baseline 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-25-variable-damage-openai-baseline-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 72/72
- Game: VariableDamageGame
- Players: gpt-5-mini, gemini-2.5-flash, claude-haiku-4-5-20251001, gpt-4o-mini
- Seed Base: 28242
- Topline Winner: GPT5Mini-AO
- Avg Turns: 24.40
- Avg Duration (s): 145.97
- Total Cost: 1.0111
<!-- AUTO_FACTS:END -->

## Why This Exists
- We already know the plain VariableDamage ordering among the current weak-tier baselines:
  - `Flash-AO ≈ Haiku-AO > Mini-AO`
- We do not yet know where `GPT5Mini-AO` lands in that same VariableDamage graph.
- FixedDamage already showed that `GPT4oMini-RC` vs `GPT5Mini-AO` is not something we should assume helps by default.
- So this package places plain `GPT5Mini-AO` into the VariableDamage baseline graph first, before any OpenAI controller branch is attempted.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers: `gpt-5-mini`, `gemini-2.5-flash`, `claude-haiku-4-5-20251001`, `gpt-4o-mini`
- Configs: handshake-only `ActionOnlyController`
- Matches planned: `24` per cell, `72` total
- Seed base: `28242`
- Turn cap: `40`

## Execution Plan
- Phase P1:
  - `GPT5Mini-AO` vs `Flash-AO`
  - `GPT5Mini-AO` vs `Haiku-AO`
  - `GPT5Mini-AO` vs `Mini-AO`
- Expansion rule:
  - only expand individual cells to `48` if the pilot comes back near-parity or behaviorally novel enough to justify the added cost

## Primary Readout
- Outcome:
  - decisive win rate
  - exact-binomial significance
  - first-player win rate
  - position-controlled split
- Behavior:
  - `safe_zone_potion_rate`
  - `danger_zone_potion_rate`
  - `lower_danger_zone_potion_rate`
  - `upper_danger_zone_potion_rate`
  - `lethal_zone_potion_rate`
  - `risk_band_potion_rate_by_scarcity`
  - `first_lethal_entry_inventory`
  - `unused_potions_on_loss_rate`
  - `high_roll_recovery_rate`

## Artifacts
- `matrix.yaml`
- `manifest.yaml`
- `analysis.md`
- `artifacts/`
- `notes/`
- `recordings/`
- `scripts/`

## Outcome
- `GPT5Mini-AO` beat `Flash-AO` `15-9` at `N=24` (`p=0.307`)
- `GPT5Mini-AO` beat `Haiku-AO` `14-10` at `N=24` (`p=0.541`)
- `GPT5Mini-AO` beat `Mini-AO` `14-10` at `N=24` (`p=0.541`)

## Main Finding
- `GPT5Mini-AO` joined the top VariableDamage baseline tier immediately, but it did **not** open a decisive new gap at pilot size.
- The main separation was behavioral, not headline win rate:
  - vs `Flash-AO`: `GPT5Mini-AO` entered first lethal states with median `2` potions left vs `0` for Flash, and converted `4/12` second-player starts vs `1/12` for Flash
  - vs `Haiku-AO`: `GPT5Mini-AO` first-potion median was `36 HP` vs `72.5 HP` for Haiku, with `0%` safe-zone healing vs `23.8%`
  - vs `Mini-AO`: `GPT5Mini-AO` first-potion median was `32.5 HP` vs `61 HP` for Mini, and first lethal-entry zero-potion rate was `21.7%` vs `95.8%`
- Across all three cells, `GPT5Mini-AO` kept `lethal_zone_potion_rate = 1.0`, avoided safe-zone potions entirely, and preserved much more inventory into critical states than the current baselines.

## Practical Read
- This package does **not** justify jumping straight to an OpenAI RC branch on the assumption that RC will close a large plain-model gap.
- If we expand one cell, `GPT5Mini-AO vs Flash-AO` is the right next rung because:
  - `Flash-AO` is still the strongest practical non-OpenAI VariableDamage reference baseline
  - it had the largest pilot gap (`15-9`)
- `GPT5Mini-AO` looks more like a cleaner top-tier baseline under uncertainty than a distant premium ceiling.
