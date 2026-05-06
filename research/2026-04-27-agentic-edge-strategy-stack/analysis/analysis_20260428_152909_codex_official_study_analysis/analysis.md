# Official Study Analysis: The Agentic Edge

Experiment: `2026-04-27-agentic-edge-strategy-stack`  
Status: final study-arc interpretation  
Primary factual source: [`results.md`](../../results.md)

Prompt/protocol transparency supplement:
[`support/protocol_and_prompt_audit.md`](support/protocol_and_prompt_audit.md)

Layman/business-facing explainer:
[`support/layman_business_explainer.md`](support/layman_business_explainer.md)

Behavioral metrics digest:
[`support/behavioral_metrics_digest.md`](support/behavioral_metrics_digest.md)

S1 frontier ladder-completion note:
[`support/s1_frontier_followup.md`](support/s1_frontier_followup.md)

## Executive Summary

The study tested whether a strategy stack can change LLM agent behavior enough
to overcome model-tier differences in two sequential decision games:
FixedDamage and VariableDamage.

The answer is strong but conditional.

In FixedDamage, the result is decisive: `FlashLite-S3-HP` beat
`GPT4oMini-S0-AO` 38/48 matches, or 79.2%, with p=0.000 and a medium effect
([cell artifact](../../artifacts/p2_fd_frontier_s3/results.json)). The
unscaffolded baseline moved in the opposite direction: `GPT4oMini-S0-AO` beat
`FlashLite-S0-AO` 48/48 matches, or 100%
([cell artifact](../../artifacts/p2_fd_tier_gap_s0/results.json)). In this
environment, the stack flipped the model-tier outcome.

In VariableDamage, the adapted stack transferred strongly within the same model:
`FlashLite-S3-RISK` beat `FlashLite-S0-AO` 41/48 matches, or 85.4%, matching
the FixedDamage full-stack result exactly
([cell artifact](../../artifacts/p2_vd_full_stack_effect_s3/results.json)).
The cross-tier frontier result was weaker: `FlashLite-S3-RISK` beat
`GPT4oMini-S0-AO` 28/48 matches, or 58.3%, but the direct result was not
statistically significant (p=0.312) and was heavily seat-confounded
([cell artifact](../../artifacts/p2_vd_frontier_s3/results.json)).

The main finding is not that a cheaper model wins. It is that agent
configuration can dominate base-model tier in the right environment, and that
the added scaffolding cost can be justified by outcome quality in FixedDamage.
For VariableDamage, the adapted stack clearly improves FlashLite, but the
cross-tier advantage over GPT4oMini is not established by this run.

P3 completed the FixedDamage cross-tier S1 ladder step. `FlashLite-S1-RC` beat
`GPT4oMini-S0-AO` 34/48 matches, or 70.8%, with
p=0.0055
([cell artifact](../../artifacts/p3_fd_frontier_s1/results.json)). This does
not change the P2 cell results; it completes the official FixedDamage tuning
arc. In FixedDamage, ReasoningController alone was enough to cross the tier
boundary, while S3 added an additional +8.4 percentage points and cleaner policy
execution.

## Study Scope

The official readout includes P2 and the targeted P3 S1 ladder-completion cell.
P0 smoke tests and P1 pilot matches are excluded from package aggregation by
`phase_model.study_phases: [P2, P3]`
([package results](../../results.json)).

The official aggregate contains:

- 9 cells.
- 48 matches per cell.
- 432 total matches.
- 432 decisive matches and 0 draws.
- Parse failure rate: 0.0%.
- Strict contract rate: 100.0%.
- Artifact validation: all passed.

All outcome claims below are cell-level claims. Package aggregates are useful
for quality checks and exposure accounting, but they are not study toplines
because the package spans multiple games, opponents, and stack conditions.

## Main Findings

### 1. Unscaffolded model tier matters, especially in FixedDamage

The S0 baseline showed a large model-tier gap in FixedDamage:
`GPT4oMini-S0-AO` beat `FlashLite-S0-AO` 48/48 matches (100%)
([cell artifact](../../artifacts/p2_fd_tier_gap_s0/results.json)).

The same baseline gap was smaller in VariableDamage:
`GPT4oMini-S0-AO` beat `FlashLite-S0-AO` 31/48 matches (64.6%), with p=0.059
and a small effect
([cell artifact](../../artifacts/p2_vd_tier_gap_s0/results.json)).

Interpretation: the lower-tier model was clearly disadvantaged without
scaffolding, but the size of the gap depended on the environment.

### 2. ReasoningController produced the largest single intervention gain

In FixedDamage, `FlashLite-S1-RC` beat `FlashLite-S0-AO` 37/48 matches
(77.1%)
([cell artifact](../../artifacts/p2_fd_controller_effect_s1/results.json)).

In VariableDamage, `FlashLite-S1-RC` beat `FlashLite-S0-AO` 38/48 matches
(79.2%)
([cell artifact](../../artifacts/p2_vd_controller_effect_s1/results.json)).

Interpretation: requiring structured reasoning before action selection was the
main mechanism shift. It repaired much of the lower-tier model's baseline
behavior in both games.

The P3 cross-tier ladder-completion cell strengthens this conclusion in
FixedDamage:
`FlashLite-S1-RC` beat `GPT4oMini-S0-AO` 34/48 matches (70.8%)
([P3 S1 frontier](../../artifacts/p3_fd_frontier_s1/results.json)). This means
the controller intervention alone crossed the model-tier boundary in that
environment.

### 3. Game-specific grounding added a smaller but consistent gain

The full stack improved on the S1 pattern in both games, but this is a
cross-cell comparison rather than a direct S3-vs-S1 head-to-head.

- FixedDamage: `FlashLite-S3-HP` beat `FlashLite-S0-AO` 41/48 matches (85.4%),
  compared with 77.1% for `FlashLite-S1-RC` against the same baseline
  ([S3 cell](../../artifacts/p2_fd_full_stack_effect_s3/results.json),
  [S1 cell](../../artifacts/p2_fd_controller_effect_s1/results.json)).
- VariableDamage: `FlashLite-S3-RISK` beat `FlashLite-S0-AO` 41/48 matches
  (85.4%), compared with 79.2% for `FlashLite-S1-RC` against the same baseline
  ([S3 cell](../../artifacts/p2_vd_full_stack_effect_s3/results.json),
  [S1 cell](../../artifacts/p2_vd_controller_effect_s1/results.json)).

Interpretation: explicit HP/risk grounding appears to add value beyond
ReasoningController alone, but it is the weakest of the confirmed mechanism
claims because it is inferred across cells. P3 also narrows the FixedDamage
claim: S3 was not required to beat GPT4oMini in that game, but it improved the
S1 cross-tier result from 70.8% to 79.2% and made potion timing more directly
aligned with the prompted survival policy.

### 4. FixedDamage supports the tier-inversion claim

The clearest headline is the FixedDamage frontier cell:
`FlashLite-S3-HP` beat `GPT4oMini-S0-AO` 38/48 matches (79.2%)
([cell artifact](../../artifacts/p2_fd_frontier_s3/results.json)).

The S1 frontier ladder-completion cell shows that the inversion begins one step
earlier: `FlashLite-S1-RC` beat the same GPT4oMini baseline 34/48 matches
(70.8%)
([P3 cell artifact](../../artifacts/p3_fd_frontier_s1/results.json)). The
FixedDamage tuning ladder is therefore:

- S0: `FlashLite-S0-AO` vs `GPT4oMini-S0-AO`: 0/48 wins (0.0%).
- S1: `FlashLite-S1-RC` vs `GPT4oMini-S0-AO`: 34/48 wins (70.8%).
- S3: `FlashLite-S3-HP` vs `GPT4oMini-S0-AO`: 38/48 wins (79.2%).

Seat split:

- `FlashLite-S3-HP` as first player: 23/24 wins (95.8%).
- `FlashLite-S3-HP` as second player: 15/24 wins (62.5%).
- `GPT4oMini-S0-AO` as first player: 9/24 wins (37.5%).
- `GPT4oMini-S0-AO` as second player: 1/24 wins (4.2%).

Interpretation: seat effects exist, but the result survives both seats for
FlashLite. This is the strongest evidence that stack design can reverse a
model-tier gap in this study.

### 5. VariableDamage does not support a strong cross-tier frontier claim

The VariableDamage frontier cell produced an aggregate win for the adapted
stack: `FlashLite-S3-RISK` beat `GPT4oMini-S0-AO` 28/48 matches (58.3%)
([cell artifact](../../artifacts/p2_vd_frontier_s3/results.json)).

That result should not be used as a strong dominance claim.

- Direct p-value: 0.312.
- Effect: negligible.
- Overall first-player win rate in the cell: 87.5%.
- `FlashLite-S3-RISK` as first player: 23/24 wins (95.8%).
- `FlashLite-S3-RISK` as second player: 5/24 wins (20.8%).
- `GPT4oMini-S0-AO` as first player: 19/24 wins (79.2%).
- `GPT4oMini-S0-AO` as second player: 1/24 wins (4.2%).

Interpretation: the VariableDamage frontier aggregate is dominated by seat
position. The adapted stack may still be useful in VariableDamage, but this run
does not establish cross-tier superiority over GPT4oMini in that environment.

## Hypothesis Readout

### H1 - Strategy Stack Effect: confirmed

Full-stack FlashLite beat action-only FlashLite 41/48 in FixedDamage and 41/48
in VariableDamage. Both results are 85.4% and statistically significant
([FD S3](../../artifacts/p2_fd_full_stack_effect_s3/results.json),
[VD S3](../../artifacts/p2_vd_full_stack_effect_s3/results.json)).

### H2 - Controller Effect: confirmed

ReasoningController alone beat action-only FlashLite 37/48 in FixedDamage and
38/48 in VariableDamage
([FD S1](../../artifacts/p2_fd_controller_effect_s1/results.json),
[VD S1](../../artifacts/p2_vd_controller_effect_s1/results.json)).

The P3 ladder-completion cell extends this from within-model repair to cross-tier
competition in FixedDamage: `FlashLite-S1-RC` beat `GPT4oMini-S0-AO` 34/48
matches
([P3 S1 frontier](../../artifacts/p3_fd_frontier_s1/results.json)).

### H3 - Grounding Effect: supported, but as cross-cell evidence

S3 exceeded S1 by 8.3 percentage points in FixedDamage and 6.2 percentage
points in VariableDamage within the P2 within-model cells. In the FixedDamage
cross-tier ladder, S3 exceeded the S1 frontier result by 8.4
percentage points. This is consistent with a grounding benefit, but the study
did not run a direct S3-vs-S1 cell.

### H4 - Seat Drift Reduction: inconclusive

Paired side-swap controlled exposure, but position effects remained strong.
Package-level first-player win rate was 68.2%, and the VariableDamage frontier
cell reached 87.5% first-player wins
([results report](../../results.md)).

### H5 - Cost-Quality Frontier: confirmed in FixedDamage, not established in VariableDamage

FixedDamage: `FlashLite-S3-HP` beat `GPT4oMini-S0-AO` 79.2%, but it cost more
per player-match. In the FD frontier cell, FlashLite S3 cost about $0.00261 per
player-match, while GPT4oMini S0 cost about $0.00134 per player-match
([FD frontier](../../artifacts/p2_fd_frontier_s3/results.json)).

The P3 ladder-completion cell shows that the threshold for crossing the FixedDamage
frontier was lower than S3: `FlashLite-S1-RC` won 70.8% against GPT4oMini S0 at
about $0.00178 per FlashLite player-match
([P3 S1 frontier](../../artifacts/p3_fd_frontier_s1/results.json)).

VariableDamage: `FlashLite-S3-RISK` cost about $0.00279 per player-match, while
GPT4oMini S0 cost about $0.00140 per player-match, but the outcome edge was
statistically weak and seat-confounded
([VD frontier](../../artifacts/p2_vd_frontier_s3/results.json)).

Interpretation: the cost-quality frontier is an outcome-quality story, not a
cheap-model story. The stack can buy better behavior, but it is not cheaper in
this configuration.

### H6 - Transfer Limitation: refined rather than simply confirmed or falsified

The architecture transferred: S1 performed well in both games, and the adapted
S3 stack reached 85.4% in both games. The parameters did not transfer unchanged:
FixedDamage used HP-threshold grounding, while VariableDamage required risk-band
grounding.

The correct claim is: the strategy-stack architecture transferred when the
grounding layer was rewritten for the target game's information structure.

## Behavioral Interpretation

The strongest behavioral signal is potion timing.

In FixedDamage, `FlashLite-S3-HP` used potions at a median first-potion HP of
20 in the frontier cell, matching the explicit survival threshold. GPT4oMini S0
used potions at a median first-potion HP of 80 in that same cell
([FD frontier](../../artifacts/p2_fd_frontier_s3/results.json)). The scaffolded
model was less conservative and more aligned with the game's actual survival
logic.

The S1 frontier ladder-completion cell shows that this was not only an S3 phenomenon:
`FlashLite-S1-RC` also had median first-potion HP of 20, reduced all-attack
collapse to 8.33%, and reached 81.54% error recovery
([P3 S1 frontier](../../artifacts/p3_fd_frontier_s1/results.json)). S3 still
improved the behavioral profile by nearly eliminating never-used-potion and
unused-potions-on-loss failures in the P2 full-stack cells.

In VariableDamage, `FlashLite-S3-RISK` used potions around the risk-band
threshold rather than the FixedDamage threshold: median first-potion HP was 41
in the S3-vs-S0 cell and 39 in the frontier cell
([VD S3](../../artifacts/p2_vd_full_stack_effect_s3/results.json),
[VD frontier](../../artifacts/p2_vd_frontier_s3/results.json)). This supports
the interpretation that risk grounding changed behavior in the intended
direction.

## Recommended External Framing

Use this as the headline:

> In FixedDamage, a grounded reasoning stack moved Gemini Flash-Lite from 0% to
> 79.2% against GPT-4o-mini, reversing the model-tier outcome in a controlled
> sequential decision game.

Use this as the transfer framing:

> The stack architecture transferred to VariableDamage when HP grounding was
> rewritten as risk-band grounding, but the cross-tier VariableDamage frontier
> result was not statistically reliable and was dominated by seat effects.

Avoid these claims:

- "The cheaper model won." It was cheaper unscaffolded, but the scaffolded
  version cost about 2x GPT4oMini S0 per player-match in the frontier cells.
- "VariableDamage proves the frontier claim." It does not; it proves strong
  within-model stack improvement and only weak cross-tier evidence.
- "Reasoning and grounding generalize to all sequential decision environments."
  The study covers two AgentDeck games and two model configurations.

## Limitations

- The study uses two synthetic games, not broad real-world tasks.
- The model roster is narrow: Gemini Flash-Lite and GPT-4o-mini.
- Provider models are live endpoints and may drift over time.
- Prompt wording is part of the intervention; results are not prompt-invariant.
- VariableDamage has large position effects, especially in the frontier cell.
- Grounding was adapted per game, so this study does not test raw prompt
  transfer from FixedDamage to VariableDamage.

## Final Verdict

The study is complete enough for a public technical narrative if the claims are
kept precise.

The strongest conclusion is that AgentDeck can measure how controller and
grounding choices reshape agent behavior, and in FixedDamage those choices were
large enough to overcome a model-tier gap. P3 shows the FixedDamage inversion
starts at S1, with S3 adding margin and more auditable policy execution. The
VariableDamage results show that the same design pattern can repair the
lower-tier model against its own baseline, but they also show why
seat-disaggregated reporting matters: the cross-tier frontier result is not
strong enough to stand alone.
