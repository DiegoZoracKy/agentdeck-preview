# Cross-Game Comparison 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-26-cross-game-comparison-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Scope: compares `FixedDamage` (`19` empirical packages, `1,320` matches) and `VariableDamage` (`12` empirical packages, `744` matches)
- Combined empirical evidence: `31` packages, `2,064` completed matches
- Canonical final stacks:
  - FixedDamage: `FlashLite-RC-TR-HP-exit`
  - VariableDamage: `FlashLite-RC-RISK`
- Topline Read:
  - the same model names did not imply the same policies across games
  - `RC` transferred for Flash-Lite, but `TR` and fixed-threshold prompting did not
  - Haiku changed the most across games, Flash was the most robust, and Mini kept the same conservative habit in both
- Next Move: stop the pre-release experiment arc and use these synthesis artifacts for the `v0.1.0` preview narrative
<!-- AUTO_FACTS:END -->

## Why This Exists
- `FixedDamage Arc 1` and `VariableDamage Arc 1` answer the within-game stories.
- This package answers the cross-game question:
  - what actually transferred
  - what broke
  - what AgentDeck had to measure differently
  - what the combined release story is

## Source Arcs
- [FixedDamage Arc 1](../2026-03-23-fixed-damage-arc-1/README.md)
- [VariableDamage Arc 1](../2026-03-26-variable-damage-arc-1/README.md)

## Final Answers
- Transfer:
  - `ReasoningController` transferred for Flash-Lite
  - turn reinforcement did not transfer
  - HP guidance transferred only after being rewritten from exact fixed-threshold language into VariableDamage risk bands
- Model behavior:
  - `Flash` was the most robust baseline across both games
  - `Haiku` changed the most: it sat clearly below `Flash` in rebuilt FixedDamage, then became coherent and co-top in VariableDamage
  - `Mini` changed least in behavior: it stayed early-healing and conservative, but VariableDamage made that cost clearer
  - `FlashLite` remained the most improvable weak model in both games
- Product value:
  - the key AgentDeck contribution was not only outcome tracking
  - it was surfacing mechanism-level failures, validating targeted interventions, and showing when those interventions did or did not transfer

## Practical Read
- If you want the shortest release-facing story:
  - FixedDamage proved the intervention workflow in a deterministic game
  - VariableDamage proved the same workflow still works under uncertainty, but only after the metrics and the prompt logic changed
- If you want the ordering takeaway:
  - rebuilt FixedDamage now supports `GPT5Mini > Flash > Haiku > Mini > FlashLite`
  - VariableDamage still supports a compressed co-top tier of `Flash`, `Haiku`, and `GPT5Mini`
- If you want the most important product claim:
  - AgentDeck is useful for diagnosing model behavior, not just for tuning weaker models

## Artifacts
- `manifest.yaml` - comparison metadata
- `results.json` / `results.csv` - summary-only placeholder outputs for contract compatibility
- `analysis.md` - detailed cross-game synthesis
- `recordings/README.md` - pointer policy for underlying packages
