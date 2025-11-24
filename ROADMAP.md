# AgentDeck Pre-Release Roadmap

> **Last Updated**: 2025-11-23
> **Status**: Final polish phase (v0.1.0-rc → v0.1.0 public) — previously tracked as v0.3.0
> **Release Readiness**: 8.0/10 (P0s cleared; polishing evidence/docs)

---

## Cleanup Plan for Clean RC Export (to delete, not archive)

Keep: `docs/research/`, `experiments/` (research reference).

Delete the following before seeding the clean repo:
- Root planning/internal (6): `MERGED_RELEASE_READINESS_PLAN.md`, `PRE_RELEASE_GAP_ANALYSIS.md`, `RELEASE_READINESS_ASSESSMENT.md`, `REVISED_PRIORITY_LIST.md`, `ROADMAP-v0.3-archive.md`, `SPEC_UPDATE_PLAN.md`
- Root analysis sessions (all 23): `analysis_session_*.md`
- Outdated release notes (1): `RELEASE_NOTES_v0.3.0.md`
- Root generated/temp (3): `.coverage`, `coverage.xml`, `experiment1_output.log`
- Secrets (1): `.env`
- Docs validation (stale/contradictory) (2): `docs/EXPERIMENT-VALIDATION-PLAN.md`, `docs/PHASE-C-VALIDATION-COMPLETE.md`
- Docs assessments (internal) (all): `docs/assessments/*.md`
- Docs proposals/planning/migration (3): `docs/planning/SPEC-BATCH-CHECKPOINT.md`, `docs/proposals/PROPOSAL-horizon1-integration.md`, `docs/migration/observability-v17.md`
- Specs archived/proposals/critiques (7): `specs/SPEC-CONTROLLER-v1.2.0-ARCHIVED.md`, `specs/SPEC-CONTROLLER-v1.3.0-ADDENDUM.md`, `specs/SPEC-CONTROLLER-v1.3.0-PROPOSAL.md`, `specs/SPEC-PLAYER-v1.x-PROPOSAL.md`, all `specs/*-CRITIQUES.md`
- Build artifacts (2): `UNKNOWN.egg-info/`, `_private/` (if present)
- Other generated/virtualenv (clean for export): `venv/`, `agentdeck_runs/`, `agentdeck_records/`, `build/`, `htmlcov/`

---

## For Newcomers - Start Here

**Essential Reading (in order):**
1. **[README.md](./README.md)** - Project overview, quick start, core capabilities
2. **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Spec-driven workflow, contribution guidelines
3. **[specs/SPEC.md](./specs/SPEC.md)** - Specification navigation hub, design principles
4. **This ROADMAP** - Current priorities, P0/P1/P2 items, and release timeline

---

## Overview

This roadmap tracks work needed for the first public release (v0.1.0) in the fresh repository. Earlier internal milestones referred to this as v0.3.0; the scope is unchanged, only the public tag resets to v0.1.0.

---

## Current Status

### Strengths ✅
- Spec-first discipline and clean architecture
- Researcher-friendly telemetry (replay, observability, deterministic experiments)
- Parallel execution validated (10× concurrency speedup)
- Zero-dependency mock demo works out of the box

### Known Gaps (must address before public tag)
- Fresh CI evidence: rerun suite under strict gates to publish current test counts/coverage with updated thresholds
- Release polish (post-P0): publish doc site/automation (PyPI, API docs) after initial tag

---

## Release Timeline Options

| Option | Duration | Scope | Readiness Score |
|--------|----------|-------|-----------------|
| **Minimum Viable** | 8-12h | Fix P0 blockers only | 7.5/10 → Usable RC |
| **Proper v0.1.0** | 23-34h | P0 + P1 priorities | 8.5/10 → Solid release |

**Recommended**: Proper v0.1.0 - Balances quality with shipping momentum.

---

## Immediate Work (Pre-Release)

### P0 Blockers (must fix before any public tag) — ~8-12h total
- [x] Fix broken URLs/repos in pyproject.toml and examples/README.md — 1h
- [x] Clean root clutter: delete 30+ planning/analysis files per cleanup list above — 1h
- [x] CI must fail on quality issues: remove `--exit-zero` for pylint, fix `|| true` for mypy, enforce coverage — 2-3h
- [x] Export `TurnBasedGame` in `__init__.py` (used in TUTORIALS.md) — 30m
- [x] Verify `.env` not in shared artifacts; rotate keys if exposed — 30m
- [x] ResultsAnalyzer.export_csv: use "gameplay" event type (not "turn"); add regression test — 1h
- [x] Add LICENSE file (MIT) + CHANGELOG entries for v0.1.0 — 1h
- [x] Align pricing.yaml to official OpenAI Standard tier values — 2h
- [x] Require explicit `model` for all LLM players (GPTPlayer, ClaudePlayer, GeminiPlayer); update README/examples/tests — 2-3h

### P1 Important (polish before v0.1.0 if time permits) — ~15-22h total
- [x] Docs consistency: reconcile test counts/coverage/readiness claims across README/validation docs — 1-2h
- [x] Docs reorg plan: define a coherent docs/ structure and author a lean, ordered set (overview → quickstart → guides → reference); relocate `docs/research/` to top-level `research/` for clarity — 3-4h
- [x] "Build your first game" walkthrough + "Debug with replay" artifact tour — 4-6h
- [x] Provider imports fail gracefully when extras missing (lazy imports with clear error messages) — 2-3h
- [x] Isolate provider SDKs into optional extras; slim base dependencies — 3-4h
- [x] Parameter naming consistency: use `controller` only; remove `action_controller` mentions — 1-2h
- [x] Python version consistency: align pyproject.toml (3.8+) with TROUBLESHOOTING claims — 15m
- [x] Packaging extras cleanup: fix recursive/all extras; move dev deps to `[dev]` — 1-2h
- [x] First impression fixes: tidy README promises (lines of code, performance claims) to match reality — 1-2h

### P2 Nice-to-Haves (post-release / v0.1.x)
- [x] LLMPlayer.reset_conversation should reset ConversationManager if externally injected (SPEC-PLAYER CS3) — 1h
- PyPI distribution + release automation — 2-3h
- Auto-generated API docs (Sphinx/MkDocs) — 4-8h
- Research module enhancements (I² heterogeneity statistic) — variable
- External contributor guidelines — 2h

---

## Notes on Pricing Scope
- Canonical tier for v0.1.0: **Standard** (input/output per 1M tokens) from the official table.
- Cached-input, batch, flex, and priority tiers are out of scope for v0.1.0; would require schema changes in `pricing.yaml` and `utils/pricing.py`.
- Image/audio/realtime entries use the same two-field schema (input/output) until richer tiering is added.
- Record pricing snapshot per run: capture the Standard-tier pricing entries for the specific models used in a batch (model → input/output per 1M) alongside match/session metadata so cost analyses remain auditable even if pricing.yaml changes.

---

## Validation & Evidence (to refresh after P0/P1)
- Re-run CI after quality gates are strict.
- Re-run minimal provider-backed experiment once explicit models are required.
- Update test counts/coverage in README and validation docs after fixes land.

---

## How to Contribute

**Before starting work:**

1. **Review this roadmap** for current priorities and parallel workstreams
2. **Check dependencies** - Each section lists what can start immediately vs what's blocked
3. **Read essential docs** - See "For Newcomers" section above
4. **Follow spec-driven workflow** - See [CONTRIBUTING.md](./CONTRIBUTING.md) Phase A → B → C
5. **Target main branch** for all PRs

**For questions:**
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines and workflow
- [specs/SPEC.md](./specs/SPEC.md) - Specification navigation hub

---

## Post-Release (v0.1.1+)

After v0.1.0 public release, iterate on community feedback:

- **Hero walkthrough narrative** - End-to-end story from hypothesis → experiment → conclusion
- **"Why AgentDeck" comparison** - Differentiation vs ad-hoc scripts, LangChain, etc.
- **Extension templates** - CLI scaffolds for games/players/spectators
- **Authoring guides** - Dedicated docs for extending AgentDeck
- **Research examples** - Showcase multi-model experiments
- **Cost-effectiveness analyzer** - Visualize cost vs win rate across experiments
- **Web documentation** - Restructure with navigation & tutorials
- **PyPI distribution** - Automate releases via GitHub Actions

---

## Summary

**Release Readiness**: 8.0/10 (P0s closed; targeting 8.5/10 with fresh CI evidence)

**Remaining to v0.1.0 final**: ~4-6h
- Fresh CI run to publish test counts/coverage with stricter gates
- Optional release polish (PyPI automation + API docs) if time allows

**Open Decisions**:
- Whether to publish doc site/API docs now or defer to v0.1.x
- When to enable release automation (PyPI + GitHub Actions) after the initial tag

**Status**: Final polish phase. Claude Code and Codex assessments align on priorities. Fix P0s first for credibility, then P1s for polish.

---

## AgentDeck Experiments (What/Why/How/Value)

**What**: A companion `agentdeck-experiments` repository for community-driven experiments—configs, prompts, seeds, manifests, and analyses—while heavy recordings live in Hugging Face Datasets.

**Why**: Keep the core repo lean and fast while enabling rich, reproducible sharing of experiments without hitting GitHub size limits (1 GB soft / 5 GB hard).

**How**: Hybrid model with clear separation:

```
agentdeck-experiments/           # GitHub repo
├── README.md                    # Contribution guide, retention policy
├── MANIFEST_SCHEMA.md           # How to document external data
├── templates/
│   ├── experiment-template/
│   └── manifest-template.yaml
├── experiments/
│   └── <experiment-slug>/
│       ├── config.yaml          # AgentDeck version, seeds, model names
│       ├── hypothesis.md        # Research question
│       ├── analysis.ipynb       # Notebook with results
│       ├── results/             # Summary CSVs, plots (small, in Git)
│       └── manifest.yaml        # Links to HF dataset + checksums
└── benchmarks/                  # Standard reproducible benchmarks
```

**Manifest template** (per experiment):
- `agentdeck_commit`, `agentdeck_version`
- `models` (names), `seeds`
- `pricing_snapshot` (Standard tier input/output per 1M)
- `hf_dataset` URL + split names
- `checksums` for linked archives
- `reproduce_commands` (CLI/py script)
- `python_version`, `hardware_notes` (optional)

**Workflow**:
1. Contributor opens PR adding `experiments/<slug>/` with README, config, manifest, notebooks, summaries
2. Upload recordings to HF Datasets (`agentdeck/<slug>`)
3. Reference HF dataset in manifest with checksums
4. No raw recordings in Git; Git LFS minimal or unused

**Value**:
- Researcher-friendly: fast clone, familiar PR workflow, easy `datasets.load_dataset("agentdeck/<slug>")`
- Scalable: HF has no practical size limits
- Auditable: manifests ensure reproducibility (versions, seeds, pricing, checksums)
- Discoverable: HF visibility in ML community + GitHub for collaboration
