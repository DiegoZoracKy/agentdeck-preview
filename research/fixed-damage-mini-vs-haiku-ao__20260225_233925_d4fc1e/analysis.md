# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 24
- Decisive matches: 24
- Draws: 0
- Win rates: {'claude-haiku-4-5-20251001-B': 0.5833333333333334, 'gpt-4o-mini-A': 0.4166666666666667}
- Topline winner: claude-haiku-4-5-20251001-B (58.3%)
- First player in first recorded match: claude-haiku-4-5-20251001-B
- Average turns: 18.416666666666668
- Average duration (s): 16.850005567073822
- Total cost: $0.259715
<!-- AUTO_FACTS:END -->

## Executive Summary
- Primary finding: In AO-only FixedDamage, Haiku finished ahead (`58.3%`) over 24 side-swapped matches.
- Secondary finding: First-player dominance remains very high (`91.7%` first-player wins), dominating method/model signal.
- Practical recommendation: Keep this as weak-model AO baseline; use larger N and/or harder game variants for stronger inference.

## Experiment Results (By Track/Cell)
- Track/cell groups (repeat as needed):
  - Group ID: `c01_fd_mini_ao_vs_haiku_ao`
  - Question: In FixedDamage, does gpt-4o-mini AO beat claude-haiku-4.5 AO under side-swap?
  - Topline: `claude-haiku-4-5-20251001-B` 14/24 (`58.3%`) vs `gpt-4o-mini-A` 10/24 (`41.7%`)

## Statistical Summary
- Sample size (`n`): `24`
- Win rates + 95% CI: wide intervals at this N; directional only.
- Effect size: not treated as decision-grade at this sample size.
- Significance notes: this run is exploratory due strong first-player confound and limited N.

## Cost & Reliability
- Total cost: `$0.259715`
- Cost per match: `$0.010821`
- Forfeit / parse-failure rates: none observed in completed session.
- Latency notes: avg match duration `16.85s`; occasional turn spikes observed but run completed without failures.

## Viewer Highlights
- Clutch examples: N/A for this pass.
- Comeback examples: sparse; most outcomes tracked first-player.
- Chaos examples: low; action cadence is highly repetitive.
- Dumb-decision examples: repeated early potion usage at 80 HP appears across both players.

## Limitations
- Domain constraints: FixedDamage remains highly deterministic with large first-player advantage.
- Confounds not controlled: no expanded N yet; no cross-game validation in this battery.

## Next Steps
- Follow-up experiments: run `Flash` and `Haiku`/`Mini` AO baselines in the same protocol; then move to VariableDamage.
- Production implications: treat FixedDamage AO as baseline sanity check, not as a definitive intelligence ranking benchmark.
