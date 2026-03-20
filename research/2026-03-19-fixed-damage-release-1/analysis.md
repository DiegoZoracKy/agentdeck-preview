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
- Outcome-policy dissociation is one of the main findings: Mini, Haiku, and Flash-Lite all landed `12-12` named-player splits under cadence while following very different policies.
- Policy stability differed sharply by model family:
  - Mini and Haiku stayed near-perfect on state-action consistency (`0.978` to `0.989`) and never collapsed into all-attack play.
  - Flash-Lite was the least stable provider cell (`0.862` to `0.866` consistency) and kept the highest all-attack rates (`37.5%` HO, `25.0%` TR).
  - Flash remained more stable than Flash-Lite but still variable (`0.879` to `0.911` consistency).
- Minimal ActionOnly contract adherence was clean across the final provider cells: every exported provider run finished with `0` parse failures and `100%` strict contract rate.
- Position dependence varied sharply by model: calibration and Mini were fully first-player dominated, Haiku fully second-player dominated, Flash-Lite strongly first-player leaning, and Flash moderately first-player leaning.
- Haiku's inversion has a clear policy mechanism in the behavioral layer: both Haiku cells scored `1.0` on `position_policy_delta`, meaning the action distribution changed maximally by position in shared visible states.

### Directional Signals
- Prompt cadence did not produce a significant within-model win-rate effect at `N=24`, which is strong evidence against large effects but not enough to rule out moderate ones.
- The Gemini cells showed decision-level movement under turn reinforcement even though they stayed outcome-null:
  - Flash-Lite reduced all-attack matches from `37.5%` to `25.0%` and improved heuristic recovery from `0.25` to `0.34`
  - Flash reduced all-attack matches from `20.8%` to `0.0%` and improved heuristic recovery from `0.45` to `0.64`
  - those shifts are promising but still descriptive at pilot scale

### What AgentDeck Made Visible
- AgentDeck's fairness metadata separated position effects from named-player splits, which is why the Haiku inversion and the weaker Gemini first-player leans are visible at all.
- AgentDeck's validated artifact flow made it possible to rerun the Google cells on a corrected structured-history adapter and replace earlier confounded artifacts without changing the research design.
- AgentDeck's replay and trajectory artifacts make mechanism visible, not just outcomes: policy drift, healing behavior, deterministic vs variable regimes, and now the computed behavioral profile are inspectable rather than inferred from scores alone.
- AgentDeck ties cost, latency, fairness, and behavior into the same validated package, so prompt-cadence tradeoffs are measurable from artifacts rather than anecdotal.

## Phase 0 Calibration
- `AttackBot` vs `AttackBot`: calibration rerun confirms pure position dominance under paired side-swap. Named bots split `12-12`, but the actual first player wins `24/24` and every match ends in 9 turns.
- `AttackBot` vs `PotionAt80Bot`: topline wins still split `12-12` because the first player wins `24/24`, but the weaker policy is clearly visible in trajectory shape. Every match extends to 15 turns because `PotionAt80Bot` burns potions at 80 HP.

## Phase 1 Cadence Pilot
- `gpt-4o-mini`: no cadence delta at `N=24`. `Mini-HO` and `Mini-TR` split `12-12`, stayed perfectly strict on the ActionOnly contract, and preserved the game's expected first-player dominance (`24/24` first-player wins). The behavioral scorer reads Mini as a stable state-grounded policy family: `0.978` to `0.989` consistency, `0.0` all-attack rate, first potion at `80 HP`, and only modest position-policy delta (`0.117` to `0.144`).
- `claude-haiku-4-5-20251001`: no cadence delta at `N=24`. `Haiku-HO` and `Haiku-TR` also split `12-12` with `0` parse failures and `100%` strict contract rate, but unlike Mini they inverted the game and the second player won `24/24`. The behavioral mechanism is explicit: both Haiku cells scored `1.0` on `position_policy_delta`, indicating the policy changes maximally by position in shared visible states.
- `gemini-2.5-flash-lite`: no cadence delta at `N=24`. `Gemini-HO` and `Gemini-TR` split `12-12`, finished with `0` parse failures and `100%` strict contract rate, and showed a strong but not absolute first-player lean (`20/24` first-player wins). Match lengths ranged from `9` to `22` turns. This is the least stable provider cell in the behavioral layer: `37.5%` HO all-attack matches dropping to `25.0%` under TR, first potion still very late at `20 HP`, and consistency only `0.862` to `0.866`.
- `gemini-2.5-flash`: no cadence delta at `N=24`. `GeminiFlash-TR` finished `14-10` over `GeminiFlash-HO`, again with negligible effect size, `0` parse failures, and `100%` strict contract rate. Flash kept only a moderate first-player lean (`16/24` first-player wins), and turn counts ranged from `14` to `25`. The behavioral layer suggests more substantive cadence movement here than in the topline score: all-attack matches fall from `20.8%` to `0.0%`, first-potion median shifts from `40 HP` to `50 HP`, and heuristic recovery rises from `0.45` to `0.64`.
- Reinforcement increased spend without changing the causal picture. `Mini-TR` cost `0.03274` vs `Mini-HO` `0.02754`, `Haiku-TR` `0.25034` vs `Haiku-HO` `0.21101`, `Gemini-TR` `0.00981` vs `Gemini-HO` `0.00849`, and `GeminiFlash-TR` `0.05276` vs `GeminiFlash-HO` `0.04430`.
- Trajectory structure split by provider family. Mini and Haiku were fully deterministic in turn count (`23` and `24` turns respectively in every match), while the Gemini cells showed real spread. Flash-Lite ranged from `9` to `22` turns, and Flash ranged from `14` to `25` turns.
- The package now carries a full `behavioral_profile` block in `results.json` and every per-cell artifact. That turns this study from an outcome-only cadence pilot into the first computed behavior package built from the same recorder artifacts.
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
- Behavioral note: the new scorer does not add inferential statistics yet. Its outputs are descriptive mechanism metrics derived from the same validated recordings.

## Cost & Reliability
- Total cost: `0.63699` across the whole package, all of it in Phase 1 provider cells (`0.06028` Mini, `0.46136` Haiku, `0.01829` Flash-Lite, `0.09706` Flash).
- Cost per match: `0.00251` for Mini, `0.01922` for Haiku, `0.00076` for Flash-Lite, `0.00404` for Flash, `0.00442` overall across all 144 matches.
- Forfeit / parse-failure rates: `0` across every exported cell after the strict `OK` handshake contract fix.
- Reliability note: the final provider runs are now fully aligned on both parseability and strictness. The earlier Gemini non-strictness disappeared once the adapter preserved native multi-turn role structure, so the release package keeps only the corrected reruns.
- Latency notes: local calibration cells complete in fractions of a second per match; provider cells averaged about `30.04s` per Mini match, `28.72s` per Haiku match, `8.19s` per Flash-Lite match, and `13.51s` per Flash match.
- Behavioral-scoring note: the final package's behavioral profile is complete, not partial. The FixedDamage scorer received the game config (`max_health=100`, `attack_damage=20`) and therefore evaluated both descriptive and heuristic metrics without unsupported gaps.

## Viewer Highlights
- Calibration highlights: `AttackBot` vs `AttackBot` is the clean fairness clip; `AttackBot` vs `PotionAt80Bot` is the clean policy-deviation clip.
- Cadence highlights: `Mini-HO` vs `Mini-TR` is the clean negative-result replay because the trajectories stay symmetric while the reinforcement path still costs more.
- Mechanism evidence: `Haiku-HO` vs `Haiku-TR` is the strongest replay pair for Release 1 because it shows cadence-insensitive outcomes alongside a fully inverted position effect, and every replay is representative because the cell has zero turn-count variance.
- Gemini highlights: the two Gemini cells are now the clearest proof that outcome-null cells can still move behaviorally. Flash-Lite stays closer to the all-attack calibration floor, while Flash shows the strongest decision-level movement under turn reinforcement even though its win-rate cell remains underpowered.

## Limitations
- FixedDamage is a behavioral microscope, not a broad benchmark.
- Position effects remain important even with paired side-swap.
- Provider integration still matters. The final package excludes earlier Gemini artifacts produced before the structured-history adapter fix, because those runs confounded contract-quality measurement with transport-layer formatting.

## Next Steps
- `P0` is complete on the final audited codebase.
- `P1` is complete on the final audited codebase for OpenAI, Anthropic, and Google.
- Expand cells only if the pilot supports a clean causal story.
- Do not expand the cadence matrix for Release 1 as an outcome study. Treat the next experiment as a separate question, likely controller type or reasoning-contract differences, with the new behavioral metrics as primary endpoints.
- Keep the public release narrative behavior-first: the topline cadence cells stayed null, but the behavioral layer shows that cadence can still move policy quality for unstable model families.
