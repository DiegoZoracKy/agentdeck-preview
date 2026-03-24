# VariableDamage Release 1

**Status**: complete  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-23-variable-damage-release-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 72/72
- Game: VariableDamageGame
- Players: AttackBot, PotionAt80Bot, gemini-2.5-flash-lite, gemini-2.5-flash
- Seed Base: 21242
- Topline Winner: Flash-AO over FlashLite-AO in the LLM baseline; PotionAt80Bot over AttackBot in calibration
- Avg Turns: 15.01
- Avg Duration (s): 16.41
- Total Cost: 0.0534
<!-- AUTO_FACTS:END -->

## Why This Exists
- Open a new research line after the FixedDamage arc by holding the core combat structure constant while introducing seeded damage uncertainty.
- Establish calibration and plain-model baseline behavior before importing any FixedDamage-derived strategy stack into VariableDamage.

## Design Snapshot
- Game + information level: `VariableDamageGame(information_level="partial")`
- Damage range: uniform inclusive `15..25`
- Models / providers: local calibration bots plus `gemini-2.5-flash-lite` and `gemini-2.5-flash`
- Configs: handshake-only `ActionOnlyController`
- Matches Planned: `72`
- Seed Base: `21242`
- Planned turn cap: `40`

## Execution Plan
- Preflight gate:
  - verify seeded RNG consumption only on `ATTACK`
  - verify paired side-swap still controls seat allocation under stochastic damage
  - verify partial-information public surface matches the game spec
- Phase P0:
  - `AttackBot` vs `AttackBot`
  - `AttackBot` vs `PotionAt80Bot`
- Phase P1:
  - `FlashLite-AO` vs `Flash-AO`
- Expansion rule:
  - expand only if baseline behavior is legible and the VariableDamage scorer lands cleanly

## Results
- `AttackBot` vs `AttackBot` split `12-12` with a mild first-player lean (`16/24` first-player wins). Randomized damage reduced, but did not erase, seat advantage for pure attack play.
- `PotionAt80Bot` beat `AttackBot` `18-6` (`p=0.0227`, medium effect). Under uncertainty, the old early-heal bot was no longer a clearly weak policy: its median first potion landed at `77 HP`, and that caution materially outperformed never healing.
- `Flash-AO` beat `FlashLite-AO` `19-5` (`p=0.00661`, medium effect). The model gap remained large, but the seat effect was much smaller than in FixedDamage (`13/24` first-player wins).
- Behaviorally, plain Flash adapted to uncertainty by healing much earlier and much more often in risky bands:
  - first potion median `45 HP` vs `18.5 HP` for Flash-Lite
  - danger-zone potion rate `54.7%` vs `6.3%`
  - lethal-zone potion rate `83.3%` vs `37.1%`
  - unused-potion losses `20.0%` vs `89.5%`
- The new VariableDamage scorer landed cleanly: all `72` matches passed artifact validation, and the baseline cells produced legible risk-band differences instead of threshold noise.

## Artifacts
- `matrix.yaml` (benchmark grid definition)
- `manifest.yaml` (repro metadata)
- `analysis.md` (interpretation plan and hypotheses)
- `artifacts/` (derived tables/plots/highlights)
- `notes/` (human run notes)
- `recordings/` (external pointers only)
- `scripts/` (execution helpers / notes)

## Storage
- Raw recordings will live under `research/2026-03-23-variable-damage-release-1/agentdeck_runs`
- Repo keeps the package contract and later lightweight derived artifacts

## Next Package
- `VariableDamage Transfer 1` should test whether the carried-forward FixedDamage stack transfers under uncertainty, but the HP-grounding text must be rewritten for stochastic damage rather than copied verbatim from FixedDamage.
