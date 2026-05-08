# Release Checklist

This checklist tracks the next public package release. It is operational release
prep, not a product roadmap.

## Next Release Target

- Version: `0.1.2`
- Purpose: publish the public-launch cleanup after `0.1.1`

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

- Bump `src/agentdeck/__init__.py` to `0.1.2`.
- Build fresh `sdist` and wheel artifacts.
- Publish to PyPI.
- Create a GitHub Release for `v0.1.2` with concise release notes.
- Verify the PyPI page, GitHub README, Hugging Face dataset, and Hugging Face
  Space point to consistent public surfaces.

## Release Notes Must Mention

- AgentDeck positioning: the game console for AI agents.
- Agentic Edge flagship study package and replay viewer.
- Research export/reporting polish.
- Package-size cleanup: viewer assets remain in the repo, not in the PyPI
  package.
