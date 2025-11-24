#!/usr/bin/env bash
set -euo pipefail

# Run the same checks as GitHub Actions locally.

VENV_PYTEST="./venv/bin/pytest"
VENV_BLACK="./venv/bin/black"

if [ ! -x "$VENV_PYTEST" ] || [ ! -x "$VENV_BLACK" ]; then
  echo "Please ensure the virtualenv is set up (expected ./venv/bin/pytest and ./venv/bin/black)." >&2
  exit 1
fi

echo "== Black check =="
$VENV_BLACK --check src tests

echo "== Pytest =="
$VENV_PYTEST tests/ -v --tb=short --cov=src/agentdeck --cov-report=xml --cov-report=term
