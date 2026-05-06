# Presentation Outline

Status: draft  
Goal: short visual deck or video explaining the AgentDeck flagship study.

## Core Message

Agent quality is not only model tier. It is the full operating setup:
`model + controller + prompt contract + grounding + game + fairness policy`.
FixedDamage ladder: FlashLite moved from `0.0%` to `70.8%` to `79.2%`
against GPT4oMini as the workflow improved.

## Slide 1 - The Question

Title: Can agent design beat model tier?

Say: This study asks whether the operating wrapper around a model can change
agent behavior enough to reverse outcomes.

## Slide 2 - The Test Environment

Title: A simple game that exposes decision quality

- FixedDamage: deterministic 20 damage.
- VariableDamage: stochastic 15-25 damage.
- Core action loop: attack or potion.
- Partial information: players saw their own HP/potions, not opponent HP/potions.
- Fairness: paired side-swap.

Point: agents were not given a full board-state oracle.

## Slide 3 - What We Changed

Title: What is a strategy stack?

| Concept | Plain meaning | In this study |
| --- | --- | --- |
| Action-only | agent only outputs the move | `ACTION: ATTACK` or `ACTION: POTION` |
| Reasoning controller | agent explains before acting | `REASONING: ... ACTION: ...` |
| Grounding | explicit task rules repeated in context | HP rule in FixedDamage; risk bands in VariableDamage |

Guardrail: S1 reasoning and S3 grounding are different. S1 did **not** receive
the 20 HP rule. S3 did.

## Slide 4 - The Tuning Ladder

Title: S0 to S1 to S3

| Step | Change | Meaning |
| --- | --- | --- |
| S0 | Action only | raw baseline |
| S1 | reasoning before action | structured decision process |
| S3 | reasoning + game grounding | auditable procedure-following |

Guardrail: **S1 did not include the 20 HP rule. S3 did.**

## Slide 5 - Baseline Failure

Title: The weaker model had potions, but did not use them

- FixedDamage: `FlashLite-S0-AO` vs `GPT4oMini-S0-AO`.
- FlashLite: `0/48`, `0.0%`.
- FlashLite all-attack match rate: `70.83%`.
- FlashLite lost with unused potions in `100.00%` of losses.
- Replay: `Study 1: Baseline Failure - FlashLite Never Heals`.

## Slide 6 - Reasoning Pivot

Title: Structured reasoning changes the critical decision

- FixedDamage: `FlashLite-S1-RC` vs `GPT4oMini-S0-AO`.
- FlashLite: `34/48`, `70.8%`.
- S1 required reasoning before action, but did **not** give the HP rule.
- Replay: `Study 2: Reasoning Pivot - FlashLite Survives`.

## Slide 7 - Grounded Stack

Title: Grounding makes the procedure explicit

- FixedDamage: `FlashLite-S3-HP` vs `GPT4oMini-S0-AO`.
- FlashLite: `38/48`, `79.2%`.
- S3 added explicit game-specific HP grounding.
- Claim: the model executed a prompted policy; it did not discover it by itself.
- Replay: `Study 3: Grounded Stack - The Policy Runs`.

## Slide 8 - Behavior Changed Beyond Win Rate

Title: The model did not just win more. It behaved differently.

- S0: attacked through danger and wasted potions.
- S1: reduced all-attack collapse and improved critical recovery.
- S3 FixedDamage: aligned with the 20 HP survival threshold.
- S3 VariableDamage: used risk-band healing.

## Slide 9 - Transfer Under Uncertainty

Title: The architecture transferred, but the rule had to change

- VariableDamage: `FlashLite-S3-RISK` vs `FlashLite-S0-AO`.
- FlashLite-S3-RISK: `41/48`, `85.4%`.
- This is within-model adapted transfer.
- HP grounding was rewritten as risk-band grounding.
- Replay: `Study 4: Risk Grounding - Handling Uncertainty`.

## Slide 10 - VariableDamage Caveat

Title: Cross-tier VariableDamage is not a dominance claim

- VariableDamage: `FlashLite-S3-RISK` vs `GPT4oMini-S0-AO`.
- FlashLite: `28/48`, `58.3%`.
- `p=0.312`, negligible effect.
- First-player win rate: `87.5%`.
- FlashLite seat split: `23/24` as first, `5/24` as second.
- Replay: `Study 5: Caveat - Good Policy Still Loses`.

## Slide 11 - Cost and Business Meaning

Title: Better behavior, higher cost

- This is an outcome-quality story, not a cheap-model story.
- Scaffolded FlashLite cost more per player-match than unscaffolded GPT4oMini
  because reasoning and grounding increased tokens.
- Business question: which full agent configuration produces reliable behavior
  for the task and budget?

## Slide 12 - What AgentDeck Adds

Title: Auditable evidence, not just benchmark scores

Show: matrix-defined cells, frozen prompts, paired side swaps, recordings,
behavioral metrics, cost telemetry, replay viewer, Hugging Face artifact store.

## Slide 13 - Final Claim

Title: Evaluate agents as systems

Say: In controlled sequential decision games, agent design changed behavior enough
to reverse a FixedDamage model-tier outcome.

Avoid:

- smaller models are generally better,
- scaffolded smaller models are always cheaper,
- VariableDamage cross-tier dominance,
- S3 made the model discover the rule by itself.

## Source Links

- Dataset: `https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study`
- Viewer: `https://huggingface.co/spaces/agentdeck/agentic-edge-viewer`
- Factual report: [`../results.md`](../results.md)
- Official analysis: [`../analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md)
