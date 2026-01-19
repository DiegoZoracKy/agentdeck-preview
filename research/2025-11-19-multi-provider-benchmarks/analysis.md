# Multi-Provider Benchmarks – Analysis

## Experiment 1 – Gemini-2.5-Flash vs GPT-4o-mini
- **Session**: `session_20251120_003003_95fe94`
- **Sample size**: 30 matches (ReasoningController, `max_output_tokens=200`)

| Player | Wins | Win Rate |
|--------|------|----------|
| GPT-4o-mini | 21 | 70 % |
| Gemini-2.5-Flash | 9 | 30 % |

- **95 % Wilson CI (GPT-4o-mini)**: [52.1 %, 83.3 %]  
- **p-value (vs 50 % null)**: 0.0428 → statistically significant advantage for GPT-4o-mini

### Cost Comparison

| Player | Total Cost | Cost / Match |
|--------|------------|--------------|
| Gemini-2.5-Flash | $0.6112 | $0.0204 |
| GPT-4o-mini | $0.0595 | $0.0020 |

- Gemini cost ≈10× GPT-4o-mini per match while losing 70 % of games.
- Latency remained the dominant pain point: Gemini reasoning steps regularly took 20–60 s (with 100 s+ spikes) despite the 200-token cap, so even at concurrency=10 the batch still lasted 16 minutes.

## Experiment 2 – Gemini-2.5-Pro vs GPT-4o-mini
- **Session**: `session_20251120_020159_706aeb`
- **Sample size**: 30 matches (ReasoningController, **no** token cap, concurrency=1 to dodge rate limits)

| Player | Wins | Win Rate |
|--------|------|----------|
| Gemini-2.5-Pro | 16 | 53.3 % |
| GPT-4o-mini | 14 | 46.7 % |

- **95 % Wilson CI**:
  - Gemini-2.5-Pro: [36.1 %, 69.8 %]
  - GPT-4o-mini: [30.2 %, 63.9 %]
- **p-value (exact binomial vs 50 % null)**: 0.856 → difference is *not* statistically significant.
- **Cohen’s h (Gemini vs 50 %)**: 0.067 (negligible effect size).

### Cost Comparison

| Player | Total Cost | Cost / Match |
|--------|------------|--------------|
| Gemini-2.5-Pro | $1.4286 | $0.0476 |
| GPT-4o-mini | $0.0912 | $0.0030 |

- Removing the cap restored valid actions but revealed how expensive Pro is: ~15× GPT spend per match for a statistically even outcome.
- Concurrency=1 turned the batch into a ~2 h 03 m run (7 379 s total) even though average per-match wall time was ~246 s.

## Cross-Experiment Takeaways
1. **Performance parity, cost disparity**: Gemini-2.5-Pro finally tied GPT-4o-mini once it could emit full reasoning, but it still offers no significant edge while costing an order of magnitude more. Flash remained both slower *and* weaker in win rate.
2. **Controller sensitivity**: ReasoningController requires enough output tokens for `REASONING` + `ACTION`; hard caps (200 tokens) directly translate into forfeits. Any future Gemini runs should either drop the cap or switch to `ActionOnlyController`.
3. **Operational friction**: Vertex AI quotas (429s) forced concurrency down to 1, so wall-clock time ballooned. A checkpoint/resume workflow would help avoid wasting partial batches when quotas trigger mid-run.

## Recommended Next Steps
1. Re-run Pro vs GPT-4o-mini with higher concurrency once quotas reset, verifying results remain statistically neutral.
2. Test ActionOnlyController for both Gemini variants to see if reduced reasoning overhead improves both latency and cost without hurting win rate.
3. Formalize checkpoint/resume design (per CONTRIBUTING workflow) so multi-hour external-provider runs can survive quota hiccups or operator interrupts.
