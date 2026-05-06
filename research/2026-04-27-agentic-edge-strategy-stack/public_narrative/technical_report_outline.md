# Technical Report Outline

Status: draft  
Experiment: `2026-04-27-agentic-edge-strategy-stack`

This outline is for a public technical report or case-study report. It is not a
new source of facts. Quantitative claims must be checked against `../results.md`
and the per-cell artifacts before publication.

## Recommended Artifact Type

Recommended default: **technical case study**.

Rationale:

- The FixedDamage result is strong enough for a public technical story.
- The VariableDamage cross-tier result is useful but caveated by seat effects
  and non-significance.
- The study has strong artifact provenance, prompt transparency, behavioral
  metrics, and replay examples.
- A paper-style artifact remains possible later, but would benefit from a
  broader model roster or an additional VariableDamage expansion focused on
  position effects.

## Working Title

**The Agentic Edge: How Strategy Stacks Changed LLM Agent Behavior in Sequential
Decision Games**

Alternative:

**Agent Design Beats Model Tier in a Controlled Survival Game**

## Abstract Shape

One paragraph:

- State the question: whether controller and prompt design can change agent
  behavior enough to overcome a base-model tier gap.
- State the setting: AgentDeck, two partial-information sequential decision
  games, two model families, fixed-N paired side-swap cells.
- State the main result: in FixedDamage, FlashLite moved from 0/48 against
  GPT4oMini-S0 to 34/48 with S1 and 38/48 with S3.
- State the behavioral result: all-attack collapse and potion misuse were
  reduced, not merely win rate changed.
- State the caveat: VariableDamage repaired within-model behavior strongly but
  did not establish robust cross-tier superiority.

## 1. Introduction

Purpose:

- Explain why static model leaderboards are insufficient for agentic behavior.
- Introduce the thesis that behavior is a property of:

```text
model + controller + prompt contract + grounding + game + fairness policy
```

Core claim:

- AgentDeck makes this configuration observable and auditable through match
  recordings, generated results, behavioral profiles, and replayable examples.

## 2. Study Design

Cover:

- Experiment package path.
- P2 + P3 official study scope.
- P0/P1 as preflight/pilot only.
- Fixed-N sampling.
- Paired side-swap and random first-player policy.
- Partial-information game views: players did not receive opponent hidden
  statistics in the prompt.
- Models:
  - `gemini-2.5-flash-lite`
  - `gpt-4o-mini`
- Games:
  - FixedDamageGame as deterministic wind tunnel.
  - VariableDamageGame as stochastic transfer environment.

## 3. Strategy Conditions

Define the ladder:

- S0: ActionOnlyController, minimal action contract.
- S1: ReasoningController, reasoning before action, no 20 HP rule and no risk
  bands.
- S3: ReasoningController plus game-specific grounding.

Prompt-transparency requirement:

- Include concise excerpts from the real prompts.
- Avoid paraphrases that imply S1 had the S3 survival rule.
- Clearly state that FixedDamage S3 used explicit 20-damage survival arithmetic.
- Clearly state that VariableDamage S3 used risk bands because damage was
  stochastic.

## 4. Main Results

FixedDamage ladder:

| Step | Matchup | FlashLite result |
| --- | --- | ---: |
| S0 | FlashLite-S0-AO vs GPT4oMini-S0-AO | 0/48, 0.0% |
| S1 | FlashLite-S1-RC vs GPT4oMini-S0-AO | 34/48, 70.8% |
| S3 | FlashLite-S3-HP vs GPT4oMini-S0-AO | 38/48, 79.2% |

VariableDamage:

- Within-model repair: FlashLite-S3-RISK beat FlashLite-S0-AO 41/48, 85.4%.
- Cross-tier frontier: FlashLite-S3-RISK beat GPT4oMini-S0-AO 28/48, 58.3%,
  but this is caveated by p=0.312, negligible effect, and severe first-player
  skew.

## 5. Behavioral Analysis

Use `support/behavioral_metrics_digest.md` and `../results.md`.

Topics:

- All-attack collapse.
- Losses with unused potions.
- Critical potion response.
- First potion HP profile.
- Safe-zone waste in VariableDamage.
- Position effects.

Core message:

- The stack changed specific decision patterns, not just aggregate win rate.

## 6. Replay Evidence

Use the five curated Space examples:

- Study 1: baseline failure.
- Study 2: reasoning pivot.
- Study 3: grounded policy execution.
- Study 4: risk grounding under uncertainty.
- Study 5: caveat where good policy still loses.

Purpose:

- Show readers the behavior directly instead of only describing tables.

## 7. Cost and Operational Framing

Core points:

- This is not a cheap-model claim.
- FlashLite S3 costs more per player-match than GPT4oMini-S0 in this study.
- The practical question is full agent configuration quality per task and
  budget, not model sticker price.

Include:

- Per-player cost table from `../results.md`.
- Note that provider pricing can drift.

## 8. Limitations

Required limitations:

- Synthetic games.
- Narrow model roster.
- Provider/model drift.
- Prompt specificity.
- Partial-information game setting may not generalize directly.
- VariableDamage seat effects.
- VariableDamage cross-tier result was not statistically significant.
- No broad domain generalization claim.
- No claim that models discovered the S3 policy unaided.

## 9. Reproducibility and Artifact Trail

List:

- Git commit/code reference.
- `manifest.yaml`.
- `matrix.yaml`.
- prompt templates.
- raw recordings on Hugging Face.
- deterministic `results.md`.
- per-cell artifacts.
- authored analysis and provenance.
- curated replay Space.

## 10. Conclusion

Recommended conclusion:

> In this controlled setting, agent design changed behavior enough to reverse a
> FixedDamage model-tier outcome. The result is narrow, auditable, and
> operationally meaningful: the agent wrapper can matter as much as the base
> model for sequential decision behavior.

Avoid:

- "A smaller model is generally better."
- "S3 is cheaper."
- "The strategy transfers unchanged."
- "VariableDamage proves cross-tier dominance."
- "The model discovered the strategy by itself."
