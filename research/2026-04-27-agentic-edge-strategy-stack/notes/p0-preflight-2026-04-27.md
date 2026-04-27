# P0 Preflight — 2026-04-27

## Status: PASS

Both P0 cells completed successfully without provider calls.

## Results

**p0_fd_bot_smoke** (FixedDamageGame, 6 matches):
- Win rates: Potion80Bot-AO 50%, AttackBot-AO 50% (paired side-swap balanced outcomes as expected)
- Avg turns: 15.0 | Duration: ~0.15s/match | Cost: $0.00
- Artifact validation: all_passed=True

**p0_vd_bot_smoke** (VariableDamageGame, 6 matches):
- Win rates: Potion80Bot-AO 50%, AttackBot-AO 50% (paired side-swap balanced)
- Avg turns: 16.8 | Duration: ~0.14s/match | Cost: $0.00
- Artifact validation: all_passed=True

**Package-level (12 matches combined):**
- schema_version: 3 — statistics, format_strictness, position_effect, artifact_validation all generated
- behavioral_profile: absent (expected — built-in scorer targets LLM behavioral events)
- Note: first-player win rate 91.7% in combined bot export is a bot-matchup artifact (AttackBot vs
  PotionAt80Bot seat-order interaction), not a structural fairness problem. Position effects in P1
  LLM cells should be reported independently.

## Recordings

Under `agentdeck_runs/` (generated artifacts, not committed):
- `p0_fd_bot_smoke/session_20260427_113252_a18822/records/` — 6 match files + 1 batch summary
- `p0_vd_bot_smoke/session_20260427_113253_bda979/records/` — 6 match files + 1 batch summary

Cell artifacts exported to `artifacts/p0_fd_bot_smoke/` and `artifacts/p0_vd_bot_smoke/`.
Package-level `results.json` and `results.csv` refreshed.

## Blockers Before P1

1. Fill `matrix.yaml` budget TBDs (`max_pilot_budget_usd`, `max_main_budget_usd`,
   `max_expansion_budget_usd`).
2. Record frozen `git_commit` and confirm `pricing_snapshot` path in `matrix.yaml`.
3. Verify provider credentials: `OPENAI_API_KEY` (for GPT-4o-mini) and Google credentials
   (for Gemini Flash-Lite — `VERTEX_PROJECT_ID` or `GOOGLE_APPLICATION_CREDENTIALS_B64`).
4. Verify live model IDs against current provider availability (`gemini-2.5-flash-lite`,
   `gpt-4o-mini`).
