# Experiment Scripts

Primary runner:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/run_experiment.py --phase P1
```

Useful variants:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/run_experiment.py --cell p1_c01_flash_lite_ao_vs_rc
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/run_experiment.py --cell p1_c02_flash_ao_vs_rc
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/run_experiment.py --list-cells
```

Export completed cells into `artifacts/`:

```bash
.venv/bin/python research/2026-03-19-fixed-damage-controller-1/scripts/export_cell_results.py --phase P1
```
