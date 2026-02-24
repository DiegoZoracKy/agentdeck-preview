# SPEC-RECORDER: Match Recording & Persistence Contract

> Status: Final
> Version: 1.3.0
> Last Updated: 2026-02-23
> Implementation: ✅ Complete (schema v1.3 event enrichment)
> Authors: Claude, Codex, Diego ZoracKy
> Audience: Core contributors, data analysts, replay implementers

## 1. Purpose
- Define the contract for recording match data, events, and metadata to persistent storage for analysis and replay.
- Ensure comprehensive data capture including gameplay events, API usage, player configurations, game settings, and environmental context for reproducible research.
- Specify atomic write semantics, schema versioning, and normalization rules so recordings remain consistent across AgentDeck versions.

## 2. Scope & Philosophy Alignment
- Upholds `SPEC.md` §2.2 composition: Recorder is a plug-in spectator that receives events, never driving execution.
- Follows `SPEC.md` §2.4 reproducibility mandates: every match captures seed, configuration, environment, and game settings (including `information_level`, `allowed_actions`) for exact replay.
- Aligns with `SPEC-OBSERVABILITY.md`: Recorder is a session-scoped spectator receiving all events (lifecycle, gameplay, domain).
- Mirrors `SPEC.md` §3.1 simplicity: JSON payloads with progressive flushing avoid complex storage backends.
- Non-goals: Replay logic (`SPEC-REPLAY.md`), data analysis (`SPEC-RESEARCH.md`), or custom storage backends (future extension).

## 3. Responsibilities
- **Event Capture**: Subscribe to all event types (SESSION, BATCH, MATCH, GAMEPLAY, domain events) and serialize them into match recordings.
- **Progressive Persistence**: Write match data incrementally (after each gameplay event) to enable crash recovery and mid-match inspection.
- **Atomic Writes**: Use atomic file replacement to prevent corruption from interrupted writes or concurrent access.
- **Metadata Collection**: Capture match context (players, game config, environment, git state, timestamps) automatically.
- **Game Configuration Capture**: Record game settings (`information_level`, `allowed_actions`) and persist player configuration snapshots (model, controller, key parameters) via `player_summaries` for reproducibility and provenance.
- **API Usage Tracking**: Aggregate token counts, costs, latencies across LLM calls via `RecorderCollector` protocol.
- **Batch Aggregation**: Produce batch summary files with match references and aggregate statistics (win rates, turn counts).
- **Schema Versioning**: Tag recordings with schema version (`1.3` for match recordings, `1.0` for batches) and enforce exact version checks in `load_match()` for current-only validation.
- **Normalization**: Provide `load_match()` utility that normalizes current schema artifacts into a consistent structure.
- **Null Object Pattern**: Provide `NullRecorder` implementation so Console always has a valid Recorder instance (never `None`).

## 4. Data Structures

### NullRecorder (No-op Implementation)

```python
class NullRecorder:
    """No-op recorder for when recording is disabled.

    Implements Recorder interface with all methods as pass-through no-ops.
    Console always has a valid Recorder instance (real or NullRecorder).
    """

    def on_session_start(self, deck, context=None) -> None:
        pass  # No-op

    def on_batch_start(self, batch_id, game, players, matches, context=None) -> None:
        pass  # No-op

    def on_match_start(self, game, players, match_id=None, context=None) -> None:
        pass  # No-op

    def on_gameplay(self, event: Event) -> None:
        pass  # No-op

    def on_event(self, event: Event, context=None) -> None:
        pass  # No-op

    def on_match_end(self, result: MatchResult, context=None) -> None:
        pass  # No-op

    def on_batch_end(self, batch_id, results, context=None) -> None:
        pass  # No-op

    def flush(self) -> None:
        pass  # No-op
```

**Guarantees**: NullRecorder MUST implement all Recorder event handlers as no-ops. Console MUST use NullRecorder when recording is disabled (never None). See SPEC-CONSOLE.md §6.8 (L1) for Null Object pattern requirements.

### MatchRecording (Internal)

```python
@dataclass
class MatchRecording:
    match_id: str
    game_name: str
    players: List[str]
    schema_version: str = "1.3"
    schema_type: str = "match"  # Required by SV1
    metadata: Dict[str, Any]
    events: List[Dict[str, Any]] = field(default_factory=list)
    usage: APIUsageTracker = field(default_factory=APIUsageTracker)
    collector_results: Dict[str, Any] = field(default_factory=dict)
    winner: Optional[str] = None
    final_state: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None
```

**Guarantees**: In-memory structure accumulates events and metadata during match execution. Serialized to JSON via `to_dict()`. Every lifecycle event stored in `events` includes the complete prompt metadata payload required for reproducibility (handshake → turn → conclusion, see PM1-PM6). The `schema_type` field distinguishes match recordings from batch recordings per SV1. Metadata MUST include `player_summaries` (list of `Player.get_summary()` snapshots) for every participant.

### BatchRecording (Internal)

```python
@dataclass
class BatchRecording:
    batch_id: str
    schema_version: str = "1.0"
    schema_type: str = "batch"  # Required by SV1
    metadata: Dict[str, Any]
    match_refs: List[Dict[str, Any]] = field(default_factory=list)
```

**Guarantees**: Aggregates match references and batch-level statistics. Written once at `BATCH_END`. The `schema_type` field distinguishes batch recordings from match recordings per SV1. Batch recordings remain at schema version "1.0" (no changes in v1.1). Match references MUST surface each match's `player_summaries` so batch files provide the same provenance.

### APIUsageTracker (Internal)

```python
@dataclass
class APIUsageTracker:
    total_calls: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    models_used: Dict[str, int] = field(default_factory=dict)
```

**Guarantees**: Extracts `usage_info` from `ActionResult.metadata` during `on_gameplay()` and accumulates per-match totals.

### RecorderCollector (Protocol)

```python
class RecorderCollector(Protocol):
    """Extension point for custom data collection.

    Example use cases:
    - Decision quality scoring
    - Reasoning analysis
    - Strategy pattern detection
    """

    def on_match_start(self, match_id: str, metadata: Dict[str, Any]) -> None: ...
    def on_gameplay(self, event: Event) -> None: ...
    def on_match_end(self) -> Dict[str, Any]: ...
```

**Guarantees**: Extension point for custom data collection. Collector results merged into match recording under `collector_data` field with namespaced keys.

## 5. Public API

### Recorder(output_dir="records", *, session=None, collectors=None, schema_version="1.3")

Create Recorder instance with optional session binding and custom collectors.

**Parameters**:
- `output_dir`: Base directory for recordings (defaults to `records/`). When a session is bound the recorder MUST redirect writes to `{run_dir}/{session_id}/records/`.
- `session`: `SessionContext` for accessing session ID, seed, directories (bound automatically by Console).
- `collectors`: List of `RecorderCollector` instances for extended data capture.
- `schema_version`: Schema version tag (default `"1.3"` for match recordings with enriched prompt metadata events and parse failure support).

**Guarantees**:
- MUST create output directory if missing (uses `session.record_directory` when session bound).
- MUST subscribe to Console EventBus as session-scoped spectator (receives all events).
- MUST tolerate being constructed before session is available (late-binding via `bind_session()`).

### bind_session(session: SessionContext)

Late-binding helper for attaching session context after construction.

**Guarantees**:
- MUST update `output_dir` to `session.record_directory`
- MUST ensure directory exists

### Event Handlers (Duck-typed, called by EventBus)

#### on_batch_start(batch_id, game, players, matches, context=None)
- Captures batch metadata (session ID, planned matches, git info, player configs, game config).
- Initializes `BatchRecording` structure.
- Extracts game configuration (`information_level`, `allowed_actions`) from game instance.
- **MUST record player order as provided to Console.run()** (mechanics-agnostic, per SPEC-CONSOLE M3).

#### on_match_start(game, players, match_id=None, context=None)
- Creates `MatchRecording` with timestamped match ID.
- Captures environment (Python version, AgentDeck version, git state).
- Records game configuration (`information_level`, `allowed_actions`).
- Records player template sources (inline vs Path, file references if applicable).
- Captures `player_summaries` from `Player.get_summary()` (model, controller, prompt config) and stores them in match metadata for provenance.
- Invokes collector `on_match_start()` hooks.
- **MUST flush initial match stub immediately** for crash recovery.

#### on_player_handshake_start(event: Event)
- Serializes `PLAYER_HANDSHAKE_START` lifecycle event into the `events` array (or pre-match buffer when match has not started).
- MUST persist prompt metadata payload (`prompt_text`, `prompt_blocks`, `controller_format`) so handshake lifecycle is fully auditable.
- MUST flush progressively when match recording is active.

#### on_player_handshake_complete(event: Event)
- Serializes PLAYER_HANDSHAKE_COMPLETE event (SPEC-OBSERVABILITY §3.1.1) into the `events` array.
- MUST persist prompt metadata in-place within the recorded event: `prompt_text`, `prompt_blocks`, `response_text`, `controller_format`, `controller_metadata`, optional `renderer_output`, and `usage_info` (PM1-PM6).
- MUST preserve `event.context` (timestamps, match_id, phase_index=None) alongside normalized payload fields: `player`, `accepted=True`, `normalized_response`, `duration`.
- **MUST flush match file progressively** after processing.

#### on_player_handshake_abort(event: Event)
- Serializes PLAYER_HANDSHAKE_ABORT event into `events`.
- MUST include the same PM1-PM6 prompt metadata plus `accepted=False` and `reason` describing the rejection cause.
- MUST preserve timing context and flush progressively.

#### on_gameplay(event: Event)
- Extracts `state_before`, `state_after`, `action`, `reasoning`, and `metadata` from the GAMEPLAY event.
- Deep copies state snapshots to prevent mutation; preserves `phase_index`, `turn_index`, `mechanic`, and `turn_context` when present.
- MUST sanitize engine-internal state keys (prefix `_`) from recorded gameplay `state_before` / `state_after` payloads.
- MUST embed prompt metadata directly in the recorded event under a `prompt` payload (PM1-PM6) when supplied by the controller/action metadata.
- MUST extract API usage from `metadata.get("usage_info")` and aggregate via `APIUsageTracker`.
- Invokes collector `on_gameplay()` hooks.
- **MUST flush match file progressively** after processing.

#### on_player_action_parse_failed(event: Event)
- Captures controller parsing failures (schema v1.3).
- MUST append event entry containing: `player`, `turn_number`, `match_id`, `timestamp`, `monotonic_time`, serialized `parse_result` (success, error, raw_response, candidates, metadata), `policy_outcome`, and any available prompt snapshot (PM1-PM6 fields).
- MUST flush immediately after recording the failure to guarantee durability.

#### on_player_conclusion(event: Event)
- Serializes PLAYER_CONCLUSION event into `events` with PM1-PM6 metadata describing post-match reflection (`prompt_text`, `prompt_blocks`, `response_text`, `reflection_text`, `outcome`, `controller_format`, `controller_metadata`, `renderer_output`, `usage_info`).
- **MUST flush match file progressively** after processing.

#### on_event(event: Event, context=None)
- Records arbitrary domain events emitted by games.
- Preserves event type, data, timestamp, duration.
- Flushes progressively.

#### on_match_end(result: MatchResult, context=None)
- Finalizes match recording with `winner`, `final_state`, `seed`, `ended_at` timestamp.
- MUST persist any failure metadata supplied by console (e.g., `metadata["outcome"] = "aborted"`, `policy_outcome`).
- Invokes collector `on_match_end()` hooks and merges results into `collector_data`.
- Appends match reference to current batch (if batch active).
- **MUST perform final atomic flush** before clearing `current_match`.

#### on_batch_end(batch_id, results, context=None)
- Writes batch summary file (`batch_{batch_id}.json`) with match references and statistics.
- Match references MUST include corresponding `player_summaries` so batch-level consumers can reconstruct model/config details per match.
- Calculates aggregate win rates, turn counts, first-player advantage metrics.
- Includes `seeds_used` list for complete seed traceability (per SPEC-CONSOLE T3).

### Recorder.load_match(path: Union[str, Path]) -> Dict[str, Any] (Static)

Load match JSON from disk and normalize structure.

**Guarantees**:
- MUST enforce `schema_version` presence and exact compatibility with the current match schema (`1.3`).
- MUST normalize `metadata["match_id"]` (falls back to filename stem if missing).
- MUST return consistent structure: `{schema_version, events, winner, final_state, seed, metadata, api_usage_summary, collector_data}`.
- MUST raise `ValueError` for missing/unsupported schema versions.

## 6. Invariants & Guarantees

### 6.1 Progressive Persistence (PP)
1. **PP1**: MUST flush match recording after every event handler invocation (`on_gameplay`, `on_event`).
2. **PP2**: MUST flush initial match stub immediately after `on_match_start()` to enable crash recovery.
3. **PP3**: MUST perform final flush in `on_match_end()` before clearing `current_match`.
4. **PP4**: MUST preserve event emission timestamps/durations from lifecycle/gameplay events (do not replace with flush-time placeholders).

### 6.2 Atomic Writes & File Safety (AW)
4. **AW1**: MUST use atomic file replacement (write to temp file, `os.replace()`) to prevent corruption from crashes or concurrent writes.
5. **AW2**: MUST create parent directories (`os.makedirs`) before atomic write attempts.
6. **AW3**: MUST generate deterministic filenames (`{match_id}.json`, `batch_{batch_id}.json`) within resolved output directory.

### 6.3 Schema Versioning (SV)
7. **SV1**: MUST tag all recordings with `schema_version` field (currently `"1.3"` for match recordings with enriched prompt events, `"1.0"` for batch recordings) and `schema_type` field (`"match"` or `"batch"`).
8. **SV2**: MUST enforce schema version checks in `load_match()` and raise `ValueError` for missing or incompatible versions.
9. **SV3**: MUST validate against the exact current match schema version (`1.3`) in `load_match()` (no major-version wildcard acceptance).

### 6.4 Metadata Completeness (MC)
10. **MC1**: MUST capture match metadata: `match_id`, `session_id`, `batch_id`, `started_at`, `ended_at`, `duration_seconds`, `winner`, `seed` (per-match seed), `players` (ordered list post-ordering), `player_order` (original indices), `player_order_source` (console/game), `first_player` (name + index; actual first actor when available, else first ordered player).
10a. **MC1a**: Match payload MUST include top-level `batch_id` equal to `metadata.batch_id`.
10b. **MC1b**: Match payload MUST expose top-level `started_at`, `ended_at`, and `duration_seconds` aligned with metadata and batch match refs for completed matches.
10c. **MC1c**: `player_order` captures roster order before runtime first-player selection; `first_player` captures the actual first actor when runtime selects one.
11. **MC2**: MUST capture environment metadata: `agentdeck_version`, `python_version`, `git_info` (commit, branch, dirty status).
12. **MC3**: MUST capture player configurations: `name`, `type`, `module`, `model`, `temperature`, `max_tokens`, masked `api_key_prefix`, template sources (inline vs file paths) and persist them in recording metadata via `player_summaries` for each player.
12a. **MC3a**: `player_summaries[].total_cost` MUST reflect finalized per-match player costs after `on_match_end()` when `metadata.match.player_costs` is available.
12b. **MC3b**: `Recorder.on_match_start()` MUST receive `context["batch_id"]`; missing batch context is invalid for the current schema.
13. **MC4**: MUST capture game configuration: `name`, `module`, `information_level` (when present), `allowed_actions` (when game exposes property).
14. **MC5**: MUST capture batch context: `session_id`, `matches_planned`, `matches_completed`, `seeds_used` (list of all per-match seeds).

### 6.5 Seed & Reproducibility (SR)
15. **SR1**: MUST persist session-level seed in batch metadata (from SessionContext).
16. **SR2**: MUST persist per-match seed in match payloads (`MatchRecording.seed`, `metadata.seed`).
17. **SR3**: MUST persist `seeds_used` list in batch recordings for complete traceability (per SPEC-CONSOLE T3).
18. **SR4**: MUST record complete player ordering metadata (per SPEC-CONSOLE M4 and SPEC-OBSERVABILITY §9.1): `players` (ordered list post-ordering), `player_order` (List[int] of original indices), `player_order_source` (Literal["console", "game"]), `first_player` (Dict with {"name": str, "index": int}, resolved to actual first actor when runtime data is available).

### 6.6 API Usage & Collectors (UC)
19. **UC1**: MUST extract `usage_info` from `ActionResult.metadata` during `on_gameplay()` when present.
20. **UC2**: MUST aggregate per-match totals: `total_calls`, `total_tokens`, `total_cost`, `average_latency_ms`, `models_used`.
21. **UC3**: MUST include `api_usage_summary` in match recordings when usage data is present.
22. **UC4**: MUST invoke collector hooks (`on_match_start`, `on_gameplay`, `on_match_end`) in registration order when collectors configured.
23. **UC5**: MUST namespace collector outputs by class name (dedupe via suffix) to avoid collisions in `collector_data`.
24. **UC6**: MUST tolerate collector errors without destabilizing recording (errors logged but not propagated).

### 6.7 Prompt Metadata Capture (PM)

**Status**: Finalized for schema v1.3.0.

Recorder embeds prompt metadata directly inside the lifecycle events captured in the `events` array. Handshake, turn, conclusion, and parse-failure events each carry a `prompt` payload describing the full exchange (no separate dialogue array).

**Requirements**:

25. **PM1**: MUST capture `prompt_text` (exact text sent to the LLM, previously `raw_prompt`) for all lifecycle phases.
26. **PM2**: MUST capture `prompt_blocks` (PromptBuilder composition: block keys, rendered content, lengths) for all phases.
27. **PM3**: MUST capture `response_text` (raw LLM output before controller parsing) for all phases.
28. **PM4**: MUST capture `renderer_output` (RenderResult metadata) when provided by the renderer during turn/conclusion phases.
29. **PM5**: MUST capture `controller_format` (format instructions delivered to the LLM) for every exchange.
30. **PM6**: MUST capture `controller_metadata` (parser outcomes, validation results, retries, normalization) for every exchange.
30a. **PM7**: SHOULD capture `call_id` when available to support deterministic request/response correlation in debug logs.

**Normalized Prompt Payload**:

Recorder stores prompt metadata under a `prompt` object within each recorded event:

```python
{
  "type": "player_handshake_complete",  # or player_handshake_abort, gameplay, player_conclusion, player_action_parse_failed
  "data": {
    "player": "Alice",
    "accepted": True,
    "normalized_response": "OK",
    "prompt": {
      "phase": "handshake",
      "turn_number": None,
      "prompt_text": "You are playing FixedDamageGame...",
      "prompt_blocks": [...],
      "response_text": "OK",
      "controller_format": "Reply with OK",
      "controller_metadata": {"accepted": True},
      "renderer_output": null,
      "usage_info": {"tokens": 12, "cost": 0.0001},
      "call_id": "ab12cd34",
      "duration": 0.234,
      "retries": 0
    }
  },
  "timestamp": 1705499452.123,
  "duration": 0.234,
  "context": {"match_id": "match_123", "session_id": "session_abc", "phase_index": None}
}
```

- `phase` MUST be one of `handshake`, `turn`, `conclusion`, or `parse_failure`.
- `turn_number` MUST hold the 1-based turn number for turn/parse_failure events (`null` for handshake/conclusion).
- `renderer_output`, `usage_info`, and `retries` are optional but SHOULD be included when provided by upstream components.
- `call_id` is optional but SHOULD be included when exposed by upstream player metadata.

**Metadata Sources**: Per SPEC-PLAYER v1.0.0 DS2 and SPEC-OBSERVABILITY §3.1.1, lifecycle events already expose the required fields. Recorder MUST deep-copy these payloads to avoid later mutation.

### Parse Failure Capture (PF) — *Updated in v1.3.0*
31. **PF1**: Recorder MUST persist `PLAYER_ACTION_PARSE_FAILED` events with full context (`parse_result`, `policy_outcome`, optional prompt snapshot) exactly as emitted by Console (SPEC-OBSERVABILITY §3.1.2).
32. **PF2**: Recorded parse-failure events MUST include a `prompt` payload with `phase="parse_failure"`, `turn_number`, `prompt_text`, `prompt_blocks`, and raw `response_text` so downstream tools can analyze the failing exchange without a separate transcript structure.

**Template Provenance** (already captured per MC3):
- Template sources (`inline` vs `file:path/to/template.txt`)
- Controller format instructions (strict parser expectations)
- Game-specific `allowed_actions` bound to controller

**Alignment**: Player lifecycle events are fully defined in SPEC-OBSERVABILITY v1.2.0 §3.1.1-3.1.2. This spec defines the event serialization contract (prompt payload embedding, parse-failure capture) for Recorder schema v1.3. See SPEC-REPLAY for how replays reconstruct lifecycle events from the enriched `events` stream.

## 7. Data Flow & Interaction

### Initialization
- Console creates Recorder with session context (or binds later via `bind_session()`).
- Recorder subscribes to EventBus as session-scoped spectator.
- Output directory created from `session.record_directory`.

### Batch Execution
- `BATCH_START` → Create `BatchRecording`, capture batch metadata (session, game config, player configs, git info).
- `MATCH_START` → Create `MatchRecording`, capture game settings (`information_level`, `allowed_actions`), player template sources, flush initial stub.
- Gameplay events → Append to `current_match.events`, extract API usage, invoke collectors, flush progressively.
- `MATCH_END` → Finalize `MatchRecording`, invoke collectors, flush, append match ref to batch.
- `BATCH_END` → Calculate batch statistics, write batch summary file with `seeds_used` list.

### Progressive Flushing
- After each event: `_flush_current_match()` → `_atomic_write()` → temp file → `os.replace()`.

### Replay Loading
- Researcher calls `Recorder.load_match(path)` → Schema validation → Normalization → Return dict.

## 8. Error Handling & Edge Cases

- **Missing schema_version**: Raise `ValueError` with descriptive message.
- **Unsupported schema_version**: Raise `ValueError` stating the exact expected version.
- **Collector exceptions**: Log error but continue recording (collectors are optional extensions).
- **Missing `usage_info` in metadata**: Silently skip API usage tracking (not all players provide usage data).
- **Concurrent writes**: Atomic replacement prevents corruption (last write wins).
- **Mid-match crashes**: Progressive flushing ensures partial data is recoverable.
- **Missing match_id**: Normalize to filename stem in `load_match()`.
- **Git metadata failures**: Capture `None` opportunistically rather than raising exceptions.
- **Lifecycle callbacks out of order**: Ignore without crashing (e.g., `on_gameplay` without active match).

## 9. Examples

### Example 1: Basic Recorder Usage (Automatic via Console)

```python
from agentdeck import AgentDeck, AgentDeckConfig, MockPlayer
from agentdeck.games.examples import FixedDamageGame

config = AgentDeckConfig(seed=42)
with AgentDeck(session=config) as deck:
    # Recorder automatically attached by Console
    game = FixedDamageGame(information_level="full")
    results = deck.play(game, [MockPlayer("A"), MockPlayer("B")], matches=3)

    # Recordings written to: deck.session.record_directory/
    # - {match_id_1}.json  (includes information_level="full", allowed_actions=["ATTACK", "POTION"])
    # - {match_id_2}.json
    # - {match_id_3}.json
    # - batch_{batch_id}.json  (includes seeds_used list)
```

### Example 2: Loading and Inspecting Recordings

```python
from agentdeck.core.recorder import Recorder

# Load match recording
match_data = Recorder.load_match("agentdeck_runs/session_20250121_143052/records/match_0001.json")

print(f"Schema: {match_data['schema_version']}")
print(f"Winner: {match_data['winner']}")
print(f"Seed: {match_data['seed']}")
print(f"Events: {len(match_data['events'])}")
print(f"Information Level: {match_data['metadata']['game_config'].get('information_level')}")
print(f"Allowed Actions: {match_data['metadata']['game_config'].get('allowed_actions')}")
print(f"API Usage: {match_data.get('api_usage_summary', {})}")
```

### Example 3: Custom Collector for Advanced Analysis

```python
from agentdeck.core.recorder import RecorderCollector
from agentdeck.core import AgentDeck

class ReasoningQualityCollector:
    def __init__(self):
        self.reasoning_lengths = []

    def on_match_start(self, match_id: str, metadata: dict) -> None:
        self.reasoning_lengths = []

    def on_gameplay(self, event: Event) -> None:
        reasoning = event.data.get("reasoning")
        if reasoning:
            self.reasoning_lengths.append(len(reasoning))

    def on_match_end(self) -> dict:
        if not self.reasoning_lengths:
            return {}
        return {
            "avg_reasoning_length": sum(self.reasoning_lengths) / len(self.reasoning_lengths),
            "max_reasoning_length": max(self.reasoning_lengths),
            "total_turns_with_reasoning": len(self.reasoning_lengths),
        }

# Use custom collector
from agentdeck.core.recorder import Recorder

recorder = Recorder(collectors=[ReasoningQualityCollector()])
config = AgentDeckConfig(seed=42)
deck = AgentDeck(recorder=recorder, session=config)
# ... recordings will include collector_data with reasoning quality metrics
```

## 10. Match JSON Schema

### Match File Structure (`{match_id}.json`)

```json
{
  "schema_version": "1.3",
  "schema_type": "match",
 "match_id": "20250121_143052",
  "batch_id": "exec_001",
  "started_at": "2026-02-23T03:00:00+00:00",
  "ended_at": "2026-02-23T03:01:01+00:00",
  "duration_seconds": 61.0,
  "game": "FixedDamageGame",
  "players": ["Alice", "Bob"],
  "player_order": [1, 0],
  "player_order_source": "console",
  "first_player": {"name": "Bob", "index": 1},
  "winner": "Alice",
  "seed": 42,
  "final_state": {"health": {"Alice": 60, "Bob": 0}, "potions": {"Alice": 2, "Bob": 0}},
  "events": [
    {
      "type": "player_handshake_complete",
      "timestamp": 1705499452.123,
      "duration": 0.234,
      "context": {"session_id": "abc123", "match_id": "20250121_143052"},
      "data": {
        "player": "Alice",
        "accepted": true,
        "normalized_response": "OK",
        "prompt": {
          "phase": "handshake",
          "turn_number": null,
          "prompt_text": "You are playing FixedDamageGame...\n\nReply with OK to confirm.",
          "prompt_blocks": [
            {"key": "game_instructions", "content": "You are playing...", "length": 45},
            {"key": "controller_format", "content": "Reply with OK", "length": 14}
          ],
          "response_text": "OK",
          "controller_format": "Reply with OK, READY, or YES to confirm",
          "controller_metadata": {"accepted": true, "normalized_response": "OK"},
          "renderer_output": null,
          "usage_info": {"tokens": 12, "cost": 0.0001, "latency_ms": 234},
          "duration": 0.234,
          "retries": 0
        }
      }
    },
    {
      "type": "match_start",
      "timestamp": 1705499452.200,
      "duration": 0.0,
      "context": {"session_id": "abc123", "match_id": "20250121_143052"},
      "data": {
        "players": ["Alice", "Bob"],
        "seed": 42,
        "turns": 5
      }
    },
    {
      "type": "gameplay",
      "timestamp": 1705499453.456,
      "duration": 1.234,
      "context": {"session_id": "abc123", "match_id": "20250121_143052", "phase_index": 0},
      "data": {
        "mechanic": "turn_based",
        "phase_index": 0,
        "player": "Alice",
        "action": "ATTACK",
        "reasoning": "Attack is best strategy",
        "state_before": {"health": {"Alice": 100, "Bob": 100}, "potions": {"Alice": 3, "Bob": 3}},
        "state_after": {"health": {"Alice": 100, "Bob": 80}, "potions": {"Alice": 3, "Bob": 3}},
        "prompt": {
          "phase": "turn",
          "turn_number": 1,
          "prompt_text": "Current game state:\n...\n\nWhat is your action?",
          "prompt_blocks": [
            {"key": "game_view", "content": "Current game state...", "length": 150},
            {"key": "controller_format", "content": "Respond with: ATTACK or POTION", "length": 32}
          ],
          "response_text": "I choose ATTACK because...",
          "controller_format": "Respond with one of: ATTACK, POTION",
          "controller_metadata": {"validated": true, "candidates": ["ATTACK", "POTION"]},
          "renderer_output": {"sections": ["game_view"], "total_length": 150},
          "usage_info": {"tokens": 150, "cost": 0.002, "latency_ms": 1234},
          "duration": 1.234,
          "retries": 0
        }
      }
    },
    {
      "type": "match_end",
      "timestamp": 1705499456.789,
      "duration": 0.0,
      "context": {"session_id": "abc123", "match_id": "20250121_143052"},
      "data": {
        "winner": "Alice",
        "final_state": {"health": {"Alice": 60, "Bob": 0}, "potions": {"Alice": 2, "Bob": 0}},
        "reason": "normal"
      }
    }
  ],
  "metadata": {
    "match_id": "20250121_143052",
    "session_id": "abc123",
    "batch_id": "exec_001",
    "started_at": "2025-01-21T14:30:52.123456",
    "ended_at": "2025-01-21T14:30:55.789012",
    "context": {
      "session_id": "abc123",
      "batch_id": "exec_001",
      "match_index": 0,
      "total_matches_in_batch": 3
    },
    "environment": {
      "agentdeck_version": "0.1.0",
      "python_version": "3.10.12",
      "git_info": {"commit": "abc123def", "branch": "spec-driven", "dirty": false}
    },
    "player_configs": {
      "Alice": {
        "type": "GPTPlayer",
        "model": "gpt-4",
        "temperature": 0.7,
        "templates": {
          "handshake": "inline",
          "turn": "inline",
          "conclusion": "inline"
        }
      },
      "Bob": {
        "type": "MockPlayer",
        "module": "agentdeck.players.mock"
      }
    },
    "game_config": {
      "name": "FixedDamageGame",
      "module": "agentdeck.games.examples.fixed_damage",
      "information_level": "full",
      "allowed_actions": ["ATTACK", "POTION"]
    },
    "session": {"session_id": "abc123", "started_at": 1705499450.0, "seed": 42},
    "match": {"turns": 5, "duration": 3.666, "truncated": false}
  },
  "api_usage_summary": {
    "total_calls": 5,
    "total_tokens": 750,
    "total_prompt_tokens": 500,
    "total_completion_tokens": 250,
    "total_cost": 0.015,
    "average_latency_ms": 1234.5,
    "models_used": {"gpt-4": 5}
  },
  "collector_data": {
    "ReasoningQualityCollector": {
      "avg_reasoning_length": 42.5,
      "max_reasoning_length": 78,
      "total_turns_with_reasoning": 4
    }
  }
}
```

### Batch File Structure (`batch_{batch_id}.json`)

```json
{
  "schema_version": "1.0",
  "schema_type": "batch",
  "batch_id": "exec_001",
  "match_refs": [
    {
      "match_id": "20250121_143052",
      "filename": "20250121_143052.json",
      "winner": "Alice",
      "turns": 5,
      "started_at": "2025-01-21T14:30:52.123456",
      "ended_at": "2025-01-21T14:30:55.789012"
    },
    {
      "match_id": "20250121_143056",
      "filename": "20250121_143056.json",
      "winner": "Bob",
      "turns": 7,
      "started_at": "2025-01-21T14:30:56.123456",
      "ended_at": "2025-01-21T14:31:01.234567"
    }
  ],
  "metadata": {
    "batch_id": "exec_001",
    "session_id": "abc123",
    "game": "FixedDamageGame",
    "players": ["Alice", "Bob"],
    "matches_planned": 3,
    "matches_completed": 3,
    "seeds_used": [42, 1234, 5678],
    "started_at": "2025-01-21T14:30:52.000000",
    "ended_at": "2025-01-21T14:31:05.000000",
    "git_info": {"commit": "abc123def", "branch": "spec-driven", "dirty": false},
    "configuration": {
      "agentdeck_version": "0.1.0",
      "python_version": "3.10.12",
      "game": {
        "name": "FixedDamageGame",
        "module": "agentdeck.games.examples.fixed_damage",
        "information_level": "full",
        "allowed_actions": ["ATTACK", "POTION"]
      },
      "players": [
        {"name": "Alice", "type": "GPTPlayer", "module": "agentdeck.players.gpt"},
        {"name": "Bob", "type": "MockPlayer", "module": "agentdeck.players.mock"}
      ]
    },
    "statistics": {
      "total_matches": 3,
      "players": {
        "Alice": {
          "matches_played": 3,
          "wins": 2,
          "losses": 1,
          "win_rate": 0.667,
          "total_turns_in_wins": 12,
          "total_turns_in_losses": 8,
          "as_first_player": {"played": 2, "wins": 1}
        },
        "Bob": {
          "matches_played": 3,
          "wins": 1,
          "losses": 2,
          "win_rate": 0.333,
          "total_turns_in_wins": 8,
          "total_turns_in_losses": 12,
          "as_first_player": {"played": 1, "wins": 0}
        }
      }
    }
  }
}
```

## 11. Recommended Practices

### Template Provenance
- When players use Path-based templates (per SPEC-PLAYER v0.4.0), record file paths in player configurations.
- **Recommended**: Version-control match artifacts alongside template files so experiments can be replayed faithfully.
- Example: Store templates in `prompts/` directory and recordings in `recordings/` with shared git history.

### Reproducibility Checklist
For perfect reproducibility, recordings MUST capture:
- ✅ Session seed (SR1)
- ✅ Per-match seeds (SR2, SR3)
- ✅ Game configuration (`information_level`, `allowed_actions`) (MC4)
- ✅ Player configurations (controllers, renderers, templates) (MC3)
- ✅ Environment (Python, AgentDeck versions, git state) (MC2)
- ✅ Player ordering metadata (`player_order`, `player_order_source`, `first_player`) (SR4)

## 12. Testing Strategy

| Focus | Invariants | Verification Goal |
|-------|------------|-------------------|
| Progressive persistence | PP1, PP2, PP3 | Verify flush after each event, initial stub, final flush. Crash mid-match and confirm partial data recoverable. |
| Atomic writes | AW1, AW2, AW3 | Simulate concurrent writes/crashes during flush. Verify no corrupted files, deterministic filenames. |
| Schema versioning | SV1, SV2, SV3 | Load recordings with valid/missing/incompatible schemas. Confirm version enforcement. |
| Metadata completeness | MC1-MC5 | Inspect match/batch files. Assert all required metadata fields present (including `information_level`, `allowed_actions`, template sources). |
| Seed traceability | SR1-SR4 | Verify session seed, per-match seeds, `seeds_used` list, and player ordering metadata (`player_order`, `player_order_source`, `first_player`) in artifacts. |
| API usage & collectors | UC1-UC6 | Run matches with LLM players. Verify `api_usage_summary` aggregation. Test collector hooks and error handling. |

## 13. Design Rationale

- **Progressive flushing**: Enables crash recovery and mid-match inspection without waiting for `MATCH_END`. Critical for long-running experiments.
- **Atomic writes**: Prevents corruption from crashes/concurrency. Uses OS-level atomic replace (`os.replace()`).
- **Schema versioning**: Supports future evolution without breaking replay. Major version = breaking change, minor = compatible.
- **Deep copying**: Prevents state mutations from affecting recordings. Games see mutable dicts, recordings are immutable snapshots.
- **Collector protocol**: Extension point for custom analysis without modifying Recorder. Duck-typed for simplicity.
- **Batch aggregation**: Single file summarizes entire batch for quick analysis (leaderboards, win rates) without loading all matches.
- **Git metadata**: Captures experiment provenance automatically. Critical for reproducible research.
- **Game configuration capture**: Recording `information_level` and `allowed_actions` enables faithful replay and A/B test analysis.
- **Template provenance**: Recording template sources (inline vs file paths) supports reproducibility when templates evolve.

## 14. Open Questions / Future Work

### Schema Evolution
- Should we support pluggable storage backends (S3, database) or keep filesystem-only?
- What compression strategy for large batches (thousands of matches)?
- Should `load_match()` support loading from URLs or just local paths?
- Do we need a `RecorderConfig` dataclass for advanced options (compression, flush frequency)?
- Should batch files include aggregated API usage across all matches?
- Migration strategy for schema version 2.0 (if needed)?

### Usability
- Should we provide helper methods for extracting template file references from recordings?
- Should we add validation helpers to verify recorded matches have complete prompt metadata?

## 15. References

- `SPEC.md` §1.1 (Research platform focus), §2.4 (Reproducibility)
- `SPEC-OBSERVABILITY.md` v1.2.0 (Event types, lifecycle events, player lifecycle events §3.1.1, parse failure events §3.1.2, payload guidelines §9)
- `SPEC-CONSOLE.md` v0.5.0 (Execution lifecycle, parse failure handling, BATCH events, seed traceability, TurnLoop delegation)
- `SPEC-PLAYER.md` v1.0.0 (Three-phase lifecycle, metadata capture DS2, template-driven prompts)
- `SPEC-CONTROLLER.md` v1.2.0 (Controller binding, format instructions, metadata, ActionParseError semantics)
- `SPEC-GAME-MECHANIC-TURN-BASED.md` v1.1.0 (Turn execution, EventFactory integration, parse failure propagation)
- `SPEC-AGENTDECK.md` (SessionState, MatchResult structures)
- `SPEC-GAME.md` v0.6.0 (Game configuration, `information_level`, `allowed_actions`, parse-failure policy hook)
- `SPEC-REPLAY.md` (Replay requirements using enriched event prompt metadata)
- Implementation: `src/agentdeck/core/recorder.py`
