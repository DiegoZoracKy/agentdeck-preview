# Research Rerun Program

Last updated: 2026-03-26
Status: Active

## Direction

The raw run data (all `agentdeck_runs/` directories) was lost. After review, the decision is **not** to restore the old raw runs — instead, run the full research program from zero using the now-productized toolchain.

The 31 committed research packages remain intact (`manifest.yaml`, `matrix.yaml`, `results.json`, `results.csv`, `analysis.md`, `README.md`). These serve as the **validation benchmark**: regenerated results will be compared against them to confirm the rerun reproduces the same story. They are not the target output.

## Toolchain

All reruns use the productized toolchain, not ad-hoc scripts:

- **Execution**: package-local `research/<package>/scripts/run_experiment.py`
- **Export + behavioral scoring**: `agentdeck-research-export` (or `scripts/research_export.py`)
- **Packaging**: `agentdeck-research-package` (or `scripts/research_package.py`)
- **Validation**: `agentdeck-research-validate` (or `scripts/research_validate.py`)

## What Gets Rerun

All 31 affected packages:

1. `2026-03-19-fixed-damage-controller-1`
2. `2026-03-19-fixed-damage-release-1`
3. `2026-03-20-fixed-damage-ablation-1`
4. `2026-03-20-fixed-damage-mini-baseline-1`
5. `2026-03-20-fixed-damage-mini-parity-1`
6. `2026-03-20-fixed-damage-parity-1`
7. `2026-03-20-fixed-damage-parity-2`
8. `2026-03-20-fixed-damage-parity-3`
9. `2026-03-20-fixed-damage-parity-4`
10. `2026-03-20-fixed-damage-threshold-1`
11. `2026-03-21-fixed-damage-ablation-2`
12. `2026-03-21-fixed-damage-gpt5mini-parity-1`
13. `2026-03-21-fixed-damage-openai-parity-1`
14. `2026-03-21-fixed-damage-openai-parity-2`
15. `2026-03-22-fixed-damage-openai-margin-1`
16. `2026-03-23-fixed-damage-cap-1`
17. `2026-03-23-fixed-damage-exit-1`
18. `2026-03-23-variable-damage-baseline-2`
19. `2026-03-23-variable-damage-controller-1`
20. `2026-03-23-variable-damage-release-1`
21. `2026-03-24-fixed-damage-baseline-completion-1`
22. `2026-03-24-variable-damage-baseline-3`
23. `2026-03-24-variable-damage-reinforcement-1`
24. `2026-03-25-fixed-damage-baseline-completion-2`
25. `2026-03-25-variable-damage-openai-baseline-1`
26. `2026-03-25-variable-damage-openai-baseline-2`
27. `2026-03-25-variable-damage-openai-parity-1`
28. `2026-03-25-variable-damage-openai-parity-2`
29. `2026-03-25-variable-damage-parity-1`
30. `2026-03-25-variable-damage-threshold-1`
31. `2026-03-26-variable-damage-premium-final-1`

## Cost / Time Envelope

These estimates carry over from the original analysis and use each package's committed `summary.total_cost` and `matches_completed * summary.avg_duration`:

- **Full rerun**: 31 packages — estimated cost **$18.1744**, estimated wall time **~35.38 hours**

Sequencing is flexible. If interrupted, prioritize the arc-anchor and capstone packages first (see suggested order below).

## Suggested Execution Order

If recovery is interrupted, this order maximizes story coverage early:

1. `2026-03-26-variable-damage-premium-final-1` — VariableDamage capstone
2. `2026-03-25-variable-damage-threshold-1` — risk-prompt breakthrough
3. `2026-03-25-variable-damage-parity-1` — scaled confirmation of tuned FlashLite condition
4. `2026-03-25-variable-damage-openai-baseline-2` — Flash vs GPT5Mini check
5. `2026-03-24-variable-damage-baseline-3` — full weak-tier VariableDamage ordering
6. `2026-03-23-variable-damage-release-1` — VariableDamage baseline anchor
7. `2026-03-24-variable-damage-reinforcement-1` — negative transfer result for TR
8. `2026-03-23-fixed-damage-exit-1` — FixedDamage final tuned capstone
9. `2026-03-24-fixed-damage-baseline-completion-1` — plain-model FixedDamage graph
10. `2026-03-25-fixed-damage-baseline-completion-2` — completes plain-model FixedDamage graph
11. `2026-03-21-fixed-damage-openai-parity-1` — strongest early evidence RC is not universally helpful
12. `2026-03-19-fixed-damage-release-1` — FixedDamage public baseline anchor
13. `2026-03-19-fixed-damage-controller-1` — first clear RC improvement package
14. `2026-03-20-fixed-damage-ablation-1`
15. `2026-03-20-fixed-damage-mini-baseline-1`
16. `2026-03-20-fixed-damage-mini-parity-1`
17. `2026-03-20-fixed-damage-parity-1`
18. `2026-03-20-fixed-damage-parity-2`
19. `2026-03-20-fixed-damage-parity-3`
20. `2026-03-20-fixed-damage-parity-4`
21. `2026-03-20-fixed-damage-threshold-1`
22. `2026-03-21-fixed-damage-ablation-2`
23. `2026-03-23-fixed-damage-cap-1`
24. `2026-03-23-variable-damage-baseline-2`
25. `2026-03-23-variable-damage-controller-1`
26. `2026-03-21-fixed-damage-gpt5mini-parity-1`
27. `2026-03-21-fixed-damage-openai-parity-2`
28. `2026-03-22-fixed-damage-openai-margin-1`
29. `2026-03-25-variable-damage-openai-baseline-1`
30. `2026-03-25-variable-damage-openai-parity-1`
31. `2026-03-25-variable-damage-openai-parity-2`

## Pre-Rerun Fix

Before running `2026-03-21-fixed-damage-gpt5mini-parity-1`, fix its manifest path anomaly:

- **File**: `research/2026-03-21-fixed-damage-gpt5mini-parity-1/manifest.yaml`
- **Problem**: `storage.raw_recordings.path` points to `research/2026-03-20-fixed-damage-mini-parity-1/agentdeck_runs` (another package's path)
- **Fix**: update to point to its own package-local path

## Validation

After each rerun, compare regenerated `results.json` against the committed version:

- win rates and decisive match counts should be within expected stochastic variance
- behavioral profiles should be consistent with the committed analysis
- any meaningful divergence should be investigated before treating the rerun as canonical

The committed research packages are the benchmark. The rerun output replaces them only after validation passes.
