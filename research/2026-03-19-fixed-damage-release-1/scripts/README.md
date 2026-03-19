# Experiment Scripts

Primary runner:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/run_experiment.py --phase P0
```

Useful variants:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/run_experiment.py --phase P1
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/run_experiment.py --cell p1_c01_mini_ho_vs_tr
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/run_experiment.py --list-cells
```

Export completed cells into `artifacts/`:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-release-1/scripts/export_cell_results.py --phase P0
```
