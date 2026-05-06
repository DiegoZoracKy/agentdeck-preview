# AgentDeck Replay Viewer

Browser-based replay viewer for AgentDeck match records. This is a beta offline
surface: useful for inspecting and sharing replays, but secondary to the record
contract itself.

## Quick Start

### Option 1: Open directly in browser

```bash
# From repo root
open viewer/index.html
# or
xdg-open viewer/index.html  # Linux
start viewer/index.html     # Windows
```

Then drag & drop a match JSON file onto the viewer.

### Local Match Library

You can preload matches and pick them from the UI:

1. Put replay files in `viewer/matches/`.
2. Optionally add sidecars next to them:
   - `my-match.json`
   - `my-match.meta.json`
3. Refresh `viewer/matches/manifest.json`:

```bash
node scripts/update_match_manifest.js
```

4. Reload `viewer/index.html` and use **Local Match Library**.

The manifest promotion step copies `subtitle`, `synopsis`, and `highlights`
from each `*.meta.json` file into the picker/runtime catalog. Long-form
`transcript` data stays in the sidecar only.

To generate a first-draft sidecar from a recorded match, use
`MatchCurator`:

```bash
python examples/replay_curate_match.py viewer/matches/fixed-damage-01-flashlite-ao-collapse-vs-flash-ao.json
```

If a canonical `*.meta.json` sidecar already exists, the example writes
`*.generated.meta.json` instead so you can inspect the draft safely.

### Curated Research Matches

The repository viewer includes general demo matches plus five curated replays
from the Agentic Edge strategy-stack study:

1. `Study 1` - S0 baseline failure: FlashLite attacks until death with all
   three potions unused.
2. `Study 2` - S1 reasoning pivot: the same HP=20 threshold moment becomes a
   heal without adding an explicit HP rule.
3. `Study 3` - S3 grounded policy: HP grounding makes the critical heal
   explicit.
4. `Study 4` - VariableDamage risk policy: risk-band grounding handles
   stochastic damage.
5. `Study 5` - VariableDamage caveat: correct-looking policy still loses from
   second seat.

These matches are meant to show behavioral contrast, not just winners. The
hosted study bundle intentionally includes only those five `Study *` examples.

### Option 2: With a local server (recommended)

```bash
# Python 3
python -m http.server 8080

# Then open http://localhost:8080/viewer/
```

The viewer is self-contained. You can serve either the repository root and open
`/viewer/`, or serve the `viewer/` directory directly and open `/`.

The study replay bundle can also be deployed as static hosting without the rest
of the repository. The first hosted study demo is the private Hugging Face Space:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

To smoke-check a stripped static bundle, point the viewer smoke test at its root:

```bash
VIEWER_ROOT=/tmp/agentic-edge-viewer-space node scripts/viewer_smoke_check.js
```

### Option 3: Load from URL

```
viewer/index.html?match=http://example.com/match.json
```

## Controls

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `←` | Previous frame |
| `→` | Next frame |
| `1` | Speed 0.5x |
| `2` | Speed 1x |
| `3` | Speed 2x |
| `4` | Speed 4x |
| `R` | Reset (load new match) |

## Supported Records

The viewer supports AgentDeck match records with schema version **1.3+**.
The bundled skins currently support:

- **ArchivistChoiceGame** (`debug`)
- **FixedDamageGame** (`debug`, `retro_jrpg_scene`)
- **VariableDamageGame** (`debug`, `retro_jrpg_scene`)

Other games require registering a custom renderer. The current viewer is
offline playback only.

Record files are generated automatically when running matches with AgentDeck:

```python
from agentdeck import AgentDeck, MockPlayer
from agentdeck.games.examples import FixedDamageGame

with AgentDeck(game=FixedDamageGame()) as deck:
    results = deck.play(
        players=[MockPlayer("Alice"), MockPlayer("Bob")],
        matches=1,
    )

# Records saved to: agentdeck_runs/{session_id}/records/match_*.json
```

## File Structure

```
viewer/
├── index.html                 # Main entry point (host)
├── matches/
│   ├── manifest.json          # UI catalog for local match picker
│   ├── *.json                 # Local replay files for quick testing
│   └── *.meta.json            # Optional subtitle/synopsis/highlights/kind sidecars
├── js/
│   ├── app.js                 # UI shell + wiring
│   ├── match-metadata.js      # Manifest + highlight normalization helpers
│   ├── record-loader.js       # Schema validation & parsing
│   ├── timeline.js            # Core playback engine
│   └── renderers/index.js     # Renderer registry (game + skin)
├── renderers/
│   └── fixed_damage/          # Portable bundled debug + retro combat renderers
├── css/
│   └── base.css               # Layout + shell styles
└── README.md                  # This file
```

## Architecture

```
Record JSON → RecordLoader → MatchData → Timeline → Renderer → DOM
                                           ↓
                                    Play/Pause/Seek
```

### RecordLoader
- Validates schema version (requires 1.3+)
- Extracts gameplay events into frames
- Normalizes state to camelCase

### Timeline
- Manages playback state (current frame, speed)
- Emits frame events to renderers
- Provides play/pause/seek/step controls

### Renderer (Interface)
- `init(container, matchData)` - Initialize display
- `renderFrame(frame)` - Update for each turn
- `renderVictory(winner)` - Show end screen
- `destroy()` - Cleanup

### RendererRegistry
- Selects the renderer based on `(matchData.game, skin)`
- Register additional renderers in your renderer file or in `viewer/js/renderers/index.js`

### Match Metadata Layer
- `MatchCurator` can generate `*.meta.json` sidecars from replayed matches
- `scripts/update_match_manifest.js` promotes sidecar metadata into the local
  viewer manifest
- The viewer surfaces:
  - picker subtitle
  - loaded-match synopsis
  - timeline highlight markers
  - in-view active highlight annotation inside the replay surface
  - optional per-highlight `kind` rendered as expressive iconography

### Bundled Combat Viewers
- **Retro JRPG Scene**: logo‑knights battle scene with top message box
- **Debug**: state‑focused developer view (before/after, reasoning, prompt/response)

## Creating Custom Renderers

```javascript
class MyRenderer {
  init(container, matchData) {
    // Setup DOM elements
  }

  renderFrame(frame) {
    // frame.player - Who acted
    // frame.action - "ATTACK" | "POTION"
    // frame.stateBefore.health - HP before
    // frame.stateAfter.health - HP after
  }

  renderVictory(winner, finalState) {
    // Show winner or draw
  }

  destroy() {
    // Cleanup
  }
}

// Register for your game + skin
RendererRegistry.register('MyGame', 'my-skin', MyRenderer);

// Create for a specific skin
RendererRegistry.create(matchData, 'my-skin');
```

## Specifications

- [SPEC-VIEWER.md](../specs/SPEC-VIEWER.md) - Viewer contract
- [SPEC-RECORDER.md](../specs/SPEC-RECORDER.md) - Record schema
- [ROADMAP.md](../ROADMAP.md) - Development roadmap

## License

Part of AgentDeck. See repository license.
