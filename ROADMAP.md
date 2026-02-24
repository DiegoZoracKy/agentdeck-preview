# AgentDeck Experiment Reset Roadmap

Last updated: 2026-02-23T00:30:00Z  
Owner: Diego + Codex + Claude

## North Star
Run a clean, reproducible mini-only benchmark from zero (gpt-4o-mini) and produce publishable research artifacts using only AgentDeck out-of-the-box capabilities.

## Locked Execution Contract
- Engine: AgentDeck only (standalone kept only as historical investigation reference).
- Models in this reset: `openai:gpt-4o-mini` only.
- Cells: `c26`, `c27`, `c28`, `c01`, `c02`, `c03`.
- Matches per cell: `24` (paired seed side-swap enabled by matrix runner).
- `concurrency=10`
- `max_turns=30`
- `temperature=1.0`
- `starting_potions=2`
- Parse behavior: real-world `FORFEIT` (no custom fallback logic).
- Conclusion phase: enabled.
- No custom calculators/prints for benchmark decisions; rely on AgentDeck records/logs/export/packager.

## What Changes Before Running
- Update `ROADMAP.md` only (this document).
- No code/spec changes in this step.

## Reset Plan

### Phase R0 - Pre-Run Sanity (No Execution Yet)
- Confirm matrix source of truth:
  - `research/2026-02-13-performance-methods-benchmark-matrix/matrix.yaml`
- Confirm runner source of truth:
  - `research/2026-02-13-performance-methods-benchmark-matrix/scripts/run_matrix_phase.py`
- Confirm venv/tooling:
  - `.venv` active and dependencies installed.
- Status: COMPLETE

### Phase R1 - Runtime Cleanup
- Remove previous runtime sessions used for investigation/parity:
  - `agentdeck_runs/session_*`
  - `standalone_runs/session_*`
- Preserve research artifacts and historical baselines:
  - keep `research/_parity/`
  - keep `research/2025-11-08-openai-benchmarks/`
  - keep committed/uncommitted research package folders in `research/`
- Status: COMPLETE
- Executed: cleaned only `agentdeck_runs/session_*` and `standalone_runs/session_*`.

### Phase R2 - Fresh Mini-Only Execution (From Zero)
Run cells one by one in this order:
1. `c26_t0_openai_weak_ao_vs_ao`
2. `c27_t0_openai_weak_coth_vs_coth`
3. `c28_t0_openai_weak_cott_vs_cott`
4. `c01_t1_openai_weak_ao_vs_coth`
5. `c02_t1_openai_weak_ao_vs_cott`
6. `c03_t1_openai_weak_coth_vs_cott`

Rules during execution:
- Keep the same runtime parameters across all six cells.
- Stop and inspect immediately if forfeit rate exceeds 5% in any cell.
- Keep all session IDs and record paths for traceability.
- Status: COMPLETE
- Sessions:
  - `c26` -> `session_20260221_193351_362c34`
  - `c27` -> `session_20260221_193521_daf3ea`
  - `c28` -> `session_20260221_193847_b74a3f`
  - `c01` -> `session_20260221_194251_bcca11`
  - `c02` -> `session_20260221_194523_6fdd63`
  - `c03` -> `session_20260221_194819_37722d`

### Phase R3 - Package + Validate
For each fresh session:
- Generate export/package artifacts (`results.json`, `results.csv`, factual markdown blocks).
- Run validator:
  - `scripts/research_validate.py --research-dir research`
- Ensure each package is status-consistent and spec-compliant.
- Status: COMPLETE
- Packages created:
  - `research/openai-mini-c26-ao-vs-ao__20260221_193351_362c34/`
  - `research/openai-mini-c27-coth-vs-coth__20260221_193521_daf3ea/`
  - `research/openai-mini-c28-cott-vs-cott__20260221_193847_b74a3f/`
  - `research/openai-mini-c01-ao-vs-coth__20260221_194251_bcca11/`
  - `research/openai-mini-c02-ao-vs-cott__20260221_194523_6fdd63/`
  - `research/openai-mini-c03-coth-vs-cott__20260221_194819_37722d/`
- Validation: `Research validation passed.`

### Phase R4 - Findings + Decision Gate
Produce a concise readout:
- Where strategy improvement is observed.
- Where expected improvement is not observed.
- Whether sample size (24/cell) is sufficient for directional claims.
- Decision:
  - proceed to expansion (`80` selected cells), or
  - adjust configuration and rerun affected cells.
- Status: IN PROGRESS

## Engine Correctness and Observability Fix Track

### P0 - Functional Correctness (Blockers)
- [x] Clamp HP to non-negative in `FixedDamageGame.update()` attack path.
  - Fixed: `0df1c8b` — `max(0, hp - damage)` in `FixedDamageGame.update()`.
  - Unit test: `test_fixed_damage_attack_clamps_health_to_zero`.
- [x] Fix recorder timing consistency (event-level and match-level timestamps).
  - Fixed: `0df1c8b` — event timestamps set at `bus.emit()` time; `started_at`/`ended_at`/`duration_seconds` derived from wall-clock at `on_match_start`/`on_match_end`.
  - Regression test: `test_gameplay_events_preserve_emission_timestamps_and_turn_durations` in `test_recorder_lifecycle.py`.
  - Note: `event.duration` / prompt-level duration (per-turn call timing) remains a future item.
- [x] Add correlation fields to LLM request/response/call debug lines.
  - Fixed: `0df1c8b` — `call_id`, `match_id`, `turn_number`, `phase` added to `api_request`/`api_response`/`api_call` in `logging.py` and propagated from `llm_player.py`.
  - Spec: `SPEC-LLM.md` CL2.

### P1 - Spec and Telemetry Consistency
- [x] Fix event-ordering editorial inconsistency in `specs/SPEC.md`.
  - Fixed: `0df1c8b` — handshake events moved under `batch_start` in lifecycle hierarchy diagram.
- [ ] Align prompt payload turn numbering semantics (`prompt.turn_number`) with spec.
  - Current issue:
    - Gameplay prompt payloads in artifacts are serialized with `turn_number: null`.
    - Spec expectations and implementation behavior are not aligned/documented clearly.
  - Acceptance:
    - Either gameplay prompt payloads carry concrete turn numbers (preferred), or spec is explicitly updated to current schema behavior with rationale.
    - `handshake/conclusion` semantics remain explicit and test-covered.
- [x] Persist `player_handshake_start` in match artifacts.
  - Fixed: `0df1c8b` — console emits `PLAYER_HANDSHAKE_START`; recorder captures it via `on_player_handshake_start`.
  - Spec: `SPEC-RECORDER.md` v1.3.0.
- [ ] Clarify `player_order` vs `first_player` semantics in specs/artifacts.
  - Current issue:
    - Readers often assume `player_order[0]` is the first actor.
    - In turn-based flow, first actor may be selected at runtime (`_first_player_idx`) after ordering.
  - Acceptance:
    - Specs explicitly document that `player_order` = ordered roster before runtime first-player selection.
    - `first_player` = actual first actor when runtime data exists.
    - Analysis docs/checklists use `first_player` (not `player_order[0]`) for first-mover metrics.
- [ ] Add artifact-level invariant checks for match/batch consistency.
  - Scope:
    - Validate monotonic and non-collapsed event timeline for gameplay events.
    - Validate top-level match timing (`started_at`/`ended_at`/`duration_seconds`) against turn contexts.
    - Validate prompt payload turn numbering coherence (`prompt.turn_number` vs `turn_context.turn_number`).
    - Validate winner/final-state consistency (`winner`, terminal HP bounds, turn count coherence).
  - Why:
    - Manual triage already surfaced timing/schema drift that should be caught automatically.
  - Acceptance:
    - Tests and/or validation script fail-fast on inconsistent artifacts.
    - Incident triage does not depend on manual log archaeology for these invariants.
- [x] Add targeted parse-failure observability regression test.
  - Fixed: `0df1c8b` — `test_parse_failure.py` covers all 5 policies (ABORT, SKIP, FORFEIT, RETRY_ONCE x2, parallel) with `PLAYER_ACTION_PARSE_FAILED` event + PM1-PM3 fields verified.
- [ ] Cleanup duplicated section/invariant numbering in `SPEC-GAME.md`.
  - Current issue:
    - section `5.6` appears twice and invariant numbers `15-18` are reused for PF and HT sections.
  - Acceptance:
    - section numbering is unique and monotonic.
    - invariant identifiers are unique and stable for cross-references/tests.

### P2 - Prompt Hygiene (Quality Improvements)
- [ ] Keep handshake/gameplay template split explicit in research configs.
  - Goal: avoid accidental instruction leakage and keep experiments interpretable.
  - Acceptance:
    - Matrix/config docs state which instruction cadence is under test (HO/HT).
    - Pre-run checklist verifies A/B symmetry for non-cadence cells.
- [ ] Make controller asymmetry explicit in experiment intent (fairness guardrail).
  - Scope:
    - For baseline/fairness cells, enforce same controller family on both sides unless cell is marked asymmetric by design.
    - Surface controller mismatch clearly in manifest/report headers.
  - Why:
    - A-vs-B controller asymmetry is valid in hypothesis tests but can silently contaminate baseline interpretation.
  - Acceptance:
    - Baseline cells fail preflight if controller asymmetry is not declared.
    - Experiment artifacts annotate whether asymmetry is intentional.
- [ ] Clarify `information_level="partial"` semantics for opponent `last_action`.
  - Current issue:
    - Text says partial shows only own stats, but `get_view()` exposes all `last_action` values.
  - Decision required:
    - either keep opponent last action visible and document it explicitly, or hide it in partial mode.
  - Acceptance:
    - Game behavior, prompt wording, and spec text are mutually consistent.
    - No contradictory guidance for experiment interpretation.
- [x] Preserve conclusion prompt sanitization of engine-internal keys.
  - Fixed: `b26e6bd` — `llm_player.py` strips `_`-prefixed keys from `{game_view}` in template-driven conclusion prompts.
  - Spec: `SPEC-PLAYER.md` CS4, `SPEC-LLM.md` CH4.
- [x] Align policy for engine-internal keys in gameplay `state_before/state_after`.
  - Decision taken:
    - sanitize internal runtime keys (prefix `_`) from recorded gameplay state payloads.
  - Acceptance:
    - Recorder sanitizes gameplay snapshots before persistence.
    - SPEC-RECORDER documents sanitized gameplay state behavior.
- [ ] Add analysis guardrail: compare artifacts only within the same `session_id`/`batch_id` during incident triage.
  - Goal: avoid false positives caused by cross-run parameter drift (e.g., potions=4 vs potions=6).
  - Acceptance:
    - Triage checklist includes explicit provenance check before causal claims.

## Artifact Policy (This Reset)
- Runtime truth: `agentdeck_runs/<session_id>/records/*.json` and logs.
- Research truth: packaged experiment folders in `research/`.
- Do not delete historical baseline evidence unless explicitly requested.

## Definition of Done
- All six mini-only cells rerun from a clean runtime state.
- Packaged artifacts generated and validation passes.
- One consolidated findings report produced with explicit go/no-go for expansion.
