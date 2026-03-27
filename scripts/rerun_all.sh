#!/usr/bin/env bash
# Full research rerun orchestration script.
# Runs all 31 experiment packages from zero, exports results, and validates.
# Usage: bash scripts/rerun_all.sh [--concurrency N] [--dry-run]
#
# Prerequisites: .env file with API keys in repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

CONCURRENCY=2
DRY_RUN=0
LOG_DIR="$REPO_ROOT/logs/rerun-$(date +%Y%m%d-%H%M%S)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --concurrency) CONCURRENCY="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

PYTHON=".venv/bin/python"
EXPORT_CLI=".venv/bin/agentdeck-research-export"
VALIDATE_CLI=".venv/bin/agentdeck-research-validate"

mkdir -p "$LOG_DIR"
echo "Log dir: $LOG_DIR"
echo "Concurrency: $CONCURRENCY"
echo "Dry run: $DRY_RUN"
echo ""

run_package() {
  local pkg="$1"
  local pkg_dir="research/$pkg"
  local run_script="$pkg_dir/scripts/run_experiment.py"
  local log="$LOG_DIR/$pkg.log"
  local pkg_concurrency="$CONCURRENCY"

  echo "========================================================================"
  echo "[$pkg]"

  if [ ! -f "$run_script" ]; then
    echo "  SKIP: no run_experiment.py found"
    return
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  DRY RUN: $PYTHON $run_script --concurrency $pkg_concurrency --dry-run"
    $PYTHON "$run_script" --concurrency "$pkg_concurrency" --dry-run 2>&1 | sed 's/^/  /'
    return
  fi

  # Step 1: Run experiment
  echo "  Running experiment (concurrency=$pkg_concurrency)..."
  if ! $PYTHON "$run_script" --concurrency "$pkg_concurrency" 2>&1 | tee "$log" | sed 's/^/  /'; then
    echo "  FAILED: run_experiment.py — see $log"
    return 1
  fi

  # Step 2: Export each cell
  local cells
  cells=$($PYTHON -c "
import yaml, sys
m = yaml.safe_load(open('$pkg_dir/matrix.yaml'))
print(' '.join(c['id'] for c in m.get('cells', [])))
")
  for cell in $cells; do
    echo "  Exporting cell: $cell"
    if ! $EXPORT_CLI --experiment-dir "$pkg_dir" --cell "$cell" 2>&1 | sed 's/^/    /'; then
      echo "  FAILED: export cell $cell"
      return 1
    fi
  done

  # Step 3: Export package-level results
  echo "  Exporting package results..."
  if ! $EXPORT_CLI --experiment-dir "$pkg_dir" --package 2>&1 | sed 's/^/  /'; then
    echo "  FAILED: export package"
    return 1
  fi

  # Step 4: Validate
  echo "  Validating..."
  if ! $VALIDATE_CLI --experiment-dir "$pkg_dir" 2>&1 | sed 's/^/  /'; then
    echo "  WARNING: validation issues — check output above"
  fi

  echo "  DONE: $pkg"
}

# Ordered by strategic priority (arc anchors and capstones first)
PACKAGES=(
  # VariableDamage capstone and key arc results
  2026-03-26-variable-damage-premium-final-1
  2026-03-25-variable-damage-threshold-1
  2026-03-25-variable-damage-parity-1
  2026-03-25-variable-damage-openai-baseline-2
  2026-03-24-variable-damage-baseline-3
  2026-03-23-variable-damage-release-1
  2026-03-24-variable-damage-reinforcement-1
  # FixedDamage capstone and key arc results
  2026-03-23-fixed-damage-exit-1
  2026-03-24-fixed-damage-baseline-completion-1
  2026-03-25-fixed-damage-baseline-completion-2
  2026-03-21-fixed-damage-openai-parity-1
  2026-03-19-fixed-damage-release-1
  2026-03-19-fixed-damage-controller-1
  # Remaining packages
  2026-03-20-fixed-damage-ablation-1
  2026-03-20-fixed-damage-mini-baseline-1
  2026-03-20-fixed-damage-mini-parity-1
  2026-03-20-fixed-damage-parity-1
  2026-03-20-fixed-damage-parity-2
  2026-03-20-fixed-damage-parity-3
  2026-03-20-fixed-damage-parity-4
  2026-03-20-fixed-damage-threshold-1
  2026-03-21-fixed-damage-ablation-2
  2026-03-21-fixed-damage-gpt5mini-parity-1
  2026-03-23-fixed-damage-cap-1
  2026-03-23-variable-damage-baseline-2
  2026-03-23-variable-damage-controller-1
  2026-03-21-fixed-damage-openai-parity-2
  2026-03-22-fixed-damage-openai-margin-1
  2026-03-25-variable-damage-openai-baseline-1
  2026-03-25-variable-damage-openai-parity-1
  2026-03-25-variable-damage-openai-parity-2
)

FAILED=()
for pkg in "${PACKAGES[@]}"; do
  if ! run_package "$pkg"; then
    FAILED+=("$pkg")
  fi
done

echo ""
echo "========================================================================"
echo "Rerun complete."
echo "Total packages: ${#PACKAGES[@]}"
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "All packages succeeded."
else
  echo "Failed packages (${#FAILED[@]}):"
  for pkg in "${FAILED[@]}"; do
    echo "  - $pkg"
  done
  exit 1
fi
