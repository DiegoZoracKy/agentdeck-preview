# Changelog

All notable changes to AgentDeck will be documented in this file.

## Unreleased
- No changes yet.

## [v0.1.0] - 2026-01-19

### Highlights
- Onboarding walkthrough and docs synced to the current Game contract.
- Research standardization: manifests, results schema, export/index scripts, and `research/INDEX.md`.
- Documentation links cleaned up and metadata aligned to v0.1.0.

### Added
- Research-grade AgentDeck console with seeded experiment orchestration, replayable recordings, and pluggable games/players/controllers/renderers/spectators.
- Parallel execution with progress, stats, and cost-tracking spectators for reproducible batch experiments.
- Example games (`FixedDamageGame`, `HangmanGame`) and prompt composition helpers to get started quickly.
- **Player Ordering System**: Console now applies Fisher-Yates shuffle for fair first-player selection per match (eliminates first-player advantage bias).
  - Added `Game.get_player_order()` hook for custom ordering logic (auction games, state-dependent, asymmetric roles).
  - Added `MatchContext.previous_match_result` field for batch-local state-dependent ordering.
  - Match metadata now includes `player_order` (original indices), `player_order_source` ("console" or "game"), and `first_player` (name + index).
  - Seed-based reproducibility: same seed produces identical player ordering across runs.
  - Comprehensive test suite (20 tests) covering validation, reproducibility, metadata tracking, and batch-local semantics.
- Replay engine emits fully-populated `Event` objects, matching live observability data.
- Added `examples/run_auction_replay.py` for end-to-end record/replay validation.
- Published migration guide at `docs/migration/observability-v17.md`.
- Research standardization artifacts: `research/SCHEMA.md`, `research/INDEX.md`, and templates under `research/_templates/`.
- Export tooling for research outputs (`scripts/research_export.py`, `scripts/research_index.py`).

### Changed
- Research utilities (`comparison.py`) now delegate player ordering to Console instead of manual alternation.
- Updated documentation and examples to reference `on_gameplay` and the unified event object flow.
- Reorganized research folders into experiment packages with manifests, results, and logs.
- Development status raised to Beta with v0.1.0 stable release metadata.

### Fixed
- Research demos now produce single batches instead of multiple batches (e.g., 1 batch with 100 matches instead of 100 batches with 1 match each).
- Dropped the transitional `on_turn` handler alias; spectators and recorder collectors should now implement `on_gameplay`.
- "First game" walkthrough now matches the current Game contract and is kept in sync with docs.
