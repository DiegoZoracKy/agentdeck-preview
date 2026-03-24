# VariableDamage Release 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-23-variable-damage-release-1`

## Factual Snapshot
<!-- AUTO_FACTS:BEGIN -->
- Status: planned
- Matches: 0/72
- Game: VariableDamageGame
- Players: AttackBot, PotionAt80Bot, gemini-2.5-flash-lite, gemini-2.5-flash
- Seed Base: 21242
- Topline Winner: TBD
- Avg Turns: TBD
- Avg Duration (s): TBD
- Total Cost: TBD
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
- Not run yet. This package is a planned baseline only.

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
- If Release 1 is clean, `VariableDamage Transfer 1` should test whether the carried-forward `FlashLite-RC-TR-HP-exit` stack transfers under uncertainty.
