# Analysis — Cross-Game Comparison 1

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Evidence base: `FixedDamage` (`19` empirical packages, `1,320` matches) plus `VariableDamage` (`12` empirical packages, `744` matches), for `2,064` completed matches overall.
- Main result: the pre-release research program showed that AgentDeck can diagnose model-specific policy failures, validate interventions causally, and test whether those interventions transfer to a harder task class.
- Core transfer finding: `RC` transferred for Flash-Lite, `TR` did not, and HP guidance had to be rewritten from exact thresholds to risk bands.
- Release-facing conclusion: the pre-release experiment arc is complete enough to support a serious `v0.1.0` preview story.
<!-- AUTO_FACTS:END -->

## What This Comparison Is Designed To Answer
1. Which findings stayed stable across games?
2. Which intervention logic transferred and which did not?
3. Which models changed the most under uncertainty?
4. What does the combined evidence actually say about AgentDeck as a product?

## What Changed Between The Games
- `FixedDamage` was a deterministic threshold game.
  - exact arithmetic often solved the state
  - first-player scripts were strong
  - the main policy question was whether the model handled threshold logic cleanly
- `VariableDamage` turned the same shell into a stochastic risk-management game.
  - exact arithmetic stopped being enough
  - first-player effects weakened
  - the key question became when to spend resources under uncertainty

## What Transferred
- `ReasoningController` on Flash-Lite:
  - helped strongly in FixedDamage
  - helped strongly again in VariableDamage
  - this is the clearest intervention that transferred cleanly across both arcs
- AgentDeck’s methodology:
  - behavioral metrics localized failures
  - targeted interventions were promoted only after state-level evidence
  - parity and premium checks tested whether the repaired policy held up

## What Did Not Transfer
- Turn reinforcement:
  - valuable in FixedDamage
  - not valuable in VariableDamage
  - in VariableDamage it worsened seat-conditioned drift instead of stabilizing the policy
- HP guidance:
  - the FixedDamage version assumed exact `20` damage and failed conceptually in VariableDamage
  - the working VariableDamage successor had to be rewritten around:
    - safe vs danger vs lethal bands
    - potion scarcity
    - first-lethal inventory timing
- “CoT helps by default”:
  - disproved across both arcs
  - RC helped some models and harmed or failed others

## Model-By-Model Read
- `FlashLite`
  - weakest untuned baseline in both games
  - most improvable weak model in both games
  - final result:
    - FixedDamage: tuned Flash-Lite beat plain Flash
    - VariableDamage: tuned Flash-Lite reached near parity with Flash and stayed respectable against `GPT5Mini-AO`
- `Flash`
  - the most robust practical baseline across both games
  - strong in deterministic thresholds
  - still strong under uncertainty
  - stayed cheap enough to remain the operational reference baseline
- `Mini`
  - the most behaviorally stable model across both games
  - kept the same early-heal, overconservative habit
  - VariableDamage exposed the cost of that habit more clearly through empty-at-lethal states
- `Haiku`
  - changed the most
  - FixedDamage:
    - bizarre seat-conditioned policy
    - `position_policy_delta = 1.0`
  - VariableDamage:
    - coherent and strong
    - effectively part of the top plain-model tier
- `gpt-5-mini`
  - FixedDamage:
    - clear untuned premium ceiling
  - VariableDamage:
    - cleaner than the field, but not massively above Flash on outcome
    - strong premium comparison point rather than a totally separate class of result
- `gpt-4o-mini` and `gpt-4o`
  - useful counterexamples to the naive “reasoning prompt = automatic improvement” story
  - RC alone was not a generic fix for either OpenAI line

## Why The Metrics Had To Evolve
- FixedDamage’s threshold-specific metrics were exactly right for the deterministic game.
- They were not enough for VariableDamage.
- The new metrics that earned their place were:
  - `safe_zone_potion_rate`
  - `first_lethal_entry_inventory`
  - lower/upper danger-zone potion rates
  - risk-band behavior under scarcity
- This is one of the strongest product proofs in the repo:
  - AgentDeck did not just rerun the same scoreboard in a new game
  - it supported a richer behavioral layer when the task demanded it

## What The Combined Evidence Says About AgentDeck
- AgentDeck is useful for more than match execution.
- The product value demonstrated here is:
  - expose hidden policy failures that win rate alone will miss
  - make interventions auditable and causal rather than ad hoc
  - test transfer instead of assuming it
  - compare behavior, outcome, and cost in one workflow
- The strongest release-facing examples are now clear:
  - FixedDamage for deterministic diagnosis and intervention ladders
  - VariableDamage for uncertainty, transfer failure, and richer behavioral metrics

## Release Read
- The pre-release experiment arc is complete enough for `v0.1.0`.
- More experiments would add depth, not new categories of evidence.
- The highest-value remaining work is now synthesis, documentation, and replay/viewer curation rather than more benchmark branches.
