# Final FixedDamage Stack

Canonical carry-forward condition for Flash-Lite in FixedDamage:

- Model: `gemini-2.5-flash-lite`
- Controller: `ReasoningController`
- Turn cadence: per-turn `{controller_format}` reinforcement
- Overlay: HP-threshold grounding with explicit no-potion exit
- Hidden Gemini thinking: `thinking_budget=0`
- Output cap: none

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
- `research/2026-03-23-fixed-damage-exit-1/matrix.yaml`
- `research/2026-03-23-fixed-damage-exit-1/README.md`
- `research/2026-03-23-fixed-damage-exit-1/analysis.md`
