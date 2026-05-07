# AgentDeck Roadmap

Last updated: 2026-05-06

## Active Focus

The flagship study execution is **complete**. Hugging Face artifact storage is
in place as a private draft, and the curated static viewer is deployed as a
private Hugging Face Space. Current focus is post-merge validation, optional
deck/video production, and then final launch. Hugging Face public visibility
remains a final step after the rest of this roadmap is complete.

Prepared on branch `study/agentic-edge-strategy-stack`; intended landing target:
`main`.

```text
research/2026-04-27-agentic-edge-strategy-stack/
```

The official study arc now aggregates P2 + P3: 9 cells × 48 matches = 432
matches, $1.13 total, all artifacts exported and validated. P2 is the primary
fixed-N study phase; P3 is the targeted FixedDamage S1 cross-tier
ladder-completion cell. See
`research/2026-04-27-agentic-edge-strategy-stack/analysis/analysis_20260428_152909_codex_official_study_analysis/`
for the official authored analysis and support docs. The FixedDamage
tier-inversion claim is strong; the VariableDamage cross-tier frontier remains
caveated by seat effects and non-significance.

## Immediate Work Order

1. Re-run viewer and research validation from `main`.
2. Produce the first visual deck/video draft from the vetted public-narrative
   sources and replay Space, if we want launch collateral before publication.
3. Final launch: make the Hugging Face dataset and Space public, validate public
   URLs, and update any remaining launch wording.

## Current Study Package

Prepared package contents:

- `manifest.yaml` - package metadata, seed base, run envelope, model roster
- `study_overview.md` - final study definition and public framing
- `matrix.yaml` - central cell plan, fairness policy, seed offsets, sampling,
  budget gates, and expansion criteria
- `prompts/` - frozen prompt templates for S0, S1, FixedDamage S3, and
  VariableDamage S3
- `scripts/run_experiment.py` - package-local phase/cell runner
- `results.md` - deterministic factual report
- `analysis/` - authored analysis directory
- `reproduction.md` - dry-run, execution, export, validation, and lock commands
- `recordings/README.md` - external raw-artifact policy
- `artifacts/README.md` - derived-artifact policy

## Study Design Commitments

- Keep `matrix.yaml` as the study spine.
- Use fixed-N sampling for the first flagship version.
- Use `paired_side_swap` with even match counts for head-to-head cells.
- Use only supported first-player policies: `random`, `fixed`, and
  `alternating`.
- Report position effects before topline win-rate claims.
- Disable conclusions in pilot/main cells to keep costs and post-match
  reflection noise controlled.
- Prefer built-in FixedDamage and VariableDamage behavioral scorers before
  adding package-local custom scoring.
- Lock any S2 controller choice after pilot and before main-run expansion.
- Name the exact prior FixedDamage package being replicated before Layer A is
  described as a replication.

## Phase P0 - Local Preflight

Purpose: verify that the package runs without provider credentials.

Cells:

- `p0_fd_bot_smoke`
- `p0_vd_bot_smoke`

Required checks:

- [x] package scaffold exists
- [x] `matrix.yaml` has explicit even match counts for runnable cells
- [x] runner supports phase, cell, dry-run, and match overrides
- [x] list cells cleanly
- [x] P0 dry-run cleanly
- [x] P0 local bot execution writes recordings
- [x] P0 cell export succeeds
- [x] research validation succeeds without introducing fake live results

## Phase P1 - Provider Pilot

Purpose: exercise the main validity surfaces before scaling.

Cells:

- `p1_fd_tier_gap_s0`
- `p1_fd_controller_effect_s1`
- `p1_fd_full_stack_effect_s3`
- `p1_fd_frontier_s3`
- `p1_vd_tier_gap_s0`
- `p1_vd_controller_effect_s1`
- `p1_vd_full_stack_effect_s3`
- `p1_vd_frontier_s3`

Before running P1:

- [x] provider credentials verified (.env loaded; OPENAI_API_KEY + Google ADC confirmed)
- [x] live model IDs confirmed available (gemini-2.5-flash-lite and gpt-4o-mini both responsive in P1 execution)
- [x] `matrix.yaml` budget envelope filled (pilot $2.00, main $10.00, expansion $5.00)
- [x] git commit and pricing snapshot recorded (commit f8ec301, run_commit faddb17, pricing updated_at 2026-02-13)
- [x] P1 dry-run cleanly

After running P1:

- [x] export every P1 cell
- [x] export package-level artifacts
- [x] validate the package
- [x] record measured cost multipliers for S0, S1, and S3 (S0 ~1×, S1 ~1×, S3-FD ~3.7×, S3-VD ~4×)
- [x] check built-in behavioral scorer coverage (all cells have per-cell behavioral profiles; no custom scorer needed)
- [x] update the authored analysis with pilot gates
- [x] decide whether S2 is needed (no — S1 and S3 provide clean isolation; defer S2)
- [x] prune or expand cells before main-run execution (retained all 8 at 48 matches/cell)

## Phase P2 - Main Run ✓ COMPLETE

Purpose: run only selected cells that support preregistered claims.

All gates met before execution:

- [x] explicit cell list in `matrix.yaml` (8 P2 cells)
- [x] fixed even match count per paired-side-swap cell (48/cell)
- [x] locked model roster
- [x] locked prompt templates
- [x] locked controller choices
- [x] budget projection from pilot telemetry (actual $0.98 vs estimate $1.34)
- [x] named FixedDamage replication target
- [x] updated the authored analysis hypothesis readout

Results summary: H1 confirmed strong (S3 vs S0: 70.8pp both tracks); H2 confirmed strong (S1 vs S0: ~57pp both tracks); H3 confirmed marginal (S3 vs S1: 8pp FD, 6pp VD); H4 inconclusive (position effects persist); H5 confirmed as an FD outcome-quality win with cost caveat, caveat VD (S3-RISK 58.3% — high position effect); H6 confirmed with precision: the adapted VD strategy stack transferred cleanly, but the study does not prove raw FixedDamage interventions transfer unchanged.

P3 ladder completion: completed `p3_fd_frontier_s1` to fill the FixedDamage
cross-tier S1 step. `FlashLite-S1-RC` beat `GPT4oMini-S0-AO` 34/48 (70.8%,
p=0.0055). P3 is now included in the official study aggregate through
`phase_model.study_phases: [P2, P3]` and documented under
`analysis/analysis_20260428_152909_codex_official_study_analysis/support/`.

## Post-P2 Work Plan

Purpose: turn the completed P2 run into a publishable research package without
overstating the findings.

Immediate analysis cleanup:

- [x] Correct the cost-quality wording in the authored analysis using per-player costs
  from cell-level artifacts. The current headline should say FlashLite S3 wins
  in FD while costing more than GPT4oMini-S0 per player-match; do not imply a
  cheaper-model cost win against GPT4oMini.
- [x] Tighten the H6 wording. The supported claim is that the adapted strategy
  stack transferred cleanly to VariableDamage. Do not claim that every
  FixedDamage intervention transfers unchanged.
- [x] Create the official authored analysis directory and support docs:
  prompt/protocol audit, layman/business explainer, S1 frontier follow-up, and
  behavioral metrics digest.
- [x] Add P3 to the official study aggregate and rerun deterministic package
  export and validation.

Required follow-up analysis:

- [x] Run a position-disaggregated readout for all P2 cells, with priority on
  `p2_vd_frontier_s3` because first-player win rate was 87.5%.
- [x] Decide whether the VD frontier result is strong enough for the paper
  headline or should be framed as a caveated positive signal.
- [x] Confirm whether any optional n=96 expansion is justified. Default is no
  expansion unless the final report depends on tightening the VD frontier or FD
  frontier confidence interval.

Publication package prep completed so far:

- [x] Add final study definition in `study_overview.md`.
- [x] Update `README.md` after the final interpretation stabilized.
- [x] Run final export and validation after documentation edits that affected
  package metadata or generated indexes.

## Next Work Order

### 1. Hugging Face Artifact Storage

Purpose: make raw and processed study artifacts durable before building public
materials around them.

Dataset:

```text
agentdeck/agentic-edge-strategy-stack-study
```

Tasks:

- [x] Decide dataset visibility, license, and final dataset name.
  - Private draft under `agentdeck`.
  - Public license remains TBD before publication.
- [x] Create the Hugging Face dataset repo.
- [x] Inventory upload payloads:
  - [x] raw recordings from P0/P1/P2/P3 `agentdeck_runs/`
  - [x] per-cell `artifacts/<cell_id>/results.{json,csv,md}`
  - [x] package-level `results.{json,csv,md}`
  - [x] `manifest.yaml`, `matrix.yaml`, `study_overview.md`, `reproduction.md`
  - [x] frozen prompt templates under `prompts/`
  - [x] authored analysis directory under `analysis/`
  - [x] pricing snapshot and git commit metadata
- [x] Decide upload layout:

  ```text
  metadata/
  prompts/
  analysis/
  p0_preflight/
  p1_pilot/
  p2_main/
  p3_supplemental/
  reports/
  ```

- [x] Generate a checksums/manifest file for uploaded artifacts.
- [x] Upload a small sample first and verify download/readability.
- [x] Upload full raw recordings and processed artifacts.
- [x] Update `recordings/README.md` with durable HF pointers.
- [x] Add HF dataset pointer to `README.md`, `study_overview.md`, and
  `reproduction.md`.
- [x] Re-run research validation after pointer updates.

Exit criteria:

- [x] HF dataset exists and contains the study payload.
- [x] Repo docs point to the HF dataset.
- [x] A fresh reader can locate raw recordings, generated results, prompts, and
  authored analysis from the repo alone.

Upload details:

- URL: `https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study`
- Initial full artifact snapshot: `13b95490cdc21dbfb1c164c683e485755f90a271`
- Latest study-arc aggregate refresh: `f7ac119f69da08261269bc5cf85fb65741e8ae88`
- Latest study dataset metadata refresh for publication inspection:
  `be6cd67794edec19be5a54ed92a1235e4a63944a`
- Curated replay Space: `https://huggingface.co/spaces/agentdeck/agentic-edge-viewer`
- Latest replay Space snapshot: `27ca787db947a393d21ed9847a8a4b44b2cbc317`
- Staged upload path: `/tmp/agentic-edge-hf-upload`
- Uploaded manifest: `upload_manifest.json`
- Checksums: `checksums.sha256`

### 2. Viewer and Example Curation

Purpose: pick representative match examples for demos, screenshots, NotebookLM,
and public storytelling.

Tasks:

- [x] Curate one S0 failure example from `p2_fd_tier_gap_s0`.
  - `match_0316b96b`: all-attack collapse, dies at HP=20 with 3 potions unused.
- [x] Curate one S1 pivot example from `p3_fd_frontier_s1`.
  - `match_0430d46c`: uses all 3 potions at HP=20/10/20, wins. Direct mirror of S0 failure.
- [x] Curate one S3 FixedDamage policy-execution example from
  `p2_fd_frontier_s3`.
  - `match_2d1955c8`: every turn shows HP arithmetic; fires POTION at HP=60, 50, 20 exactly.
- [x] Curate one VariableDamage risk-policy example from
  `p2_vd_full_stack_effect_s3`.
  - `match_63fd5bc4`: risk-band rule running visibly at HP=54, 39, 16.
- [x] Curate one VariableDamage caveat example from `p2_vd_frontier_s3`.
  - `match_c2fe0872`: FlashLite follows policy correctly, loses by 2 HP going second.
- [x] Add viewer sidecars or notes for selected matches.
  - Sidecars under `viewer/`: `index.md` + 5 per-match `.md` files with full turn narratives.
- [x] Confirm viewer can load selected examples cleanly.
  - Playwright-validated both paths: 5 raw recordings via `viewer/index.html?match=...` and 5 catalog
    entries via `viewer/matches/study-*`. Each confirmed: `#viewer-container` and `#controls-container`
    visible, expected match/player text present, no page or console errors, playback advances T1→T2.
  - Missing browser libs resolved without sudo: extracted under `/tmp/agentdeck-pw-libs` with
    `LD_LIBRARY_PATH`. Screenshots and `summary.json` written to `/tmp/agentdeck-viewer-validation/`.
  - JS-layer pre-check (RecordLoader.validate via Node.js): all 5 PASS, schema=1.3, frames 16–25.

Exit criteria:

- [x] The study has a small set of demo-ready examples.
- [x] Each example has a one-sentence reason for inclusion.

### 3. Canonical Code Reference

Purpose: make the study reproducible after the main repo evolves without
duplicating source files inside the research package.

Decision:

- The exact AgentDeck git commit is the canonical source-of-truth for game,
  controller, recorder, exporter, validator, and behavioral scorer code.
- The study package should point to that commit wherever reproducibility or
  implementation details matter.
- Do not copy source files into the package unless a future publication venue
  explicitly requires a code snapshot.

Tasks:

- [x] Add Hugging Face `metadata/code_reference.yaml` pointing to the latest
  committed AgentDeck code reference.
  - Dataset snapshot: `409b20f3b63adbf1ee6867704e11918fb303ab63`
  - Superseded by study-arc aggregate refresh:
    `f7ac119f69da08261269bc5cf85fb65741e8ae88`
  - Code reference commit: `d659bdf244d1f0462c0d43aa2609be6c3c4a7672`
  - Historical execution commits remain recorded separately in `matrix.yaml`
    `frozen_inputs`.
- [x] Confirm local study docs point to the final package/viewer commit references before
  publication.
- [ ] Add direct GitHub commit links to the study README/reproduction docs once
  the branch is pushed.
- [x] Re-run research validation after metadata/doc updates.

Exit criteria:

- A reader can resolve the exact implementation by following the recorded commit
  hash.
- The research package stays lightweight and avoids duplicated source snapshots.

### 4. Static Viewer Hosting

Purpose: make the curated match replays accessible from a stable URL before
building public narrative material around them.

Decision:

- Use a Hugging Face Space first because it sits next to the research dataset
  and is the best audience fit for replayable study evidence.
- Keep the Space viewer-only: `viewer/`, bundled renderer assets, and curated
  `viewer/matches/study-*` examples. Avoid exposing unrelated local generated
  research files through the hosted artifact.
- Keep GitHub Pages as a later product/docs route using the same portable viewer
  bundle.

Tasks:

- [x] Make the viewer portable by bundling runtime renderer CSS/JS and assets
  under `viewer/renderers/`.
- [x] Validate the portable viewer locally when serving either repo root or
  `viewer/` directly.
- [x] Create a private Hugging Face Space for the curated replay viewer.
- [x] Upload the first Space bundle with only the five curated study matches.
- [x] Verify the remote Space files and local Space bundle behavior.
- [x] Fix private-Space scene background loading by moving the retro background
  image out of stylesheet-relative `url(...)` resolution and into renderer-owned
  app-origin asset loading.
- [x] Ensure the deploy artifact includes:
  - [x] `index.html`
  - [x] viewer CSS/JS assets
  - [x] bundled renderer CSS/JS used by FixedDamage and VariableDamage
  - [x] curated `matches/study-*` records and `.meta.json` sidecars
  - [x] `matches/manifest.json` containing only the study entries
- [x] Add Space and dataset cross-links.
- [x] Update `scripts/viewer_smoke_check.js` so the five curated `study-*`
  matches are covered by the cheap local regression check.
- [x] Extend `scripts/viewer_smoke_check.js` with `VIEWER_ROOT` so stripped
  static bundles can be checked directly.
- [x] Validate `/tmp/agentic-edge-viewer-space` directly with the smoke check.
- [x] Manually hard-refresh the private Space and confirm the background,
  selected-match picker, first replay, and victory overlay render correctly.
  - Confirmed after Space snapshot `27ca787db947a393d21ed9847a8a4b44b2cbc317`.
  - Victory overlay stacking fixed in the portable retro JRPG renderer.
- [x] Polish the five curated match labels/synopses for non-technical readers.
- [x] Refresh the Space bundle after label/synopsis polish.
- [x] Improve match-picker UX so selecting a different match loads it
  immediately; keep the reload button as a manual fallback.
  - Deployed in Space snapshot `27ca787db947a393d21ed9847a8a4b44b2cbc317`.
- [x] Polish select controls so the dropdown arrow has consistent right
  spacing in the match, skin, mobile-sheet, and speed selectors.
  - Deployed in Space snapshot `27ca787db947a393d21ed9847a8a4b44b2cbc317`.
- [x] Keep the reasoning panel above combatants in the retro JRPG scene while
  preserving the victory overlay as the top layer.
  - Deployed in Space snapshot `27ca787db947a393d21ed9847a8a4b44b2cbc317`.
- [x] Decide public Space history strategy.
  - Decision: keep the existing private Space history. The current file surface
    is clean, and rewriting/deploying a single-commit Space would add process
    risk without improving the public study artifact.
- [x] Final-inspect the private Hugging Face Space before publication:
  - [x] file surface contains only the static viewer bundle, five curated
    matches, renderer assets, and required HF metadata
  - [x] Space card/metadata has correct public-facing wording and links
  - [x] no stale, draft-only, private-note, or unrelated research files remain
- [x] Final-inspect the private Hugging Face dataset before publication:
  - [x] file surface contains canonical study artifacts and external raw
    recordings only
  - [x] dataset card/metadata has correct public-facing wording and Space link
  - [x] no downstream public-narrative drafts or stale package outputs remain
  - Dataset metadata refresh snapshot:
    `be6cd67794edec19be5a54ed92a1235e4a63944a`
- [ ] Final launch step after the rest of this roadmap is complete:
  - [ ] make the Hugging Face dataset public
  - [ ] make the Hugging Face Space public
  - [ ] run public URL validation for the dataset, Space, and all five curated
    examples
  - [ ] update any remaining local launch/docs wording that still assumes
    private-only visibility
- [ ] Optional later: add a GitHub Pages deployment workflow for the same bundle.

Exit criteria:

- Each curated match has a stable hosted URL.
- The hosted viewer loads the five examples with no console/page errors.
- Presentation/docs can link directly to replayable evidence.

Hosting details:

- Space URL: `https://huggingface.co/spaces/agentdeck/agentic-edge-viewer`
- Space snapshot: `27ca787db947a393d21ed9847a8a4b44b2cbc317`
- Space visibility: private draft
- Local Space bundle: `/tmp/agentic-edge-viewer-space`
- Local validation screenshots: `/tmp/agentdeck-hf-space-bundle-validation/`
- Background-fix validation screenshots:
  `/tmp/agentdeck-hf-space-bg-validation/`

### 5. Public Narrative Package

Purpose: turn the study into external-facing material without overstating the
findings.

Tasks:

- [x] Draft a public findings report from `study_overview.md`,
  `results.md`, behavioral metrics, prompt audit, and selected match examples.
- [x] Build a NotebookLM source bundle list:
  - [x] `study_overview.md`
  - [x] official authored analysis
  - [x] layman/business explainer
  - [x] behavioral metrics digest
  - [x] prompt/protocol audit
  - [x] deterministic `results.md`
  - [x] selected P3/S1 follow-up if using a dedicated S1 slide
  - [x] local paths plus Hugging Face links for all recommended sources
- [x] Create a presentation outline:
  - [x] why AgentDeck
  - [x] what was tested
  - [x] S0 to S1 to S3 tuning ladder
  - [x] behavior changed beyond win rate
  - [x] VariableDamage transfer and caveat
  - [x] business implications
  - [x] reproducibility and artifact trail
- [x] Add a deck QA checklist with slide-by-slide claim, number, prompt, and
  caveat checks.
- [ ] Produce first visual deck/video draft.
  - Deferred until the public dataset/Space URLs are stable.
- [x] Review all numbers against `results.md` and per-cell artifacts.
- [x] Use the private Space as the replay evidence surface while drafting the
  public deck/video.
- [ ] After the narrative package stabilizes, refresh Hugging Face dataset
  metadata and the Space bundle with final links and labels.

Exit criteria:

- Public narrative has correct numbers and caveats.
- FixedDamage headline is strong and precise.
- VariableDamage is framed as strong within-model repair, not strong cross-tier
  dominance.

### 6. Technical Report / Paper-Readiness

Purpose: decide whether this becomes a technical report only or a paper-style
artifact.

Tasks:

- [x] Draft technical report outline.
  - `public_narrative/technical_report_outline.md`
- [x] Add prior-research comparison using committed artifacts, not only
  historical human writeups.
  - `public_narrative/prior_research_context.md`
  - Decision: older arc packages are useful context, but their March synthesis
    aggregate `results.json` files are not the primary numeric source for the
    flagship claims.
- [x] Decide whether older arc packages are contextual background or empirical
  evidence in the final report.
  - Decision for current public artifact: treat older arc packages as contextual
    background unless a later paper pass revalidates their artifacts directly.
- [x] Add limitations section:
  - [x] synthetic games
  - [x] narrow model roster
  - [x] provider drift
  - [x] prompt specificity
  - [x] VariableDamage seat effects
  - [x] no broad domain generalization claim
- [x] Decide whether arXiv-style submission is justified.
  - Decision for now: publish as a technical case study. Keep paper-style
    submission as a later option after broader model coverage or a
    VariableDamage position-effect expansion.

Exit criteria:

- We know whether the public artifact is a case study, technical report, or
  paper candidate.

### 7. Final Repo Cleanup and Commit Decision

Purpose: keep research artifacts, engine changes, and release packaging cleanly
separated.

Tasks:

- [x] Review dirty worktree and separate:
  - [x] engine/product changes:
    - `specs/SPEC-VIEWER.md`
    - `scripts/viewer_smoke_check.js`
    - `viewer/README.md`
    - `viewer/index.html`
    - `viewer/css/base.css`
    - `viewer/js/app.js`
    - `viewer/matches/manifest.json`
    - `viewer/matches/study-*`
    - `viewer/renderers/`
  - [x] flagship research package artifacts:
    - `research/2026-04-27-agentic-edge-strategy-stack/`
    - `research/INDEX.md`
  - [x] public narrative material:
    - `research/2026-04-27-agentic-edge-strategy-stack/public_narrative/`
  - [x] legacy generated research refreshes:
    - older `research/2026-03-*/results.json` files normalized separately so
      pairwise statistics only contain direct head-to-head comparisons under
      the current validator.
  - [x] generated local run artifacts that should remain uncommitted:
    - no `agentdeck_runs/` directories are currently staged/tracked.
  - [x] unrelated local-only docs to keep out of this study branch unless
    explicitly requested:
    - `docs/spec-driven-value-*`
    - `docs/spec-driven-value-report_codex - Copia.md:Zone.Identifier`
- [x] Run full tests for engine changes.
  - `.venv/bin/python -m pytest` -> 541 passed, 2 skipped.
- [x] Run research export/validate one final time.
  - `.venv/bin/python scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --package --no-generated-at`
  - `.venv/bin/python scripts/research_validate.py --research-dir research`
  - `node scripts/viewer_smoke_check.js`
  - `VIEWER_ROOT=/tmp/agentic-edge-viewer-space node scripts/viewer_smoke_check.js`
- [x] Decide exactly what to commit for the study package.
  - Recommended commit group: `research/2026-04-27-agentic-edge-strategy-stack/`
    plus `research/INDEX.md`.
  - Include the analysis directory, generated package outputs, per-cell P1/P2/P3
    artifacts, study overview, viewer notes, recordings pointers, and public
    narrative package.
  - Historical March result normalization is committed separately as
    `c29cbf1`.
- [x] Decide exactly what to commit for engine/product polish.
  - Recommended commit group: `specs/SPEC-VIEWER.md`,
    `scripts/viewer_smoke_check.js`, `viewer/README.md`,
    `viewer/index.html`, `viewer/css/base.css`, `viewer/js/app.js`,
    `viewer/matches/manifest.json`, `viewer/matches/study-*`, and
    `viewer/renderers/`.
  - This should be separate from the study-package commit so product/viewer
    evolution is reviewable on its own.
- [x] Only after explicit authorization: commit.

Release policy:

- [x] Do not commit the research package until explicitly authorized.
- [ ] Do not push or publish a new package version until the entire experiment
  package, writeup, artifact pointers, and any necessary engine polish are
  finished.
- [x] Keep engine/product polish tracked separately from research artifacts.

## Research Workflow

Use package-local execution and shared export/validation:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --list-cells
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1 --dry-run
agentdeck-research-export --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --package --no-generated-at
agentdeck-research-validate --research-dir research
```

Raw recordings should be stored externally, with pointers under
`research/2026-04-27-agentic-edge-strategy-stack/recordings/`.

If the console entry points are not installed in a checkout, use the repo-local
wrappers:

```bash
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --list-cells
python3 scripts/research_validate.py --research-dir research
```

## Deferred AgentDeck Product Work

These are not blockers for the study package:

- Native session recovery in the research CLI
- Segmented execution as a framework-level capability
- Duplicate-session pruning in core
- Promotion of package-specific runner logic into framework core
- Broader Autonomous Researcher workflows
- MatchCurator recording-first refactor and LLM-backed curation

## 0.2.x Engineering Hardening

- Decompose `console.py` into narrower lifecycle, scheduling,
  fairness/player-ordering, parse-failure, conclusion, metadata, and
  replay/event-dispatch modules.
- Pick one stable strict-mypy island first, then expand enforcement
  progressively instead of flipping the whole codebase at once.
