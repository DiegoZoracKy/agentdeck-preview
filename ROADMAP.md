# AgentDeck Roadmap

Last updated: 2026-03-17
Owner: Diego + Codex + Claude

## Goal
Close the pre-release blocker sweep on a clean baseline, then run a fresh
release-facing research sprint from reset templates.

## What Belongs In `main`
- Engine correctness and observability fixes
- Provider/runtime compatibility updates
- Replay viewer baseline
- Research export, packaging, indexing, and validation tooling
- Research templates, schema docs, and specs
- No committed benchmark packages or one-off experiment runners

## Release Status
- AgentDeck should be presented as a public beta / preview.
- The code/spec blocker sweep is now part of the baseline branch.
- `1.0` is still blocked on stronger default methodology and a polished public research package.

## Open Blockers

### Core Execution
- [x] Add native fairness controls in the core API.
  - Pairing policy (`none`, `paired_side_swap`)
  - First-player policy (`random`, fixed, alternating for diagnostics)
  - Persist selected policy in batch/match metadata
- [x] Align prompt payload turn numbering semantics (`prompt.turn_number`) with the recorder/spec contract.
- [x] Clarify `player_order` vs `first_player` semantics in specs, artifacts, and analysis docs.

### Artifact Integrity
- [x] Add artifact-level invariant checks for:
  - monotonic gameplay timeline
  - top-level timing consistency
  - prompt payload turn-number coherence
  - winner/final-state consistency
- [x] Ensure release docs and public spec surfaces are mutually consistent.
- [x] Either add `src/py.typed` or stop claiming typed-package support in packaging metadata.

### Prompt And Scenario Clarity
- [x] Keep handshake/gameplay template split explicit in research configs.
- [x] Make controller asymmetry explicit in experiment intent and preflight checks.
- [x] Clarify `information_level=\"partial\"` semantics for opponent `last_action`.

### Viewer Positioning
- [x] Decide whether the viewer remains documented as experimental or is promoted to a beta surface.
- [x] Keep viewer docs aligned with the actual supported record contract.

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
1. Design a new FixedDamage matrix from scratch around within-model perturbations.
2. Run the first release-facing behavioral cells on the reset baseline.
3. Package a human-written report with viewer-supported replay highlights.
4. Use that package as the public beta showcase for AgentDeck.
