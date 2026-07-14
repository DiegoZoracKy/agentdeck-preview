#!/usr/bin/env bash
set -euo pipefail

# Run the same checks as GitHub Actions locally.

if [ -x "./venv/bin/python" ]; then
  VENV_DIR="./venv"
elif [ -x "./.venv/bin/python" ]; then
  VENV_DIR="./.venv"
else
  VENV_DIR="./venv"
fi

VENV_PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Please ensure the virtualenv is set up (expected ./venv or ./.venv with Python)." >&2
  exit 1
fi

echo "== Black check =="
$VENV_PYTHON -m black --check src tests

echo "== Pytest =="
$VENV_PYTHON -m pytest tests/ -v --tb=short --cov=src/agentdeck --cov-report=xml --cov-report=term
