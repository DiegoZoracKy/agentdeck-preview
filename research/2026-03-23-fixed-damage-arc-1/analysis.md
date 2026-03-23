# Analysis — FixedDamage Arc 1

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Arc scope: `17` packages and `1,032` completed FixedDamage matches.
- Main result: FixedDamage established that strategy stack can materially reshape effective model ranking in a deterministic sequential game, but only when the interventions match the model's actual failure mode.
- Canonical carry-forward condition: `FlashLite-RC-TR-HP-exit`.
- Next move: stop adding FixedDamage branches and start `VariableDamageGame`.
<!-- AUTO_FACTS:END -->

## What The Arc Set Out To Test
- Whether AgentDeck could expose meaningful behavioral differences between LLMs
  in a simple audited game.
- Whether prompt/controller interventions could turn a weaker model into a
  competitive one.
- Whether those interventions decomposed into distinct, testable pieces.
- Whether the resulting gains were outcome-real, behavioral-only, or mostly
  formatting artifacts.

## Causal Ladder
- [Release 1](../2026-03-19-fixed-damage-release-1/README.md):
  - established the baseline
  - showed that identical-looking outcomes could hide very different policies
  - exposed strong first-player effects and several plain-policy pathologies
- [Controller 1](../2026-03-19-fixed-damage-controller-1/README.md):
  - showed that `ReasoningController` materially improved `Flash-Lite`
  - framed CoT/reasoning structure as a real intervention, not just a prompt style
- [Parity 1](../2026-03-20-fixed-damage-parity-1/README.md):
  - proved plain `Flash` was clearly stronger than plain `Flash-Lite`
  - showed that `RC` could narrow the gap but not close it
- [Parity 2](../2026-03-20-fixed-damage-parity-2/README.md) and [Threshold 1](../2026-03-20-fixed-damage-threshold-1/README.md):
  - isolated the second-player threshold bug
  - showed that HP-grounded prompting was the mechanism fix
- [Parity 3](../2026-03-20-fixed-damage-parity-3/README.md) and [Parity 4](../2026-03-20-fixed-damage-parity-4/README.md):
  - promoted the full stack into dedicated Flash parity tests
  - showed genuine competitiveness with Flash, though not yet a stable formal claim
- [Ablation 1](../2026-03-20-fixed-damage-ablation-1/README.md) and [Ablation 2](../2026-03-21-fixed-damage-ablation-2/README.md):
  - showed that removing TR or RC materially harms the stack
  - established that the final behavior was decomposable rather than accidental
- [Mini Baseline 1](../2026-03-20-fixed-damage-mini-baseline-1/README.md) and [Mini Parity 1](../2026-03-20-fixed-damage-mini-parity-1/README.md):
  - closed the causal gap against `gpt-4o-mini`
  - proved tuned Flash-Lite did not beat Mini just because Mini was weak in general
- [GPT-5 Mini Parity 1](../2026-03-21-fixed-damage-gpt5mini-parity-1/README.md):
  - established the ceiling for this branch
  - plain `gpt-5-mini` remained stronger than the tuned Flash-Lite stack
- [OpenAI Parity 1](../2026-03-21-fixed-damage-openai-parity-1/README.md), [OpenAI Parity 2](../2026-03-21-fixed-damage-openai-parity-2/README.md), and [OpenAI Margin 1](../2026-03-22-fixed-damage-openai-margin-1/README.md):
  - showed the same stack logic did not transfer automatically to `gpt-4o-mini`
  - `RC` alone made `gpt-4o-mini` much worse
  - prompt micro-tuning could fix local states without closing the full parity gap
- [FlashLite Cap 1](../2026-03-23-fixed-damage-cap-1/README.md):
  - showed that output capping was the wrong cost lever
  - it made Flash-Lite cheaper than Flash, but damaged the critical low-HP policy
- [FlashLite Exit 1](../2026-03-23-fixed-damage-exit-1/README.md):
  - closed the loop
  - a one-line no-potion escape clause removed the pathological tail and turned the old near-significant Flash parity result into a significant `35-13` win

## Final FixedDamage Answers
1. Can a weaker model become competitive through strategy?

Yes.
- Plain `FlashLite-AO` lost decisively to plain `Flash-AO` in [Parity 1](../2026-03-20-fixed-damage-parity-1/README.md).
- The final stack `FlashLite-RC-TR-HP-exit` beat `Flash-AO` `35-13` in [Exit 1](../2026-03-23-fixed-damage-exit-1/README.md).

2. Was the improvement real at the mechanism layer?

Yes.
- The behavioral layer repeatedly localized why the model failed:
  - second-player threshold inversion
  - pure-attack collapse
  - low-HP hesitation
  - no-potion deadlock tail
- Each major intervention was justified by state-level evidence before it was promoted.

3. Did the interventions decompose cleanly?

Yes.
- `RC` was essential for Flash-Lite.
- `TR` stabilized the policy across turns.
- `HP` grounding corrected the threshold reasoning itself.
- the no-potion exit clause removed a prompt-created tail defect.
- output caps were counterproductive in this task.

4. Did the same recipe work equally well on other models?

No.
- It transferred strongly enough to beat plain `gpt-4o-mini` when applied to Flash-Lite.
- It did not transfer cleanly to `gpt-4o-mini` itself.
- `gpt-5-mini` remained stronger than any tuned baseline we tried in FixedDamage.

## Competitive Endpoints That Matter
- Gemini ladder:
  - plain `Flash-AO` > plain `FlashLite-AO`
  - final `FlashLite-RC-TR-HP-exit` > plain `Flash-AO`
- OpenAI mini ladder:
  - plain `Mini-AO` crushed plain `FlashLite-AO`
  - tuned `FlashLite-RC-TR-HP` crushed plain `Mini-AO`
  - this is the strongest direct proof that the stack, not the base model, created the reversal
- Premium ceiling:
  - plain `gpt-5-mini` still beat tuned Flash-Lite
  - this set the upper boundary of the FixedDamage branch

## Cost Read
- The branch disproved the easy version of the business story.
  - the best-performing stack was not always the cheapest one on mean spend
- What it did show:
  - weak models can become much more competitive through prompt/controller strategy
  - average spend, median spend, and tail spend can tell different stories
  - naive output caps are a bad optimization if they clip the exact low-HP states where reasoning matters
- The successful final optimization was qualitative, not budgetary:
  - remove pathological dead-end reasoning
  - preserve policy quality

## Canonical Final Stack
The best Flash-Lite condition discovered in FixedDamage is:

- model: `gemini-2.5-flash-lite`
- controller: `ReasoningController`
- turn cadence: turn reinforcement via `{controller_format}`
- overlay: repaired HP-threshold grounding with explicit no-potion exit
- hidden Gemini thinking: `thinking_budget=0`
- no output cap

Exact carry-forward turn addition:

```text
{game_view}

{controller_format}

Before acting, calculate: does your current HP minus one ATTACK (20 damage) leave you alive?
If no and you still have potions, use POTION.
If no and you have no potions, ATTACK anyway.
Otherwise, act on your best read of the state.
```

Canonical source:
- [Exit 1 README](../2026-03-23-fixed-damage-exit-1/README.md)
- [Exit 1 analysis](../2026-03-23-fixed-damage-exit-1/analysis.md)
- [Exit 1 matrix](../2026-03-23-fixed-damage-exit-1/matrix.yaml)

## Why FixedDamage Is Done
- The game already answered the big research questions for this task class.
- New FixedDamage branches now have sharply diminishing returns.
- The remaining open problem is not more deterministic threshold tuning.
- It is whether the same strategy logic survives when exact arithmetic no
  longer solves the task cleanly.

## Next Research Move
- Start `VariableDamageGame` as a new branch.
- Carry `FlashLite-RC-TR-HP-exit` into that game as the opening Flash-Lite condition.
- Rebuild the behavioral layer around uncertainty and risk bands rather than exact HP thresholds.
