# SPEC-REPLAY: Replay Engine Contract

> Status: Final v1.1.0
> Version: 1.1.0
> Last Updated: 2026-01-20
> Implementation: ✅ Complete (Recorder schema v1.3 alignment)
> Authors: Codex, Claude (consensus)
> Audience: Data analysts, debugging tool authors, visualization developers, core contributors

## 1. Purpose
- Make replay the **canonical way** to re-run recorded matches for analysis, debugging, and demonstration without re-executing live games.
- Guarantee **event parity** (live == replay): same event types, same payloads, same prompt metadata, same timing relationships, same ordering.
- Enable data-driven iteration via faithful reconstruction of three-phase lifecycle (handshake → turns → conclusion) with complete prompt metadata.

## 2. Scope & Philosophy Alignment
- Grounded in `SPEC.md` §2.4: reproducibility requires perfect replay parity for research validity.
- Upholds `SPEC-OBSERVABILITY.md`: Replay emits same event types with same payloads as live execution for spectator compatibility.
- Reinforces `SPEC.md` §2.4: enable data-driven iteration via replay analysis tools that behave identically to live spectators.
- **Clean slate design**: v1.1 spec targets SPEC-RECORDER v1.3 format only—no backward compatibility, no legacy shims.
- **Event parity over inference**: Refuse to synthesize missing data; replay is playback, not re-execution.
- Non-goals: Recording logic (`SPEC-RECORDER.md`), spectator implementations (`SPEC-SPECTATOR.md`), live execution (`SPEC-CONSOLE.md`).

## 3. Responsibilities
- **Artifact Ingestion**: Load SPEC-RECORDER v1.3 artifacts (JSON schema 1.x) and hydrate deterministic event timeline including three-phase lifecycle.
- **Prompt Replay**: Consume Recorder's enriched `events` stream (schema v1.3) and emit lifecycle events with embedded prompt payloads so prompt metadata survives round-trip without a separate dialogue transcript.
- **Context Reconstruction**: Rebuild EventContext from stored metadata (session_id, batch_id, match_id, phase_index, timestamp) without recomputation.
- **Event Emission**: Emit PLAYER_HANDSHAKE_* → MATCH_START → recorded events → PLAYER_CONCLUSION (when present) → MATCH_END through EventBus for spectator consumption (matches live execution order per SPEC-CONSOLE §6.6 E1).
- **Playback Control**: Support speed multiplier (2.0 = 2x speed, 0.5 = half speed, 0.0 = instant) via ReplayScheduler for time-based delays.
- **Spectator Binding**: Subscribe spectators to isolated EventBus before replay, unsubscribe after (same semantics as live execution).
- **State Tracking**: Maintain state_before/state_after continuity during gameplay event replay using recorded turn metadata (no on-the-fly recomputation).
- **Parity Guarantees**: Ensure replayed events match recorded events (type, data, context, ordering) for analysis validity.

## 4. Data Structures

### ReplayEngine

```python
class ReplayEngine:
    def __init__(
        self,
        match_artifact: Union[MatchResult, Dict[str, Any]],
        *,
        scheduler: Optional[ReplayScheduler] = None,
    ):
        """
        Load match for replay.

        Args:
            match_artifact: MatchResult object or dict (from Recorder.load_match()).
                           MUST conform to SPEC-RECORDER v1.3 schema.
            scheduler: Playback scheduler (defaults to ReplayScheduler()).

        Raises:
            ValueError: If schema_version missing or != 1.x
        """
        self.events: List[Event]           # Deserialized events
        self.metadata: Dict[str, Any]      # Match metadata (players, game, session_id, etc.)
        self.match_metadata: Dict[str, Any]  # Match-level metadata (turns, duration, etc.)
        self.winner: Optional[str]
        self.final_state: Dict[str, Any]
        self.seed: int
        self.event_bus = EventBus()        # Isolated EventBus for this replay
        self.scheduler = scheduler or ReplayScheduler()
```

**Guarantees**: MUST deserialize Recorder schema v1.3 artifacts. MUST hydrate events (with embedded prompt payloads) and metadata. MUST initialize isolated EventBus. MUST raise ValueError if schema invalid.

### ReplayScheduler

```python
class ReplayScheduler:
    def __init__(self, speed: float = 1.0):
        """
        Control playback speed.

        Args:
            speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x faster, 0.0 = instant)
        """
        self.speed = speed

    def compute_delay(self, last_event: Optional[Event], current_event: Event) -> float:
        """
        Calculate delay between events based on timestamps and speed multiplier.

        Returns:
            Delay in seconds (0.0 if speed <= 0 or NaN)
        """
```

**Guarantees**: MUST compute delays from event timestamps. MUST respect speed multiplier (speed=2.0 → half delay). MUST treat speed <= 0 or NaN as zero delay (instant replay).

## 5. Public API

### ReplayEngine(match_artifact, *, scheduler=None)

Create ReplayEngine from recorded match.

**Contract**:
- Accept: MatchResult or dict from `Recorder.load_match()` conforming to Recorder schema v1.3 (enriched events), optional ReplayScheduler
- Perform: Deserialize events into Event objects, rehydrate metadata (match_id, session_id, players, game, seed), initialize isolated EventBus
- Raise: ValueError if `schema_version` missing or not compatible with v1.3, ValueError if mandatory sections (`events`, `metadata`) missing
- MUST: Validate event prompt payloads follow SPEC-RECORDER §6.7 (PM1-PM6) structure
- MUST: Initialize ReplayScheduler (use provided or create default)

### replay(spectators: List[Spectator], speed: Optional[float] = None) -> None

Execute replay with spectators.

**Contract**:
- Accept: List of spectator instances, optional speed override (overrides scheduler's default speed)
- Perform: Subscribe spectators to EventBus, emit lifecycle and recorded events with computed delays, unsubscribe spectators
- Emit: Event sequence per LC1-LC5 (PLAYER_HANDSHAKE_* → MATCH_START → recorded events → PLAYER_CONCLUSION → MATCH_END)
- Raise: ValueError if speed is invalid type
- MUST: Catch and log spectator exceptions per SPEC-SPECTATOR §5.3 EI1 (error isolation), continue replay with remaining spectators
- MUST: Respect speed multiplier for delays (0.0 = instant, 2.0 = 2x speed)
- MUST: Replay events in exact recorded order
- MUST: Rehydrate EventContext for each event (session_id, match_id, phase_index, timestamp)
- MUST: Emit prompt metadata from the recorded event payloads (handshake, gameplay, conclusion, parse_failure)

## 6. Invariants & Guarantees

### 6.1 Input Normalization (IN)
1. **IN1**: MUST accept only SPEC-RECORDER schema v1.3 artifacts (raise ValueError if `schema_version` missing or incompatible with v1.3).
2. **IN2**: MUST accept dict artifacts from `Recorder.load_match()` (JSON schema v1.3). MAY accept `MatchResult` objects for convenience, but MUST require `match_result.metadata["events"]` to contain recorded events serialized by Recorder.
3. **IN3**: MUST validate that every event requiring prompt metadata (handshake, gameplay, conclusion, parse_failure) includes a well-formed `prompt` payload per SPEC-RECORDER §6.7. Raise ValueError if any prompt payload is missing required fields.

### 6.2 Event Parity (EP)
4. **EP1**: MUST replay every recorded event exactly once, in recorded order, with identical event type and data payload.
5. **EP2**: MUST emit event types consistent with live execution (MATCH_START, PLAYER_HANDSHAKE_*, GAMEPLAY, domain events, PLAYER_CONCLUSION, MATCH_END).
6. **EP3**: EventContext MUST be rehydrated with same session_id, match_id, phase_index, timestamp as recorded (no recomputation).

### 6.3 Timing & Ordering (TO)
7. **TO1**: MUST replay events sequentially in recorded order; no reordering allowed.
8. **TO2**: MUST compute inter-event delays via ReplayScheduler and apply speed multiplier (delay = recorded_delta / speed).
9. **TO3**: MUST treat speed <= 0 or NaN as zero delay (instant replay, skip all waits).

### 6.4 Context Reconstruction (CR)
10. **CR1**: MUST extract session_id, batch_id, match_id from metadata when not present in event context.
11. **CR2**: MUST preserve phase_index from recorded events as read-only (do not recompute from turn_number or other fields).

### 6.5 Lifecycle Events (LC)
12. **LC1**: MUST emit events in exact order: **PLAYER_HANDSHAKE_START** → **PLAYER_HANDSHAKE_COMPLETE|ABORT** (per player) → **MATCH_START** → **GAMEPLAY** events → **PLAYER_CONCLUSION** (per player when present) → **MATCH_END**. This matches live execution order per SPEC-CONSOLE §6.6 E1.
13. **LC2**: MUST emit recorded PLAYER_HANDSHAKE_* events (with embedded prompt payloads) before MATCH_START to match live execution ordering.
14. **LC3**: MUST emit MATCH_START after handshake phase completes, with rehydrated game/player metadata.
15. **LC4**: MUST emit MATCH_END after all recorded gameplay/domain events AND any PLAYER_CONCLUSION events, with MatchResult containing winner, final_state, seed.
16. **LC5**: MUST emit recorded PLAYER_CONCLUSION events before MATCH_END when present (prompt payload `phase="conclusion"`).

### 6.6 Prompt Metadata Replay (PM)
17. **PM1**: MUST deliver `prompt.prompt_text`, `prompt.prompt_blocks`, and `prompt.response_text` from the recorded event payload to spectators for handshake/turn/conclusion/parse_failure phases.
18. **PM2**: MUST include optional `prompt.renderer_output`, `prompt.controller_format`, `prompt.controller_metadata`, `prompt.usage_info`, and `prompt.retries` in emitted events when present in the recording.
19. **PM3**: MUST treat the recorded event payload (`event.data["prompt"]`) as the canonical source for prompt metadata (never synthesize or recompute prompt data).

### 6.7 State Tracking (ST)
20. **ST1**: MUST maintain state_before/state_after continuity across GAMEPLAY events (state_after from event N becomes state_before for event N+1).
21. **ST2**: MUST use recorded turn_number and phase_index without recomputation (playback, not re-execution).

### 6.8 Spectator Isolation (SI)
22. **SI1**: MUST emit events through a dedicated EventBus instance, preventing interference with live sessions or other replays.
23. **SI2**: MUST unsubscribe spectators after replay completes (leave spectator instances clean for reuse).
24. **SI3**: MUST catch and log spectator exceptions per SPEC-SPECTATOR §5.3 EI1 (error isolation). Framework catches exceptions, logs them, and continues replay with remaining spectators. This matches live execution error handling.
25. **SI4** (Logger Injection): MUST inject logger into spectators before EventBus subscription if `spectator.logger is None`. Check `if getattr(spectator, "logger", None) is None` and assign `spectator.logger = getattr(self, "logger", None)`. This mirrors Console's late-binding pattern (SPEC-CONSOLE §6.8 P4) and enables spectators to write to core log streams per SPEC-SPECTATOR §5.5 (LI1-LI5). Implementation: replay.py:82-85.

## 7. Data Flow & Interaction

### Replay Initialization
1. ReplayEngine receives match_artifact (MatchResult or dict).
2. Validate schema_version is compatible with Recorder v1.3 (raise ValueError otherwise).
3. Deserialize events into Event objects (including prompt payloads).
4. Extract metadata (match_id, session_id, batch_id, players, game, seed).
5. Initialize isolated EventBus and ReplayScheduler.

### Replay Execution
1. Subscribe spectators to EventBus.
2. Emit PLAYER_HANDSHAKE_START for each player.
3. Emit recorded PLAYER_HANDSHAKE_COMPLETE|ABORT events (prompt payload phase="handshake").
4. Emit MATCH_START with reconstructed game/player metadata (AFTER handshake phase, matching live execution order per SPEC-CONSOLE §6.6 E1).
5. For each recorded event in chronological order (including PLAYER_CONCLUSION when present):
   - Compute delay from timestamps via scheduler.
   - Sleep delay (unless speed == 0.0).
   - Rehydrate EventContext (match_id, session_id, phase_index, timestamp).
   - Emit event through EventBus (spectators receive).
   - Catch and log any spectator exceptions (error isolation per SPEC-SPECTATOR §5.3 EI1).
6. Emit MATCH_END with MatchResult (winner, final_state, seed).
7. Unsubscribe spectators from EventBus.

**Key Principle**: Replay uses recorded turn metadata (turn_number, phase_index, timestamps)—no on-the-fly recomputation. The recorded event payload (`event.data["prompt"]`) is the **canonical source** for all prompt metadata.

### Event Routing
- MATCH_START/END → Lifecycle events with reconstructed metadata
- PLAYER_HANDSHAKE_* → Recorded events with `prompt.phase="handshake"`
- GAMEPLAY → State continuity maintained (ST1), recorded phase_index preserved (CR2)
- Domain events → Emitted with original payloads and rehydrated context
- PLAYER_CONCLUSION → Recorded events with `prompt.phase="conclusion"`

## 8. Error Handling & Edge Cases

**Input Validation**:
- Missing `schema_version` or `schema_version != 1.x` → **MUST raise ValueError** with descriptive message stating required schema version.
- Missing mandatory sections (`events`, `metadata`) → **MUST raise ValueError** listing missing fields.
- Malformed prompt payload (`event.data["prompt"]` missing required PM fields per SPEC-RECORDER §6.7) → **MUST raise ValueError** with specific validation error.

**Playback Control**:
- `speed < 0` or `speed == NaN` → **MUST treat as 0.0** (instant replay, skip all delays).
- Invalid `speed` type (e.g., string) → **MUST raise ValueError**.

**Spectator Exceptions**:
- Spectator raises exception during event handling → **MUST catch and log** per SPEC-SPECTATOR §5.3 EI1 (error isolation).
- Replay **MUST continue** with remaining spectators after logging exception (same error handling as live execution).
- Framework provides error isolation to prevent spectator failures from stopping replay.

**Context Reconstruction**:
- Missing context fields in recorded events → **MUST fallback to metadata** (session_id, match_id from metadata.session_id, metadata.match_id).
- Missing `phase_index` in recorded event → **MUST raise ValueError** (required field for deterministic turn ordering).

## 9. Examples

### Example 1: Basic replay with stats spectator

```python
from agentdeck.core.recorder import Recorder
from agentdeck.core.replay import ReplayEngine
from agentdeck.spectators import StatsTracker

# Load match from recorder
match_data = Recorder.load_match("agentdeck_runs/session_ABC/records/match_abc123.json")

# Replay with stats spectator
engine = ReplayEngine(match_data)
engine.replay(spectators=[StatsTracker()], speed=1.0)  # Real-time playback
```

### Example 2: Speed control

```python
# Instant replay (skip all delays)
engine = ReplayEngine(match_data)
engine.replay(spectators=[StatsTracker()], speed=0.0)

# Slow motion (half speed for detailed observation)
engine.replay(spectators=[DebugVisualizer()], speed=0.5)

# Fast forward (2x speed for quick analysis)
engine.replay(spectators=[SummaryCollector()], speed=2.0)
```

### Example 3: Prompt metadata analysis

```python
class PromptMetadataAnalyzer:
    """Analyze LLM prompts and responses from replay."""

    def on_player_handshake_complete(self, event: Event) -> None:
        data = event.data
        print(f"[HANDSHAKE] {data['player']}")
        print(f"  Prompt length: {len(data['prompt_text'])} chars")
        print(f"  Template blocks: {len(data['prompt_blocks'])} placeholders")
        print(f"  Response: {data['normalized_response']}")

    def on_player_conclusion(self, event: Event) -> None:
        data = event.data
        print(f"[CONCLUSION] {data['player']}")
        print(f"  Outcome: {data['outcome']}")
        print(f"  Reflection: {data['reflection_text']}")

    def on_gameplay(self, event: Event) -> None:
        ctx = event.context
        prompt = event.data.get('prompt')
        if prompt and 'prompt_text' in prompt:
            print(f"[TURN {ctx['phase_index']}] Prompt: {len(prompt['prompt_text'])} chars")

# Replay match and analyze all prompts
engine = ReplayEngine(match_data)
engine.replay(spectators=[PromptMetadataAnalyzer()], speed=0.0)
```

### Example 4: Prompt-only viewer

```python
class PromptViewer:
    """View only the LLM prompt/response exchanges (handshake, turns, conclusion)."""

    def __init__(self):
        self.exchanges = []

    def on_player_handshake_complete(self, event: Event) -> None:
        prompt = event.data.get('prompt', {})
        self.exchanges.append({
            "phase": "handshake",
            "player": event.data['player'],
            "prompt": prompt.get('prompt_text', ''),
            "response": prompt.get('response_text', ''),
        })

    def on_gameplay(self, event: Event) -> None:
        prompt = event.data.get('prompt')
        if prompt:
            self.exchanges.append({
                "phase": "turn",
                "turn": event.context.get('phase_index'),
                "player": event.data.get('player'),
                "prompt": prompt.get('prompt_text', ''),
                "response": prompt.get('response_text', ''),
            })

    def on_player_conclusion(self, event: Event) -> None:
        prompt = event.data.get('prompt', {})
        self.exchanges.append({
            "phase": "conclusion",
            "player": event.data['player'],
            "prompt": prompt.get('prompt_text', ''),
            "response": prompt.get('response_text', ''),
        })

    def print_summary(self):
        for i, exchange in enumerate(self.exchanges):
            print(f"\n--- Exchange {i+1}: {exchange['phase']} ---")
            print(f"Player: {exchange['player']}")
            print(f"Prompt: {exchange['prompt'][:200]}...")
            print(f"Response: {exchange['response'][:200]}...")

# Replay and extract prompt exchanges
viewer = PromptViewer()
engine = ReplayEngine(match_data)
engine.replay(spectators=[viewer], speed=0.0)
viewer.print_summary()
```

## 10. Testing Strategy

| Focus | Invariants | Verification Goal |
|-------|------------|-------------------|
| Input normalization | IN1-IN3 | Feed v1.3 artifacts (dict and MatchResult). Assert schema validation. Verify ValueError on wrong schema. |
| Event parity | EP1-EP3 | Record live match. Replay. Diff event streams (type, data, context, order). Assert exact match. |
| Timing control | TO1-TO3 | Mock `time.sleep()`. Verify delay computation and speed multiplier accuracy. Test instant (0.0), slow-mo (0.5), fast (2.0). |
| Context reconstruction | CR1-CR2 | Inspect rehydrated EventContext. Confirm match_id, session_id, phase_index preserved from recording. Verify no recomputation. |
| Lifecycle events | LC1-LC5 | Capture emitted event sequence. Verify order: PLAYER_HANDSHAKE_* → MATCH_START → GAMEPLAY → PLAYER_CONCLUSION → MATCH_END. |
| Prompt metadata | PM1-PM3 | Inspect recorded event payloads (`event.data["prompt"]`). Replay. Verify prompt_text, prompt_blocks, response_text, renderer_output, controller_format, controller_metadata delivered to spectators. |
| State tracking | ST1-ST2 | Verify state_before/state_after continuity. Confirm turn_number/phase_index match recorded values (no recomputation). |
| Spectator isolation | SI1-SI3 | Verify dedicated EventBus created. Confirm spectators unsubscribed post-replay. Test exception propagation. |

**Critical Test: Event Stream Diff**
1. Run live match with recorder
2. Capture event stream to list (via test spectator)
3. Replay recorded match
4. Capture replayed event stream to list (via same test spectator)
5. Diff the two lists (type, data, context, order)
6. Assert: Zero differences (perfect parity)

**Prompt Metadata Integrity Test**
1. Load recording with embedded prompt payloads
2. Replay with prompt metadata analyzer
3. Verify every event carrying a `prompt` object is replayed with identical contents
4. Confirm prompt_blocks accurately represents PromptBuilder composition
5. Verify renderer_output includes RenderResult metadata when applicable

## 11. Design Rationale

| Decision | Rationale |
|----------|-----------|
| **Event parity over inference** | Refusing to synthesize missing data ensures reproducibility and prevents silent failures. If data is missing, fail noisily rather than guess. |
| **Prompt-centric replay** | Embedding prompt metadata inside recorded events keeps a single timeline while enabling prompt UX research and A/B testing analysis. |
| **Scheduler abstraction** | Decoupling delay computation enables future pause/seek/bookmark features without rewriting replay core. Speed control is essential for debugging (instant), visualization (real-time), and demos (slow-motion). |
| **Clean slate (Recorder v1.3 only)** | No backward compatibility shims keeps implementation simple, testable, and maintainable. Historical recordings can be migrated offline if needed. |
| **Isolated EventBus** | Dedicated EventBus per replay prevents interference with live sessions and enables concurrent replay (e.g., batch analysis). |
| **No recomputation** | Replay is playback, not re-execution. Using recorded metadata (turn_number, phase_index, timestamps) ensures perfect parity without re-running game logic. |
| **Spectator exception propagation** | Same error handling semantics as live execution ensures spectators behave identically during replay and live runs. |

## 12. Open Questions / Future Work

### Playback Control Enhancements
- Should replay support **pause/resume** controls for interactive debugging?
- Do we need **seek APIs** for large recordings (jump to specific turn, bookmark positions)?
- Should we add **replay_prompts_only(spectators)** helper for prompt-focused analysis (skip gameplay/state events)?

### Multi-Match Replay
- Should replay support **SESSION_START/BATCH_START** reproduction for multi-match sessions?
- How should batch-level replay work (sequential matches with shared spectators)?

### State Verification
- How should replay integrate with **deterministic RNG snapshots** to rebuild intermediate state for verification?
- Should ReplayEngine validate state_after matches expected_state from game rules (catch recording bugs)?

### Metrics & Observability
- What metrics should ReplayEngine expose (events_replayed, duration, spectator_errors, memory_usage)?
- Should replay emit its own observability events (REPLAY_START, REPLAY_END, REPLAY_ERROR)?

## 13. References

- `specs/SPEC.md` §2.4 (Reproducibility, replay parity)
- `specs/SPEC-OBSERVABILITY.md` §3.1.1 (Player lifecycle events), §8.1 (Event payload schemas)
- `specs/SPEC-RECORDER.md` v1.3.0 §6.7 (Prompt payload structure within events)
- `specs/SPEC-PLAYER.md` v0.4.0 (Three-phase player model: handshake → turn → conclusion)
- `specs/SPEC-CONSOLE.md` v0.3.0 (Live execution lifecycle for comparison), §6.8 P4 (Logger injection pattern)
- `specs/SPEC-SPECTATOR.md` v1.2.0 (Logger injection contract §5.5 LI1-LI5, spectator lifecycle, error isolation)
- `specs/AGENTS.md` §2.3 (Data-driven iteration philosophy)

---

**Ready for implementation.**
This specification defines the v1.1.0 contract for replay with complete lifecycle support (handshake, turns, conclusion, parse failures) using Recorder v1.3's enriched event payloads as the single source of prompt metadata.
