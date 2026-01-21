# Viewer Status (2026-01-20)

## Where we are
- A working replay viewer exists under `viewer/` with a clean split:
  - `viewer/js/record-loader.js` for schema validation + frame extraction.
  - `viewer/js/timeline.js` for playback control.
  - `viewer/js/app.js` for UI wiring.
  - `viewer/js/renderers/index.js` registry and `viewer/js/renderers/fixed_damage_ffvi.js` renderer.
  - `viewer/css/base.css` for shell layout and `viewer/css/ffvi.css` for FFVI skin.
- Renderer now derives max HP from recorded config params when present, falling back to first frame state then default 100.
- Frame ordering uses `context.turn_index` (alias of `phase_index`) when present, with safe fallbacks.
- Docs/specs aligned to this structure: `specs/SPEC-VIEWER.md` and `ROADMAP.md`.

## What’s intentionally left untouched
- `turn_index` vs `phase_index` aliasing remains in core (spec + code) for now.
- No live/broadcast replay work yet — viewer is offline playback only.

## Draft specs in progress (not implemented yet)
- `specs/drafts/SPEC-GAME-v0.8.0.md`: adds `Game.describe()` + `get_config_params()` for generic game config export.
- `specs/drafts/SPEC-RECORDER-v1.4.0.md`: recorder captures `game_config.params` via `Game.describe()`.

## Where we’re heading next
1. Review/approve the draft specs above.
2. Implement `Game.describe()` and `get_config_params()` in `src/agentdeck/core/base/game.py`.
3. Update recorder to store `game_config` from `Game.describe()`.
4. Update example games (`FixedDamageGame`, `HangmanGame`) to return params.
5. Add tests to assert `game_config.params` are recorded and schema version expectations updated.

## Branch status
- Current branch: `viewer/replay-viewer`
- Latest commit: `c6293d2` (viewer refactor + registry + app split)
