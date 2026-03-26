# Final VariableDamage Stack

Canonical carry-forward condition for Flash-Lite in VariableDamage:

- Model: `gemini-2.5-flash-lite`
- Controller: `ReasoningController`
- Turn cadence: risk-grounded per-turn guidance
- Overlay: scarcity-aware danger/lethal prompt
- Hidden Gemini thinking: `thinking_budget=0`
- Output cap: none

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
- `research/2026-03-25-variable-damage-parity-1/matrix.yaml`
- `research/2026-03-26-variable-damage-premium-final-1/matrix.yaml`
- `research/2026-03-26-variable-damage-premium-final-1/README.md`
- `research/2026-03-26-variable-damage-premium-final-1/analysis.md`
