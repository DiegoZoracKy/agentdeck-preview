# Development Setup Guide

This guide helps contributors set up their local development environment for AgentDeck.

## Prerequisites

- Python 3.10+ (3.11 recommended)
- Git
- Virtual environment tool (venv, conda, etc.)

## Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/agentdeck/agentdeck.git
cd agentdeck

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -e ".[dev]"

# 4. Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# 5. Run tests to verify setup
pytest
```

## Pre-Commit Hooks

Pre-commit hooks automatically check code quality before each commit. This catches issues early and keeps the codebase consistent.

### What Gets Checked

- **Black**: Code formatting (100 char line length)
- **isort**: Import sorting
- **flake8**: Linting (style and errors)
- **mypy**: Type checking (optional, can be slow)
- **Standard checks**: Trailing whitespace, YAML/JSON syntax, file sizes

### Installation

```bash
pip install pre-commit
pre-commit install
```

### Usage

Pre-commit runs automatically on `git commit`. To run manually:

```bash
# Check all files
pre-commit run --all-files

# Check specific files
pre-commit run --files src/agentdeck/core/player.py

# Skip hooks for emergency commits (not recommended)
git commit --no-verify
```

### First-Time Setup

After installing pre-commit, the first run will download hook dependencies (~1-2 minutes). Subsequent runs are fast.

```bash
# Trigger initial setup
pre-commit run --all-files
```

## Code Quality Tools

### Black (Code Formatter)

```bash
# Format all code
black src/ tests/

# Check formatting without changes
black --check src/ tests/
```

### Pylint (Linter)

```bash
# Lint source code
pylint src/agentdeck
```

### Mypy (Type Checker)

```bash
# Type check source code
mypy src/agentdeck

# Type check with less noise
mypy src/agentdeck --no-error-summary
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/agentdeck --cov-report=html

# Run specific test file
pytest tests/unit/test_controller.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_handshake"
```

## CI/CD Pipeline

Our GitHub Actions CI runs:

1. **Tests** (Python 3.10, 3.11)
   - Full test suite with coverage
   - Coverage uploaded to Codecov

2. **Code Quality**
   - Black format check
   - Pylint linting
   - Mypy type checking

3. **Dependency Audit**
   - Verify core install works
   - Verify dev install works
   - Smoke test imports

### Viewing CI Results

- Check the "Actions" tab on GitHub
- CI runs on all pushes and pull requests
- PRs won't merge if CI fails

## Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes** (pre-commit hooks run on commit)
   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```

3. **Run tests locally**
   ```bash
   pytest
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

## Troubleshooting

### Pre-commit hooks failing

If hooks fail, fix the issues and commit again:

```bash
# Hooks will auto-fix some issues (Black, isort)
git add .
git commit -m "your message"

# For persistent issues, check what failed:
pre-commit run --all-files
```

### Mypy taking too long

Mypy can be slow on large codebases. You can skip it:

```bash
# Skip mypy in pre-commit
SKIP=mypy git commit -m "your message"
```

Or disable it in `.pre-commit-config.yaml` by commenting out the mypy hook.

### Import errors in tests

Make sure you installed the package in editable mode:

```bash
pip install -e ".[dev]"
```

## Additional Resources

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [ROADMAP.md](../ROADMAP.md) - Project roadmap
- [specs/SPEC.md](../specs/SPEC.md) - Specification hub

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions or share ideas
- **Specs**: Refer to specification documents for design decisions
