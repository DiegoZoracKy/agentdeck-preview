# AgentDeck Roadmap

Last updated: 2026-03-26
Owner: Diego + Codex + Claude

## Release Position
- AgentDeck targets a public beta / preview release, not `1.0`.
- All spec-compliance audit waves (0–6) are complete.
- All pre-release blocker-level spec drifts are resolved.
- The research showcase has expanded beyond the original FixedDamage plan to a two-arc study covering both deterministic and stochastic game settings.

## What Is Already Done

- Core fairness, recorder, artifact-validation, and metadata fixes
- Viewer beta baseline
- Research export, packaging, validation, and index tooling
- Spec-compliance audit ledger (`docs/spec-compliance/`)
- **FixedDamage Arc 1**: 19 packages, 1,000+ matches, full intervention ladder (RC → TR → HP → exit), cross-provider comparisons, behavioral scorer
- **VariableDamage Arc**: 20+ packages covering plain-model baselines, intervention ladder (RC → RISK), cross-provider comparisons, new behavioral metrics (safe_zone_potion_rate, danger subbands, first_lethal_entry_inventory), and the final main-arc premium pilot

## Remaining Pre-Release Work

### 1. Final Experiments (Codex executing)
- [x] `FlashLite-RC-RISK` vs `GPT5Mini-AO` at `N=24` — main VariableDamage arc final
- [ ] `GPT-5-AO` vs `Flash-AO` at `N=24` — premium behavioral appendix (budget-gated)
- [ ] `Opus-AO` vs `Flash-AO` at `N=24` — premium behavioral appendix (budget-gated)

### 2. Research Synthesis
- [ ] VariableDamage Arc 1 summary (parallel to FixedDamage Arc 1)
- [ ] Cross-game comparison document — what transfers across games, what doesn't, what the behavioral layer revealed that win rates alone couldn't
- [ ] Update `research/INDEX.md` and arc-level READMEs to reflect the completed two-arc picture

### 3. Release Docs
- [ ] "How to run a study" — reproducible workflow guide for external users
- [ ] Release-facing product narrative — what AgentDeck is useful for, grounded in the two-arc results
- [ ] README / top-level docs pass for consistency with current research state

### 4. Research CLI Promotion
- [ ] Promote cell export and package aggregation into the core research CLI, eliminating per-package `export_cell_results.py` and `export_package_results.py` boilerplate
  - Scope:
    - `agentdeck research export --cell <id> --matrix matrix.yaml`
    - `agentdeck research aggregate --matrix matrix.yaml`
    - discover and retain full session history per `matrix.yaml` cell
    - export cell artifacts with canonical `source.recordings_dirs`
    - refresh package-level exports from aggregated cell history
  - Non-goal:
    - moving `run_experiment.py` execution logic into the framework baseline

## Release Gates

### Beta Gate
- [ ] Final experiments committed and validated
- [ ] VariableDamage Arc 1 summary written
- [ ] Cross-game comparison document written
- [ ] Research CLI promotion complete (no per-package export script boilerplate)
- [ ] README and release docs tell a consistent product story

### `1.0` Gate
- Stronger methodological defaults for benchmark fairness
- Session recovery and segmented execution supported natively in the research CLI
- Ongoing spec-compliance discipline built into normal development, not only pre-release cleanup
