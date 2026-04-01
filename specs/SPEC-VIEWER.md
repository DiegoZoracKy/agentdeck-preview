# SPEC-VIEWER: Browser Replay Viewer Contract

> **Status**: Final
> **Version**: 0.4.0
> **Last Updated**: 2026-04-01
> **Implementation**: ✅ Offline beta surface (schema v1.3+ loader, local library, smoke-check) / 🚧 Planned (curation sidecars + metadata UI)
> **Audience**: Viewer developers, skin authors, integration engineers

## 1. Purpose

- Provide a browser-based visualization layer for AgentDeck match records
- Enable researchers to "watch" AI agent matches with intuitive playback controls
- Define stable contracts between record loading, timeline playback, and rendering
- Support pluggable "skins" (`retro_jrpg_scene`, `debug`, custom) without coupling to specific UI frameworks
- Require the bundled offline viewer to support both `FixedDamageGame` and `VariableDamageGame`

## 2. Scope & Philosophy Alignment

- Upholds `SPEC.md` §3.2 separation: Viewer consumes records, never affects gameplay
- Supports `CONTRIBUTING.md` modularity: Timeline engine, renderers, and UI are independent
- Aligns with design doc principle: **"The product is the record contract, not the UI"**
- Non-goals: Live streaming, video export, sound, and broadcast orchestration. The current viewer is an offline replay surface.

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

### 3.4 Renderer Registry (Optional)
- Map `matchData.game` to a renderer implementation
- Provide a simple selection mechanism for swapping skins

### 3.5 Match Metadata Layer
- Accept curated match metadata from a sidecar-derived manifest entry
- Display:
  - picker-facing `subtitle`
  - loaded-match `synopsis`
  - timeline highlight markers
  - active-frame highlight badge
- Keep optional long-form `transcript` out of the runtime manifest payload

## 4. Data Structures

### 4.1 MatchData (Normalized Input)

```typescript
interface MatchData {
  schemaVersion: string;        // "1.3"
  matchId: string;
  game: string;                 // "FixedDamageGame" | "VariableDamageGame" | ...
  players: string[];            // ["Alice", "Bob"]
  winner: string | null;
  seed: number;
  frames: GameplayFrame[];      // Extracted from events
  finalState: GameState;
  metadata: MatchMetadata;
  lifecycle: {
    handshakes: object[];
    conclusions: object[];
  };
  outcome: string;
  forfeitReason: string | null;
  forfeitingPlayer: string | null;
}
```

### 4.2 GameplayFrame (Per-Turn Data)

```typescript
interface GameplayFrame {
  index: number;                // 0-based frame index
  turnNumber: number;           // Game turn (1-based)
  player: string;               // Acting player
  action: string | object;      // "ATTACK" | "POTION" | ... or normalized action payload
  stateBefore: GameState;
  stateAfter: GameState;
  timestamp: number;            // Original event timestamp
  prompt?: PromptData;          // Optional prompt/response data
  reasoning?: string | null;
}
```

### 4.3 GameState (Combat-State Shape Used By Bundled Skins)

```typescript
interface GameState {
  health: Record<string, number>;
  potions: Record<string, number>;
  turn: number;
  lastAction: Record<string, string | null>;
}
```

The bundled offline combat skins assume this state shape and therefore MUST work for both:
- `FixedDamageGame`
- `VariableDamageGame`

Games with different state contracts MAY still use the viewer, but they MUST register their own renderers.

### 4.4 PromptData (Optional Debug Info)

```typescript
interface PromptData {
  promptText: string;
  responseText: string;
  duration: number;
}
```

### 4.5 MatchHighlight (Viewer Metadata)

```typescript
interface MatchHighlight {
  turn: number;                 // 1-based turn number
  label: string;               // <= 50 chars, short badge/picker copy
}
```

### 4.6 MatchMetadataSidecar (Portable Sidecar Artifact)

```typescript
interface MatchMetadataSidecar {
  version: number;             // 1
  subtitle: string;
  synopsis: string;
  highlights: MatchHighlight[];
  transcript?: Array<{
    turn: number;              // 1-based turn number
    text: string;
  }>;
}
```

### 4.7 MatchManifestEntry (Viewer Runtime Catalog)

```typescript
interface MatchManifestEntry {
  label: string;
  path: string;
  subtitle?: string | null;
  synopsis?: string | null;
  highlights?: MatchHighlight[];
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
- V3: MUST preserve frame ordering by `context.turn_index` (alias of `phase_index`) when present
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
  readonly currentFrameData: GameplayFrame | null
  readonly matchData: MatchData

  // Events
  onFrame(callback: (frame: GameplayFrame) => void): void
  onEnd(callback: (winner: string | null) => void): void
  onStateChange(callback: () => void): void
  offFrame(callback): void
  offEnd(callback): void
  offStateChange(callback): void
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
  renderVictory(
    winner: string | null,
    finalState: GameState,
    extras?: { outcome?: string; forfeitReason?: string | null; forfeitingPlayer?: string | null }
  ): void

  // Cleanup resources
  destroy(): void
}
```

**Guarantees:**
- R1: `init()` MUST be callable multiple times (re-init for new match)
- R2: `renderFrame()` MUST handle any valid `GameplayFrame`
- R3: `destroy()` MUST remove all DOM elements added by renderer
- R4: Renderers MUST NOT modify `MatchData` or `GameplayFrame` objects

### 5.4 RendererRegistry (Optional)

```javascript
// Register a renderer for a game and skin
RendererRegistry.register(gameName: string, skin: string, rendererClass: Function): void

// Get available skins for a game
RendererRegistry.getAvailableSkins(gameName: string): string[]

// Resolve a renderer for a match and skin
RendererRegistry.create(matchData: MatchData, skin: string): Renderer
RendererRegistry.get(gameName: string, skin: string): Function | null
```

**Guarantees:**
- RR1: `create()` MUST throw a clear error when no renderer is registered for the (game, skin) pair
- RR2: `getAvailableSkins()` MUST return all registered skins for a game in sorted order
- RR3: The bundled offline viewer MUST register at least one renderer for both `FixedDamageGame` and `VariableDamageGame`

### 5.5 Match Manifest Promotion

```javascript
// Promote sidecar metadata into manifest entries
updateManifestFromSidecars(matchesDir: string): ManifestPayload
```

**Guarantees:**
- MP1: Manifest promotion MUST preserve `label` + `path` for every bundled match
- MP2: When `matches/<name>.meta.json` exists, promotion MUST copy `subtitle`, `synopsis`, and `highlights` into the manifest entry
- MP3: Promotion MUST NOT copy `transcript` into the manifest
- MP4: Missing sidecars MUST be tolerated; the manifest entry remains valid with only `label` + `path`

## 6. Invariants & Guarantees

### 6.1 Record Compatibility (RC)
1. **RC1**: Viewer MUST support schema v1.3+ records from SPEC-RECORDER
2. **RC2**: Viewer MUST fail fast with clear error on unsupported schema
3. **RC3**: Unknown event types MUST be skipped, not crash playback
4. **RC4**: Missing optional fields MUST use sensible defaults
5. **RC5**: Bundled combat skins MUST accept both `FixedDamageGame` and `VariableDamageGame` records when the normalized state contains `health`, `potions`, `turn`, and `lastAction`

### 6.2 Playback Integrity (PI)
5. **PI1**: Frame order MUST match original event order (by `turn_index`/`phase_index`)
6. **PI2**: State transitions MUST be accurate (stateBefore → stateAfter)
7. **PI3**: Playback MUST be deterministic (same record → same frames)
8. **PI4**: Speed changes MUST not skip or duplicate frames

### 6.3 Renderer Independence (RI)
9. **RI1**: Timeline MUST work with any conforming Renderer
10. **RI2**: Renderers MUST work with any conforming Timeline
11. **RI3**: Multiple renderers MAY be attached to one Timeline
12. **RI4**: Renderer failures MUST NOT crash Timeline

### 6.4 Metadata UI (MU)
13. **MU1**: The viewer MUST accept manifest entries with or without metadata fields; missing `subtitle`, `synopsis`, or `highlights` MUST degrade gracefully.
14. **MU2**: When `subtitle` is present, the viewer MUST surface it near match selection so users can decide what to watch before loading.
15. **MU3**: When `synopsis` is present, the viewer MUST show it in the loaded-match info panel.
16. **MU4**: When `highlights` are present, the timeline MUST render a marker for each highlighted turn.
17. **MU5**: When playback reaches a highlighted turn, the viewer MUST surface the matching `label` as the active key-moment badge.
18. **MU6**: Highlight markers MUST map by 1-based turn number, not by raw frame index, so curated metadata remains readable and stable across renderer implementations.

## 7. Error Handling

| Condition | Behavior | User Message |
|-----------|----------|--------------|
| Invalid JSON | Reject load | "Invalid JSON format" |
| Schema < 1.3 | Reject load | "Unsupported schema version: {v}. Requires 1.3+" |
| Missing required field | Reject load | "Missing required field: {field}" |
| No gameplay events | Allow load, warn | "No gameplay events found" |
| Renderer throws | Log, continue | (silent, playback continues) |
| Invalid sidecar metadata | Skip metadata, keep match loadable | "Invalid metadata for {match}" |

## 8. Examples

### 8.1 Basic Usage

```javascript
// Load record
const json = await fetch('match_xxx.json').then(r => r.json());
const matchData = RecordLoader.load(json);

// Create timeline and renderer with specific skin
const timeline = new Timeline(matchData);
const renderer = RendererRegistry.create(matchData, 'retro_jrpg_scene');

// Initialize
renderer.init(document.getElementById('viewer'), matchData);

// Connect timeline to renderer
timeline.onFrame(frame => renderer.renderFrame(frame));
timeline.onEnd(winner => renderer.renderVictory(winner, matchData.finalState));

// Start playback
timeline.play();
```

### 8.1.1 Skin Selection

```javascript
// Get available skins for the game
const skins = RendererRegistry.getAvailableSkins(matchData.game);
// ['debug', 'retro_jrpg_scene']

// Switch skins dynamically
function switchSkin(newSkin) {
  renderer.destroy();
  renderer = RendererRegistry.create(matchData, newSkin);
  renderer.init(container, matchData);
  // Reconnect timeline callbacks...
}
```

### 8.1.2 Curated Match Metadata

```json
{
  "label": "FixedDamage 1: FlashLite-AO collapse vs Flash-AO",
  "path": "matches/fixed-damage-01-flashlite-ao-collapse-vs-flash-ao.json",
  "subtitle": "Ignores recovery and collapses",
  "synopsis": "FlashLite never touches its potion, then reaches the late fight in lethal range with no recovery left to use. The loss is a behavioral failure to engage the recovery mechanic at all.",
  "highlights": [
    { "turn": 8, "label": "Flash pushes to lethal range" },
    { "turn": 9, "label": "Still attacks instead of healing" },
    { "turn": 11, "label": "Collapse completes" }
  ]
}
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
| Renderer registry | RR1 | Register renderer, create instance, assert error on unknown game |
| Manifest promotion | MP1-MP4, MU1 | Merge sidecars, preserve fallback entries, exclude transcript |
| Metadata UI | MU2-MU6 | Subtitle preview, synopsis panel, timeline markers, active highlight badge |
| Error handling | All error cases | Invalid inputs produce expected errors |

## 10. Design Rationale

- **Record-first**: Viewer is a **consumer** of the record contract. Changes to visualization don't require record format changes.
- **Pluggable renderers**: Separation allows a retro-JRPG skin, debug view, future Unity renderer, etc. without core changes.
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
- [ROADMAP.md](../ROADMAP.md) - Implementation roadmap
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development workflow
