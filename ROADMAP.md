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
- [ ] Clamp HP to non-negative in `FixedDamageGame.update()` attack path.
  - Why: current runtime evidence shows `health: 10 -> -10` in real matches.
  - Acceptance:
    - No negative HP values in `records/match_*.json` final or intermediate states.
    - No negative HP deltas in debug/info logs for fresh smoke run.
    - Unit test coverage for clamp behavior and winner logic unchanged.
- [ ] Fix recorder timing consistency (event-level and match-level timestamps).
  - Scope:
    - `event.timestamp` in match artifacts must reflect emission time, not flush/write time.
    - `event.duration` / prompt-level duration must reflect real turn/call duration (not fixed placeholder values).
    - `started_at` / `ended_at` / `duration_seconds` in match artifacts must be non-null and aligned with batch match refs.
  - Why:
    - Current artifacts show compressed event timelines and mismatch between match file vs batch metadata.
  - Acceptance:
    - Event timeline span is coherent with turn durations for long matches.
    - `records/match_*.json` and `records/batch_*.json` agree on match start/end windows.
    - No `started_at=None` / `ended_at=None` for completed matches.
- [ ] Add correlation fields to LLM request/response/call debug lines.
  - Scope: include at least `match_id`, `turn_number`, `phase`, `player`, `call_id` (or `request_id` equivalent).
  - Why: current `debug.log` interleaving prevents reliable per-match reconstruction in parallel batches.
  - Acceptance:
    - Every `API request`, `API response`, and `API call` line can be joined deterministically to one match/turn.
    - Manual inspection of a concurrent batch is unambiguous without fallback to raw JSON.

### P1 - Spec and Telemetry Consistency
- [ ] Fix event-ordering editorial inconsistency in `specs/SPEC.md`.
  - Current issue: hierarchy snippet implies handshake nested under `match_start`, while ordering text says handshake precedes `MATCH_START`.
  - Acceptance:
    - Single, unambiguous lifecycle order in docs.
    - Cross-reference remains aligned with `specs/SPEC-CONSOLE.md`.
- [ ] Align prompt payload turn numbering semantics (`prompt.turn_number`) with spec.
  - Current issue:
    - Gameplay prompt payloads in artifacts are serialized with `turn_number: null`.
    - Spec expectations and implementation behavior are not aligned/documented clearly.
  - Acceptance:
    - Either gameplay prompt payloads carry concrete turn numbers (preferred), or spec is explicitly updated to current schema behavior with rationale.
    - `handshake/conclusion` semantics remain explicit and test-covered.
- [ ] Persist `player_handshake_start` in match artifacts (or formalize omission in spec).
  - Current issue: artifacts contain `player_handshake_complete`/`abort` but not `player_handshake_start`.
  - Acceptance:
    - Event pipeline and recorder behavior are explicit and consistent (implementation + spec + tests).
    - Handshake lifecycle is fully auditable in match artifacts.
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
- [ ] Add targeted parse-failure observability regression test.
  - Goal: prove `PLAYER_ACTION_PARSE_FAILED` event emission + recorder persistence path in worker/sequential flows.
  - Acceptance:
    - Test forces parse failure and asserts event presence + policy metadata.
    - Recorded match JSON contains parse-failure event payload fields.
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
- [ ] Preserve conclusion prompt sanitization of engine-internal keys.
  - Status: already fixed in engine; keep as release gate verification.
  - Acceptance:
    - No `_turn_count` / `_first_player_idx` in LLM-facing conclusion prompt blocks for new sessions.
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
