# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 144 total matches across 6 cells
- Decisive matches: 144
- Draws: 0
- Win rates: no cadence comparison was significant at `N=24`; the strong signals are positional and policy-stability differences
- Topline winner: none; the signal is positional and behavioral, not name-based
- First player in first recorded match: Attack-B
- Strict contract rate: `1.0` overall across all exported cells
- Artifact validation: all exported cells passed
- Average turns: 17.64 overall
- Average duration (s): 13.46 overall
- Total cost: 0.63699
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary

### Confirmed Behavioral Findings
- Turn reinforcement increased spend in every provider cell without producing a decisive win-rate shift.
- Policy stability differed sharply by model family: Mini and Haiku were fully deterministic, while both Gemini cells showed visible trajectory spread.
- Minimal ActionOnly contract adherence was clean across the final provider cells: every exported provider run finished with `0` parse failures and `100%` strict contract rate.
- Position dependence varied sharply by model: calibration and Mini were fully first-player dominated, Haiku fully second-player dominated, Flash-Lite strongly first-player leaning, and Flash moderately first-player leaning.

### Directional Signals
- Prompt cadence did not produce a significant within-model win-rate effect at `N=24`, which is strong evidence against large effects but not enough to rule out moderate ones.
- In Flash, turn reinforcement still produced the largest named-player lean (`14-10`) in the package. That direction is interesting, but still descriptive at pilot scale.

### What AgentDeck Made Visible
- AgentDeck's fairness metadata separated position effects from named-player splits, which is why the Haiku inversion and the weaker Gemini first-player leans are visible at all.
- AgentDeck's validated artifact flow made it possible to rerun the Google cells on a corrected structured-history adapter and replace earlier confounded artifacts without changing the research design.
- AgentDeck's replay and trajectory artifacts make mechanism visible, not just outcomes: policy drift, healing behavior, and deterministic vs variable regimes are inspectable in records rather than inferred from scores alone.
- AgentDeck ties cost, latency, fairness, and behavior into the same validated package, so prompt-cadence tradeoffs are measurable from artifacts rather than anecdotal.

## Phase 0 Calibration
- `AttackBot` vs `AttackBot`: calibration rerun confirms pure position dominance under paired side-swap. Named bots split `12-12`, but the actual first player wins `24/24` and every match ends in 9 turns.
- `AttackBot` vs `PotionAt80Bot`: topline wins still split `12-12` because the first player wins `24/24`, but the weaker policy is clearly visible in trajectory shape. Every match extends to 15 turns because `PotionAt80Bot` burns potions at 80 HP.

## Phase 1 Cadence Pilot
- `gpt-4o-mini`: no cadence delta at `N=24`. `Mini-HO` and `Mini-TR` split `12-12`, stayed perfectly strict on the ActionOnly contract, and preserved the game's expected first-player dominance (`24/24` first-player wins).
- `claude-haiku-4-5-20251001`: no cadence delta at `N=24`. `Haiku-HO` and `Haiku-TR` also split `12-12` with `0` parse failures and `100%` strict contract rate, but unlike Mini they inverted the game and the second player won `24/24`.
- `gemini-2.5-flash-lite`: no cadence delta at `N=24`. `Gemini-HO` and `Gemini-TR` split `12-12`, finished with `0` parse failures and `100%` strict contract rate, and showed a strong but not absolute first-player lean (`20/24` first-player wins). Match lengths ranged from `9` to `22` turns.
- `gemini-2.5-flash`: no cadence delta at `N=24`. `GeminiFlash-TR` finished `14-10` over `GeminiFlash-HO`, again with negligible effect size, `0` parse failures, and `100%` strict contract rate. Flash kept only a moderate first-player lean (`16/24` first-player wins), and turn counts ranged from `14` to `25`.
- Reinforcement increased spend without changing the causal picture. `Mini-TR` cost `0.03274` vs `Mini-HO` `0.02754`, `Haiku-TR` `0.25034` vs `Haiku-HO` `0.21101`, `Gemini-TR` `0.00981` vs `Gemini-HO` `0.00849`, and `GeminiFlash-TR` `0.05276` vs `GeminiFlash-HO` `0.04430`.
- Trajectory structure split by provider family. Mini and Haiku were fully deterministic in turn count (`23` and `24` turns respectively in every match), while the Gemini cells showed real spread. Flash-Lite ranged from `9` to `22` turns, and Flash ranged from `14` to `25` turns.
- The earlier aborted Haiku pilot is no longer part of the result set. After tightening the handshake contract to require exactly `OK`, the rerun completed cleanly and is the only release-facing Haiku data.
- The earlier Gemini exports that used flattened labeled history are no longer part of the result set. The final package keeps only the structured-history Gemini reruns.

## Statistical Summary
- Sample size (`n`): 24 decisive matches per provider cadence cell; 144 decisive matches overall across the package.
- Win rates + 95% CI:
  - Mini and Haiku both landed exactly `0.5` with exact-binomial `95%` intervals of `[0.314, 0.686]`
  - Flash-Lite also landed exactly `0.5` with exact-binomial `95%` intervals of `[0.314, 0.686]`
  - Flash landed `0.417` vs `0.583`, with overlapping intervals `[0.245, 0.612]` and `[0.388, 0.755]`
- Effect size: every cadence comparison remained `negligible` (`0.0` for Mini/Haiku/Flash-Lite, `0.167` for Flash).
- Significance notes: no cadence comparison was statistically significant. The strong statistical signal in this package is positional, not cadence-based: `24/24` first-player wins for calibration and Mini, and `24/24` second-player wins for Haiku. Under a `p=0.5` null, either `24/24` directional extreme has one-sided probability `5.96e-08`.

## Cost & Reliability
- Total cost: `0.63699` across the whole package, all of it in Phase 1 provider cells (`0.06028` Mini, `0.46136` Haiku, `0.01829` Flash-Lite, `0.09706` Flash).
- Cost per match: `0.00251` for Mini, `0.01922` for Haiku, `0.00076` for Flash-Lite, `0.00404` for Flash, `0.00442` overall across all 144 matches.
- Forfeit / parse-failure rates: `0` across every exported cell after the strict `OK` handshake contract fix.
- Reliability note: the final provider runs are now fully aligned on both parseability and strictness. The earlier Gemini non-strictness disappeared once the adapter preserved native multi-turn role structure, so the release package keeps only the corrected reruns.
- Latency notes: local calibration cells complete in fractions of a second per match; provider cells averaged about `30.04s` per Mini match, `28.72s` per Haiku match, `8.19s` per Flash-Lite match, and `13.51s` per Flash match.

## Viewer Highlights
- Calibration highlights: `AttackBot` vs `AttackBot` is the clean fairness clip; `AttackBot` vs `PotionAt80Bot` is the clean policy-deviation clip.
- Cadence highlights: `Mini-HO` vs `Mini-TR` is the clean negative-result replay because the trajectories stay symmetric while the reinforcement path still costs more.
- Mechanism evidence: `Haiku-HO` vs `Haiku-TR` is the strongest replay pair for Release 1 because it shows cadence-insensitive outcomes alongside a fully inverted position effect, and every replay is representative because the cell has zero turn-count variance.
- Gemini highlights: the two Gemini cells are now the cleanest viewer contrast for variable policy under identical contract adherence. Flash-Lite stays fast and shorter-horizon, while Flash runs longer and more potion-heavy.

## Limitations
- FixedDamage is a behavioral microscope, not a broad benchmark.
- Position effects remain important even with paired side-swap.
- Provider integration still matters. The final package excludes earlier Gemini artifacts produced before the structured-history adapter fix, because those runs confounded contract-quality measurement with transport-layer formatting.

## Next Steps
- `P0` is complete on the final audited codebase.
- `P1` is complete on the final audited codebase for OpenAI, Anthropic, and Google.
- Expand cells only if the pilot supports a clean causal story.
- Do not expand the cadence matrix for Release 1. Treat the next experiment as a separate question, likely controller type or reasoning-contract differences rather than cadence.
- Keep the public release narrative behavior-first: cadence stayed null, but position dependence and policy stability diverged sharply by model family.
