# FixedDamage Release Experiment Plan

Status: Draft for consensus before implementation and execution
Date: 2026-03-17

## Why This Plan Exists

This study is intended to be the first public research package that demonstrates
the value of AgentDeck as a product.

That means the experiment should showcase AgentDeck's native strengths rather
than rely on custom scripts, custom printouts, or one-off analysis logic.

The release-facing package should primarily demonstrate:
- native fairness controls (`paired_side_swap`, first-player metadata)
- native recorder + replay contract
- native research export, invariant validation, and package structure
- native viewer support for curated replay highlights
- behavior-first analysis (`format_strictness`, `position_effect`, replay evidence)

## Product Goal

Show that AgentDeck can reveal and package a subtle behavioral effect in a
simple, deterministic, replayable environment.

The strongest release story is not "who wins FixedDamage." The strongest story
is "AgentDeck made a behavioral question visible, measurable, reproducible, and
watchable."

## Proposed Release Question

Recommended primary question:

"How sensitive is model behavior in FixedDamage to prompt cadence, and can
AgentDeck make that sensitivity legible through replayable, validated research
artifacts?"

This keeps the study:
- causal
- small enough to finish
- aligned with the product's real value

## Release 1 Consensus Scope

Release 1 should include:
- Phase 0 calibration
- Phase 1 prompt-cadence track

Release 1 should not include:
- Phase 2 visibility track
- three-model breadth for its own sake
- leaderboard framing

Current agreed scope:
- public calibration cells are included in the package
- default environment is `information_level="partial"`
- initial provider scope is two models
- cadence sensitivity is the research question
- behavioral trajectories over raw win rate is the AgentDeck value argument

## Non-Goals

Do not optimize this release study for:
- broad cross-provider leaderboard claims
- grand statements about model quality
- custom scoring systems outside the AgentDeck research contract
- bespoke experiment infrastructure that does not belong in AgentDeck

## FixedDamage As A Release Case

Why FixedDamage is still a good release case:
- deterministic and easy to explain
- trivial dominant policy makes deviations legible
- strict controller contract makes format compliance measurable
- replay viewers are easy to understand
- first-player effects are known and can therefore demonstrate AgentDeck's
  fairness and position-effect surfaces

Why FixedDamage is not enough on its own:
- it is strongly position-sensitive
- it is too small for provider ranking claims
- raw win rate is less informative than behavior and trajectory

Conclusion:
Use FixedDamage as a behavioral microscope, not a leaderboard arena.

## Recommended Study Structure

### Phase 0: Calibration

Purpose:
Prove the environment and fairness machinery behave as expected before spending
money on provider runs.

Recommended cells:
- `AttackBot` vs `AttackBot`
- `AttackBot` vs `PotionAt80Bot`

AgentDeck surfaces demonstrated:
- paired side-swap
- first-player metadata
- replay artifacts
- research export and validation

Expected result:
- `AttackBot` vs `AttackBot` shows pure position effect
- `PotionAt80Bot` is visibly suboptimal in replay and results

Release note:
- these cells should be public and should appear early in the package narrative
- they are the cleanest demonstration that the framework and fairness machinery
  are behaving correctly before LLM variance enters

### Phase 1: Prompt-Cadence Track

Purpose:
Use a causally clean within-model comparison to test whether cadence changes
behavior.

Recommended design:
- same base model on both sides
- same controller on both sides
- same game config on both sides
- only prompt cadence changes

Recommended cell pattern:
- `model_handshake_only` vs `model_turn_reinforced`

Recommended initial models:
- `gpt-4o-mini`
- Anthropic Haiku target chosen in the matrix for the release run

Scope note:
- start with two models only
- add a third model only if the pilot confirms the question is worth expansion

Game config:
- `FixedDamageGame`
- `information_level="partial"`
- `ActionOnlyController`
- `pairing_policy="paired_side_swap"`
- `first_player_policy="random"`
- `conclusion.enabled=false`

Sampling:
- pilot at `N=24`
- expand selected cells to `N=80`

Primary metrics:
- `format_strictness`
- `position_effect`
- win rate
- replay-visible policy deviations

Behavioral markers to inspect in replay:
- potion at full HP
- potion at 80 HP
- repeated ATTACK adherence
- off-policy healing chains

Expected release value:
- even a negative result is useful if it is clean
- if one model is cadence-sensitive and another is not, that is a strong
  showcase result

### Phase 2: Visibility Track (Optional For Release 1)

Purpose:
Test whether information visibility changes policy quality.

Important constraint:
`information_level` is a game-level setting, not a per-player setting. That
means visibility cannot be isolated by giving different views to each side in a
single standard match.

Recommended approach if included:
- run separate cells under `information_level="full"` and `"partial"`
- compare the same model against the same baseline or reference condition
- do not treat these as direct head-to-head within a single match

Recommendation:
Do not make this required for the first public release package unless Phase 1 is
already complete and clear.

## Concrete Cadence Configuration

This must be explicit before implementation so the study has a clean causal
factor.

Common settings for both cadence conditions:
- game: `FixedDamageGame(information_level="partial")`
- controller: `ActionOnlyController`
- fairness: `pairing_policy="paired_side_swap"`, `first_player_policy="random"`
- conclusion phase: disabled
- same model on both sides within a cell
- same controller on both sides within a cell

Handshake content for both conditions:
- the handshake must include both the game instructions and the gameplay action
  format once, plus the handshake acknowledgement instruction
- the intent is that both conditions learn the action format at match start
- the only difference is whether the action format is repeated on turn prompts

Recommended explicit handshake template:

```text
{game_instructions}

When taking gameplay turns, use exactly this format:
{controller_format}

{handshake_controller_format}
```

With `ActionOnlyController` bound to FixedDamage, the relevant gameplay format is:

```text
Respond with: ACTION: <action>
Allowed actions: ATTACK, POTION
```

Cadence condition definitions:

1. `handshake_only`
   - handshake template: explicit template above
   - turn template: `{game_view}`
   - interpretation: action format is presented once at match start only

2. `turn_reinforced`
   - handshake template: explicit template above
   - turn template: `{game_view}\n\n{controller_format}`
   - interpretation: the same action format is repeated on every gameplay turn

Prompt-builder requirement:
- the matrix should encode this difference through native `PromptBuilder`
  settings only
- no custom prompt concatenation outside AgentDeck

## Native-AgentDeck Requirement

The public release study should use AgentDeck-native surfaces end to end.

That means:
- use `AgentDeckConfig` fairness controls
- use `ConclusionPolicy` explicitly rather than leaving irrelevant phases on by accident
- use standard controllers and prompt-builder settings
- use native spectators/monitors when live run visibility is useful
- rely on Recorder output as the source of truth
- use `research_export.py`, `research_validate.py`, and packaged results
- curate replay highlights from AgentDeck records in the viewer

Avoid:
- custom terminal summaries as the headline artifact
- custom print-based result reporting as the experiment surface
- ad hoc JSON post-processing outside the research contract
- one-off experiment outputs that cannot be replayed or validated through
  AgentDeck

## Recommended Public Package Shape

One release-facing package should include:
- human-written `README.md`
- human-written `analysis.md`
- `manifest.yaml`
- `matrix.yaml`
- generated `results.json` and `results.csv`
- curated replay list for viewer inclusion

The package should be able to support a public narrative like:

"In a deterministic, strict-format game, AgentDeck revealed that prompt cadence
changed policy quality for some models and not others, and the replay artifacts
made the mechanism inspectable."

## Success Criteria

The study is ready for public release when all of the following are true:
- at least one causally clean track is complete
- all exported artifact invariants pass
- the package is fully valid under `research_validate.py`
- the top finding can be explained through both results and replays
- the viewer has at least 2-3 curated highlights that support the narrative
- the result demonstrates AgentDeck features, not custom glue code

## Expected Result Shapes

Good outcomes:
- one model shows cadence sensitivity and another does not
- all models look cadence-insensitive, but AgentDeck cleanly falsifies the
  hypothesis
- the main release result is a behavior pattern visible in replay, not just a
  p-value

Bad outcomes:
- the study collapses into "model A beat model B"
- first-player bias dominates the story
- the package depends on custom metrics not available in AgentDeck outputs

## Remaining Decisions Before Implementation

1. Which Anthropic Haiku model string should the Release 1 matrix pin?
2. Should Phase 0 use only `AttackBot` and `PotionAt80Bot`, or do we also want a
   second intentionally bad baseline such as `GreedyPotionBot`?
3. What should the public package title be once the first pilot result shape is known?

## Recommended Next Step

If this plan looks right, the next implementation step should be:

1. create the actual experiment package under `research/`
2. encode Phase 0 + Phase 1 into `matrix.yaml`
3. add a repo-local runner script that uses AgentDeck-native configuration only
4. execute calibration first
5. run pilot provider cells
6. package only the cells that survive causal and methodological scrutiny
