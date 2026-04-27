# Reproduction

This package is execution-ready once credentials, budget limits, and the frozen
commit fields in `matrix.yaml` are filled.

## Environment

Run commands from the repository root.

Provider-backed cells require:

- `OPENAI_API_KEY`
- `VERTEX_PROJECT_ID` or `GOOGLE_APPLICATION_CREDENTIALS_B64`
- optional `VERTEX_LOCATION`

Before live execution, record:

- AgentDeck git commit
- AgentDeck package version
- provider model IDs
- pricing snapshot
- approved pilot/main/expansion budget limits

## Inspect the Matrix

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --list-cells
```

## Dry Runs

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1 --dry-run
```

## Local Preflight

`P0` uses local policy bots only and should not make provider calls.

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0
```

After `P0`, export and validate the preflight cells:

```bash
agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --cell p0_fd_bot_smoke \
  --no-generated-at

agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --cell p0_vd_bot_smoke \
  --no-generated-at

agentdeck-research-validate --research-dir research
```

## Provider Pilot

Run the provider-backed pilot only after the dry runs, local preflight, and
budget envelope pass.

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1
```

Export each cell, then refresh package-level artifacts:

```bash
agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --phase P1 \
  --no-generated-at

agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --package \
  --no-generated-at
```

Built-in FixedDamage and VariableDamage behavioral profiles are computed during
export when the package uses automatic behavioral scoring. Use
`agentdeck-research-score` only if a package-local custom scorer is added or a
scorer change requires rescoring.

## Main-Run Lock

Before adding `P2` cells:

- fill all `TBD` budget values in `matrix.yaml`
- record measured pilot cost multipliers
- lock the selected model roster
- lock the S2 controller choice if S2 is added
- name the exact prior FixedDamage package being replicated
- keep all paired-side-swap match counts even
- update `analysis.md` with pilot gates and expansion decisions

Raw recordings belong in external storage, not git. Store only artifact pointers
under `recordings/`.

## Development Checkout Fallbacks

If the package has not been installed and the `agentdeck-research-*` console
scripts are unavailable, use the repo-local wrappers:

```bash
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --list-cells
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --phase P1 --no-generated-at
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --package --no-generated-at
python3 scripts/research_validate.py --research-dir research
```
