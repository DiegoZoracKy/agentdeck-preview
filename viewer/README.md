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
├── index.html           # Main entry point
├── js/
│   ├── record-loader.js # Schema validation & parsing
│   ├── timeline.js      # Core playback engine
│   └── renderers/
│       └── ffvi.js      # FFVI battle renderer
├── css/
│   └── ffvi.css         # FFVI styling
├── sample-match.json    # Example match for testing
└── README.md            # This file
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

### FFVIRenderer
- FFVI-inspired battle visualization
- Animated HP bars, damage numbers
- Attack/heal animations
- Victory screen

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
```

## Specifications

- [SPEC-VIEWER.md](../specs/SPEC-VIEWER.md) - Viewer contract
- [SPEC-RECORDER.md](../specs/SPEC-RECORDER.md) - Record schema
- [ROADMAP-VIEWER.md](../ROADMAP-VIEWER.md) - Development roadmap

## License

Part of AgentDeck. See repository license.
