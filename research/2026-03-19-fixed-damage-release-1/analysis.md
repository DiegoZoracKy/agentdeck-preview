# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 144 total matches across 6 cells
- Decisive matches: 144
- Draws: 0
- Win rates: no cadence comparison was significant at `N=24`; the strong signals are positional and contract-strictness differences
- Topline winner: none; the signal is positional and behavioral, not name-based
- First player in first recorded match: Attack-B
- Strict contract rate: `0.853` overall, ranging from `0.182` (Flash-Lite) to `1.0` (bots, Mini, Haiku)
- Artifact validation: all exported cells passed
- Average turns: 18.47 overall
- Average duration (s): 16.96 overall
- Total cost: 0.66768
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position-effect claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: prompt cadence was not the story. Across `gpt-4o-mini`, `claude-haiku-4-5-20251001`, `gemini-2.5-flash-lite`, and `gemini-2.5-flash`, no handshake-only vs turn-reinforced comparison was significant at `N=24`.
- The real signal is behavioral regime. Calibration and Mini stayed in the game's natural first-player-dominant regime (`24/24` first-player wins), Haiku inverted the game completely (`24/24` second-player wins), Flash-Lite was nearly balanced with a slight second-player lean (`13/24` second-player wins), and Flash returned to strong first-player dominance (`22/24` first-player wins).
- A second product-level finding is contract-quality visibility. All cells finished with `0` parse failures, but strict ActionOnly compliance varied sharply by model family: Mini and Haiku were perfectly strict, Flash was high (`0.902`), and Flash-Lite was very low (`0.182`) while remaining recoverably parseable.
- Practical recommendation: use this package to show that AgentDeck's fairness metadata, replay, and validated artifacts surface differences in position dependence, response strictness, and cost that raw win-rate tables would flatten away. Treat cadence as a clean negative result, not the public headline.

## Phase 0 Calibration
- `AttackBot` vs `AttackBot`: calibration rerun confirms pure position dominance under paired side-swap. Named bots split `12-12`, but the actual first player wins `24/24` and every match ends in 9 turns.
- `AttackBot` vs `PotionAt80Bot`: topline wins still split `12-12` because the first player wins `24/24`, but the weaker policy is clearly visible in trajectory shape. Every match extends to 15 turns because `PotionAt80Bot` burns potions at 80 HP.

## Phase 1 Cadence Pilot
- `gpt-4o-mini`: no cadence delta at `N=24`. `Mini-HO` and `Mini-TR` split `12-12`, stayed perfectly strict on the ActionOnly contract, and preserved the game's expected first-player dominance (`24/24` first-player wins).
- `claude-haiku-4-5-20251001`: no cadence delta at `N=24`. `Haiku-HO` and `Haiku-TR` also split `12-12` with `0` parse failures and `100%` strict contract rate, but unlike Mini they inverted the game and the second player won `24/24`.
- `gemini-2.5-flash-lite`: no cadence delta at `N=24`. `Gemini-HO` finished `13-11` over `Gemini-TR` with negligible effect size and no parse failures, but strict ActionOnly compliance was only `0.182` overall. Flash-Lite also broke the earlier position patterns, landing close to balanced with a slight second-player lean (`13/24` second-player wins).
- `gemini-2.5-flash`: no cadence delta at `N=24`. `GeminiFlash-TR` finished `14-10` over `GeminiFlash-HO`, again with negligible effect size and no parse failures. Flash was much stricter than Flash-Lite (`0.902` strict contract rate) and strongly first-player dominated (`22/24` first-player wins).
- Reinforcement increased spend without changing the causal picture. `Mini-TR` cost `0.03274` vs `Mini-HO` `0.02754`, `Haiku-TR` `0.25034` vs `Haiku-HO` `0.21101`, `Gemini-TR` `0.01362` vs `Gemini-HO` `0.01196`, and `GeminiFlash-TR` `0.06471` vs `GeminiFlash-HO` `0.05575`.
- Trajectory structure split by provider family. Mini and Haiku were fully deterministic in turn count (`23` and `24` turns respectively in every match), while the Gemini cells showed real spread. Flash-Lite ranged from `11` to `24` turns, and Flash ranged from `13` to `25` turns with most matches ending at `25`.
- The earlier aborted Haiku pilot is no longer part of the result set. After tightening the handshake contract to require exactly `OK`, the rerun completed cleanly and is the only release-facing Haiku data.

## Statistical Summary
- Sample size (`n`): 24 decisive matches per provider cadence cell; 144 decisive matches overall across the package.
- Win rates + 95% CI:
  - Mini and Haiku both landed exactly `0.5` with exact-binomial `95%` intervals of `[0.314, 0.686]`
  - Flash-Lite landed `0.542` vs `0.458`, with overlapping intervals `[0.351, 0.721]` and `[0.279, 0.649]`
  - Flash landed `0.417` vs `0.583`, with overlapping intervals `[0.245, 0.612]` and `[0.388, 0.755]`
- Effect size: every cadence comparison remained `negligible` (`0.0` for Mini/Haiku, `0.083` for Flash-Lite, `0.167` for Flash).
- Significance notes: no cadence comparison was statistically significant. The strong statistical signal in this package is positional, not cadence-based: `24/24` first-player wins for calibration and Mini, and `24/24` second-player wins for Haiku. Under a `p=0.5` null, either `24/24` directional extreme has one-sided probability `5.96e-08`.

## Cost & Reliability
- Total cost: `0.66768` across the whole package, all of it in Phase 1 provider cells (`0.06028` Mini, `0.46136` Haiku, `0.02558` Flash-Lite, `0.12046` Flash).
- Cost per match: `0.00251` for Mini, `0.01922` for Haiku, `0.00107` for Flash-Lite, `0.00502` for Flash, `0.00464` overall across all 144 matches.
- Forfeit / parse-failure rates: `0` across every exported cell after the strict `OK` handshake contract fix.
- Reliability note: parseability and strictness are not the same thing. Flash-Lite remained fully recoverable with `0` parse failures even though most turns were non-strict under ActionOnly, while Flash was much stricter.
- Latency notes: local calibration cells complete in fractions of a second per match; provider cells averaged about `30.04s` per Mini match, `28.72s` per Haiku match, `13.13s` per Flash-Lite match, and `29.60s` per Flash match.

## Viewer Highlights
- Calibration highlights: `AttackBot` vs `AttackBot` is the clean fairness clip; `AttackBot` vs `PotionAt80Bot` is the clean policy-deviation clip.
- Cadence highlights: `Mini-HO` vs `Mini-TR` is the clean negative-result replay because the trajectories stay symmetric while the reinforcement path still costs more.
- Mechanism evidence: `Haiku-HO` vs `Haiku-TR` is the strongest replay pair for Release 1 because it shows cadence-insensitive outcomes alongside a fully inverted position effect, and every replay is representative because the cell has zero turn-count variance.
- Contract-quality highlights: the two Gemini cells are the cleanest viewer contrast for ActionOnly strictness. Flash-Lite regularly drifts into recoverable non-strict formatting, while Flash stays much closer to a single clean action line.

## Limitations
- FixedDamage is a behavioral microscope, not a broad benchmark.
- Position effects remain important even with paired side-swap.

## Next Steps
- `P0` is complete on the final audited codebase.
- `P1` is complete on the final audited codebase for OpenAI, Anthropic, and Google.
- Expand cells only if the pilot supports a clean causal story.
- Do not expand the cadence matrix for Release 1. Treat the next experiment as a separate question, likely controller type or reasoning-contract differences rather than cadence.
- Keep the public release narrative behavior-first: cadence stayed null, but position dependence and contract strictness diverged sharply by model family.
