# SPEC-VIEWER: Browser Replay Viewer Contract

> **Status**: Draft
> **Version**: 0.1.0
> **Last Updated**: 2026-01-20
> **Implementation**: 🚧 Phase 1 (in progress)
> **Authors**: Diego Zoracky, Claude
> **Audience**: Viewer developers, skin authors, integration engineers

## 1. Purpose

- Provide a browser-based visualization layer for AgentDeck match records
- Enable researchers to "watch" AI agent matches with intuitive playback controls
- Define stable contracts between record loading, timeline playback, and rendering
- Support pluggable "skins" (FFVI, debug, custom) without coupling to specific UI frameworks

## 2. Scope & Philosophy Alignment

- Upholds `SPEC.md` §3.2 separation: Viewer consumes records, never affects gameplay
- Supports `CONTRIBUTING.md` modularity: Timeline engine, renderers, and UI are independent
- Aligns with design doc principle: **"The product is the record contract, not the UI"**
- Non-goals: Live streaming, video export, sound, mobile optimization (v1)

## 3. Responsibilities

### 3.1 Record Loader
- Validate incoming JSON against schema v1.3+
- Extract gameplay frames from `events[]`
- Provide normalized `MatchData` structure to timeline and renderers
- Reject incompatible schema versions with clear error messages

### 3.2 Timeline Engine
- Parse `MatchData` into ordered frame sequence
- Provide playback controls: play, pause, step, seek, speed
- Emit frame events to registered renderers
- Maintain playback state (current frame, playing, speed)

### 3.3 Renderer (Interface)
- Initialize visual representation from `MatchData`
- Update display on each frame event
- Render victory/conclusion state
- Clean up resources on destroy

## 4. Data Structures

### 4.1 MatchData (Normalized Input)

```typescript
interface MatchData {
  schemaVersion: string;        // "1.3"
  matchId: string;
  game: string;                 // "FixedDamageGame"
  players: string[];            // ["Alice", "Bob"]
  winner: string | null;
  seed: number;
  frames: GameplayFrame[];      // Extracted from events
  finalState: GameState;
  metadata: MatchMetadata;
}
```

### 4.2 GameplayFrame (Per-Turn Data)

```typescript
interface GameplayFrame {
  index: number;                // 0-based frame index
  turnNumber: number;           // Game turn (1-based)
  player: string;               // Acting player
  action: string;               // "ATTACK" | "POTION" | ...
  stateBefore: GameState;
  stateAfter: GameState;
  timestamp: number;            // Original event timestamp
  prompt?: PromptData;          // Optional prompt/response data
}
```

### 4.3 GameState (FixedDamageGame)

```typescript
interface GameState {
  health: Record<string, number>;
  potions: Record<string, number>;
  turn: number;
  lastAction: Record<string, string | null>;
}
```

### 4.4 PromptData (Optional Debug Info)

```typescript
interface PromptData {
  promptText: string;
  responseText: string;
  duration: number;
}
```

## 5. Public API

### 5.1 RecordLoader

```javascript
// Load and validate a match record
RecordLoader.load(json: object): MatchData
RecordLoader.loadFromFile(file: File): Promise<MatchData>
RecordLoader.validate(json: object): ValidationResult
```

**Guarantees:**
- V1: MUST reject schema versions < 1.3
- V2: MUST extract all `type: "gameplay"` events into frames
- V3: MUST preserve frame ordering by `context.turn_index`
- V4: MUST normalize state keys to camelCase for JS consumption

### 5.2 Timeline

```javascript
class Timeline {
  constructor(matchData: MatchData)

  // Playback control
  play(): void
  pause(): void
  step(direction: 1 | -1 = 1): void
  seek(frameIndex: number): void
  setSpeed(multiplier: number): void

  // State (read-only)
  readonly currentFrame: number
  readonly totalFrames: number
  readonly isPlaying: boolean
  readonly speed: number

  // Events
  onFrame(callback: (frame: GameplayFrame) => void): void
  onEnd(callback: (winner: string | null) => void): void
  offFrame(callback): void
  offEnd(callback): void
}
```

**Guarantees:**
- T1: `play()` MUST emit frames at intervals of `baseDelay / speed`
- T2: `step()` MUST emit exactly one frame and pause
- T3: `seek()` MUST clamp to valid frame range [0, totalFrames-1]
- T4: Frame callbacks MUST receive complete `GameplayFrame` data
- T5: `onEnd` MUST fire after last frame with winner from `MatchData`

### 5.3 Renderer (Interface)

```javascript
interface Renderer {
  // Initialize renderer in DOM container
  init(container: HTMLElement, matchData: MatchData): void

  // Render a gameplay frame (called by Timeline)
  renderFrame(frame: GameplayFrame): void

  // Render match conclusion
  renderVictory(winner: string | null, finalState: GameState): void

  // Cleanup resources
  destroy(): void
}
```

**Guarantees:**
- R1: `init()` MUST be callable multiple times (re-init for new match)
- R2: `renderFrame()` MUST handle any valid `GameplayFrame`
- R3: `destroy()` MUST remove all DOM elements added by renderer
- R4: Renderers MUST NOT modify `MatchData` or `GameplayFrame` objects

## 6. Invariants & Guarantees

### 6.1 Record Compatibility (RC)
1. **RC1**: Viewer MUST support schema v1.3 records from SPEC-RECORDER
2. **RC2**: Viewer MUST fail fast with clear error on unsupported schema
3. **RC3**: Unknown event types MUST be skipped, not crash playback
4. **RC4**: Missing optional fields MUST use sensible defaults

### 6.2 Playback Integrity (PI)
5. **PI1**: Frame order MUST match original event order (by turn_index)
6. **PI2**: State transitions MUST be accurate (stateBefore → stateAfter)
7. **PI3**: Playback MUST be deterministic (same record → same frames)
8. **PI4**: Speed changes MUST not skip or duplicate frames

### 6.3 Renderer Independence (RI)
9. **RI1**: Timeline MUST work with any conforming Renderer
10. **RI2**: Renderers MUST work with any conforming Timeline
11. **RI3**: Multiple renderers MAY be attached to one Timeline
12. **RI4**: Renderer failures MUST NOT crash Timeline

## 7. Error Handling

| Condition | Behavior | User Message |
|-----------|----------|--------------|
| Invalid JSON | Reject load | "Invalid JSON format" |
| Schema < 1.3 | Reject load | "Unsupported schema version: {v}. Requires 1.3+" |
| Missing required field | Reject load | "Missing required field: {field}" |
| No gameplay events | Allow load, warn | "No gameplay events found" |
| Renderer throws | Log, continue | (silent, playback continues) |

## 8. Examples

### 8.1 Basic Usage

```javascript
// Load record
const json = await fetch('match_xxx.json').then(r => r.json());
const matchData = RecordLoader.load(json);

// Create timeline and renderer
const timeline = new Timeline(matchData);
const renderer = new FFVIRenderer();

// Initialize
renderer.init(document.getElementById('viewer'), matchData);

// Connect timeline to renderer
timeline.onFrame(frame => renderer.renderFrame(frame));
timeline.onEnd(winner => renderer.renderVictory(winner, matchData.finalState));

// Start playback
timeline.play();
```

### 8.2 Playback Controls

```javascript
// Keyboard controls
document.addEventListener('keydown', (e) => {
  switch(e.code) {
    case 'Space': timeline.isPlaying ? timeline.pause() : timeline.play(); break;
    case 'ArrowRight': timeline.step(1); break;
    case 'ArrowLeft': timeline.step(-1); break;
    case 'Digit1': timeline.setSpeed(1); break;
    case 'Digit2': timeline.setSpeed(2); break;
  }
});
```

## 9. Testing Strategy

| Focus | Invariants | Verification |
|-------|------------|--------------|
| Schema validation | RC1-RC4 | Load v1.3 records, reject v1.2, skip unknown events |
| Frame extraction | PI1-PI3 | Compare extracted frames to source events |
| Playback timing | T1, PI4 | Measure frame intervals at different speeds |
| Renderer contract | R1-R4, RI1-RI4 | Mock renderer, verify callbacks |
| Error handling | All error cases | Invalid inputs produce expected errors |

## 10. Design Rationale

- **Record-first**: Viewer is a **consumer** of the record contract. Changes to visualization don't require record format changes.
- **Pluggable renderers**: Separation allows FFVI skin, debug view, future Unity renderer, etc. without core changes.
- **No framework dependency**: Vanilla JS ensures viewer works anywhere (iframe, Jupyter, standalone).
- **Fail-safe playback**: Renderer errors don't crash timeline; unknown events are skipped.

## 11. Future Work

- **Debug renderer**: Show prompts, responses, and controller metadata
- **Multi-game support**: Abstract game-specific state handling
- **Narration integration**: Connect to Spectator-derived narration streams
- **Export**: Single-file HTML bundle, animated GIF
- **Hosted viewer**: Load records from URLs

## 12. References

- [SPEC-RECORDER.md](SPEC-RECORDER.md) v1.3 - Record schema
- [SPEC-REPLAY.md](SPEC-REPLAY.md) - Python replay engine
- [ROADMAP-VIEWER.md](../ROADMAP-VIEWER.md) - Implementation roadmap
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development workflow
