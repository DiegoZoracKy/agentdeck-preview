# AgentDeck Roadmap

Last updated: 2026-03-17
Owner: Diego + Codex + Claude

## Goal
Promote the current platform baseline to `main`, then run a fresh pre-release research sprint from a clean branch.

## What Belongs In `main`
- Engine correctness and observability fixes
- Provider/runtime compatibility updates
- Replay viewer baseline
- Research export, packaging, indexing, and validation tooling
- Research templates, schema docs, and specs
- No committed benchmark packages or one-off experiment runners

## Release Status
- AgentDeck should be presented as a public beta / preview.
- `1.0` is still blocked on methodological controls, artifact integrity checks, and public-surface consistency.

## Open Blockers

### Core Execution
- [ ] Add native fairness controls in the core API.
  - Pairing policy (`none`, `paired_side_swap`)
  - First-player policy (`random`, fixed, alternating for diagnostics)
  - Persist selected policy in batch/match metadata
- [ ] Align prompt payload turn numbering semantics (`prompt.turn_number`) with the recorder/spec contract.
- [ ] Clarify `player_order` vs `first_player` semantics in specs, artifacts, and analysis docs.

### Artifact Integrity
- [ ] Add artifact-level invariant checks for:
  - monotonic gameplay timeline
  - top-level timing consistency
  - prompt payload turn-number coherence
  - winner/final-state consistency
- [ ] Ensure release docs and public spec surfaces are mutually consistent.
- [ ] Either add `src/py.typed` or stop claiming typed-package support in packaging metadata.

### Prompt And Scenario Clarity
- [ ] Keep handshake/gameplay template split explicit in research configs.
- [ ] Make controller asymmetry explicit in experiment intent and preflight checks.
- [ ] Clarify `information_level=\"partial\"` semantics for opponent `last_action`.

### Viewer Positioning
- [ ] Decide whether the viewer remains documented as experimental or is promoted to a beta surface.
- [ ] Keep viewer docs aligned with the actual supported record contract.

## Fresh Research Reset
- Start from templates plus an empty research index.
- Treat FixedDamage as a behavioral case study, not a leaderboard.
- Prefer within-model perturbation cells over cross-provider ranking claims.
- Prioritize behavioral metrics above raw win rate:
  - format strictness
  - first-player split
  - policy deviations such as potion timing
- Only package public-facing findings once the experiment design is causally clean.

## Immediate Next Steps
1. Merge the cleaned integration baseline into `main`.
2. Branch fresh from `main` for the pre-release sprint.
3. Close the remaining blocker items above.
4. Design a new FixedDamage matrix from scratch.
5. Run and package the first release-facing research report.
