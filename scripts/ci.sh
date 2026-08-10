#!/usr/bin/env bash
set -euo pipefail

# Run the same checks as GitHub Actions locally.

CI_TMP_ROOT="${AGENTDECK_CI_TMP_ROOT:-$PWD/.tmp/ci}"
mkdir -p "$CI_TMP_ROOT"
CI_TMP_DIR="$(mktemp -d "$CI_TMP_ROOT/agentdeck-core-ci.XXXXXX")"
trap 'rm -rf "$CI_TMP_DIR"' EXIT
export TMPDIR="$CI_TMP_DIR"
export TMP="$CI_TMP_DIR"
export TEMP="$CI_TMP_DIR"

if ! command -v node >/dev/null 2>&1; then
  NVM_NODE_ROOT="${NVM_DIR:-$HOME/.nvm}/versions/node"
  if [ -d "$NVM_NODE_ROOT" ]; then
    NODE_BIN_DIR="$(find "$NVM_NODE_ROOT" -mindepth 3 -maxdepth 3 -type f -name node -printf '%h\n' 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "$NODE_BIN_DIR" ]; then
      export PATH="$NODE_BIN_DIR:$PATH"
    fi
  fi
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Please install Node.js or expose it on PATH for the viewer contract checks." >&2
  exit 1
fi

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

echo "== Spec registry =="
$VENV_PYTHON scripts/spec_registry.py check

echo "== External authoring types (strict consumer boundary) =="
find tests/fixtures/instruments -type d -name __pycache__ -prune -exec rm -rf {} +
find tests/fixtures/instruments -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
$VENV_PYTHON -m mypy --strict --follow-imports=silent \
  tests/fixtures/instruments/number_duel/number_duel

echo "== Static security audit (medium/high severity, medium/high confidence) =="
$VENV_PYTHON -m bandit -r src/agentdeck -ll -ii -q

echo "== Runtime dependency audit =="
$VENV_PYTHON -m pip_audit --strict --progress-spinner off \
  --disable-pip --no-deps --requirement requirements/runtime.txt

echo "== Pytest =="
$VENV_PYTHON -m pytest tests/ -v --tb=short --cov=src/agentdeck --cov-report=xml --cov-report=term
