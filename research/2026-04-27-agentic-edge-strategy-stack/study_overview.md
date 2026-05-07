# AgentDeck Flagship Study: Final Definition

Experiment ID: `2026-04-27-agentic-edge-strategy-stack`  
Working title: **The Agentic Edge: Strategy Stack Effects on LLM Agency in Sequential Decision Environments**  
Status: completed study arc

## Why This Document Exists

This document is the final project definition for the AgentDeck flagship study.
It supersedes the original v0.1 planning note and captures what the study became
after pilot execution, main-run execution, targeted ladder completion, and
analysis.

The original plan asked whether AgentDeck could support a paper-grade
replication and extension study. The completed study answers a more concrete
question:

> Can agent design change LLM behavior enough to overcome a base-model tier gap
> in sequential decision environments?

The study is also a product proof for AgentDeck:

> AgentDeck can turn AI agent behavior into auditable evidence, not just run
> model-vs-model demos.

## Core Thesis

Agent behavior is not only a property of the base model.

It is a property of the complete agent configuration:

```text
model + controller + prompt contract + grounding + game environment + fairness policy
```

The study uses controlled games to show how that configuration affects
decisions over time: when to attack, when to heal, how to handle risk, whether
resources are wasted, whether behavior changes by seat, and what the cost of
better behavior is.

## What We Actually Ran

The completed package lives at:

```text
research/2026-04-27-agentic-edge-strategy-stack/
```

The durable artifact store is the Hugging Face dataset:

```text
https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study
```

The curated replay viewer is deployed as a Hugging Face Space:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

Initial full artifact snapshot:

```text
13b95490cdc21dbfb1c164c683e485755f90a271
```

Latest study-arc aggregate refresh:

```text
f7ac119f69da08261269bc5cf85fb65741e8ae88
```

Latest curated replay Space snapshot:

```text
27ca787db947a393d21ed9847a8a4b44b2cbc317
```

GitHub references for the package and viewer:

- Study package: [`e9dc6a77`](https://github.com/agentdeck/agentdeck/commit/e9dc6a77b3495dc80b6deed71b07a2af83c1cc64)
- Portable viewer: [`f98e05c5`](https://github.com/agentdeck/agentdeck/commit/f98e05c5efbbb558594aaccd08fd370d92360d85)
- Curated viewer examples: [`b8771c4d`](https://github.com/agentdeck/agentdeck/commit/b8771c4d21ab5591b3d37aee44eaf307acaee13f)
- Implementation reference: [`d659bdf2`](https://github.com/agentdeck/agentdeck/commit/d659bdf244d1f0462c0d43aa2609be6c3c4a7672)

The execution freeze remains documented in `matrix.yaml`; these GitHub
references document the curated package and viewer commits.

The official aggregate includes the primary fixed-N study phase plus the
targeted FixedDamage S1 ladder-completion cell.

| Phase | Purpose | Status |
| --- | --- | --- |
| P0 | Local bot smoke tests, no provider calls | complete |
| P1 | Live-provider pilot, 8 cells x 12 matches | complete |
| P2 | Primary fixed-N study phase, 8 cells x 48 matches | complete |
| P3 | Targeted FixedDamage S1 cross-tier ladder completion | complete |

The official study arc is scoped by `matrix.yaml`:

```yaml
phase_model:
  study_phases: [P2, P3]
```

This keeps P0 preflight and P1 pilot evidence outside the official topline while
including the S1 ladder step needed for the FixedDamage S0 -> S1 -> S3 arc.

## Games

### FixedDamageGame

FixedDamage is the deterministic behavioral wind tunnel.

Damage is fixed at 20, so survival thresholds are clear. This makes it useful
for studying:

- survival logic,
- potion timing,
- resource waste,
- critical-state behavior,
- all-attack collapse,
- seat-conditioned policy drift.

### VariableDamageGame

VariableDamage is the stochastic transfer environment.

Damage varies from 15 to 25, so the agent cannot rely on a single deterministic
threshold. This makes it useful for studying:

- risk under uncertainty,
- danger and lethal-zone behavior,
- whether FixedDamage repairs transfer,
- whether grounding must be rewritten for the new environment.

## Models

The final study used two live model families:

| Label | Provider | Model | Role |
| --- | --- | --- | --- |
| FlashLite | Google | `gemini-2.5-flash-lite` | lower-tier/lite model |
| GPT4oMini | OpenAI | `gpt-4o-mini` | stronger practical baseline |

This study is not a broad leaderboard. It is a controlled agent-configuration
study.

## Strategy Conditions

The final ladder used S0, S1, and S3. S2 was considered during planning but not
run because P1 showed S1 and S3 were sufficient for a clean first study.

### S0: Action-Only Baseline

Controller: `ActionOnlyController`

The model received the game view and a minimal action format:

```text
ACTION: <attack|potion>
```

Purpose: measure raw behavior with minimal operational scaffolding.

### S1: ReasoningController

Controller: `ReasoningController`

The model had to produce a reasoning field before choosing an action:

```text
REASONING: ...
ACTION: <attack|potion>
```

Purpose: isolate the effect of structured reasoning and action formatting.

Important: S1 did not include the FixedDamage 20 HP survival rule or the
VariableDamage risk-band policy.

### S3: Reasoning Plus Game-Specific Grounding

Controller: `ReasoningController`

S3 kept the S1 reasoning/action structure and repeated game-specific grounding
inside the turn prompt.

FixedDamage S3 used HP survival grounding:

```text
Before acting, calculate whether your current HP minus one ATTACK (20 damage) leaves you alive.
- If no and you still have potions, use POTION.
- If no and you have no potions, ATTACK anyway.
- If yes, act on your best read of the state.
- Do not use POTION at full health.
```

VariableDamage S3 used risk-band grounding:

```text
Before acting, check your risk band carefully.
- If your HP is above 55, do not use POTION.
- If your HP is 25 or lower and you have potions, use POTION.
- If your HP is 26 to 40 and you have 2 or 3 potions, prefer POTION now rather than entering the lethal zone with fewer resources.
- If your HP is 25 or lower and you have no potions, ATTACK anyway.
- Otherwise, act on your best read of the state.
```

Purpose: test whether explicit game-policy grounding adds margin and improves
behavioral consistency beyond S1.

## Research Workflow Surfaces Exercised

The study intentionally used AgentDeck's major research workflow surfaces where
they strengthened validity:

- matrix-defined cells in `matrix.yaml`,
- fixed seeds and seed offsets,
- paired side-swap fairness,
- random first-player policy,
- frozen prompt templates,
- controller and prompt interventions,
- recorder artifacts,
- per-cell export,
- package export,
- deterministic `results.md`,
- artifact validation,
- built-in behavioral profiles,
- cost and format-strictness metrics,
- authored analysis under `analysis/`,
- external raw-recording pointer policy.

The study did not use every AgentDeck API for its own sake. The guiding rule
was:

> Exercise every major AgentDeck research workflow surface that strengthens
> validity.

## Main Results

### FixedDamage: Strong Tier Inversion

The FixedDamage ladder is the clearest result:

| Condition | Matchup | FlashLite win rate |
| --- | --- | ---: |
| S0 | FlashLite-S0-AO vs GPT4oMini-S0-AO | 0.0% |
| S1 | FlashLite-S1-RC vs GPT4oMini-S0-AO | 70.8% |
| S3 | FlashLite-S3-HP vs GPT4oMini-S0-AO | 79.2% |

Interpretation:

- Unscaffolded FlashLite lost every match to GPT4oMini in FixedDamage.
- Structured reasoning alone crossed the model-tier boundary.
- HP grounding added margin and made the policy easier to audit.

The strongest FixedDamage claim is:

> In this controlled sequential game, agent design was large enough to reverse a
> model-tier outcome.

### VariableDamage: Strong Within-Model Repair, Weak Cross-Tier Frontier

VariableDamage showed strong stack transfer inside the FlashLite family:

- `FlashLite-S3-RISK` beat `FlashLite-S0-AO` 41/48 matches, or 85.4%.

The cross-tier VariableDamage frontier was weaker:

- `FlashLite-S3-RISK` beat `GPT4oMini-S0-AO` 28/48 matches, or 58.3%.
- The result was not statistically significant.
- The cell was heavily seat-confounded.

Interpretation:

- The architecture transferred when grounding was rewritten for stochastic
  risk.
- The VariableDamage cross-tier frontier should not be used as a strong
  dominance claim.

## Behavioral Findings

Win rate is not the whole story. The behavioral metrics show why behavior
changed.

In FixedDamage:

- S0 FlashLite often collapsed into attack-only behavior and lost with unused
  potions.
- S1 reduced attack-only collapse and improved critical-state recovery.
- S3 nearly eliminated the worst resource-use failures and aligned potion timing
  with the prompted survival policy.

In VariableDamage:

- S1 shifted FlashLite toward earlier risk-sensitive healing.
- S3-RISK avoided safe-zone potion waste and healed reliably in lethal-zone
  opportunities.

Behavioral metrics used:

- all-attack match rate,
- first potion profile,
- never-used-potion rate,
- unused potions on loss,
- state-action consistency,
- position policy delta,
- critical potion response rate,
- error recovery rate,
- wasted full-health potion rate,
- risk-band potion rates for VariableDamage.

## Cost Interpretation

The result is not "the cheaper model won."

After scaffolding, FlashLite was a lower-tier model but not cheaper in the
frontier cells. Reasoning and longer prompts increased token cost.

Correct framing:

> The stack bought better outcome quality in FixedDamage, but it did not create
> a simple cost win.

This matters commercially because it reframes the question from:

> Which model is cheapest?

to:

> Which agent configuration produces the best behavior per dollar for the task?

## Hypothesis Readout

| Hypothesis | Result |
| --- | --- |
| H1: Strategy stacks reduce survival-policy failures | confirmed |
| H2: ReasoningController improves behavior for unstable models | confirmed |
| H3: Grounding adds value beyond reasoning | supported, but partly cross-cell |
| H4: Strategy stacks reduce seat drift | inconclusive |
| H5: Scaffolded lower-tier model can beat stronger unscaffolded model | confirmed in FixedDamage, not established in VariableDamage |
| H6: FixedDamage improvements transfer partially to VariableDamage | refined: architecture transferred when grounding was adapted |

## What This Proves

This study proves a narrow but important claim:

> In controlled sequential decision environments, the agent stack can change
> behavior enough to alter outcomes, including a FixedDamage model-tier
> inversion.

It also proves a product claim:

> AgentDeck can produce auditable behavioral evidence about AI agents: prompts,
> actions, costs, position effects, behavioral metrics, generated reports, and
> authored analysis can all be traced through one reproducible package.

## What This Does Not Prove

The study does not prove that:

- smaller models are generally better,
- smaller models are always cheaper after scaffolding,
- FixedDamage prompts transfer unchanged to stochastic games,
- strategy stacks generalize to all real-world tasks,
- VariableDamage cross-tier dominance was established.

The correct scope is:

> Within these games, model configurations, prompt templates, and provider
> conditions, agent design materially changed behavior and FixedDamage outcomes.

## Public Narrative

For a general audience:

> We showed that AI performance is not only about choosing the strongest model.
> A weaker model with a better operating procedure can behave more reliably than
> a stronger model with weak structure. In FixedDamage, structured reasoning
> moved FlashLite from 0.0% to 70.8% against GPT4oMini, and explicit grounding
> moved it to 79.2%.

For a technical audience:

> The study isolates controller and grounding effects in paired, seeded,
> matrix-defined sequential games. The largest intervention effect came from
> ReasoningController; game-specific grounding added smaller but meaningful
> policy precision. Seat effects were observable and materially affected
> VariableDamage interpretation.

For AgentDeck positioning:

> AgentDeck is a research platform for studying AI agents as behaving systems,
> not just answer generators.

## Canonical Source Files

- [`README.md`](README.md) - package entry point and execution status
- [`manifest.yaml`](manifest.yaml) - package metadata
- [`matrix.yaml`](matrix.yaml) - study phases, cells, configs, fairness, seeds
- [`results.md`](results.md) - deterministic factual report for the official study aggregate
- [`analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md`](analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md) - official authored interpretation
- [`analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md`](analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md) - raw prompt/protocol transparency
- [`analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md`](analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md) - behavioral metric narrative
- [`analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md`](analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md) - business-facing explanation
- [`analysis/analysis_20260428_152909_codex_official_study_analysis/support/s1_frontier_followup.md`](analysis/analysis_20260428_152909_codex_official_study_analysis/support/s1_frontier_followup.md) - P3 S1 cross-tier follow-up
- [`recordings/README.md`](recordings/README.md) - Hugging Face artifact pointer and uploaded layout
