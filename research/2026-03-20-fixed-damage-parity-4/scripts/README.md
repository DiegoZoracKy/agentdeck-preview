# Experiment Scripts

Primary runner:

```bash
.venv/bin/python research/2026-03-20-fixed-damage-parity-4/scripts/run_experiment.py --phase P1
```

Useful variants:

```bash
.venv/bin/python research/2026-03-20-fixed-damage-parity-4/scripts/run_experiment.py --cell p1_c01_flash_lite_rc_tr_hp_vs_flash_ao
.venv/bin/python research/2026-03-20-fixed-damage-parity-4/scripts/run_experiment.py --list-cells
```

Export completed cells into `artifacts/`:

```bash
.venv/bin/python research/2026-03-20-fixed-damage-parity-4/scripts/export_cell_results.py --phase P1
.venv/bin/python research/2026-03-20-fixed-damage-parity-4/scripts/export_package_results.py
```
