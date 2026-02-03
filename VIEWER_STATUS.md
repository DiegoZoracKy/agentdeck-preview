# Viewer Status (2026-02-03)

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

## Pre-merge checklist (we're intentionally not merging yet)
- ✅ `viewer/sample-match.json` is a real `FixedDamageGame` recording (renders out-of-the-box).
- ✅ Added a lightweight smoke-check: `node scripts/viewer_smoke_check.js`.
- ⏳ Decide whether Phase E belongs on this branch or a follow-up branch.

## What’s intentionally left untouched
- `turn_index` vs `phase_index` aliasing remains in core (spec + code) for now.
- No live/broadcast replay work yet — viewer is offline playback only.

## Draft specs in progress (not implemented yet)
- `specs/drafts/SPEC-GAME-v0.8.0.md`: adds `Game.describe()` + `get_config_params()` for generic game config export.
- `specs/drafts/SPEC-RECORDER-v1.4.0.md`: recorder captures `game_config.params` via `Game.describe()`.

## Where we’re heading next
1. **Phase D (Viewer MVP)**: Fix the sample record mismatch and add a lightweight smoke-check for `viewer/`.
2. **Phase E (Spec-first)**: Review/approve the draft specs above and promote them to `specs/`.
3. Implement `Game.describe()` and `get_config_params()` in `src/agentdeck/core/base/game.py`.
4. Update recorder to store `game_config.params` from `Game.describe()`.
5. Update example games (`FixedDamageGame`, `HangmanGame`) to return params.
6. Add tests to assert `game_config.params` are recorded and schema version expectations updated.

## Branch status
- Current branch: `viewer/replay-viewer`
- Ahead of `main`: 6 commits (+ local changes)
