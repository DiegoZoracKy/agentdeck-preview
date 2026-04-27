# Scripts

This package intentionally keeps execution package-local.

- `run_experiment.py` reads `matrix.yaml`, resolves phase/cell selections, and
  runs AgentDeck with the configured game, players, prompts, and fairness policy.
- A package-local `behavioral_scorer.py` is intentionally absent for v0.1.
  Built-in FixedDamage and VariableDamage behavioral profiles should be used
  first. Add a scorer only after the pilot proves a paper-specific composite
  metric is needed.

Common commands:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --list-cells
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1 --dry-run
```

Use `agentdeck-research-export` for cell/package artifacts. Use
`agentdeck-research-score` only after adding a package-local scorer with a
`SCORER` object.
