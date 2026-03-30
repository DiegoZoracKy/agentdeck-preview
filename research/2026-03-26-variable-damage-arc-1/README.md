# VariableDamage Arc 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-26-variable-damage-arc-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Scope: `12` VariableDamage packages, `744` completed matches
- Game: `VariableDamageGame(information_level="partial")`
- Providers: `local`, `google`, `openai`, `anthropic`
- Canonical final stack: `FlashLite-RC-RISK`
- Topline Read:
  - uncertainty changed both the baseline ranking and the failure modes worth measuring
  - `RC` transferred to Flash-Lite, `TR` did not, and the fixed `20` HP rule had to be redesigned as a risk-band prompt
  - the final premium ceiling check still closed at near parity: `FlashLite-RC-RISK` edged `GPT5Mini-AO` `13-11`, but the gap stayed null and narrow
- Next Move: stop the VariableDamage experiment line here and switch fully to synthesis and release-facing docs
<!-- AUTO_FACTS:END -->

## Why This Exists
- The VariableDamage branch now spans `12` empirical packages.
- It answered the transfer question that FixedDamage left open:
  - would the same intervention logic survive once exact arithmetic stopped solving the game cleanly?
- This arc package is the single entrypoint for the whole branch:
  - what changed under uncertainty
  - which interventions transferred
  - which interventions failed to transfer
  - what the final carry-forward Flash-Lite condition is

## Arc Map
- Baseline and calibration:
  - [VariableDamage Release 1](../2026-03-23-variable-damage-release-1/README.md)
  - [VariableDamage Baseline 2](../2026-03-23-variable-damage-baseline-2/README.md)
  - [VariableDamage Baseline 3](../2026-03-24-variable-damage-baseline-3/README.md)
- Flash-Lite intervention ladder:
  - [VariableDamage Controller 1](../2026-03-23-variable-damage-controller-1/README.md)
  - [VariableDamage Reinforcement 1](../2026-03-24-variable-damage-reinforcement-1/README.md)
  - [VariableDamage Threshold 1](../2026-03-25-variable-damage-threshold-1/README.md)
  - [VariableDamage Parity 1](../2026-03-25-variable-damage-parity-1/README.md)
- OpenAI and premium baselines:
  - [VariableDamage OpenAI Baseline 1](../2026-03-25-variable-damage-openai-baseline-1/README.md)
  - [VariableDamage OpenAI Baseline 2](../2026-03-25-variable-damage-openai-baseline-2/README.md)
  - [VariableDamage OpenAI Parity 1](../2026-03-25-variable-damage-openai-parity-1/README.md)
  - [VariableDamage OpenAI Parity 2](../2026-03-25-variable-damage-openai-parity-2/README.md)
  - [VariableDamage Premium Final 1](../2026-03-26-variable-damage-premium-final-1/README.md)

## Final Answers
- Outcome layer:
  - plain `FlashLite-AO` was again the weakest baseline, but the ordering above it changed under uncertainty
  - the effective top tier we observed was `Flash-AO`, `Haiku-AO`, and `GPT5Mini-AO`, with no decisive separation among them, `Mini-AO` below them, and `FlashLite-AO` at the bottom
  - cleaned OpenAI baseline pilots came back:
    - `GPT5Mini-AO` vs `Flash-AO`: `14-10`
    - `GPT5Mini-AO` vs `Haiku-AO`: `12-12`
    - `GPT5Mini-AO` vs `Mini-AO`: `14-10`
  - the final tuned Flash-Lite condition reached near parity with `Flash-AO` and stayed respectable against `GPT5Mini-AO`
- Behavioral layer:
  - FixedDamage metrics were not enough here
  - the key VariableDamage metrics became:
    - `safe_zone_potion_rate`
    - `first_lethal_entry_inventory`
    - lower/upper danger subband rates
    - risk-band behavior under scarcity
  - the decisive Flash-Lite fixes were:
    - `ReasoningController`
    - a risk-grounded turn-time prompt
  - the failed transfer was clear too:
    - turn reinforcement did not help Flash-Lite here
- Cost layer:
  - `Flash-AO` remained the practical cheap reference baseline
  - `GPT5Mini-AO` remained cleaner, but not decisively stronger, while costing materially more
  - the final tuned Flash-Lite condition stayed about `3.2x` cheaper per player-match than `GPT5Mini-AO` in the premium pilot

## Canonical Final Stack
The final carry-forward Flash-Lite condition for VariableDamage is:

- Base model: `gemini-2.5-flash-lite`
- Controller: `ReasoningController`
- Turn cadence: risk-grounded per-turn guidance
- Overlay: scarcity-aware VariableDamage risk-band prompt
- Hidden Gemini thinking: `thinking_budget=0`
- Fairness settings used in parity and premium runs:
  - `pairing_policy=paired_side_swap`
  - `first_player_policy=random`

Exact turn-time addition:

```text
{game_view}

{controller_format}

Before acting, check your risk band carefully.
- If your HP is above 55, do not use POTION.
- If your HP is 25 or lower and you have potions, use POTION.
- If your HP is 26 to 40 and you have 2 or 3 potions, prefer POTION now rather than entering the lethal zone with fewer resources.
- If your HP is 25 or lower and you have no potions, ATTACK anyway.
- Otherwise, act on your best read of the state.
```

Source of record:
- [VariableDamage Parity 1](../2026-03-25-variable-damage-parity-1/README.md)
- [VariableDamage Premium Final 1](../2026-03-26-variable-damage-premium-final-1/README.md)
- [VariableDamage Premium Final 1 matrix](../2026-03-26-variable-damage-premium-final-1/matrix.yaml)

## Practical Read
- If you want the best-known Flash-Lite setup for VariableDamage, use `FlashLite-RC-RISK`.
- If you want the main scientific takeaway, it is this:
  - interventions do not transfer by name alone
  - they transfer only when they match the new game’s real failure mode
- If you want the baseline ranking takeaway, it is this:
  - VariableDamage compressed the top of the field into a co-top tier rather than revealing a single runaway premium model
- If you want the release-facing continuation, read:
  - [FixedDamage Arc 1](../2026-03-23-fixed-damage-arc-1/README.md)
  - [Cross-Game Comparison 1](../2026-03-26-cross-game-comparison-1/README.md)

## Artifacts
- `manifest.yaml` - arc-level summary metadata
- `results.json` / `results.csv` - summary-only placeholder outputs for contract compatibility
- `analysis.md` - deeper arc synthesis
- `recordings/README.md` - where to find the underlying recording pointers
- `notes/final-stack.md` - canonical carry-forward stack
