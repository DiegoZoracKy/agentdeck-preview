# Raw Run Recovery Plan

Last updated: 2026-03-26
Status: Active

## Situation

The tracked research packages are still intact:
- `README.md`
- `analysis.md`
- `results.json`
- `results.csv`
- `manifest.yaml`
- `matrix.yaml`
- curated `artifacts/` and `notes/`

What is missing is the local raw run layer:
- root `agentdeck_runs/`
- root `agentdeck_records/`
- package-local `research/*/agentdeck_runs/`
- discarded-session `logs/`

This happened because generated runtime directories were cleaned as if they were disposable local artifacts, but in this repo they also served as the raw-recording backing for committed research manifests.

## What Was Verified

- No trash/recycle copy is available from this workspace.
- No sibling workspace contains matching `research/*/agentdeck_runs/` directories.
- `31` experiment manifests now point to missing `storage.raw_recordings.path` directories.
- All `31` affected packages still have committed `matrix.yaml`, `scripts/run_experiment.py`, and exported results, so they are rerunnable.

## Recommendation

Do **not** rerun all `31` packages immediately.

Use a staged restore:

1. **Tier 1: public-story recovery**
   - restores the packages most likely to matter for release, demos, audits, and direct questions
2. **Tier 2: causal-support recovery**
   - restores the cheaper ladder/support packages that make the arc reasoning auditable
3. **Tier 3: expensive parity/comparison recovery**
   - restores the most expensive OpenAI and premium support packages only if full raw parity is still needed

## Cost / Time Envelope

- **Tier 1**
  - `13` packages
  - estimated rerun cost: **$9.0479**
  - estimated wall time at prior observed durations: **18.55 hours**
- **Tier 2**
  - `12` packages
  - estimated rerun cost: **$2.1127**
  - estimated wall time: **4.82 hours**
- **Tier 3**
  - `6` packages
  - estimated rerun cost: **$7.0138**
  - estimated wall time: **12.01 hours**
- **Full parity**
  - `31` packages
  - estimated rerun cost: **$18.1744**
  - estimated wall time: **35.38 hours**

These estimates use each package's already-exported `summary.total_cost` and `matches_completed * summary.avg_duration`.

## Tier 1: Public-Story Recovery

Restore these first:

| Package | Why it matters | Est. cost | Est. wall time |
|---|---|---:|---:|
| `2026-03-26-variable-damage-premium-final-1` | final VariableDamage capstone | `$0.3082` | `0.71h` |
| `2026-03-25-variable-damage-threshold-1` | risk-prompt breakthrough | `$0.2220` | `1.09h` |
| `2026-03-25-variable-damage-parity-1` | scaled confirmation of the tuned Flash-Lite condition | `$0.2613` | `1.07h` |
| `2026-03-25-variable-damage-openai-baseline-2` | top-of-graph `Flash` vs `GPT5Mini` check | `$0.5770` | `2.25h` |
| `2026-03-24-variable-damage-baseline-3` | full weak-tier VariableDamage ordering | `$1.1723` | `1.98h` |
| `2026-03-23-variable-damage-release-1` | VariableDamage baseline anchor | `$0.0534` | `0.33h` |
| `2026-03-24-variable-damage-reinforcement-1` | negative transfer result for TR | `$0.1892` | `1.25h` |
| `2026-03-23-fixed-damage-exit-1` | FixedDamage final tuned capstone | `$0.2188` | `0.85h` |
| `2026-03-24-fixed-damage-baseline-completion-1` | closes most of the plain-model FixedDamage graph | `$1.4289` | `2.06h` |
| `2026-03-25-fixed-damage-baseline-completion-2` | finishes the plain-model FixedDamage graph | `$2.1301` | `3.17h` |
| `2026-03-21-fixed-damage-openai-parity-1` | strongest early evidence that RC is not universally helpful | `$1.5763` | `2.94h` |
| `2026-03-19-fixed-damage-release-1` | FixedDamage public baseline anchor | `$0.6370` | `0.54h` |
| `2026-03-19-fixed-damage-controller-1` | first clear RC improvement package | `$0.2735` | `0.32h` |

### Suggested Tier 1 execution order

If recovery is interrupted, this order maximizes value early:

1. `2026-03-26-variable-damage-premium-final-1`
2. `2026-03-25-variable-damage-threshold-1`
3. `2026-03-25-variable-damage-parity-1`
4. `2026-03-25-variable-damage-openai-baseline-2`
5. `2026-03-24-variable-damage-baseline-3`
6. `2026-03-23-variable-damage-release-1`
7. `2026-03-24-variable-damage-reinforcement-1`
8. `2026-03-23-fixed-damage-exit-1`
9. `2026-03-24-fixed-damage-baseline-completion-1`
10. `2026-03-25-fixed-damage-baseline-completion-2`
11. `2026-03-21-fixed-damage-openai-parity-1`
12. `2026-03-19-fixed-damage-release-1`
13. `2026-03-19-fixed-damage-controller-1`

## Tier 2: Causal-Support Recovery

These are cheaper support packages that strengthen auditability of the causal ladders:

- `2026-03-20-fixed-damage-ablation-1`
- `2026-03-20-fixed-damage-mini-baseline-1`
- `2026-03-20-fixed-damage-mini-parity-1`
- `2026-03-20-fixed-damage-parity-1`
- `2026-03-20-fixed-damage-parity-2`
- `2026-03-20-fixed-damage-parity-3`
- `2026-03-20-fixed-damage-parity-4`
- `2026-03-20-fixed-damage-threshold-1`
- `2026-03-21-fixed-damage-ablation-2`
- `2026-03-23-fixed-damage-cap-1`
- `2026-03-23-variable-damage-baseline-2`
- `2026-03-23-variable-damage-controller-1`

Tier 2 subtotal:
- cost: **$2.1127**
- wall time: **4.82 hours**

## Tier 3: Expensive OpenAI / Premium Support Recovery

Restore only if full raw parity still matters after Tier 1 + Tier 2:

- `2026-03-21-fixed-damage-gpt5mini-parity-1`
- `2026-03-21-fixed-damage-openai-parity-2`
- `2026-03-22-fixed-damage-openai-margin-1`
- `2026-03-25-variable-damage-openai-baseline-1`
- `2026-03-25-variable-damage-openai-parity-1`
- `2026-03-25-variable-damage-openai-parity-2`

Tier 3 subtotal:
- cost: **$7.0138**
- wall time: **12.01 hours**

## Pre-Rerun Fix

One manifest already has a path anomaly that should be corrected before any rerun/recovery work:

- `research/2026-03-21-fixed-damage-gpt5mini-parity-1/manifest.yaml`
  - current `storage.raw_recordings.path` points to:
    - `research/2026-03-20-fixed-damage-mini-parity-1/agentdeck_runs`
  - it should point to its own package-local path

This is a preexisting manifest drift, not part of the deletion incident, but it should be fixed before recovery so the restored package points at the correct raw run directory.

## Full Affected Package Inventory

All affected packages:

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

## Practical Decision Rule

Use this stopping rule:

- If the goal is **public confidence for the release branch**, restore **Tier 1** and stop.
- If the goal is **stronger causal auditability of both arcs**, restore **Tier 1 + Tier 2**.
- If the goal is **full manifest/raw-path parity across every executable package**, restore **all three tiers**.
