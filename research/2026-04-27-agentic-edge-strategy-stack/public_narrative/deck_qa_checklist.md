# Deck QA Checklist

Status: draft review gate  
Purpose: validate any NotebookLM, slide, video, or public narrative draft before
sharing it outside the team.

This checklist exists because the story is strong but easy to overstate. Use it
after generating a deck or video script and before publishing screenshots,
slides, or spoken narration.

## Required Source Set

The deck must be generated or reviewed against these sources:

- [`../results.md`](../results.md)
- [`../study_overview.md`](../study_overview.md)
- [`../analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md)
- [`../analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md)
- [`../analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md)
- [`../analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md)
- [`notebooklm_sources.md`](notebooklm_sources.md)
- [`presentation_outline.md`](presentation_outline.md)

Use the Space for visual evidence:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

Do not use screenshots as the source of numeric claims. Screenshots illustrate
claims; `results.md`, cell artifacts, and support docs substantiate them.

## Must-Pass Headline Numbers

Every deck must preserve these exact headline numbers:

| Claim | Correct number | Source |
| --- | ---: | --- |
| FixedDamage S0 cross-tier | FlashLite-S0-AO 0/48, 0.0% vs GPT4oMini-S0-AO | `results.md`, `p2_fd_tier_gap_s0` |
| FixedDamage S1 cross-tier | FlashLite-S1-RC 34/48, 70.8% vs GPT4oMini-S0-AO | `results.md`, `p3_fd_frontier_s1` |
| FixedDamage S3 cross-tier | FlashLite-S3-HP 38/48, 79.2% vs GPT4oMini-S0-AO | `results.md`, `p2_fd_frontier_s3` |
| VariableDamage S3 within-model | FlashLite-S3-RISK 41/48, 85.4% vs FlashLite-S0-AO | `results.md`, `p2_vd_full_stack_effect_s3` |
| VariableDamage S3 cross-tier | FlashLite-S3-RISK 28/48, 58.3% vs GPT4oMini-S0-AO | `results.md`, `p2_vd_frontier_s3` |
| VariableDamage cross-tier p-value | p=0.312 | `results.md`, `p2_vd_frontier_s3` |
| VariableDamage first-player skew | 87.5% first-player win rate | `results.md`, `p2_vd_frontier_s3` |
| VariableDamage FlashLite seat split | 23/24 first, 5/24 second | `results.md`, `p2_vd_frontier_s3` |

If a generated draft uses different numbers, stop and fix the draft before
working on visuals.

## Behavioral Claims To Preserve

Allowed behavioral claims:

- S0 FlashLite often attacked through danger and lost with unused potions.
- In `p2_fd_tier_gap_s0`, FlashLite-S0-AO had 70.83% all-attack match rate.
- In `p2_fd_tier_gap_s0`, FlashLite-S0-AO lost with unused potions in 100.00%
  of its losses.
- S1 reduced all-attack collapse and improved critical-state recovery.
- S1 did not include the FixedDamage 20 HP survival rule.
- S3 did include explicit game-specific grounding.
- In `p2_fd_frontier_s3`, FlashLite-S3-HP median first potion HP was 20, while
  GPT4oMini-S0-AO median first potion HP was 80.
- In VariableDamage, S3-RISK improved FlashLite strongly against FlashLite-S0-AO.
- In VariableDamage, the cross-tier result is weak because of seat effects and
  non-significance.

Claims to reject:

- "The smaller model discovered the strategy by itself."
- "S1 used the 20 HP rule."
- "S3 proves the model is intrinsically smarter."
- "FlashLite was cheaper than GPT4oMini after scaffolding."
- "VariableDamage proves cross-tier dominance."
- "These results generalize to all business tasks."

## Slide-by-Slide QA

### Slide 1 - The Question

- [ ] Asks whether agent design can beat model tier.
- [ ] Does not frame the study as a general model leaderboard.
- [ ] Mentions AgentDeck evaluates behavior over time, not static answers.

### Slide 2 - The Test Environment

- [ ] Describes FixedDamage as deterministic 20 damage.
- [ ] Describes VariableDamage as stochastic 15 to 25 damage.
- [ ] Mentions attack/potion decisions and limited resources.
- [ ] Mentions paired side-swap or fairness controls if methodology is shown.

### Slide 3 - The Tuning Ladder

- [ ] S0 = action-only baseline.
- [ ] S1 = reasoning before action.
- [ ] S3 = reasoning plus game-specific grounding.
- [ ] Explicitly states S1 did not include the 20 HP rule.
- [ ] Explicitly states S3 did include game-specific policy grounding.

### Slide 4 - Baseline Failure

- [ ] Uses FixedDamage S0 cross-tier result: 0/48, 0.0%.
- [ ] Uses Study 1 replay as visual evidence.
- [ ] If behavioral metrics appear, uses 70.83% all-attack and 100.00% unused
  potions on loss exactly.
- [ ] Does not imply GPT4oMini is universally stronger; this is the tested cell.

### Slide 5 - Reasoning Pivot

- [ ] Uses FixedDamage S1 cross-tier result: 34/48, 70.8%.
- [ ] Uses Study 2 replay as visual evidence.
- [ ] Says the reasoning format changed the decision process.
- [ ] Does not claim S1 included explicit survival-threshold instructions.

### Slide 6 - Grounded Stack

- [ ] Uses FixedDamage S3 cross-tier result: 38/48, 79.2%.
- [ ] Uses Study 3 replay as visual evidence.
- [ ] Explains S3 as explicit game-policy grounding.
- [ ] Does not say the model independently invented the rule.

### Slide 7 - Behavior Beyond Win Rate

- [ ] Uses metrics from `behavioral_metrics_digest.md`.
- [ ] Includes at least one metric beyond win rate.
- [ ] Separates FixedDamage HP-threshold behavior from VariableDamage risk-band
  behavior.

### Slide 8 - Transfer Under Uncertainty

- [ ] Uses VariableDamage within-model result: 41/48, 85.4%.
- [ ] Says the architecture transferred when grounding was adapted.
- [ ] Does not say the FixedDamage prompt transferred unchanged.
- [ ] Uses Study 4 replay as visual evidence.

### Slide 9 - VariableDamage Caveat

- [ ] Uses cross-tier result: 28/48, 58.3%.
- [ ] Includes p=0.312.
- [ ] Includes first-player win rate 87.5%.
- [ ] Includes FlashLite-S3-RISK seat split: 23/24 first, 5/24 second.
- [ ] Uses Study 5 replay as visual evidence.
- [ ] Clearly says this is not a strong dominance claim.

### Slide 10 - Cost and Business Meaning

- [ ] Says this is not a cheap-model story.
- [ ] Says scaffolding increased token cost.
- [ ] Frames the business question as full configuration quality per dollar.
- [ ] Does not claim scaffolded FlashLite was cheaper than GPT4oMini.

### Slide 11 - What AgentDeck Adds

- [ ] Shows evidence trail: matrix, prompts, recordings, results, behavioral
  metrics, costs, seat effects, viewer, Hugging Face storage.
- [ ] Does not imply AgentDeck proves broad real-world generalization by itself.

### Slide 12 - Final Claim

- [ ] Final claim is scoped to controlled sequential decision environments.
- [ ] Says FixedDamage tier inversion, not universal model superiority.
- [ ] Includes limitations or "what this does not prove."

## Visual QA

For each visual:

- [ ] Numbers in charts sum or compare correctly.
- [ ] Labels match the actual cell being shown.
- [ ] S1 and S3 are not conflated.
- [ ] If showing prompt snippets, they are either exact quotes from
  `protocol_and_prompt_audit.md` or clearly labeled as simplified paraphrases.
- [ ] Screenshots from the replay viewer are illustrative and not used as raw
  numeric evidence.
- [ ] Portuguese or English copy preserves the same claim boundaries.

## Final Approval Checklist

- [ ] All headline numbers checked against `results.md`.
- [ ] Behavioral numbers checked against `behavioral_metrics_digest.md`.
- [ ] Prompt claims checked against `protocol_and_prompt_audit.md`.
- [ ] VariableDamage caveat is present.
- [ ] Cost caveat is present.
- [ ] No universal claims about smaller models.
- [ ] No claim that the model discovered the strategy by itself.
- [ ] No claim that S1 had the 20 HP rule.
- [ ] Replay Space hard-refreshed and visually checked.
- [ ] Dataset and Space links work for intended audience.

