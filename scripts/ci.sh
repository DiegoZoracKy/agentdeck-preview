#!/usr/bin/env bash
set -euo pipefail

# Run the same checks as GitHub Actions locally.

if [ -x "./venv/bin/pytest" ]; then
  VENV_DIR="./venv"
elif [ -x "./.venv/bin/pytest" ]; then
  VENV_DIR="./.venv"
else
  VENV_DIR="./venv"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PYTEST="$VENV_DIR/bin/pytest"
VENV_BLACK="$VENV_DIR/bin/black"

if [ ! -x "$VENV_PYTHON" ] || [ ! -x "$VENV_PYTEST" ] || [ ! -x "$VENV_BLACK" ]; then
  echo "Please ensure the virtualenv is set up (expected ./venv or ./.venv with Python, pytest, and black)." >&2
  exit 1
fi

echo "== Black check =="
$VENV_PYTHON -m black --check src tests

echo "== Pytest =="
$VENV_PYTHON -m pytest tests/ -v --tb=short --cov=src/agentdeck --cov-report=xml --cov-report=term
