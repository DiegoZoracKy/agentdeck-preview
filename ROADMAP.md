# AgentDeck Roadmap

Last updated: 2026-03-30

## Release Position
- AgentDeck targets a public beta / preview release, not `1.0`.
- All spec-compliance audit waves (0–6) are complete.
- All pre-release blocker-level spec drifts are resolved.
- The research showcase has expanded beyond the original FixedDamage plan to a two-arc study covering both deterministic and stochastic game settings.

## Scope of This Roadmap
This roadmap tracks implementation, documentation, examples, research workflow, and in-repo release readiness for AgentDeck itself.

It does not track:
- external launch operations or social/media plans
- showcase surfaces outside the repo
- broader AI-first meta-experiment storytelling
- Autonomous Researcher exploration tracks

Those live in separate internal planning.

## What Is Already Done

- Core fairness, recorder, artifact-validation, and metadata fixes
- Viewer beta baseline
- Research export, packaging, validation, and index tooling
- Spec-compliance audit ledger (`docs/spec-compliance/`)
- **FixedDamage Arc 1**: 19 packages, 1,000+ matches, full intervention ladder (RC → TR → HP → exit), cross-provider comparisons, behavioral scorer
- **VariableDamage Arc 1**: 12 packages, 744 matches, plain-model baselines, intervention ladder (RC → RISK), cross-provider comparisons, new behavioral metrics (`safe_zone_potion_rate`, danger subbands, `first_lethal_entry_inventory`), and the main-arc premium pilot

## Remaining Pre-Release Work

### 1. Final Experiments
- [x] `FlashLite-RC-RISK` vs `GPT5Mini-AO` at `N=24` — main VariableDamage arc final

**Optional Pre-Release Appendix (budget permitting)**
- [ ] `GPT-5-AO` vs `Flash-AO` at `N=24` — premium behavioral appendix
- [ ] `Opus-AO` vs `Flash-AO` at `N=24` — premium behavioral appendix

### 2. Research Synthesis
- [x] VariableDamage Arc 1 summary (parallel to FixedDamage Arc 1)
- [x] Cross-game comparison document:
  - what transfers across games and what does not
  - what the behavioral layer revealed beyond win rates alone
  - how deterministic and stochastic settings probe different aspects of agent behavior
- [x] Update `research/INDEX.md` and arc-level READMEs to reflect the completed two-arc picture

### 3. Docs & Examples Productization
- [x] README first-touch pass:
  - make AgentDeck's primary promise explicit: bring an idea, turn it into a runnable, replayable, analyzable behavioral experiment
  - reduce early overload from deep research detail
  - align wording with beta / preview release posture
- [x] Top-level docs pass for consistency with the completed two-arc research picture
- [x] "How to run a study" guide for external users
- [x] Examples pass:
  - confirm a clean progression across `mock_demo.py`, `first_game_walkthrough.py`, `minimal_experiment.py`, replay / spectator workflows
  - ensure `examples/README.md` reflects the intended onboarding ladder
- [x] Minimal `run_experiment.py` template for research packages, without promoting package-specific execution logic into framework core

### 4. Research Workflow Productization
- [x] Ship one supported research CLI workflow for cell export and package aggregation on matrix-based studies, reducing reliance on per-package export boilerplate
  - Scope:
    - `agentdeck research export --cell <id> --matrix matrix.yaml`
    - `agentdeck research aggregate --matrix matrix.yaml`
    - discover and retain full session history per `matrix.yaml` cell
    - export cell artifacts with canonical `source.recordings_dirs`
    - refresh package-level exports from aggregated cell history
  - Beta target:
    - one coherent, documented common-case workflow for matrix-based export/aggregation
  - Stretch goal:
    - eliminate per-package `export_cell_results.py` and `export_package_results.py` boilerplate entirely
  - Non-goal:
    - moving `run_experiment.py` execution logic into the framework baseline
- [x] Document `matrix.yaml` as a stable research contract with a minimal template
- [x] Ensure the documented workflow across `research_export.py`, `research_validate.py`, `research_index.py`, and `research_package.py` is coherent and externally legible

### 5. Viewer Showcase Curation

The viewer is beta-functional but its `matches/` directory still contains pre-research placeholder matches (Haiku vs. Sonnet, GPT-4o vs. GPT-4o-mini). It does not yet reflect the research story at all. This is the primary remaining in-repo product gap before release.

- [x] Select 4–6 canonical FixedDamage matches from the completed arc (flagship game, clearest behavioral signal)
- [x] Copy selected match recordings into `viewer/matches/`
- [x] Update `viewer/matches/manifest.json` with labeled entries
- [x] Confirm viewer renders them correctly end-to-end
- [x] Add a brief note in `viewer/README.md` on what the curated matches represent

**Constraints:**
- VariableDamage renderer is not yet registered in the viewer; FixedDamage only for now
- Depends on the 31-package rerun completing and exports settling first
- Pick matches that show behavioral contrast (e.g., plain AO vs. RC-TR-HP, a potion decision turning point, a loss from poor HP management)

## Release Gates

### Beta Gate
- [x] Main-arc final experiment committed and validated
- [x] VariableDamage Arc 1 summary written
- [x] Cross-game comparison document written
- [x] Supported research workflow shipped and documented for the common matrix-based export/aggregation path
- [x] README, examples, and release-facing docs tell a consistent product story
- [x] Viewer curated with research matches (section 5 above)

## Optional Appendix (Not A Beta Gate)
- [ ] `GPT-5-AO` vs `Flash-AO` at `N=24`
- [ ] `Opus-AO` vs `Flash-AO` at `N=24`

### `1.0` Gate
- Stronger methodological defaults for benchmark fairness
- Robust session lifecycle management (recovery, segmented execution, duplicate pruning)
- Ongoing spec-compliance discipline built into normal development, not only pre-release cleanup

## Explicitly Deferred Beyond `v0.1.0`
- Native session recovery in the research CLI
- Segmented execution as a framework-level capability
- Duplicate-session pruning and recovery orchestration in core
- Promotion of package-specific `run_experiment.py` logic into framework baseline
- Autonomous Researcher workflows
