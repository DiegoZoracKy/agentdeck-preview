# VariableDamage Controller 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-23-variable-damage-controller-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: VariableDamageGame
- Players: gemini-2.5-flash-lite, gpt-4o-mini
- Seed Base: 23242
- Topline Winner: FlashLite-RC over FlashLite-AO directionally; Mini-RC over Mini-AO only marginally
- Avg Turns: 19.79
- Avg Duration (s): 48.55
- Total Cost: 0.1134
<!-- AUTO_FACTS:END -->

## Why This Exists
- Follow the VariableDamage AO baselines with the first controller-only intervention package.
- Test RC only on the models that still look plausibly improvable in this game class: Flash-Lite and GPT-4o Mini.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers: `gemini-2.5-flash-lite`, `gpt-4o-mini`
- Configs: handshake-only `ActionOnlyController` vs `ReasoningController`
- Matches Planned: `48`
- Seed Base: `23242`
- Turn cap: `40`

## Execution Plan
- Phase P1:
  - `FlashLite-AO` vs `FlashLite-RC`
  - `Mini-AO` vs `Mini-RC`
- Expansion rule:
  - expand only if the pilot shows a legible behavioral gain worth carrying forward before any turn reinforcement or guided prompt work

## Results
- `FlashLite-RC` beat `FlashLite-AO` `17-7` at `N=24`. The pilot stopped just short of formal significance (`p=0.0639`), but the behavioral signal is strong enough to justify a Flash-Lite follow-up.
- `Mini-RC` only edged `Mini-AO` `13-11` (`p=0.839`). That is effectively null at pilot size, and the behavior says RC mostly traded away Mini’s conservative discipline rather than producing a clean upgrade.
- Flash-Lite was the real RC candidate in VariableDamage:
  - first potion median moved from `16 HP` to `46 HP`
  - danger-zone potion rate rose from `8.7%` to `36.1%`
  - lethal-zone potion rate rose from `34.8%` to `90.0%`
  - unused-potion losses dropped from `94.1%` to `0%`
  - second-player wins improved from `0/12` to `5/12`
- Mini showed the opposite pattern: RC reduced its extreme early-heal policy, but the gain did not translate into a meaningful outcome improvement.
  - first potion median moved from `77 HP` to `37.5 HP`
  - danger-zone potion rate fell from `76.5%` to `26.4%`
  - lethal-zone potion rate fell from `100%` to `53.7%`
  - unused-potion losses worsened from `0%` to `63.6%`
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
- Raw recordings will live under `research/2026-03-23-variable-damage-controller-1/agentdeck_runs`
- Repo keeps the package contract and later lightweight derived artifacts

## Next Package
- Mini does not justify a VariableDamage RC follow-up.
- Flash-Lite does. The next package should stay on the Flash-Lite line, either by expanding this RC cell to `N=48` or by testing the next intervention layer on top of the now-legible RC behavior.
