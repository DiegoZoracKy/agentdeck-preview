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
2. Refresh `viewer/matches/manifest.json`:

```bash
node scripts/update_match_manifest.js
```

3. Reload `viewer/index.html` and use **Local Match Library**.

### Curated Research Matches

The bundled local library now mixes rebuilt `FixedDamage` and `VariableDamage`
research replays:

1. plain `FlashLite-AO` collapse against `Flash-AO`
2. `ReasoningController` partially repairing that collapse
3. the final `FlashLite-RC-TR-HP-exit` stack winning as second player
4. `gpt-4o-mini RC` backfiring against `gpt-5-mini`
5. Haiku's seat-conditioned pathology against `Flash-AO`
6. a premium plain-baseline reference match: `Flash-AO` vs `GPT5Mini-AO`
7. the VariableDamage premium ceiling check: `FlashLite-RC-RISK` vs `GPT5Mini-AO`
8. the compressed VariableDamage top tier: `GPT5Mini-AO` vs `Flash-AO`

These matches are meant to show behavioral contrast, not just winners.

### Option 2: With a local server (recommended)

```bash
# Python 3
python -m http.server 8080

# Then open http://localhost:8080/viewer/
```

Serve the repository root, not the `viewer/` directory by itself. The bundled
skins load shared assets from `src/agentdeck/games/examples/...`.

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
The bundled combat skins currently support:

- **FixedDamageGame**
- **VariableDamageGame**

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
│   └── *.json                 # Local replay files for quick testing
├── js/
│   ├── app.js                 # UI shell + wiring
│   ├── record-loader.js       # Schema validation & parsing
│   ├── timeline.js            # Core playback engine
│   └── renderers/index.js     # Renderer registry (game + skin)
├── css/
│   └── base.css               # Layout + shell styles
└── README.md                  # This file

src/agentdeck/games/examples/fixed_damage/
├── game.py                    # Game logic
└── viewers/                   # Bundled combat viewers reused by both games
    ├── ffvi_scene/
    │   ├── renderer.js
    │   ├── styles.css
    │   └── assets/
    │       └── bg-placeholder.svg
    └── debug/
        ├── renderer.js
        └── styles.css
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

### Bundled Combat Viewers
- **FFVI Scene**: logo‑knights battle scene with top message box
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
