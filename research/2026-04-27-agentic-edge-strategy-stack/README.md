# The Agentic Edge: Strategy Stack Effects on LLM Agency

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-04-27-agentic-edge-strategy-stack`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 432/540
- Game: MixedFixedVariableBenchmark
- Players: flashlite=google:gemini-2.5-flash-lite, gpt4omini=openai:gpt-4o-mini
- Seed Base: 2026042701
- Topline Winner: See per-cell results (matrix aggregate)
- Avg Turns: 19.90277777777778
- Avg Duration (s): 17.787702986487634
- Total Cost: $1.128308
- Aggregation Scope: study_phases
- Phases Included: P2, P3
- Cells Included: 9
<!-- AUTO_FACTS:END -->

Note: 540 total staged matches were run across P0-P3. The official study
aggregate includes 432 matches from P2 and P3; P0 smoke tests and P1 pilot
cells are excluded from topline claims.

## Why This Exists
This package contains the completed flagship AgentDeck study. The study asks
whether strategy stacks can change LLM agent behavior enough to overcome
model-tier differences in sequential decision environments.

The package is intentionally matrix-first. `matrix.yaml` is the source of truth
for pilot cells, prompt/config references, fairness policy, seed offsets, and
expansion gates.

For the final project definition and public framing, see
[`study_overview.md`](study_overview.md).

## Design Snapshot
- Games: `FixedDamageGame(information_level="partial")` and `VariableDamageGame(information_level="partial")`
- Main live model tiers: Gemini Flash-Lite and GPT-4o-mini
- Strategy conditions:
  - `S0_AO`: Action-only baseline
  - `S1_RC`: ReasoningController without explicit grounding
  - `S3_FIXED_FULL`: Reasoning + FixedDamage HP grounding
  - `S3_VARIABLE_FULL`: Reasoning + VariableDamage risk grounding
- Fairness: `pairing_policy=paired_side_swap`, `first_player_policy=random`, even match counts
- Stopping rule: fixed-N pilot, no progressive stopping
- Conclusions: disabled for pilot/main result cells

## Execution Plan
- `P0`: no-provider preflight cells using local policy bots.
- `P1`: 8 live-provider pilot cells, 12 matches each.
- `P2`: primary fixed-N study phase, 8 cells x 48 matches each.
- `P3`: targeted FixedDamage S1 cross-tier ladder-completion cell.

Pilot expansion gates:
- runner dry-run succeeds
- provider credentials and model IDs are verified
- no unexpected max-turn truncation
- cell exports validate
- cost projection fits the budget envelope
- built-in behavioral scorer coverage is sufficient for the hypothesis tested

## Results
The official study arc is complete. P2 ran 8 cells x 48 matches, and P3 ran the
targeted FixedDamage S1 cross-tier ladder-completion cell. `results.json` is
scoped by `phase_model.study_phases: [P2, P3]`; P0 smoke and P1 pilot matches
are excluded. See `results.md` for the generated factual report, including
cell-level results and seat splits.

Headline: strategy stack effects replicate at n=48/cell. FlashLite S3-HP beats GPT4oMini 79.2% in FD; FlashLite S3-RISK beats GPT4oMini 58.3% in VD (frontier narrowed from pilot; position effects in VD are high). H1-H3 and H6 confirmed; H5 confirmed with caveats in VD; H4 inconclusive. Use `analysis/README.md` for instructions on writing independent interpretation reports.

P1 pilot: 8 cells x 12 matches each (96 matches). See `artifacts/p1_*/` for
pilot cell artifacts.

P3 ladder-completion result: `FlashLite-S1-RC` beat `GPT4oMini-S0-AO` 34/48
matches (70.8%, p=0.0055), filling the FixedDamage S0 -> S1 -> S3 progression.
See `artifacts/p3_fd_frontier_s1/results.md` and the authored follow-up analysis
under `analysis/analysis_20260428_152909_codex_official_study_analysis/support/`.

## External Artifacts

Raw recordings and the full staged artifact payload are stored in the Hugging
Face dataset:

```text
https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study
```

The curated replay viewer is deployed as a Hugging Face Space:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

Initial full artifact snapshot:

```text
13b95490cdc21dbfb1c164c683e485755f90a271
```

Latest study-arc aggregate refresh:

```text
f7ac119f69da08261269bc5cf85fb65741e8ae88
```

Latest curated replay Space snapshot:

```text
27ca787db947a393d21ed9847a8a4b44b2cbc317
```

The dataset includes metadata, prompts, authored analysis, generated reports,
per-cell artifacts, and P0/P1/P2/P3 raw recordings. See
`recordings/README.md` for the storage layout and checksum pointers. The Space
contains only the five curated viewer matches, not the full raw recording set.

## Code References

The live runs and artifact generation used the execution freeze recorded in
`matrix.yaml`. Key GitHub commits:

- Study package: [`e9dc6a77`](https://github.com/agentdeck/agentdeck/commit/e9dc6a77b3495dc80b6deed71b07a2af83c1cc64)
- Portable viewer: [`f98e05c5`](https://github.com/agentdeck/agentdeck/commit/f98e05c5efbbb558594aaccd08fd370d92360d85)
- Curated viewer examples: [`b8771c4d`](https://github.com/agentdeck/agentdeck/commit/b8771c4d21ab5591b3d37aee44eaf307acaee13f)

The Hugging Face dataset also records the implementation/code-reference commit:

[`d659bdf2`](https://github.com/agentdeck/agentdeck/commit/d659bdf244d1f0462c0d43aa2609be6c3c4a7672)

## Authored Analysis
`results.md` is the generated factual report for the official study aggregate. New
human or AI-authored interpretation belongs under `analysis/`.

To analyze this experiment, read `analysis/README.md` and create a new
timestamped `analysis_...` subdirectory under `analysis/`.

Existing authored reviews:
- `analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md`
- `analysis/analysis_20260428_152909_codex_official_study_analysis/support/s1_frontier_followup.md`
- `analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md`
- `analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md`
- `analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md`

## Artifacts
- `manifest.yaml` - package metadata and current run envelope
- `study_overview.md` - final study definition and public framing
- `matrix.yaml` - pilot matrix and expansion plan
- `prompts/` - frozen prompt templates used by matrix configs
- `scripts/run_experiment.py` - package-local runner
- `results.md` - generated factual report
- `analysis/README.md` - authored analysis instructions
- `analysis/` - authored human/AI interpretation workspace
- `reproduction.md` - execution and export commands
- `recordings/README.md` - external storage pointer policy

Raw match recordings should not be committed to git.

## Preflight
From the repo root:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --list-cells
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0 --dry-run
```

When ready to run local bot smoke tests:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0
```

## Pilot
Provider-backed pilot cells require the corresponding provider credentials:

- `OPENAI_API_KEY`
- `VERTEX_PROJECT_ID` or `GOOGLE_APPLICATION_CREDENTIALS_B64`
- optional `VERTEX_LOCATION`

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1
```

## Export

```bash
agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --phase P1 \
  --no-generated-at

agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --package \
  --no-generated-at

agentdeck-research-validate --research-dir research --write-index
```

`agentdeck-research-score` is not required for the built-in FixedDamage and
VariableDamage profiles during normal export. Add a package-local
`scripts/behavioral_scorer.py` only if the pilot justifies custom composite
metrics.

In an uninstalled development checkout, use the repo-local wrappers instead:

```bash
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --list-cells
python3 scripts/research_validate.py --research-dir research
```
