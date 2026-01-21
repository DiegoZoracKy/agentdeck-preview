# ROADMAP: AgentDeck Replay Viewer

**Status**: Active Development
**Owner**: AgentDeck Team
**Created**: 2026-01-20
**Goal**: Browser-based FFVI-style replay viewer for match records

---

## Vision

Transform AgentDeck match records into **shareable, watchable experiences**. A researcher runs a match, gets a JSON record, opens it in a browser, and watches AI agents battle in FFVI-style combat.

**Core Insight**: The product is the **record contract**, not the UI. If records are rigorous and stable, anyone can build any visualization (React, Vue, Unity, etc.).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     viewer/index.html                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │  Record Loader  │───▶│     Timeline Engine             │ │
│  │  (validates     │    │  - parseRecord(json)            │ │
│  │   schema v1.3)  │    │  - play/pause/seek/step         │ │
│  └─────────────────┘    │  - speed control                │ │
│                         │  - onFrame(callback)            │ │
│                         └──────────────┬──────────────────┘ │
│                                        │                    │
│                         ┌──────────────▼──────────────────┐ │
│                         │     Renderer Interface          │ │
│                         │  - init(container, match)       │ │
│                         │  - renderFrame(frame)           │ │
│                         │  - renderVictory(winner)        │ │
│                         └──────────────┬──────────────────┘ │
│                                        │                    │
│                    ┌───────────────────┼────────────────┐   │
│                    ▼                   ▼                ▼   │
│           ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│           │FFVIRenderer  │  │DebugRenderer │  │ Future   │ │
│           │(battle skin) │  │(data view)   │  │ skins... │ │
│           └──────────────┘  └──────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
viewer/
├── index.html              # Entry point (loads everything)
├── js/
│   ├── timeline.js         # Core playback engine
│   ├── record-loader.js    # Schema validation + parsing
│   ├── renderers/
│   │   ├── base.js         # Renderer interface
│   │   ├── ffvi.js         # FFVI battle renderer
│   │   └── debug.js        # Debug/data renderer (future)
│   └── narration.js        # Auto-generate battle text
├── css/
│   ├── viewer.css          # Base viewer styles
│   └── ffvi.css            # FFVI skin styles
├── assets/
│   └── (sprites, sounds - future)
└── README.md               # Usage documentation
```

---

## Phases

### Phase 0: Foundation (Today) ✅
- [x] Analyze existing record schema (v1.3)
- [x] Document viewer requirements
- [x] Create this roadmap

### Phase 1: Core Implementation (Today)
- [ ] Write `specs/SPEC-VIEWER.md` (lightweight)
- [ ] Implement `viewer/js/timeline.js`
- [ ] Implement `viewer/js/renderers/ffvi.js`
- [ ] Create `viewer/index.html` with controls
- [ ] Add `viewer/css/ffvi.css`
- [ ] Test with real FixedDamageGame record

### Phase 2: Polish (Today/Tomorrow)
- [ ] Add file picker / drag-drop loading
- [ ] Keyboard shortcuts (space=play/pause, arrows=step)
- [ ] Speed control (0.5x, 1x, 2x, 4x)
- [ ] Turn indicator / progress bar
- [ ] Victory screen with stats

### Phase 3: Integration (Future)
- [ ] Python CLI: `agentdeck watch <match.json>`
- [ ] Auto-open browser from Python
- [ ] Single-file HTML export (bundled)
- [ ] Embed in Jupyter notebooks

### Phase 4: Ecosystem (Future)
- [ ] Debug renderer (show prompts/responses)
- [ ] Additional game skins
- [ ] Narration spectator integration
- [ ] Share links (hosted viewer + record URL)

---

## Record Contract (Input)

The viewer consumes AgentDeck match records (schema v1.3). Key fields:

```javascript
{
  "schema_version": "1.3",
  "match_id": "match_xxx",
  "game": "FixedDamageGame",
  "players": ["Alice", "Bob"],
  "winner": "Bob",
  "seed": 42,
  "events": [
    // player_handshake_complete (per player)
    // gameplay (per turn) - has state_before/state_after
    // player_conclusion (per player)
  ],
  "final_state": { "health": {...}, "potions": {...} },
  "metadata": { "player_summaries": [...], "game_config": {...} }
}
```

**Critical for visualization:**
- `events[type=gameplay].data.state_before.health` - HP before action
- `events[type=gameplay].data.state_after.health` - HP after action
- `events[type=gameplay].data.action` - "ATTACK" or "POTION"
- `events[type=gameplay].data.player` - Who acted

---

## Timeline Engine API

```javascript
class Timeline {
  constructor(record) { }

  // Playback control
  play()              // Start/resume playback
  pause()             // Pause playback
  step(direction=1)   // Step forward/backward one frame
  seek(frameIndex)    // Jump to specific frame
  setSpeed(multiplier)// 0.5, 1, 2, 4

  // State
  get currentFrame()  // Current frame index
  get totalFrames()   // Total gameplay frames
  get isPlaying()     // Playback state
  get speed()         // Current speed multiplier

  // Events
  onFrame(callback)   // Called with frame data on each frame
  onEnd(callback)     // Called when match ends
}
```

---

## Renderer Interface

```javascript
class Renderer {
  // Initialize renderer in container
  init(container, matchData) { }

  // Render a gameplay frame
  renderFrame(frame) { }
  // frame = {
  //   player: "Bob",
  //   action: "ATTACK",
  //   stateBefore: { health: {Bob: 100, Alice: 80}, ... },
  //   stateAfter: { health: {Bob: 100, Alice: 60}, ... },
  //   turnNumber: 3
  // }

  // Render victory screen
  renderVictory(winner, finalState) { }

  // Cleanup
  destroy() { }
}
```

---

## FFVI Renderer Design

```
┌────────────────────────────────────────────────────────────┐
│                    FIXED DAMAGE BATTLE                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│    ┌─────────┐                        ┌─────────┐         │
│    │  BOB    │                        │  ALICE  │         │
│    │  ┌───┐  │                        │  ┌───┐  │         │
│    │  │ @ │  │        ATTACK!         │  │ @ │  │         │
│    │  └───┘  │       ─────────►       │  └───┘  │         │
│    │         │                        │         │         │
│    │ HP ████████░░ 80/100             │ HP ██████░░░░ 60  │
│    │ 🧪 3                             │ 🧪 3              │
│    └─────────┘                        └─────────┘         │
│                                                            │
├────────────────────────────────────────────────────────────┤
│  Turn 3: Bob uses ATTACK! Alice takes 20 damage!           │
├────────────────────────────────────────────────────────────┤
│  [▶ Play] [⏸] [⏮ Prev] [⏭ Next]  Speed: [1x ▼]  Turn 3/9  │
└────────────────────────────────────────────────────────────┘
```

**Visual Elements:**
- Two character panels (left = player 1, right = player 2)
- HP bars with segmented fill (FFVI style)
- Potion counter
- Action text with animation
- Damage numbers floating up
- Flash effect on hit
- Victory fanfare animation

---

## Success Criteria

**Phase 1 Complete When:**
1. Can load a FixedDamageGame match JSON
2. Displays two players with HP bars
3. Steps through turns showing actions
4. HP bars update correctly
5. Shows winner at end

**MVP Complete When:**
1. Play/pause/step controls work
2. Speed control works
3. Can drag-drop any match JSON
4. Looks recognizably "FFVI-like"

---

## Non-Goals (v1)

- Live match streaming (websockets)
- Video export (mp4/gif)
- Sound effects
- Mobile optimization
- Hosted SaaS
- Multiple game support (FixedDamageGame only for v1)

---

## References

- [SPEC-RECORDER.md](specs/SPEC-RECORDER.md) - Record schema v1.3
- [SPEC-REPLAY.md](specs/SPEC-REPLAY.md) - Replay engine contract
- [Design Notes](docs/planning/) - Original browser viewer design
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
