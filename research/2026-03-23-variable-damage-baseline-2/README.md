# VariableDamage Baseline 2

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-23-variable-damage-baseline-2`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 96/96
- Game: VariableDamageGame
- Players: gemini-2.5-flash-lite, gpt-4o-mini, claude-haiku-4-5-20251001
- Seed Base: 22242
- Topline Winner: Haiku-AO over FlashLite-AO decisively; Mini-AO over FlashLite-AO directionally
- Avg Turns: 19.35
- Avg Duration (s): 39.01
- Total Cost: 0.4279
<!-- AUTO_FACTS:END -->

## Why This Exists
- Extend the VariableDamage baseline beyond Gemini before importing any controller or prompt-stack intervention.
- Measure plain-model behavior under uncertainty first, so later RC decisions are tied to actual risk-band failures rather than assumptions carried over from FixedDamage.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers: `gemini-2.5-flash-lite`, `gpt-4o-mini`, `claude-haiku-4-5-20251001`
- Configs: handshake-only `ActionOnlyController`
- Matches Planned: `96`
- Seed Base: `22242`
- Turn cap: `40`

## Execution Plan
- Phase P1:
  - `FlashLite-AO` vs `Mini-AO`
  - `FlashLite-AO` vs `Haiku-AO`
- Expansion rule:
  - no expansion in this package; use the exported risk-band behavior to decide whether Mini or Haiku earn an RC-only follow-up

## Results
- `Mini-AO` beat `FlashLite-AO` `30-18`, but the result stayed statistically null at `N=48` (`p=0.111`, small effect). The interesting part was behavioral: Mini healed extremely early and consistently, with median first potion `79 HP` and danger-zone potion rate `96.8%`.
- `Haiku-AO` beat `FlashLite-AO` `38-10` (`p=6.17e-05`, medium effect). Unlike FixedDamage, Haiku did not look seat-inverted or pathological here; it was simply stronger and much better calibrated under uncertainty.
- Flash-Lite lost for the same basic reason in both cells: it still attacked too deep into the danger and lethal bands, then died holding resources.
  - vs Mini: danger-zone potion rate `6.8%`, lethal-zone potion rate `40.2%`, unused-potion losses `100%`
  - vs Haiku: danger-zone potion rate `9.6%`, lethal-zone potion rate `37.8%`, unused-potion losses `100%`
- Both cells exported cleanly with `100%` strict contract rate and `0` parse failures.

## Artifacts
- `matrix.yaml` (benchmark grid definition)
- `manifest.yaml` (repro metadata)
- `analysis.md` (interpretation plan and hypotheses)
- `artifacts/` (derived tables/plots/highlights)
- `notes/` (human run notes)
- `recordings/` (external pointers only)
- `scripts/` (execution helpers / notes)

## Storage
- Raw recordings will live under `research/2026-03-23-variable-damage-baseline-2/agentdeck_runs`
- Repo keeps the package contract and later lightweight derived artifacts

## Next Package
- This sweep does not justify a Haiku RC branch.
- If the cross-provider VariableDamage branch continues, `Mini-AO` is the only plausible RC-only candidate because its policy is coherent but visibly overconservative.
- If the main line stays focused on weaker-model equalization, the better next move remains `VariableDamage Transfer 1` for Flash-Lite.
