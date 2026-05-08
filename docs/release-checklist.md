# Release Checklist

This checklist tracks public package releases. It is operational release prep,
not a product roadmap.

## Before Tagging

- Push the current launch commits and wait for CI to pass.
- Confirm the README, package metadata, and PyPI long description contain no
  stale beta/team/contact wording.
- Confirm the package author is `Diego ZoracKy`.
- Confirm the viewer is excluded from package data and the built artifacts stay
  small.
- Run the local checks:

```bash
./scripts/ci.sh
python -m build --sdist --wheel
```

## Release Steps

- Bump `src/agentdeck/__init__.py`.
- Build fresh `sdist` and wheel artifacts.
- Publish to PyPI.
- Create a GitHub Release for the version tag with concise release notes.
- Verify the PyPI page, GitHub README, Hugging Face dataset, and Hugging Face
  Space point to consistent public surfaces.

## Release Notes Must Mention

- AgentDeck positioning: the game console for AI agents.
- Agentic Edge flagship study package and replay viewer.
- Research export/reporting polish.
- Package-size cleanup: viewer assets remain in the repo, not in the PyPI
  package.
