# Release Checklist

This checklist tracks public package releases. It is operational release prep,
not a product roadmap.

## Workbench Source Promotion

- Freeze the approved private Workbench checkpoint and audit its public content.
- Prepare one consolidated commit on the current public `main`, with its real
  creation timestamp. Preserve existing public history and keep intermediate
  Workbench commits out of the public commit's ancestry.
- Record the private checkpoint, public base, candidate commit, public tree and
  any content exclusions in the private promotion audit. Validate the exact
  public candidate from a clean checkout before pushing it.
- After the authorized public sync and successful public CI, create an immutable
  annotated tag `public-sync/YYYY-MM-DD.N` on the source Workbench checkpoint.
  Use the sync completion date in `America/Sao_Paulo` and a daily sequence number.
  Record both full commit hashes, the public tree, previous promotion, scope and
  audit/CI references in its private annotation.
- Push that exact tag only to the private `work` remote. Use explicit refs for
  all promotion pushes; never use `--tags`, `--follow-tags` or `--mirror` to the
  public remote. A Workbench tag would expose its private commit ancestry.
- Keep public version tags separate: they point to approved public commits.
  A private sync tag does not constitute a package release.

Keep the detailed mapping and subsequent-sync audit in the private Workbench.

## Before Tagging

- Push the approved consolidated public candidate and wait for CI to pass.
- Confirm the README, package metadata, and PyPI long description contain no
  stale beta/team/contact wording.
- Confirm the package author is `Diego ZoracKy`.
- Confirm the viewer is excluded from package data and the built artifacts stay
  small.
- Build the candidate artifacts and compare the candidate `sdist` against the
  latest published `sdist` on PyPI. Choose the version number from that diff,
  not from the size of the final release commit.
- Build release artifacts from a clean clone or disposable worktree. Setuptools
  can retain removed packages from local ignored source and `build/` directories;
  artifacts built in a long-lived development worktree are not release candidates.
- Run the local checks:

```bash
./scripts/ci.sh

RELEASE_ROOT="$(mktemp -d /tmp/agentdeck-release.XXXXXX)"
git clone --local . "$RELEASE_ROOT/source"
(
  cd "$RELEASE_ROOT/source"
  python -m build --sdist --wheel --outdir "$RELEASE_ROOT/dist"
)
```

### Published Package Diff Gate

Before publishing, compare against the package that users can actually install:

```bash
PREVIOUS=0.2.0
CANDIDATE=0.4.0
WORKDIR=/tmp/agentdeck-release-diff
export PREVIOUS CANDIDATE WORKDIR

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR/previous" "$WORKDIR/candidate"

python - <<'PY'
import json
import os
import urllib.request
from pathlib import Path

version = os.environ["PREVIOUS"]
out = Path(os.environ["WORKDIR"]) / f"agentdeck_ai-{version}.tar.gz"
with urllib.request.urlopen(f"https://pypi.org/pypi/agentdeck-ai/{version}/json", timeout=30) as r:
    data = json.load(r)
sdist = next(item for item in data["urls"] if item["packagetype"] == "sdist")
with urllib.request.urlopen(sdist["url"], timeout=30) as r:
    out.write_bytes(r.read())
PY

tar -xzf "$WORKDIR/agentdeck_ai-$PREVIOUS.tar.gz" -C "$WORKDIR/previous" --strip-components=1
tar -xzf "$RELEASE_ROOT/dist/agentdeck_ai-$CANDIDATE.tar.gz" -C "$WORKDIR/candidate" --strip-components=1
diff -ru "$WORKDIR/previous/src/agentdeck" "$WORKDIR/candidate/src/agentdeck" | less
```

If code or artifact schema changed, do not publish a patch-only version. If a
record/replay field, public import path, or artifact contract changed, call that
out explicitly in the release notes and choose at least a minor version.

## Release Steps

- Build fresh `sdist` and wheel artifacts.
- Create and push the version tag before upload; every PyPI artifact must be
  reachable from a Git tag.
- Publish to PyPI.
- Create a GitHub Release for the version tag with concise release notes.
- Verify the PyPI page, GitHub README, Hugging Face dataset, and Hugging Face
  Space point to consistent public surfaces.

## Release Notes Must Mention

- AgentDeck positioning: the game console for AI agents.
- Agentic Edge flagship study package and replay viewer.
- Replacement of the legacy Research APIs by Study, RecordCorpus, Measure,
  Evidence, and Finding; the `agentic-edge-research` tag remains available for
  historical reproduction.
- Package-size cleanup: viewer assets remain in the repo, not in the PyPI
  package.
