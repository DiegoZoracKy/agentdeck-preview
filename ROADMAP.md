# AgentDeck Roadmap (Research + Product Release)

Last updated: 2026-02-19T18:20:00Z
Owner: Diego + Codex + Claude

## North Star
Prove cost-efficiency gains from strategy tuning (AO vs CoT-H vs CoT-T) in a reproducible benchmark, and ship the same evidence as a product-facing experience in the viewer.

## Current Snapshot
- Completed:
  - Recorder hardening committed (`fd13df6`) and validated.
  - Packaging/spec workflow commit completed (`9ec7414`).
  - Viewer mobile/desktop stabilization committed (`53d4cd8`, `330df52`, `ab10a65`).
  - One-match smoke package generated at `research/2026-02-18-openai-mini-smoke`.
- Current repo state:
  - Working tree was clean at kickoff for this phase.
  - Ready to proceed with matrix preflight.
  - Execution focus now: mini-only baseline-first sprint (`c26`, `c27`, `c28`, `c01`, `c02`, `c03`).

## Source of Truth
- Matrix: `research/2026-02-13-performance-methods-benchmark-matrix/matrix.yaml`
- Out-of-the-box execution contract: `research/2026-02-13-performance-methods-benchmark-matrix/OUT_OF_THE_BOX_REQUIREMENTS.md`
- Research package contract (draft): `specs/drafts/SPEC-RESEARCH-EXPERIMENT-v1.2.0.md`
- Recorder contract (final): `specs/SPEC-RECORDER.md`

## Product + Engineering Principles (Locked)
- Use only AgentDeck native execution features for runs (no ad-hoc calculators/print pipelines).
- Research docs in core must stay framework-level; experiment-specific docs stay inside each `research/<experiment>/`.
- Current-version-first: no backward-compat constraints for pre-launch artifacts/specs.
- Keep provenance auditable: freeze inputs before each major run and keep runtime git state clean.
- Viewer polish should support adoption, but must not block benchmark execution.

## Runtime Decisions (Locked)
- `max_turns = 30`
- `concurrency = 10`
- `conclusion = enabled` (feature showcase + research realism)
- `max_tokens`: do not cap unless API requires; when required use high headroom to avoid truncation forfeits.
- Parse policy for benchmark remains real-world (`FORFEIT` behavior on parse failure).
- Campaign order: `Preflight -> A1 -> A2 -> A3 -> A4`.

## Statistics Direction (Spec Track)
This is the target behavior for experiment artifacts:
- `results.json.statistics` is core research output (not optional narrative).
- Requirement policy:
  - MUST for `complete|archived`.
  - SHOULD for `running` when `n_decisive > 0`.
- Quality tiers: `insufficient|low|moderate|high` with explicit numeric thresholds.
- Actionability:
  - `is_actionable` explicit bool.
  - false for insufficient evidence.
- Recommendation math:
  - `n_recommended_total = max(min_decisive_for_inference, n_for_80pct_power, n_for_precision)`.
  - Power target uses configured MDE (not fragile observed effect from tiny N).
- Separation of concerns:
  - packager writes factual blocks only.
  - interpretation remains human-owned.

## Experiment Identity / Naming Direction
- Stable series id: `experiment_key`.
- Unique run id: `experiment_id`.
- Preferred unique folder pattern:
  - `research/<experiment_key>__<session_suffix>/`
  - where `session_suffix = YYYYMMDD_HHMMSS_hash6` (reused from `session_id`).
- Goal: deterministic traceability between packaged experiment and raw session artifacts, with collision-free same-day reruns.

## Execution Plan

### Phase 0 - Hardening Baseline
- Status: COMPLETE
- Exit achieved: recorder and packager validations green.

### Phase 1 - One-Match Smoke (OOTB)
- Status: COMPLETE
- Output: `research/2026-02-18-openai-mini-smoke`
- Purpose: validate end-to-end flow (run -> record -> package -> validate).

### Phase 2 - Matrix Preflight Gate
- Status: NEXT
- Scope: 4 sentinel cells, 6 matches each (`matrix.yaml -> execution_plan.preflight`).
- Gate:
  - forfeit/instability <= 5%.
  - prompt/config correctness confirmed for all providers in preflight.
- If failed:
  - fix config/prompt/provider limits and rerun preflight only.

### Phase 2.5 - Mini-Only Strategy Sprint (Current)
- Status: NEXT
- Scope: run only `gpt-4o-mini` baseline + Track 1 cells.
  - `c26_t0_openai_weak_ao_vs_ao` (baseline AO vs AO)
  - `c27_t0_openai_weak_coth_vs_coth` (baseline CoT-H vs CoT-H)
  - `c28_t0_openai_weak_cott_vs_cott` (baseline CoT-T vs CoT-T)
  - `c01_t1_openai_weak_ao_vs_coth` (AO vs CoT-H)
  - `c02_t1_openai_weak_ao_vs_cott` (AO vs CoT-T)
  - `c03_t1_openai_weak_coth_vs_cott` (CoT-H vs CoT-T)
- Matches: 24 per cell (pilot), deterministic seeds by runner.
- Objective:
  - establish robust mirror baselines before method comparisons;
  - quantify CoT uplift over AO;
  - quantify incremental uplift of persistent instruction reinforcement (CoT-T) over handshake-only (CoT-H).
- Note:
  - OpenAI-only run (no Anthropic/Google dependency for this sprint).

### Phase 3 - A1 OpenAI Strategy Discovery
- Status: PENDING
- Scope: 7 cells, 24 matches/cell.
- Objective:
  - prove CoT uplift,
  - test instruction persistence impact (CoT-H vs CoT-T),
  - calibrate behavior on top-tier OpenAI model.
- Deliverable:
  - publishable A1 package + curated viewer highlights.

### Phase 4 - A2 Opponent Strategy Calibration
- Status: PENDING
- Scope: Anthropic/Google AO vs CoT-T calibration cells.
- Objective: determine strongest/worst opponent strategy assumptions for later head-to-head claims.

### Phase 5 - A3 OpenAI Cost-Efficiency Showcase
- Status: PENDING
- Scope: mini strategy variants vs 4o / 5.2 variants.
- Objective: establish the central thesis (task tuning can beat raw model spend).

### Phase 6 - A4 Cross-Provider Challenge
- Status: PENDING
- Scope: tuned mini strategy vs weak/strong Anthropic and Google settings.
- Objective: external validity of the cost-efficiency thesis.

## Immediate Checklist (Start Here)
- [x] Freeze matrix inputs in `matrix.yaml.frozen_inputs` (`git_tag`, `git_commit`, `prompt_template_version`).
- [x] Resolve and confirm mini-only execution plan via dry-run.
- [ ] Execute mini-only baseline-first sprint (`c26-c28`, `c01-c03`, 24 matches/cell).
- [ ] Package + validate mini-only sprint results and publish interim findings.
- [ ] Run preflight sentinel cells (4 x 6).
- [x] Validate generated research artifacts (`research_validate.py`).
- [ ] Check preflight reliability gate (<= 5% forfeit/instability).
- [ ] Decide go/no-go for A1.

## Commands
- Validate research packages:
  - `.venv/bin/python scripts/research_validate.py --research-dir research`
- Targeted regression tests:
  - `.venv/bin/pytest -q tests/unit/test_recorder_lifecycle.py tests/integration/test_match_lifecycle.py tests/unit/test_research_packager.py`
- One-match smoke runner:
  - `python3 research/2026-02-13-performance-methods-benchmark-matrix/scripts/run_one_match_openai_mini.py`

## Open Questions (Non-Blocking for Preflight)
- Final numeric thresholds for tier boundaries and `is_actionable` cut.
- Whether to emit `statistics` in all `running` packages by default or only when explicitly requested.
- Timestamp readability convention (`YYYYMMDD` vs `YYYY-MM-DD`) across session/experiment ids.
