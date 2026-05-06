# Protocol and Prompt Audit

Experiment: `2026-04-27-agentic-edge-strategy-stack`  
Scope: P2 primary phase, P3 S1 ladder-completion cell, and the prompt/config
surfaces that produced them  
Status: ad-hoc transparency supplement for the official study analysis

## Purpose

This document explains exactly what was tuned in the Agentic Edge study. It is
meant to prevent an overbroad reading of the result.

The study did not simply test whether generic reasoning or chain-of-thought
improves a weaker model. It tested a stack made of:

1. A controller/output-format intervention.
2. A game-specific grounding intervention.
3. A repeated turn-time instruction surface.

The strongest result should therefore be described as:

> A lower-tier model can outperform a stronger unscaffolded model when it is
> given structured reasoning plus explicit game-policy grounding in the tested
> environment.

It should not be described as:

> The lower-tier model discovered the strategy on its own.

## Execution Surface

The package-local runner is
[`scripts/run_experiment.py`](../../../scripts/run_experiment.py). It reads
[`matrix.yaml`](../../../matrix.yaml), resolves each selected cell, builds the
game, creates the players, injects prompt templates, and calls `AgentDeck.play`.

The study used:

- `FixedDamageGame(information_level="partial", attack_damage=20)`.
- `VariableDamageGame(information_level="partial", min_attack_damage=15,
  max_attack_damage=25)`.
- `pairing_policy: paired_side_swap`.
- `first_player_policy: random`.
- `max_turns: 40`.
- `conclusion.enabled: false`.
- `temperature: 0.2` for both live LLM providers.
- `gemini-2.5-flash-lite` with `thinking_budget: 0`.
- `gpt-4o-mini`.

P2 was the primary fixed-N study phase. P3 was added as a targeted FixedDamage
S1 cross-tier ladder-completion cell. P0 smoke tests and P1 pilot cells are
excluded from the package aggregate by `phase_model.study_phases: [P2, P3]`.

## Strategy Conditions

### S0_AO - Action-only baseline

Controller: `ActionOnlyController`  
Turn template: [`prompts/turn_action_only.txt`](../../../prompts/turn_action_only.txt)

Raw turn template:

```text
{game_view}

{controller_format}
```

Expanded controller format after game binding:

```text
Respond with: ACTION: <action>
Allowed actions: ATTACK, POTION
```

This condition did not ask the model to produce reasoning and did not add any
HP threshold, risk-band, or strategy advice beyond the game rules.

### S1_RC - ReasoningController only

Controller: `ReasoningController`  
Turn template: [`prompts/turn_reasoning.txt`](../../../prompts/turn_reasoning.txt)

Raw turn template:

```text
{game_view}

{controller_format}
```

Expanded controller format after game binding:

```text
Please respond in the following format:
REASONING: [Your step-by-step thought process]
ACTION: [Your chosen action]
Allowed actions: ATTACK, POTION
```

This is the generic reasoning/output-structure intervention. It forced a
reasoning field before the action field, but it did not encode the FixedDamage
20 HP rule or the VariableDamage risk-band policy.

### S3_FIXED_FULL - ReasoningController plus FixedDamage HP grounding

Controller: `ReasoningController`  
Turn template:
[`prompts/turn_fixed_full_stack.txt`](../../../prompts/turn_fixed_full_stack.txt)

Raw turn template:

```text
{game_view}

{controller_format}

Before acting, calculate whether your current HP minus one ATTACK (20 damage) leaves you alive.
- If no and you still have potions, use POTION.
- If no and you have no potions, ATTACK anyway.
- If yes, act on your best read of the state.
- Do not use POTION at full health.
```

This condition included explicit domain-policy grounding. It was not merely
"think carefully." It told the player to evaluate a one-attack survival
threshold and gave action guidance for the result.

This is close to a compact policy rule. That is acceptable for this study only
if the claim is framed honestly: the stack made the model reliably execute a
known game policy; it did not prove the model independently discovered that
policy.

### S3_VARIABLE_FULL - ReasoningController plus VariableDamage risk grounding

Controller: `ReasoningController`  
Turn template:
[`prompts/turn_variable_full_stack.txt`](../../../prompts/turn_variable_full_stack.txt)

Raw turn template:

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

This was also explicit policy grounding. It adapted the FixedDamage threshold
idea to the stochastic VariableDamage environment by replacing a fixed 20-damage
survival check with risk-band guidance.

This means the study tested adapted transfer, not raw prompt transfer. The
architecture transferred; the grounding instructions were rewritten for the
game.

## Handshake Prompt

All strategy conditions used the same handshake template:
[`prompts/handshake_default.txt`](../../../prompts/handshake_default.txt).

Raw handshake template:

```text
{game_instructions}

When gameplay begins, use this response format:
{controller_format}

{handshake_controller_format}
```

The handshake front-loaded the game rules and the response format. It did not
include the S3 HP or risk-band grounding. Those were repeated only in the turn
prompt.

### Expanded FixedDamage handshake: action-only player

Example from a P2 FixedDamage frontier recording:
[`match_ff29140b.json`](../../../agentdeck_runs/p2_fd_frontier_s3/session_20260427_232501_92cb00/records/match_ff29140b.json)

```text
Fixed Damage Combat Game

Starting Conditions:
- Each player starts with 100 HP
- Each player has 3 potions

Actions:
- ATTACK: Deals 20 damage to opponent
- POTION: Restores 30 HP (max 100)

Win Condition:
- First player to reduce opponent to 0 HP wins
- If both reach 0 HP simultaneously, the match is a draw

Information Level: partial
- "full": Players see all stats (opponent HP/potions)
- "partial": Players see only their own HP/potions, but last actions remain visible

When gameplay begins, use this response format:
Respond with: ACTION: <action>
Allowed actions: ATTACK, POTION

Reply with exactly 'OK' and nothing else if you understand and are ready to begin.
```

### Expanded FixedDamage handshake: reasoning player

Example from the same P2 FixedDamage frontier recording:
[`match_ff29140b.json`](../../../agentdeck_runs/p2_fd_frontier_s3/session_20260427_232501_92cb00/records/match_ff29140b.json)

```text
Fixed Damage Combat Game

Starting Conditions:
- Each player starts with 100 HP
- Each player has 3 potions

Actions:
- ATTACK: Deals 20 damage to opponent
- POTION: Restores 30 HP (max 100)

Win Condition:
- First player to reduce opponent to 0 HP wins
- If both reach 0 HP simultaneously, the match is a draw

Information Level: partial
- "full": Players see all stats (opponent HP/potions)
- "partial": Players see only their own HP/potions, but last actions remain visible

When gameplay begins, use this response format:
Please respond in the following format:
REASONING: [Your step-by-step thought process]
ACTION: [Your chosen action]
Allowed actions: ATTACK, POTION

Reply with exactly 'OK' and nothing else if you understand and are ready to begin.
```

## Turn Prompt Composition

Every turn prompt had this shape:

```text
{text_renderer_game_view}

{controller_format}

{optional_strategy_grounding}
```

The game view was produced by `TextRenderer` from each player's partial
information view. With `information_level="partial"`, players saw their own HP
and potions, not the opponent's hidden HP/potion state. Last actions remained
visible.

Example game-view skeleton:

```text
=== Current Game State ===
You are: <player_name>
Turn: <turn_number>

Health:
  You: <own_hp>

Potions:
  You: <own_potions>

Last Action:
  <player_a>: <last_action_or_None>
  <player_b>: <last_action_or_None>

=========================
```

## Expanded Turn Examples

### FixedDamage S3 turn at the lethal threshold

Example from
[`match_ff29140b.json`](../../../agentdeck_runs/p2_fd_frontier_s3/session_20260427_232501_92cb00/records/match_ff29140b.json):

```text
=== Current Game State ===
You are: FlashLite-S3-HP
Turn: 14

Health:
  You: 20

Potions:
  You: 3

Last Action:
  GPT4oMini-S0-AO: ATTACK
  You: ATTACK

=========================

Please respond in the following format:
REASONING: [Your step-by-step thought process]
ACTION: [Your chosen action]
Allowed actions: ATTACK, POTION

Before acting, calculate whether your current HP minus one ATTACK (20 damage) leaves you alive.
- If no and you still have potions, use POTION.
- If no and you have no potions, ATTACK anyway.
- If yes, act on your best read of the state.
- Do not use POTION at full health.
```

The recorded response was:

```text
REASONING: My current HP is 20. An ATTACK from the opponent deals 20 damage. 20 - 20 = 0. If I am attacked, I will reach 0 HP. Since I have potions (3 remaining) and would not survive an attack, I should use a POTION to heal.
ACTION: POTION
```

This is the clearest example of why the S3 condition should be treated as
explicit policy execution, not strategy discovery.

### FixedDamage S0 action-only turn

Example from the same frontier recording, for the unscaffolded GPT4oMini player:

```text
=== Current Game State ===
You are: GPT4oMini-S0-AO
Turn: 22

Health:
  You: 10

Potions:
  You: 0

Last Action:
  FlashLite-S3-HP: POTION
  You: ATTACK

=========================

Respond with: ACTION: <action>
Allowed actions: ATTACK, POTION
```

The recorded response was:

```text
ACTION: ATTACK
```

S0 had no reasoning field and no threshold/risk instruction.

### VariableDamage S3 risk-band turn

Example from
[`match_ff9a67ab.json`](../../../agentdeck_runs/p2_vd_frontier_s3/session_20260427_234104_2e5995/records/match_ff9a67ab.json):

```text
=== Current Game State ===
You are: FlashLite-S3-RISK
Turn: 13

Health:
  You: 40

Potions:
  You: 3

Last Action:
  You: ATTACK
  GPT4oMini-S0-AO: ATTACK

=========================

Please respond in the following format:
REASONING: [Your step-by-step thought process]
ACTION: [Your chosen action]
Allowed actions: ATTACK, POTION

Before acting, check your risk band carefully.
- If your HP is above 55, do not use POTION.
- If your HP is 25 or lower and you have potions, use POTION.
- If your HP is 26 to 40 and you have 2 or 3 potions, prefer POTION now rather than entering the lethal zone with fewer resources.
- If your HP is 25 or lower and you have no potions, ATTACK anyway.
- Otherwise, act on your best read of the state.
```

The recorded response was:

```text
REASONING: My HP is 40, which falls into the category of "26 to 40 and you have 2 or 3 potions". The rule states to "prefer POTION now rather than entering the lethal zone with fewer resources". I have 3 potions. Therefore, I should use a potion.
ACTION: POTION
```

Again, the result demonstrates compliance with explicit risk-band scaffolding,
not unassisted strategic discovery.

## What Was Being Reinforced

The study used turn-time reinforcement in S3 by repeating the grounding
instruction on every turn. The repeated content was not generic encouragement.
It was specific decision policy:

- FixedDamage: evaluate whether one 20-damage attack would leave the player
  alive, then use potion if the answer is no and potions remain.
- VariableDamage: classify HP into risk bands and decide whether potion use is
  prohibited, preferred, required, or left to judgment.

The "act on your best read of the state" fallback left some room for model
judgment, but only after the explicit rule checks.

## What Was Not Included

- No S2 condition was run in the final P2 matrix.
- No conclusion/reflection prompts were enabled for study cells.
- No custom behavioral scorer was used for the official result.
- No hidden opponent HP/potion information was shown in partial-information
  game views.
- No provider-specific model reasoning mode was enabled for Gemini Flash-Lite;
  the matrix set `thinking_budget: 0`.

## Interpretation Guidance

Use precise wording:

- S1 tested structured reasoning/output requirements.
- S3 tested structured reasoning plus explicit game-specific policy grounding.
- FixedDamage S3 is close to a survival-threshold policy prompt.
- VariableDamage S3 is a hand-authored risk-band policy prompt.
- The study measures the effect of agent design around a model, not only the
  intrinsic strategic ability of the base model.
- The P3 ladder-completion cell shows that S1 alone was enough to beat GPT4oMini in
  the FixedDamage cross-tier matchup; S3 added margin and policy precision.

Presentation-safe claim:

> In FixedDamage, explicit policy-grounded scaffolding made FlashLite execute a
> better game strategy and beat unscaffolded GPT4oMini.

More precise after P3:

> In FixedDamage, structured reasoning alone crossed the model-tier boundary,
> and explicit HP grounding further improved the result and made the policy
> easier to audit.

Avoid:

> FlashLite discovered the winning strategy through reasoning alone.

## Source Files

- [`matrix.yaml`](../../../matrix.yaml)
- [`scripts/run_experiment.py`](../../../scripts/run_experiment.py)
- [`prompts/handshake_default.txt`](../../../prompts/handshake_default.txt)
- [`prompts/turn_action_only.txt`](../../../prompts/turn_action_only.txt)
- [`prompts/turn_reasoning.txt`](../../../prompts/turn_reasoning.txt)
- [`prompts/turn_fixed_full_stack.txt`](../../../prompts/turn_fixed_full_stack.txt)
- [`prompts/turn_variable_full_stack.txt`](../../../prompts/turn_variable_full_stack.txt)
- [`results.md`](../../../results.md)
- [`p2_fd_frontier_s3/results.json`](../../../artifacts/p2_fd_frontier_s3/results.json)
- [`p2_vd_frontier_s3/results.json`](../../../artifacts/p2_vd_frontier_s3/results.json)
- [`p3_fd_frontier_s1/results.json`](../../../artifacts/p3_fd_frontier_s1/results.json)
- [`s1_frontier_followup.md`](s1_frontier_followup.md)
