# Multi-Provider Benchmarks – Execution Log

## Experiment: Gemini 2.5 Flash vs GPT-4o-mini

**Started**: 2025-11-20 00:30 UTC  
**Session**: `session_20251120_003003_95fe94`  
**Configuration**:
- Game: `FixedDamageGame(max_health=100, attack_damage=20, potion_heal=30, starting_potions=2, information_level="partial")`
- Controller: `ReasoningController` for both players
- Players:
  - GeminiPlayer `gemini-2.5-flash`, temperature=1.0, `generation_config={"max_output_tokens": 200}`
  - GPTPlayer `gpt-4o-mini`, temperature=1.0
- Matches: 30
- Seed: 2084
- Concurrency: 10
- Spectators: Recorder → `recordings/`, `StatsTracker`, `TokenUsageTracker`, `ProgressDisplay`

---

## Execution Highlights

| Time (UTC) | Event |
|------------|-------|
| 00:30 | Batch `batch_1e` started with 30 matches planned |
| 00:44 | Gemini reasoning turns observed taking up to ~160 s even with 200-token cap |
| 00:46 | Match 30/30 completed (winner: GPT-4o-mini) |
| 00:46 | Batch summary emitted, artifacts written to `recordings/session_20251120_003003_95fe94/` |

### Performance & Cost
- Total duration: **16 m 03 s** (964.35 s)
- Avg per match: **216.9 s** (concurrency mitigates overall time but Gemini latency dominates)
- API spend:
  - Gemini-2.5-Flash: **$0.6112**
  - GPT-4o-mini: **$0.0595**
  - Total: **$0.6707** (≈ $0.0224/match)

### Outcomes
- GPT-4o-mini wins: **21/30 (70 %)**
- Gemini-2.5-Flash wins: **9/30 (30 %)**
- No draws recorded

Artifacts for reproducibility:
- Logs: `recordings/session_20251120_003003_95fe94/logs/`
- Recordings (per-match JSON): `recordings/session_20251120_003003_95fe94/records/`

---

## Experiment: Gemini 2.5 Pro vs GPT-4o-mini

**Started**: 2025-11-20 02:01 UTC  
**Session**: `session_20251120_020159_706aeb`  
**Configuration**:
- Game: `FixedDamageGame(max_health=100, attack_damage=20, potion_heal=30, starting_potions=2, information_level="partial")`
- Controller: `ReasoningController` for both players (no max-token cap applied)
- Players:
  - GeminiPlayer `gemini-2.5-pro`, temperature=1.0
  - GPTPlayer `gpt-4o-mini`, temperature=1.0
- Matches: 30
- Seed: 2084
- Concurrency: 1 (throttled to avoid Vertex/OpenAI 429s)
- Spectators: Recorder → `recordings/`, `StatsTracker`, `TokenUsageTracker`, `ProgressDisplay`

### Execution Highlights

| Time (UTC) | Event |
|------------|-------|
| 02:02 | Batch `batch_84` started after removing Gemini’s 200-token cap |
| 02:05 | Match `match_2a64177a` validated – Gemini produced full `REASONING` + `ACTION` blocks |
| 03:10 | Mid-run inspection confirmed steady but slow match cadence due to concurrency=1 |
| 04:05 | Batch completed, summary + costs written to `recordings/session_20251120_020159_706aeb/` |

### Performance & Cost
- Total duration: **7 379.6 s** (~2 h 03 m)
- Avg per match: **246 s** (serialized execution because of concurrency=1)
- API spend:
  - Gemini-2.5-Pro: **$1.4286**
  - GPT-4o-mini: **$0.0912**
  - Total: **$1.5198** (≈ $0.0507/match)

### Outcomes
- Gemini-2.5-Pro wins: **16/30 (53.3 %)**
- GPT-4o-mini wins: **14/30 (46.7 %)**
- Draws: **0**

Artifacts for reproducibility:
- Logs: `recordings/session_20251120_020159_706aeb/logs/`
- Recordings: `recordings/session_20251120_020159_706aeb/records/`
