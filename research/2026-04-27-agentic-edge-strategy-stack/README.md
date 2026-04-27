# The Agentic Edge: Strategy Stack Effects on LLM Agency

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-04-27-agentic-edge-strategy-stack`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: planned
- Matches: 0/108
- Game: MixedFixedVariableBenchmark
- Players: flashlite=google:gemini-2.5-flash-lite, gpt4omini=openai:gpt-4o-mini
- Seed Base: 2026042701
- Topline Winner: Potion80Bot-AO (58.3%)
- Avg Turns: 15.916666666666666
- Avg Duration (s): 0.14326727390289307
- Total Cost: $0.000000
<!-- AUTO_FACTS:END -->

## Why This Exists
This package prepares the next flagship AgentDeck study. The study asks whether
strategy stacks can change LLM agent behavior enough to overcome model-tier
differences in sequential decision environments.

The package is intentionally matrix-first. `matrix.yaml` is the source of truth
for pilot cells, prompt/config references, fairness policy, seed offsets, and
expansion gates.

## Design Snapshot
- Games: `FixedDamageGame(information_level="partial")` and `VariableDamageGame(information_level="partial")`
- Main model tiers in the pilot: Gemini Flash-Lite and GPT-4o-mini
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
- `P2`: reserved for selected main-run cells after pilot review.

Pilot expansion gates:
- runner dry-run succeeds
- provider credentials and model IDs are verified
- no unexpected max-turn truncation
- cell exports validate
- cost projection fits the budget envelope
- built-in behavioral scorer coverage is sufficient for the hypothesis tested

## Results
No live results yet. After pilot execution, cell artifacts should be exported
under `artifacts/<cell_id>/`, then aggregated into top-level `results.json`.

## Artifacts
- `manifest.yaml` - package metadata and current run envelope
- `matrix.yaml` - pilot matrix and expansion plan
- `prompts/` - frozen prompt templates used by matrix configs
- `scripts/run_experiment.py` - package-local runner
- `analysis.md` - human-owned interpretation shell
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
