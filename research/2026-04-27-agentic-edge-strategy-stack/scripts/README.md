# Scripts

This package intentionally keeps execution package-local.

- `run_experiment.py` reads `matrix.yaml`, resolves phase/cell selections, and
  runs AgentDeck with the configured game, players, prompts, and fairness policy.
- `reproduce_current.py` reads the pinned public Hugging Face revision without
  mutation, verifies all source Record bytes against the pinned checksum
  manifest, adapts local copies, records source-to-adapted hashes, derives
  current Evidence, checks frozen results, and writes authored Finding reports.
- A package-local `behavioral_scorer.py` is intentionally absent for v0.1.
  Built-in FixedDamage and VariableDamage behavioral profiles should be used
  first. Add a scorer only after the pilot proves a paper-specific composite
  metric is needed.

Common commands:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --list-cells
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/reproduce_current.py \
  --cache-dir /tmp/agentdeck-agentic-edge-cache \
  --output-root /tmp/agentdeck-agentic-edge-reproduction
```

The generated package artifacts used the historical `agentdeck-research-export`
workflow, and optional custom scoring used `agentdeck-research-score`. Those
commands are available from the `agentic-edge-research` tag, not current `main`.
The current reproducer closes the historical Study → Evidence → Finding chain.
The older commands remain useful only for reproducing the exact `0.2` package
generation transcript.
