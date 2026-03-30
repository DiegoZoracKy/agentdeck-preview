# FixedDamage Arc 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-23-fixed-damage-arc-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Scope: `19` empirical FixedDamage packages, `1,320` completed matches
- Game: `FixedDamageGame(information_level="partial")`
- Providers: `local`, `google`, `openai`, `anthropic`
- Canonical final stack: `FlashLite-RC-TR-HP-exit`
- Topline Read:
  - strategy stack mattered more than base-model choice alone in this game
  - plain `FlashLite-AO` lost badly to stronger baselines, but the final Flash-Lite stack still became the strongest Gemini condition we found
  - the rebuilt parity ladder no longer supports a decisive Flash-Lite-over-Flash claim; the right final read is competitive / near-parity, not clear dominance
- Next Move: treat FixedDamage as closed and use `VariableDamage Arc 1` plus the cross-game synthesis as the release-facing continuation
<!-- AUTO_FACTS:END -->

## Why This Exists
- The FixedDamage branch now spans `19` empirical packages plus this summary.
- Each package is atomic and auditable, but the full research story is spread
  across many READMEs.
- This arc package is the single entrypoint for the whole branch:
  - what was asked
  - what was tried
  - what the causal ladder was
  - what the final answer is
  - which exact stack should be carried forward

## Arc Map
- Baseline and behavioral discovery:
  - [FixedDamage Release 1](../2026-03-19-fixed-damage-release-1/README.md)
- Controller intervention:
  - [FixedDamage Controller 1](../2026-03-19-fixed-damage-controller-1/README.md)
- Flash-Lite mechanism and parity ladder:
  - [FixedDamage Parity 1](../2026-03-20-fixed-damage-parity-1/README.md)
  - [FixedDamage Parity 2](../2026-03-20-fixed-damage-parity-2/README.md)
  - [FixedDamage Threshold 1](../2026-03-20-fixed-damage-threshold-1/README.md)
  - [FixedDamage Parity 3](../2026-03-20-fixed-damage-parity-3/README.md)
  - [FixedDamage Parity 4](../2026-03-20-fixed-damage-parity-4/README.md)
  - [FixedDamage FlashLite Cap 1](../2026-03-23-fixed-damage-cap-1/README.md)
  - [FixedDamage FlashLite Exit 1](../2026-03-23-fixed-damage-exit-1/README.md)
- Flash-Lite ablations:
  - [FixedDamage Ablation 1](../2026-03-20-fixed-damage-ablation-1/README.md)
  - [FixedDamage Ablation 2](../2026-03-21-fixed-damage-ablation-2/README.md)
- Cross-provider baselines and parity:
  - [FixedDamage Mini Baseline 1](../2026-03-20-fixed-damage-mini-baseline-1/README.md)
  - [FixedDamage Mini Parity 1](../2026-03-20-fixed-damage-mini-parity-1/README.md)
  - [FixedDamage GPT-5 Mini Parity 1](../2026-03-21-fixed-damage-gpt5mini-parity-1/README.md)
  - [FixedDamage OpenAI Parity 1](../2026-03-21-fixed-damage-openai-parity-1/README.md)
  - [FixedDamage OpenAI Parity 2](../2026-03-21-fixed-damage-openai-parity-2/README.md)
  - [FixedDamage OpenAI Margin 1](../2026-03-22-fixed-damage-openai-margin-1/README.md)
  - [FixedDamage Baseline Completion 1](../2026-03-24-fixed-damage-baseline-completion-1/README.md)
  - [FixedDamage Baseline Completion 2](../2026-03-25-fixed-damage-baseline-completion-2/README.md)

## Final Answers
- Outcome layer:
  - plain `Flash` beat plain `Flash-Lite`
  - the final Flash-Lite stack reached near parity with plain `Flash`, but the rebuilt set does not support the older stronger claim that it clearly beat `Flash-AO`
  - tuned Flash-Lite still beat plain `gpt-4o-mini`
  - plain `gpt-5-mini` remained the best untuned premium baseline we tested
  - the completed plain-model ordering is now closed:
    - `GPT5Mini-AO > Flash-AO > Haiku-AO > Mini-AO > FlashLite-AO`
- Behavioral layer:
  - the behavioral scorer was the key unlock
  - it surfaced state-level bugs that win rates alone would not explain
  - the decisive Flash-Lite fixes were:
    - turn-time reasoning structure
    - turn reinforcement
    - HP-threshold grounding
    - a no-potion escape clause to remove the dead-end low-HP loop
- Cost layer:
  - strategy stack can beat stronger plain baselines, but not always while
    staying cheaper on mean spend
  - output caps were the wrong cost lever in this game
  - the final prompt exit clause improved tail quality far more cleanly than
    `max_tokens=128`

## Canonical Final Stack
The final carry-forward Flash-Lite condition for FixedDamage is:

- Base model: `gemini-2.5-flash-lite`
- Controller: `ReasoningController`
- Turn cadence: turn-reinforced
- HP overlay: repaired threshold grounding with no-potion exit
- Hidden Gemini thinking: `thinking_budget=0`
- Fairness settings used in parity runs:
  - `pairing_policy=paired_side_swap`
  - `first_player_policy=random`

Exact turn-time addition:

```text
{game_view}

{controller_format}

Before acting, calculate: does your current HP minus one ATTACK (20 damage) leave you alive?
If no and you still have potions, use POTION.
If no and you have no potions, ATTACK anyway.
Otherwise, act on your best read of the state.
```

Source of record:
- [FixedDamage FlashLite Exit 1](../2026-03-23-fixed-damage-exit-1/README.md)
- [FixedDamage FlashLite Exit 1 analysis](../2026-03-23-fixed-damage-exit-1/analysis.md)
- [FixedDamage FlashLite Exit 1 matrix](../2026-03-23-fixed-damage-exit-1/matrix.yaml)

## Practical Read
- If you want the best-known Flash-Lite setup for this game, use
  `FlashLite-RC-TR-HP-exit`.
- If you want the main scientific takeaway, it is this:
  - in constrained sequential tasks, prompt strategy can transform a weak model
    from clearly losing to genuinely competitive against stronger plain baselines
- If you want the next research question, it is no longer inside FixedDamage.
  That question is now answered in [VariableDamage Arc 1](../2026-03-26-variable-damage-arc-1/README.md)
  and [Cross-Game Comparison 1](../2026-03-26-cross-game-comparison-1/README.md).

## Artifacts
- `manifest.yaml` - arc-level summary metadata
- `results.json` / `results.csv` - summary-only placeholder outputs for contract compatibility
- `analysis.md` - deeper arc synthesis
- `recordings/README.md` - where to find the underlying recording pointers
- `notes/final-stack.md` - canonical carry-forward stack
