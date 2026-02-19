# AgentDeck Roadmap (Execution-First)

Last updated: 2026-02-19T01:56:39Z
Owner: Diego + Codex + Claude

## North Star
Deliver a credible and engaging research release proving cost-efficiency gains from strategy tuning (AO vs CoT-H vs CoT-T), starting with OpenAI anchor experiments and then cross-provider validation.

## Source of Truth
- Matrix: `research/2026-02-13-performance-methods-benchmark-matrix/matrix.yaml`
- Experiment package spec (current): `specs/drafts/SPEC-RESEARCH-EXPERIMENT-v1.2.0.md`
- Recorder spec (current): `specs/SPEC-RECORDER.md`

## Operating Rules
- Use only AgentDeck out-of-the-box execution features for experiment runs.
- Keep provenance clean before major runs (commit critical recorder/runtime changes first).
- Validate artifacts with `scripts/research_validate.py` after packaging.
- Keep viewer as product anchor, but do not block research execution on UI polish.

## Locked Decisions
- `max_turns = 30`
- `concurrency = 10`
- `conclusion = enabled`
- Avoid restrictive `max_tokens` caps that can cause forfeit by truncation.
- Preflight gate before full A1.
- Campaign order: Preflight -> A1 -> A2 -> A3 -> A4.

## Current Status
- Completed:
  - Recorder correctness hardening committed (`fd13df6`): batch context enforcement + finalized player summary costs.
  - Viewer detour isolated in dedicated commits (`53d4cd8`, `330df52`, `ab10a65`).
- In progress:
  - Research packaging/spec refinement block (uncommitted working tree).

## Execution Roadmap

### Phase 0 - Baseline Hardening (Done)
- Status: COMPLETE
- Exit criteria met:
  - Recorder changes committed and tests passing.
  - Research validator passing on repo state.

### Phase 1 - Close Pending Research Packaging Block (Now)
- Status: IN PROGRESS
- Scope:
  - `src/agentdeck/research/packager.py`
  - `tests/unit/test_research_packager.py`
  - `specs/drafts/SPEC-RESEARCH-EXPERIMENT-v1.2.0.md`
  - smoke artifact updates:
    - `research/2026-02-18-openai-mini-smoke/manifest.yaml`
    - `research/2026-02-18-openai-mini-smoke/results.json`
    - `research/INDEX.md`
- Exit criteria:
  - Targeted tests pass.
  - `scripts/research_validate.py --research-dir research` passes.
  - Commit created for this block.

### Phase 2 - Spec Finalization for Statistical Artifacts
- Status: PENDING
- Decisions to lock in spec:
  - Tier thresholds (`insufficient|low|moderate|high`) with numeric boundaries.
  - `statistics` requirement policy:
    - MUST for `complete|archived`
    - SHOULD for `running` when `n_decisive > 0`.
  - Clarify 2-player behavior (`comparisons` vs `pairwise_comparisons`).
  - Standardize actionable interpretation message field.
  - Align examples with default parameters.
- Exit criteria:
  - Draft updated and internally approved for implementation.

### Phase 3 - Preflight Gate (4 Sentinel Cells)
- Status: PENDING
- Source: `matrix.yaml -> execution_plan.preflight`
- Run:
  - 4 cells x 6 matches each.
- Gate:
  - Forfeit/parse instability <= 5%.
  - If gate fails: fix config and rerun preflight.

### Phase 4 - A1 OpenAI Strategy Discovery
- Status: PENDING
- Source: `matrix.yaml -> execution_plan.phases[A1]`
- Run:
  - 7 cells x 24 matches per cell.
- Outputs:
  - Packaged artifacts, validated.
  - Initial viewer curation from highlights.

### Phase 5 - A1 Drop (Research + Product)
- Status: PENDING
- Deliverables:
  - Research package updated (results + analysis + index).
  - Curated matches linked to viewer.
  - Short findings summary: uplift, instruction persistence impact, cost-per-win narrative.

### Phase 6 - Continue Campaign
- Status: PENDING
- Next phases:
  - A2 Opponent Strategy Calibration
  - A3 OpenAI Cost-Efficiency Showcase
  - A4 Cross-Provider Challenge

## Immediate Checklist (Start Here)
- [ ] Commit pending Phase 1 packaging/spec/artifact changes.
- [ ] Re-run validator and keep output green.
- [ ] Freeze matrix inputs (`git_tag`, `git_commit`, prompt template version, pricing snapshot).
- [ ] Execute preflight sentinel cells.
- [ ] Decide go/no-go for A1.

## Command Sheet
- Validate research packages:
  - `.venv/bin/python scripts/research_validate.py --research-dir research`
- Targeted tests (recorder/packager path):
  - `.venv/bin/pytest -q tests/unit/test_recorder_lifecycle.py tests/integration/test_match_lifecycle.py tests/unit/test_research_packager.py`
- One-match smoke:
  - `python3 research/2026-02-13-performance-methods-benchmark-matrix/scripts/run_one_match_openai_mini.py`

## Non-Blocking Backlog
- Experiment/session naming harmonization (`YYYY-MM-DD` readability vs current compact timestamp).
- Final decision on unique rerun folder convention tied to session suffix.
- Additional baked-in statistics ergonomics once A1 real data lands.
