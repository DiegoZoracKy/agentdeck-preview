# Analysis — VariableDamage Arc 1

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Arc scope: `12` empirical packages and `744` completed VariableDamage matches.
- Main result: VariableDamage established that AgentDeck’s intervention workflow still works under uncertainty, but the successful logic changed from fixed HP thresholds to risk bands and inventory timing.
- Canonical carry-forward condition: `FlashLite-RC-RISK`.
- Next move: stop adding VariableDamage branches and switch to synthesis and release-facing docs.
<!-- AUTO_FACTS:END -->

## What The Arc Set Out To Test
- Whether the FixedDamage intervention story survived once attack damage became stochastic.
- Whether the same models would keep the same relative ordering under uncertainty.
- Whether the behavioral layer needed to evolve beyond exact thresholds.
- Whether a tuned weak model could remain respectable against both practical and premium baselines in the harder game.

## Causal Ladder
- [Release 1](../2026-03-23-variable-damage-release-1/README.md):
  - recalibrated the game class
  - showed that variance weakened the old deterministic first-player script
  - proved that early healing could become rational in this game
- [Baseline 2](../2026-03-23-variable-damage-baseline-2/README.md) and [Baseline 3](../2026-03-24-variable-damage-baseline-3/README.md):
  - established the plain-model ordering under uncertainty
  - showed that `Flash-AO`, `Haiku-AO`, and later `GPT5Mini-AO` formed the effective top tier
  - showed that `Mini-AO` remained coherent but overconservative and that plain `FlashLite-AO` remained the weakest baseline
- [Controller 1](../2026-03-23-variable-damage-controller-1/README.md):
  - showed that `ReasoningController` again materially helped `Flash-Lite`
  - showed that the same RC move did not justify a Mini branch
- [Reinforcement 1](../2026-03-24-variable-damage-reinforcement-1/README.md):
  - showed that TR did not transfer from FixedDamage
  - TR failed to improve the headline outcome and worsened seat-conditioned drift
- [Threshold 1](../2026-03-25-variable-damage-threshold-1/README.md):
  - replaced the broken fixed-20 HP instruction with a real VariableDamage risk prompt
  - fixed the remaining inventory-timing and seat-drift problem cleanly enough to tie Flash at pilot size
- [Parity 1](../2026-03-25-variable-damage-parity-1/README.md):
  - expanded the successful treatment to `N=48`
  - held the main mechanism at scale and finished `26-22` over `Flash-AO`, still non-significant but clearly viable
- [OpenAI Baseline 1](../2026-03-25-variable-damage-openai-baseline-1/README.md), [OpenAI Parity 1](../2026-03-25-variable-damage-openai-parity-1/README.md), and [OpenAI Parity 2](../2026-03-25-variable-damage-openai-parity-2/README.md):
  - extended the uncertainty story across OpenAI models
  - showed that `gpt-4o-mini RC` still was not a generic win
  - showed that premium `gpt-4o` could be pilot-competitive with `gpt-5-mini`, but RC added cost without changing the outcome
- [OpenAI Baseline 2](../2026-03-25-variable-damage-openai-baseline-2/README.md):
  - expanded `Flash-AO` vs `GPT5Mini-AO`
  - showed that the practical cheap baseline and the premium clean baseline were effectively co-top in outcome, though not in style
- [Premium Final 1](../2026-03-26-variable-damage-premium-final-1/README.md):
  - closed the branch
  - the carried-forward Flash-Lite treatment stayed respectable against `GPT5Mini-AO` without reopening the old failure modes

## Final VariableDamage Answers
1. Did uncertainty change the baseline story?

Yes.
- FixedDamage mostly rewarded exact threshold arithmetic.
- VariableDamage rewarded risk management and inventory timing.
- The top of the plain-model field changed from a clearer premium ceiling to a flatter top tier:
  - `Flash-AO`, `Haiku-AO`, and `GPT5Mini-AO` all looked strong
  - `Mini-AO` remained below them
  - `FlashLite-AO` remained the weakest untuned baseline

2. Did the FixedDamage intervention recipe transfer cleanly?

No.
- `RC` transferred for `FlashLite`.
- `TR` did not.
- the FixedDamage HP instruction did not.
- the carry-forward prompt had to be rewritten in terms of VariableDamage risk bands and potion scarcity.

3. Did the behavioral layer need to evolve?

Yes.
- Exact threshold metrics were not enough for this game.
- The decisive VariableDamage metrics became:
  - `safe_zone_potion_rate`
  - `first_lethal_entry_inventory`
  - lower/upper danger-zone potion rates
  - risk-band behavior under scarcity
- These metrics made the new failure modes legible:
  - over-healing in safe states
  - arriving at lethal states empty
  - miscalibrated one-potion danger behavior

4. How far did the tuned weak-model line get?

Far enough to validate the workflow, but not far enough to erase the premium gap completely.
- `FlashLite-RC-RISK` held near parity with `Flash-AO` at `N=48` in [Parity 1](../2026-03-25-variable-damage-parity-1/README.md).
- It then lost only `11-13` to `GPT5Mini-AO` in [Premium Final 1](../2026-03-26-variable-damage-premium-final-1/README.md), with a null result and a still-clean policy.
- The remaining premium edge was narrow:
  - cleaner danger-zone selectivity
  - better first-lethal inventory preservation

## Competitive Endpoints That Matter
- Plain baseline tiering:
  - `Flash-AO`, `Haiku-AO`, and `GPT5Mini-AO` formed the effective top tier we observed
  - `Mini-AO` sat below them with a stable early-heal policy
  - `FlashLite-AO` was the weakest plain baseline
- OpenAI specific:
  - `gpt-4o-mini RC` again disproved the naive “CoT always helps” story
  - premium `gpt-4o` was competitive with `gpt-5-mini`, but RC did not add enough value to justify the cost
- Tuned weak-model endpoint:
  - `FlashLite-RC-RISK` became a credible near-parity condition against Flash and a respectable near-parity condition against `gpt-5-mini`

## Cost Read
- The branch again rejected the easy version of the business story.
  - the cleanest or strongest policy was not always the cheapest on mean spend
- What it did show:
  - `Flash-AO` can stay co-top while being much cheaper than `GPT5Mini-AO`
  - `FlashLite-RC-RISK` can become respectable against a premium baseline while staying materially cheaper than that premium model
  - RC or premium model choice alone is not automatically cost-effective

## Canonical Final Stack
The best Flash-Lite condition discovered in VariableDamage is:

- model: `gemini-2.5-flash-lite`
- controller: `ReasoningController`
- turn cadence: risk-grounded per-turn guidance
- overlay: scarcity-aware danger/lethal prompt
- hidden Gemini thinking: `thinking_budget=0`
- no TR layer
- no output cap

Exact carry-forward turn addition:

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

Canonical source:
- [VariableDamage Parity 1 README](../2026-03-25-variable-damage-parity-1/README.md)
- [VariableDamage Premium Final 1 README](../2026-03-26-variable-damage-premium-final-1/README.md)
- [VariableDamage Premium Final 1 matrix](../2026-03-26-variable-damage-premium-final-1/matrix.yaml)

## Why VariableDamage Is Done
- The branch answered the main open question from FixedDamage:
  - would the same intervention logic survive under uncertainty?
- The answer is now clear enough for `v0.1.0`:
  - some logic transferred
  - some did not
  - the tool still surfaced the right failure modes and guided the repair
- More packages here would add detail, not new narrative beats.

## Next Move
- Stop the main experiment line.
- Read the full story together with:
  - [FixedDamage Arc 1](../2026-03-23-fixed-damage-arc-1/README.md)
  - [Cross-Game Comparison 1](../2026-03-26-cross-game-comparison-1/README.md)
- Put product effort into:
  - release-facing docs
  - reproducibility guidance
  - replay/viewer curation
