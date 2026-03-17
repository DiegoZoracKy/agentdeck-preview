# AgentDeck Experiment Reset Roadmap

Last updated: 2026-03-16T00:00:00Z
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

## Research Artifact Metrics Upgrade (2026-03-04)
- [x] Add inferential statistics directly to `results.json` export (`schema_version: 2`):
  - per-player CI / p-value / effect size
  - pairwise comparison payload
  - basic quality flags
- [x] Add game-agnostic `format_strictness` block to `results.json`:
  - parse-failure rate
  - strict contract pass rate
  - recoverable non-strict rate
- [x] Add game-agnostic `position_effect` block to `results.json`:
  - first-player win rate
  - upset rate (second-player wins)
  - per-player split (wins as first vs second)
- [x] Keep implementation modular in core research module:
  - `src/agentdeck/research/recording_metrics.py`
  - consumed by `scripts/research_export.py`
- [x] Extend validator for extended metrics on `results.json.schema_version >= 2`.
- [x] Extend packager factual hydration to surface key stats/strictness in `analysis.md`.

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
- Status: COMPLETE
- Outcome: dominant first-player signal across all cells (see Post-R4 pivot below). Method/cadence effects underpowered at n=24 in original game config. Pivot to weak-model cross-provider battery with paired side-swap.

## Post-R4 Research Pivot

### Context Lock
- OpenAI Responses API migration merged at `b043b66` and smoke-validated via battery runs.
- Battery runs unblocked.

### Why Pivot
- Current reset run shows dominant first-player signal in FixedDamageGame:
  - `c26`: 24/24 first-player wins (100%)
  - `c02`: 24/24 first-player wins (100%)
  - `c27`: 20/24 (83.3%)
  - `c28`: 22/24 (91.7%)
  - `c01`: 19/24 (79.2%)
  - `c03`: 20/24 (83.3%)
- With this regime, method/cadence effects are underpowered at `n=24` and can be confounded by game dynamics.

### Phase P1 - Free Behavioral Extraction (No API Cost)
- Goal: publishable behavioral finding from existing records before new spend.
- Input: existing packaged runs from `c26/c27/c28/c01/c02/c03` (latest reset sessions).
- Output:
  - POTION probability by own HP bucket, split by controller/cadence.
  - Early-turn decision profile (first two opportunities as first vs second player).
  - Forfeit profile by cell and controller.
- Acceptance:
  - Analysis artifact committed under `research/` with reproducible script + tables.
  - No new model calls.

### Phase P2 - Game Viability Smoke (Cheap Gate)
- Goal: verify if parameterized FixedDamageGame can reduce first-player dominance enough to measure strategy effects.
- Candidate regimes:
  - `starting_potions=4`
  - `starting_potions=6`
- Minimum run shape:
  - AO vs AO mirror
  - side-swap enabled
  - `n=30` (15 paired seeds) per regime
- Go/No-Go thresholds:
  - first-player win rate <= 70%
  - forfeit rate <= 5%
  - no schema/recorder invariant violations
- Decision:
  - If threshold passes in at least one regime, proceed to P3 with that regime.
  - If all fail, redesign mechanics before matrix expansion (e.g., SHIELD action or variable damage).

### Phase P3 - Compact Method Matrix (Equalized Cadence)
- Run only cells that isolate method/cadence cleanly; skip redundant mirror reruns unless reliability gate requires rerun.
- Target cells:
  1. AO-HT vs CoT-T-HT (method effect, cadence fixed)
  2. CoT-H-HT vs CoT-T-HT (turn reinforcement effect, controller family fixed)
  3. AO-HO vs AO-HT (cadence effect, method fixed)
- Rules:
  - same model (`gpt-4o-mini`) for both players
  - side-swap required
  - parse policy `FORFEIT`
  - game params fixed from P2 winner regime
- Sample sizing:
  - start at `n=50` per cell
  - expand to `n=80` only if CI/p-value decision rules from `sampling_policy` are triggered
  - if first-player remains >80%, pause and redesign game instead of brute-force N

### Phase P4 - Separate Sprint for Model-Selection Narrative
- Keep model-comparison claim (`mini` vs stronger model) outside method matrix.
- Precondition:
  - P3 must establish stable method/cadence behavior in mini-only regime.
- Then run dedicated cross-model sprint with explicit controls and separate hypotheses.

### Reliability Gate Overrides
- If any target cell exceeds forfeit threshold (`>5%`), rerun only that cell after fix.
- Example already observed: `c28` reset run had 2/24 forfeits (8.3%); treat as reliability issue, not strategy result.

### Operational Note
- Maintain strict provenance in analysis:
  - compare only artifacts from same `session_id`/`batch_id` set per claim
  - do not mix runs with different game parameters (e.g., potions 2 vs 4 vs 6) in a single causal conclusion.

### Core Experiment Controls (Backlog)
- [ ] Add first-player/pairing policies as native AgentDeck execution options (not runner-only YAML logic).
  - Current gap:
    - `paired_seed_side_swap.enabled` exists only in matrix runner logic (`run_matrix_phase.py`), not in `AgentDeckConfig` / `AgentDeck.play`.
    - This makes fairness controls non-portable across scripts and creates duplicate orchestration logic.
  - Scope:
    - Introduce core-level execution options for:
      - player pairing policy (`none`, `paired_side_swap`)
      - first-player policy (`random` default; optional fixed/alternating modes for diagnostics)
    - Persist selected policies in match/batch metadata for auditability.
  - Acceptance:
    - Same fairness experiment can be run through core API without custom runner orchestration.
    - Metadata explicitly records pairing/first-player policy per match/batch.
    - Specs updated before implementation (spec-first), including invariants and observability fields.

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

## OpenAI Responses API Migration

### Context
- OpenAI has released a new `POST /v1/responses` endpoint intended to replace Chat Completions.
- Key improvements: 40–80% cache improvement, 3% reasoning improvement (SWE-bench), unified token param (`max_output_tokens`), and server-side conversation history support.
- `.venv` has `openai==2.15.0` — Responses API is available now.
- Precondition: merge and smoke-validate before the next battery runs (see Phase R2 constraint note above).

### API Parameter Mapping

| Chat Completions | Responses API |
|---|---|
| `messages` | `input` (non-system messages only) |
| `system` role message(s) | `instructions` (extracted + joined deterministically) |
| `max_tokens` / `max_completion_tokens` | `max_output_tokens` (unified, no model branching needed) |
| `client.chat.completions.create()` | `client.responses.create()` |
| `response.choices[0].message.content` | `response.output_text` (with fallback — see below) |
| `response.usage.prompt_tokens` | `response.usage.input_tokens` |
| `response.usage.completion_tokens` | `response.usage.output_tokens` |

### Architecture Decisions

#### Phase 1 = Client-Side History (now)
- Set `store=False` — AgentDeck passes full conversation history on every call (existing behavior preserved, no server-side state).
- No behavior change in Phase 1; purely a drop-in API swap.

#### Phase 2 = Server-Side History (future, explicit opt-in only)
- NOT in scope until Phase 1 is stable and a clear cost/performance case exists.
- If implemented, MUST include:
  - `response_id` + `previous_response_id` persisted in match metadata.
  - Explicit reset behavior on `reset_conversation()`, `clone()`, and match boundaries.
  - Reproducibility note in spec: local replay is no longer self-contained context when server history is active.

### Safeguards Required Before Coding

#### 1. Scope: This Is a >1-File Migration
Files that must change:
- `src/agentdeck/players/openai_player.py` — core implementation
- `tests/unit/test_openai_player.py` — dedicated `GPTPlayer` tests (currently thin)
- `tests/conftest.py` — Responses API mock shape (replace/extend Chat Completions mock)
- `specs/SPEC-LLM.md` — new invariants (Phase MA)
- `specs/SPEC-PLAYER.md` — token field note (Phase MA)

#### 2. Parameter Compatibility Layer (Critical)
`**self.config` is currently forwarded blindly; some legacy Chat Completions params will 400 on the Responses API (e.g., `n`, `logprobs`).

Required:
- Define an explicit allowlist of Responses API supported keys (e.g., `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`, `stop`, `seed`, `user`).
- Map legacy token params: `max_tokens` / `max_completion_tokens` → `max_output_tokens`.
- Reject unsupported keys with a clear `ValueError` that names the offending param (not a silent drop or a 400 from the API).

#### 3. System/Instructions Extraction: Robust Multi-Message Case
- If multiple `system` role messages exist, join their `content` values deterministically (e.g., `"\n\n".join(...)`) into a single `instructions` string.
- Do NOT silently discard all but the first system message.

#### 4. Response Text Extraction: Fallback + Observability
- Primary: `response.output_text`
- Fallback: parse `response.output` list for items where `type == "message"` and extract `content[].text`.
- If result is empty/None after both paths: raise an explicit `RuntimeError` with the full response repr (not a silent empty string that propagates as a forfeit).

#### 5. Token Metadata Contract: Internal Keys Stay Stable
Downstream consumers (pricing, packager, spectators) use `prompt_tokens` / `completion_tokens`.
- Keep internal metadata keys as `prompt_tokens` / `completion_tokens` (map from API's `input_tokens` / `output_tokens`).
- Optionally surface provider-native keys as `input_tokens` / `output_tokens` alongside (additive, not replacing).
- Do NOT rename internal keys — that would silently break cost calculation and artifact schema.

#### 6. Dedicated `GPTPlayer` Tests Required
Currently the GPT call path is barely asserted at the unit level. The new test file MUST cover:
- Calls `client.responses.create` (not `chat.completions.create`).
- Payload contains `instructions` + `input` keys.
- Single system message extracted correctly.
- Multiple system messages joined into `instructions`.
- No system message → `instructions` key absent.
- `max_output_tokens` is used; `max_tokens` / `max_completion_tokens` are absent.
- Token fields mapped to internal `prompt_tokens` / `completion_tokens`.
- Unsupported config param (e.g., `n=2`) raises `ValueError` before the API call.
- Empty / null `output_text` with no fallback match → `RuntimeError`.

#### 7. Migration Gate Before Full Rollout
After Phase MC passes:
- Run 1-match smoke to confirm end-to-end path.
- Run small AO vs AO batch (e.g., 6 matches).
- Compare vs current baseline: forfeit rate, token accounting, artifact shape.
- Gate: no regressions before using in next battery sprint.

### Migration Phases

#### Phase MA - Spec (Required Before Implementation)
- [x] Add to `SPEC-LLM.md`: invariants OR1-OR5 — `b043b66`
- [x] Add to `SPEC-PLAYER.md`: token mapping note CS5 — `b043b66`
- [x] Update `SPEC-LLM.md` cross-references — `b043b66`

#### Phase MB - Implementation — COMPLETE `b043b66`
- `_RESPONSES_API_ALLOWLIST`, `_validate_and_remap_config()`, system→instructions extraction, `responses.create`, `output_text` fallback, token mapping, `store=False`.

#### Phase MC - Tests — COMPLETE `b043b66`
- `tests/conftest.py` updated with Responses API mock shape.
- `tests/unit/test_openai_player.py`: all 9 cases covered (request shape, system extraction, token remapping, config validation, empty output fallback).
- Migration gate: smoke-validated via B1/B2/B3 battery runs — no regressions in forfeit rate, token accounting, or artifact shape.

### Status
- [x] Phase MA (spec) — `b043b66`
- [x] Phase MB (implementation) — `b043b66`
- [x] Phase MC (tests) — `b043b66`
- [x] Migration gate — smoke-validated via B1/B2/B3 battery runs

## Artifact Policy (This Reset)
- Runtime truth: `agentdeck_runs/<session_id>/records/*.json` and logs.
- Research truth: packaged experiment folders in `research/`.
- Do not delete historical baseline evidence unless explicitly requested.

## Definition of Done
- All six mini-only cells rerun from a clean runtime state.
- Packaged artifacts generated and validation passes.
- One consolidated findings report produced with explicit go/no-go for expansion.
