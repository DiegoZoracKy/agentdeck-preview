# The Agentic Edge: Public Findings Report

Status: draft  
Experiment: `2026-04-27-agentic-edge-strategy-stack`

## Short Version

This study shows that AI agent performance is not only about the base model.
In a controlled sequential decision game, changing the agent wrapper changed the
behavior enough to reverse a model-tier outcome.

The clearest result is FixedDamage:

| Step | Matchup | FlashLite result |
| --- | --- | ---: |
| S0 baseline | FlashLite-S0-AO vs GPT4oMini-S0-AO | 0/48, 0.0% |
| S1 reasoning | FlashLite-S1-RC vs GPT4oMini-S0-AO | 34/48, 70.8% |
| S3 grounded stack | FlashLite-S3-HP vs GPT4oMini-S0-AO | 38/48, 79.2% |

The headline claim is narrow but strong:

> In FixedDamage, structured agent design moved a lower-tier model from losing
> every match to beating a stronger unscaffolded model in 79.2% of matches.

## What Was Tested

The study used AgentDeck to run AI agents through turn-based combat games. Each
agent had to decide when to attack and when to use limited healing resources.

The study compared:

- Gemini Flash-Lite as the lower-tier model.
- GPT-4o-mini as the stronger practical baseline.
- Action-only agents.
- Agents that had to reason before acting.
- Agents with reasoning plus game-specific grounding rules.

This was not a broad model leaderboard. It was a controlled test of agent
configuration:

```text
model + controller + prompt contract + grounding + game + fairness policy
```

## The Tuning Ladder

### S0: Minimal Action Format

The baseline agent received the game rules and a minimal action contract.

```text
ACTION: <attack|potion>
```

In FixedDamage, FlashLite-S0-AO never beat GPT4oMini-S0-AO across 48 matches.
Behaviorally, the weaker model often attacked until death while still holding
unused potions.

Curated replay: `Study 1: Baseline Failure - FlashLite Never Heals`.

### S1: Structured Reasoning Before Action

S1 required a reasoning field before the action field.

```text
REASONING: ...
ACTION: <attack|potion>
```

S1 did not include the FixedDamage 20 HP survival rule and did not include the
VariableDamage risk-band rule. It changed the decision process, not the game
policy.

In FixedDamage, this step alone crossed the model-tier boundary:
FlashLite-S1-RC beat GPT4oMini-S0-AO 34/48 matches, or 70.8%.

Curated replay: `Study 2: Reasoning Pivot - FlashLite Survives`.

### S3: Structured Reasoning Plus Game-Specific Grounding

S3 kept the reasoning/action structure and added explicit task grounding.

For FixedDamage, the grounding told the agent to check whether one more
20-damage attack would leave it alive. If not, and it still had a potion, it
should use the potion.

For VariableDamage, the grounding used risk bands because incoming damage varied
from 15 to 25.

In FixedDamage, FlashLite-S3-HP beat GPT4oMini-S0-AO 38/48 matches, or 79.2%.
S3 also made the decision policy easier to audit because the prompt connected
the action to specific HP survival logic.

Curated replay: `Study 3: Grounded Stack - The Policy Runs`.

## Behavioral Findings Beyond Win Rate

Win rate says who won. The behavioral metrics show why.

FixedDamage:

- FlashLite-S0-AO had a 70.83% all-attack match rate in the S0 tier-gap cell.
- FlashLite-S0-AO lost with unused potions in 100.00% of its losses in that
  cell.
- FlashLite-S1-RC reduced all-attack collapse and improved critical recovery.
- FlashLite-S3-HP nearly eliminated the worst resource-use failures in the
  full-stack FixedDamage cell.
- In the S3 frontier cell, FlashLite-S3-HP used its first potion at median
  HP=20, while GPT4oMini-S0-AO used first potion at median HP=80.

VariableDamage:

- FlashLite-S3-RISK beat FlashLite-S0-AO 41/48 matches, or 85.4%.
- Its behavior improved strongly: no all-attack matches, no losses with unused
  potions, no safe-zone potion waste, and 100.00% lethal-zone potion response in
  the S3 risk-stack cell.

## The VariableDamage Caveat

VariableDamage supports the within-model repair story, but not a strong
cross-tier dominance story.

The cross-tier VariableDamage frontier cell was:

```text
FlashLite-S3-RISK 28/48 (58.3%) vs GPT4oMini-S0-AO 20/48 (41.7%)
```

That aggregate should be caveated:

- p-value: 0.312
- effect: negligible
- first-player win rate: 87.5%
- FlashLite-S3-RISK as first player: 23/24
- FlashLite-S3-RISK as second player: 5/24

The correct public framing is:

> The adapted risk stack repaired FlashLite strongly in VariableDamage, but this
> run did not establish robust cross-tier superiority over GPT4oMini.

Curated replay: `Study 5: Caveat - Good Policy Still Loses`.

## Cost Framing

This is not a cheap-model story.

In the official aggregate, average cost per player-match was:

| Player | Avg cost |
| --- | ---: |
| FlashLite-S0-AO | $0.000613 |
| FlashLite-S1-RC | $0.001412 |
| FlashLite-S3-HP | $0.002317 |
| FlashLite-S3-RISK | $0.002501 |
| GPT4oMini-S0-AO | $0.001192 |

The stack bought better FixedDamage behavior, but it increased token usage. The
business question is not "which model is cheapest?" It is:

> Which full agent configuration produces the best behavior for the task and
> budget?

## What This Proves

This study supports these claims:

- Agent behavior is shaped by the complete agent stack, not only the base model.
- In FixedDamage, structured reasoning alone changed enough behavior to reverse
  a model-tier outcome.
- In FixedDamage, game-specific grounding added margin and made the policy more
  auditable.
- In VariableDamage, the adapted stack repaired FlashLite strongly against its
  own baseline.
- AgentDeck produced an auditable trail: matrix, prompts, recordings, generated
  results, behavioral metrics, costs, position effects, and authored analysis.

## What This Does Not Prove

This study does not prove that:

- smaller models are generally better,
- scaffolded smaller models are always cheaper,
- FixedDamage rules transfer unchanged to stochastic games,
- the VariableDamage cross-tier frontier was robust,
- these game results generalize automatically to all business workflows.

The correct scope is:

> Within these games, model configurations, prompts, and provider conditions,
> agent design materially changed behavior and FixedDamage outcomes.

## Replay Evidence

Private draft Space:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

Curated examples:

1. Baseline Failure - FlashLite never heals.
2. Reasoning Pivot - the same HP=20 moment becomes a heal.
3. Grounded Stack - the survival policy runs visibly.
4. Risk Grounding - the stack adapts to uncertain damage.
5. Caveat - good risk policy still loses from second seat.

