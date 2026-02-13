# AgentDeck Replay Viewer

Browser-based FFVI-style replay viewer for AgentDeck match records.

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

### Option 2: With a local server (recommended)

```bash
# Python 3
cd viewer
python -m http.server 8080

# Then open http://localhost:8080
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
The default renderer targets **FixedDamageGame** records; other games require
registering a custom renderer.

Record files are generated automatically when running matches with AgentDeck:

```python
from agentdeck import AgentDeck, MockPlayer
from agentdeck.games.examples import FixedDamageGame

with AgentDeck() as deck:
    result = deck.play(
        game=FixedDamageGame(),
        players=[MockPlayer("Alice"), MockPlayer("Bob")]
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
└── viewers/                   # Bundled viewers for the game
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

### FixedDamageGame Viewers
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
