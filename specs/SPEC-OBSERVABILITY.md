# AgentDeck Observability & Event Specification

> Status: Final
> Version: 2.0.0
> Last Updated: 2026-05-30
> Implementation: ⬜ Planned (canonical GameplayEventData v2 + recorder/replay parity)
> Audience: Core developers, game authors, spectator authors

---

## 1. Purpose

This specification locks down AgentDeck’s event model so researchers can build games and spectators with confidence while the framework delivers:

- **Predictable, mechanic-agnostic observability**  
- **Replay fidelity** (events replay exactly as recorded)  
- **Tiny games** (rules only) and **composable spectators**

It merges prior drafts into a single consensus document aligned with the philosophy in `SPEC.md` and `CONTRIBUTING.md`.

---

## 2. Terminology

| Term    | Meaning |
|---------|---------|
| **Session** | Lifespan of an `AgentDeck` instance (may span many runs and matches). |
| **Run** | One invocation of `AgentDeck.play()` or `AgentDeck.replay()` (can include batches/matches). |
| **Batch** | Optional grouping of multiple matches within a run. |
| **Match** | One complete execution of a game between players. |
| **Phase** | Mechanic-defined progression unit (turn, round, step, question, etc.). |

---

## 3. Event Categories & Responsibilities

AgentDeck distinguishes three tiers of events. Ownership indicates which layer emits the event.

| Category | Ownership | Description |
|----------|-----------|-------------|
| **Lifecycle** | Framework (`AgentDeck` / `Console`) | Session/run/batch/match boundaries. |
| **Structural gameplay** | Framework execution flow (e.g., TurnLoop) | Mechanic-agnostic `GAMEPLAY` events emitted once per phase. |
| **Domain** | Game author (via helper) | Game-specific signals (e.g., `bid_placed`, `card_drawn`). |

### 3.1 Lifecycle Events

| EventType | Emitted by | Scope | Notes |
|-----------|------------|-------|-------|
| `SESSION_START` / `SESSION_END` | AgentDeck | Session spectators only | Fired when the deck context opens/closes. Includes session seed. |
| `BATCH_START` / `BATCH_END` | Console | All spectators | Mandatory; emitted around every run (treat matches=1 as size-1 batch) and serve as run-level boundaries. Includes batch_id and seed metadata. |
| `MATCH_START` / `MATCH_END` | Console | All spectators | Include match metadata, final `MatchResult`, per-match seed, and ordered player list. |
| `PLAYER_HANDSHAKE_START` / `PLAYER_HANDSHAKE_COMPLETE` / `PLAYER_HANDSHAKE_ABORT` | Console | All spectators | Player handshake phase events (before first turn). Include prompt metadata for reproducibility. |
| `PLAYER_CONCLUSION` | Console | All spectators | Optional post-match reflection phase. Include prompt metadata when conclusion executed. |
| `PLAYER_ACTION_PARSE_FAILED` | Console | All spectators | Emitted when controller parsing fails. Includes raw response, candidates, metadata, and policy outcome. |

> **Note:** `RUN_START` / `RUN_END` events are not currently implemented. Use `BATCH_START`/`END` for run-level boundaries when needed, or `SESSION_START`/`END` for session-level tracking.

#### 3.1.1 Player Lifecycle Events

Player lifecycle events track the three-phase player model (handshake → turn → conclusion) defined in `SPEC-PLAYER.md`.

**Handshake Phase Events** (emitted before first turn):

- **`PLAYER_HANDSHAKE_START`**: Emitted when Console begins handshake for a player
  - Signals start of LLM invocation for handshake prompt
  - Includes `player`, `match_id`, `prompt_text` (raw handshake prompt)

- **`PLAYER_HANDSHAKE_COMPLETE`**: Emitted when player acknowledges successfully
  - Includes `player`, `match_id`, `response_text` (raw LLM response), `normalized_response` (parsed acknowledgement), `accepted=True`
  - Prompt metadata: `prompt_text`, `prompt_blocks`, `response_text`, `renderer_output`, `controller_format`, `controller_metadata`

- **`PLAYER_HANDSHAKE_ABORT`**: Emitted when player rejects handshake
  - Includes `player`, `match_id`, `response_text`, `normalized_response`, `accepted=False`, `reason` (rejection explanation)
  - Console aborts match after this event per SPEC-CONSOLE H1

**Conclusion Phase Event** (emitted before `MATCH_END` when policy enabled):

- **`PLAYER_CONCLUSION`**: Emitted when the conclusion phase runs for a player (per Console policy)
  - Includes `player`, `match_id`, `reflection_text` (LLM response, may be empty), `outcome` (match result summary)
  - Prompt metadata: `prompt_text`, `prompt_blocks`, `response_text`, `renderer_output`
  - Emitted even when a player returns an empty reflection; policy determines who concludes

**Parse Failure Event** (emitted during turn execution):

- **`PLAYER_ACTION_PARSE_FAILED`**: Emitted when an action controller cannot parse the LLM response
  - Includes `player`, `match_id`, `turn_number`, `parse_result` (serialized `ParseResult`), `policy_outcome` (value from `ParseFailurePolicy`), optional `prompt_text` and `prompt_blocks`
  - Provides full failure context for recorder, spectators, and replay to analyse instruction-following issues
  - Emitted before any policy action (skip/abort/forfeit/retry) is applied

**Prompt Metadata Fields** (included in COMPLETE/ABORT/CONCLUSION events):

All player lifecycle events include complete LLM dialogue metadata for reproducibility:

| Field | Type | Description |
|-------|------|-------------|
| `prompt_text` | str | Exact prompt string sent to LLM (after PromptBuilder composition) |
| `prompt_blocks` | List[Dict] | PromptBuilder metadata showing template composition and placeholder values |
| `response_text` | str | Raw LLM response text (before controller parsing) |
| `renderer_output` | Dict | RenderResult metadata from game view formatting |
| `controller_format` | str | Format instruction string shown to LLM |
| `controller_metadata` | Dict | Parsing/validation metadata from controller (success, retries, fallback info) |

These fields enable faithful match replay per SPEC-REPLAY and support A/B testing of prompt variations.

### 3.2 Structural Gameplay Event

- `EventType.GAMEPLAY` is the canonical mechanic-agnostic decision event.
- Emitted once per phase by the execution helper (e.g., TurnLoop).
- Payload shape is defined by [SPEC-GAMEPLAY-EVENT-DATA.md](SPEC-GAMEPLAY-EVENT-DATA.md).
- Games **never** emit `GAMEPLAY` directly; they rely on the mechanic helper.

Minimal shape:

```python
{
    "mechanic": "turn_based",
    "phase_index": 0,
    "state_before": {...},
    "state_after": {...},
    "player": "Alice",
    "action": {
        "value": "ATTACK",
        "reasoning": "...",
        "metadata": {...},
    },
    "interaction": {
        "prompt_text": "...",
        "prompt_blocks": [...],
        "response_text": "...",
        "usage_info": {...},
        "renderer_output": {...},
        "controller_format": "...",
        "controller_metadata": {...},
    },
    "turn_context": {...},
}
```

Structural gameplay events MUST NOT emit `turn_index`, `action.raw_response`, or top-level prompt transcript fields. Human-facing turn numbers belong in `turn_context`.

### 3.3 Domain Events

- Emitted through the `GameEventEmitter` helper (see §7).  
- Naming convention: `snake_case`, past-tense (e.g., `bid_placed`, `question_answered`).  
- Must be JSON-serializable.  
- Spectators subscribe by implementing `on_<event_name>(event)`.

---

## 4. Unified Event Object

All spectators receive a single `Event` object, which is replay/recording friendly.

```python
@dataclass
class Event:
    type: str               # e.g., "gameplay", "bid_placed", "match_start"
    data: Dict[str, Any]    # Structured payload (see tables above)
    context: EventContext   # Envelope metadata
```

### 4.1 EventContext Schema

`EventContext` (existing TypedDict) is extended to include phase metadata.

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | Optional[str] | Set when the console has session context. |
| `batch_id` | Optional[str] | Present between `BATCH_START`/`END`. |
| `match_id` | Optional[str] | Present between `MATCH_START`/`END`. |
| `phase_index` | Optional[int] | Zero-based; present during gameplay or domain events when known. |
| `timestamp` | float | Wall-clock time (`time.time()`), or preserved emission timestamp when supplied by upstream replay/worker context. |
| `monotonic_time` | float | Monotonic clock (`time.monotonic()`), or preserved emission monotonic value when supplied upstream. |

`phase_index` is the only structural phase key. `turn_index` is intentionally not part of the v2 event envelope.

---

## 5. Spectator Scopes

| Scope | How to attach | Events received | Typical use |
|-------|---------------|-----------------|-------------|
| **Session** | `AgentDeck(..., spectators=[...])` | All lifecycle events, all runs, all matches, structural gameplay, domain events. No need to re-attach per run. | Recorders, cost trackers, session-wide analytics. |
| **Execution** | `deck.play(..., spectators=[...])` or `deck.replay(...)` | `BATCH_*`, `MATCH_*`, `GAMEPLAY`, domain events for that execution only. | Per-run visualizers, ad-hoc analysis, replay tooling. |

Semantics are **additive**: active spectators = session defaults + execution extras. No implicit override, no dedupe.

---

## 6. Emission Responsibilities

| Layer | Responsibilities |
|-------|------------------|
| `AgentDeck` | Manage session lifecycle, spectator registration, seeding. |
| `Console` | Emit lifecycle events, manage RNG/match orchestration, bind helpers, ensure cleanup. |
| Execution flow (e.g., TurnLoop) | Emit `GAMEPLAY`, update phase index, call custom helper hooks. |
| `Game` | Implement rules. Use `self.emit_event(...)` for domain-specific signals. |

---

## 7. GameEventEmitter Helper

### 7.1 Contract

```python
class GameEventEmitter:
    """Injects structural context and forwards custom events to the EventBus."""

    def __init__(self, event_bus: EventBus, match_id: Optional[str]) -> None:
        """Initialize emitter with event bus and match identifier.

        Args:
            event_bus: EventBus to forward events through
            match_id: Optional match identifier to inject into event payloads
        """
        self._event_bus = event_bus
        self._match_id = match_id
        self._phase_index: Optional[int] = None

    def set_phase_index(self, phase_index: int) -> None:
        """Called by the execution helper before emitting events for that phase."""
        self._phase_index = phase_index

    def clear_phase_index(self) -> None:
        """Optional helper when a match ends."""
        self._phase_index = None

    def emit(self, event_type: str, **payload: Any) -> None:
        """Emit a domain event with automatically injected context.

        Automatically injects into the payload dict:
        - match_id (if set)
        - phase_index (if set)

        Games may override these by passing them explicitly in payload.
        """
        data: Dict[str, Any] = dict(payload)

        if self._match_id is not None:
            data.setdefault("match_id", self._match_id)

        if self._phase_index is not None:
            data.setdefault("phase_index", self._phase_index)

        self._event_bus.emit(event_type, **data)
```

Key points:

- Games never interact with `EventBus` directly.
- Constructor takes `match_id` directly (simpler than extracting from `MatchContext`).
- `phase_index` is injected into the payload dict when the execution layer has set it.
- `EventBus` adds the remaining envelope (`session_id`, `timestamp`, `monotonic_time`, batch context).
- Games may override auto-injected values by passing them explicitly in the payload.
- Helper is **bound per match** and cleared in a `finally` block (mirrors `event_factory` binding).

### 7.2 Game Convenience Wrapper

```python
class Game(ABC):
    def emit_event(self, event_type: str, **payload: Any) -> None:
        if self.event_emitter:
            self.event_emitter.emit(event_type, **payload)
```

This keeps game code to "one-line emissions."

---

## 8. EventFactory Helper

### 8.1 Contract

EventFactory provides structured event construction helpers for mechanics and games. `MatchRuntime.record_turn()` remains the canonical live GAMEPLAY emission path, while `EventFactory.turn()` mirrors that payload shape for direct construction and tests.

```python
class EventFactory:
    """Build canonical event payloads for recordings and spectators."""

    def __init__(self, match_id: str) -> None:
        """Initialize with match_id for event context.

        Args:
            match_id: Match identifier to inject into all events
        """
        self._match_id = match_id

    def turn(
        self,
        *,
        player: str,
        action: ActionResult,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        turn_context: TurnContext,
    ) -> Event:
        """Create the standardized GAMEPLAY event payload for a turn.

        Args:
            player: Player who acted
            action: ActionResult from player.decide()
            state_before: Game state before action (will be deep-copied)
            state_after: Game state after action (will be deep-copied)
            turn_context: Turn metadata (turn_number, phase_index, duration, rng)

        Returns:
            Event with GameplayEventData v2 (SPEC-GAMEPLAY-EVENT-DATA.md):
                action.value + action.reasoning + action.metadata
                interaction.prompt_text + interaction.response_text + usage/cost metadata
                state_before + state_after + turn_context

        Guarantees:
            - Emits the canonical v2 payload used by live turn recording
            - Deep copies state_before and state_after (SPEC-GAME-MECHANIC-TURN-BASED EC1)
            - Deep copies action metadata and interaction metadata to prevent mutations
            - Sets mechanic="turn_based" (SPEC-GAME-MECHANIC-TURN-BASED EC2)
            - Sets phase_index = turn_context.phase_index (SPEC-GAME-MECHANIC-TURN-BASED EC3)
        """
        metadata = copy.deepcopy(action.metadata) if hasattr(action, "metadata") else {}
        return Event(
            type="gameplay",
            data={
                "match_id": self._match_id,
                "mechanic": "turn_based",
                "phase_index": turn_context.phase_index,
                "player": player,
                "action": {
                    "value": action.action,
                    "reasoning": action.reasoning if hasattr(action, 'reasoning') else None,
                    "metadata": metadata,
                },
                "interaction": {
                    "prompt_text": metadata.get("prompt_text"),
                    "prompt_blocks": metadata.get("prompt_blocks", []),
                    "response_text": metadata.get("response_text") or getattr(action, "raw_response", None),
                    "usage_info": metadata.get("usage_info"),
                    "renderer_output": metadata.get("renderer_output"),
                    "controller_format": metadata.get("controller_format"),
                    "controller_metadata": metadata.get("controller_metadata"),
                },
                "state_before": copy.deepcopy(state_before),
                "state_after": copy.deepcopy(state_after),
                "turn_context": turn_context.to_dict() if hasattr(turn_context, 'to_dict') else {},
            },
            context={
                "match_id": self._match_id,
                "phase_index": turn_context.phase_index,
            }
        )

    def custom(
        self,
        event_type: str,
        payload: Dict[str, Any],
        *,
        turn_context: Optional[TurnContext] = None,
    ) -> Event:
        """Attach shared metadata to arbitrary game events.

        Args:
            event_type: Custom event type (e.g., "card_drawn")
            payload: Event-specific data
            turn_context: Optional turn context for phase_index

        Returns:
            Event with type=event_type, data=payload+metadata, context

        Guarantees:
            - Injects match_id into data
            - Injects phase_index if turn_context provided (SPEC-GAME-MECHANIC-TURN-BASED EC4)
            - Preserves all payload fields
        """
        data = copy.deepcopy(payload)
        data.setdefault("match_id", self._match_id)

        context = {"match_id": self._match_id}

        if turn_context:
            phase_index = turn_context.phase_index
            data.setdefault("phase_index", phase_index)
            context["phase_index"] = phase_index

        return Event(type=event_type, data=data, context=context)
```

### 8.2 TurnLoop Integration

EventFactory is bound to TurnLoop per match (see SPEC-GAME-MECHANIC-TURN-BASED §4.1):

```python
# Console creates TurnLoop with match context
turn_loop = TurnLoop(game, console, players, match_context)

# TurnLoop records gameplay through the runtime helper
self.runtime.record_turn(
    player=current_player_name,
    state_before=adapter.before,
    state_after=final_state,
    action=action,
    turn_context=turn_context,
)

# Games use event_factory.custom() when they need prebuilt domain Event objects
custom_events = game.get_events(state_before, player, action)
for event in custom_events:
    runtime.emit_event(event.type, **event.data)
```

### 8.3 Design Rationale

- **Canonical Live Path**: `MatchRuntime.record_turn()` owns live GAMEPLAY emission so recorder, replay, and observers see one consistent payload shape.
- **Structured Helper Surface**: EventFactory still provides reusable helpers for direct event construction and custom-domain events.
- **Mutation Prevention**: Deep-copying states and metadata prevents spectator mutations from corrupting recordings (SPEC-GAME-MECHANIC-TURN-BASED EC1)
- **Metadata Injection**: Automatically injects match_id and phase_index, reducing boilerplate for direct event construction

---

## 9. Event Payload Guidelines

### 9.1 Lifecycle Events (framework-owned)

| Field | Type | Required | Event | Notes |
|-------|------|----------|-------|-------|
| `session_id` | str | ✓ | SESSION_START, SESSION_END | Unique session identifier. |
| `seed` | int | ✓ | SESSION_START | Session-level base seed (always non-null after resolution). |
| `batch_id` | str | ✓ | BATCH_START, BATCH_END | Unique batch identifier. |
| `matches` | int | ✓ | BATCH_START | Number of matches in batch. |
| `seeds_used` | List[int] | ✓ | BATCH_END | Per-match seeds executed in this batch (for traceability). |
| `match_id` | str | ✓ | MATCH_START, MATCH_END | Unique match identifier. |
| `seed` | int | ✓ | MATCH_START, MATCH_END | Per-match seed used for this specific match. |
| `player_names` | List[str] | ✓ | MATCH_START, MATCH_END | Ordered player list (post-ordering, may be shuffled by Console or game). |
| `player_order` | List[int] | ✓ | MATCH_START, MATCH_END | Original indices showing pre-ordering positions (e.g., [1, 0] means original player 1 is first in ordered list). |
| `player_order_source` | str | ✓ | MATCH_START, MATCH_END | Source of ordering decision: "console" (Fisher-Yates shuffle) or "game" (custom override). |
| `first_player` | Dict[str, Any] | ✓ | MATCH_START, MATCH_END | First-acting player metadata: {"name": str, "index": int} where index is original position (falls back to first ordered player when runtime selection is unavailable). |
| `result` | MatchResult | ✓ | MATCH_END | Complete match result with metadata. |
| `player` | str | ✓ | PLAYER_HANDSHAKE_*, PLAYER_CONCLUSION | Player name for lifecycle events. |
| `prompt_text` | str | ✓ | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT, PLAYER_CONCLUSION, PLAYER_ACTION_PARSE_FAILED* | Raw prompt sent to LLM (when provided). |
| `prompt_blocks` | List[Dict] | ✓ | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT, PLAYER_CONCLUSION, PLAYER_ACTION_PARSE_FAILED* | PromptBuilder metadata. |
| `response_text` | str | ✓ | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT, PLAYER_CONCLUSION | Raw LLM response. |
| `renderer_output` | Dict | Optional | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT, PLAYER_CONCLUSION | RenderResult metadata. |
| `controller_format` | str | ✓ | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT | Format instruction for handshake. |
| `controller_metadata` | Dict | ✓ | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT | Parsing/validation metadata. |
| `normalized_response` | str | ✓ | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT | Parsed acknowledgement. |
| `accepted` | bool | ✓ | PLAYER_HANDSHAKE_COMPLETE, PLAYER_HANDSHAKE_ABORT | True if accepted, False if rejected. |
| `reason` | str | Optional | PLAYER_HANDSHAKE_ABORT | Rejection explanation. |
| `reflection_text` | str | ✓ | PLAYER_CONCLUSION | Post-match reflection response. |
| `outcome` | str | ✓ | PLAYER_CONCLUSION | Match result summary. |
| `parse_result` | Dict | ✓ | PLAYER_ACTION_PARSE_FAILED | Serialized `ParseResult` (success flag, error text, candidates, metadata). |
| `policy_outcome` | str | ✓ | PLAYER_ACTION_PARSE_FAILED | Value from `ParseFailurePolicy` (abort/skip/forfeit/retry). |
| `raw_response` | str | ✓ | PLAYER_ACTION_PARSE_FAILED | Raw LLM response that failed parsing. |

*For `PLAYER_ACTION_PARSE_FAILED`, `prompt_text`/`prompt_blocks` are optional but recommended so recorder/replay tooling can reconstruct full inputs.

**Seed Traceability**: All lifecycle events include seed metadata for complete reproducibility:
- `SESSION_START`: session-level base seed
- `BATCH_START`: references session seed (available in context)
- `MATCH_START`: per-match derived seed (before game execution)
- `MATCH_END`: same per-match seed (for correlation)
- `BATCH_END`: complete list of seeds_used across all matches

**Player Order Recording**: MATCH_START and MATCH_END include complete player ordering metadata for mechanics-agnostic tracking and research analysis:
- `player_names` (List[str]): Ordered list post-ordering (post-shuffle or post-game override)
- `player_order` (List[int]): Original indices showing pre-ordering positions (e.g., [1, 0] means original player at index 1 is first in ordered list)
- `player_order_source` (Literal["console", "game"]): Indicates whether Console applied Fisher-Yates shuffle ("console") or game provided custom ordering ("game")
- `first_player` (Dict): First-acting player metadata with {"name": str, "index": int} where index is original position; falls back to first ordered player when no runtime first-player signal exists

Console records ordering metadata and, when available, runtime-selected first-actor metadata. Research utilities can use `player_order_source` to distinguish console randomization from game-controlled ordering.

**MatchResult.metadata Schema**: The `result` field in MATCH_END events carries a `MatchResult` payload with standardized metadata structure (per SPEC-CONSOLE M1-M4):

```python
{
    "game": str,                        # Game class name (e.g., "FixedDamageGame")
    "players": List[str],               # Player names (ordered, same as player_names)
    "player_names": List[str],          # Ordered player names (post-ordering)
    "player_order": List[int],          # Original indices (e.g., [1, 0])
    "player_order_source": str,         # "console" or "game"
    "first_player": {                   # First player metadata
        "name": str,                    #   Player name
        "index": int                    #   Original position
    },
    "duration": float,                  # Match duration in seconds
    "handshake_completed": bool,        # Whether handshake phase succeeded
    "seed": int,                        # Per-match seed
    "batch_id": str,                    # Batch identifier
    "truncated_by_max_turns": bool,     # Whether match hit max_turns limit
    "turns": int,                       # Number of turns executed
    # Additional game-specific metadata may be present
}
```

This schema is consistent across MatchResult objects, MATCH_END events, and recorder files.

### 9.2 Structural Gameplay (framework-owned)

`SPEC-GAMEPLAY-EVENT-DATA.md` is authoritative. This table is a navigation summary.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `mechanic` | str | ✓ | `"turn_based"`, `"simultaneous"`, `"quiz"`, etc. |
| `phase_index` | int | ✓ | Zero-based canonical counter. |
| `state_before` | Dict | ✓ | Deep copy for replay. |
| `state_after` | Dict | ✓ | Deep copy for replay. |
| `player` | str | Optional | Present in sequential mechanics. |
| `action` | Dict | ✓ | Canonical action object with `value`, `reasoning`, and `metadata`. |
| `interaction` | Dict | ✓ | Prompt, response, usage, renderer, and controller metadata. |
| `turn_context` / `round_context` | Dict | Optional | Mechanic-specific context dictionaries. |

### 9.3 Domain Events (game-owned)

- Payload is defined by the game; must be JSON-serializable.  
- Framework automatically appends envelope metadata (`event.context`).  
- Recommended naming: snake_case, past-tense verbs (`question_answered`, `card_drawn`).  
- If a game needs the current phase, rely on the auto-injected `phase_index` or add human-readable fields (`question_number`) explicitly.

---

## 9. API Usage

### 9.1 Game author

```python
class AuctionGame(TurnBasedGame):
    def setup(self, players: list[str]) -> dict[str, Any]:
        return {"bids": {p: 0 for p in players}, "leader": None}

    def update(self, state, player, action, *, rng):
        bid = int(action.action)  # Game update receives ActionResult; GAMEPLAY events serialize this as action.value.
        previous = state["leader"]
        state["bids"][player] = bid
        if previous is None or bid > state["bids"][previous]:
            state["leader"] = player

        self.emit_event(
            "bid_placed",
            player=player,
            bid=bid,
            previous_leader=previous,
            is_leading=(state["leader"] == player),
        )
        return state
```

### 9.2 Spectator author

```python
class BidTracker:
    def on_bid_placed(self, event: Event) -> None:
        data = event.data
        ctx = event.context
        leader = "None" if data["previous_leader"] is None else data["previous_leader"]
        print(f"[{ctx['match_id']} | phase {ctx['phase_index']}] "
              f"{data['player']} bid {data['bid']} (prev leader: {leader})")

    def on_gameplay(self, event: Event) -> None:
        if event.data.get("mechanic") == "turn_based":
            print(f"Phase {event.context['phase_index']} completed.")
```

In every handler, `event.type` identifies the event, `event.context` provides envelope metadata, and `event.data` contains payload.

---

## 10. Spectator Guidelines

### Handler Signatures

**Preferred:** Accept a single `Event` object for new spectators:

```python
def on_gameplay(self, event: Event) -> None:
    player = event.data["player"]
    phase = event.context["phase_index"]
```

**Alternative style:** The EventBus also routes to kwargs handlers:

```python
def on_gameplay(self, **kwargs) -> None:
    player = kwargs["player"]
    phase = kwargs["context"]["phase_index"]
```

Both styles work identically. The EventBus automatically detects the signature via introspection. Use `Event` objects for new code as they provide better type safety and consistency with recording/replay.

### Best Practices

- Treat `event.data` as read-only.
- Use `event.context` for structural metadata (session, match, phase, timestamps).
- When targeting specific mechanics, check `event.data["mechanic"]`.
- Use session scope for long-lived analytics; use execution scope for ad-hoc tools.
- Custom events should use snake_case, past-tense names; spectators implement `on_<name>`.

### Logger Injection

Per `SPEC-SPECTATOR.md` §5.5 (LI1-LI5), Console and ReplayEngine automatically inject logger into spectators:

- Console/ReplayEngine inject `spectator.logger = self.logger` before EventBus subscription if `spectator.logger is None`
- Spectators can use `self.logger.info()`, `self.logger.debug()`, etc. to write to core log streams (info.log, debug.log, console)
- Spectators may provide custom logger via constructor (bypasses injection)
- This enables INFO-level match narratives and structured logging without explicit configuration

See SPEC-SPECTATOR §5.5 and SPEC-CONSOLE §6.8 P4 for complete logger injection contract.

---

## 11. Replay & Recording

- Recorder serializes the event stream as canonical event payloads.
- `GAMEPLAY` data MUST follow `SPEC-GAMEPLAY-EVENT-DATA.md` and be written by Recorder v2.0 without structural reshaping.
- Domain payloads **must** be JSON-serializable.
- Replay rehydrates `EventContext` faithfully and replays events in order.
- `ReplayEngine` emits the same event payloads observers would receive live.
- Custom events need no special handling; they flow through the recorder identically.

---

## 12. Design Rationale

| Decision | Rationale |
|----------|-----------|
| **Single `Event` argument** | Simplifies spectator APIs, improves validation, works better for replay tooling, avoids signature churn. |
| **Zero-based `phase_index`** | Matches programming conventions; human-friendly counters remain in payload (`turn_context["turn_number"]`). |
| **Auto-injected envelope** | Games stay focused on domain logic—no need to recreate session/match context. |
| **String event types** | Keeps duck-typing ergonomic (`on_bid_placed`). Enums remain for framework events. |
| **Snake_case recommendation** | Aligns with Python style while keeping flexibility. |
| **Player ordering metadata** | Recording `player_order_source` enables research analysis to distinguish console fairness randomization from game-controlled ordering (auction winners, asymmetric roles). Explicit `first_player` field simplifies common queries without reconstructing from indices. |

---

## 13. Implementation Phases

The observability system was implemented across seven phases:

1. **Event Dataclass & EventBus** - Unified Event object with context envelope
2. **GameEventEmitter & Game API** - Domain event emission with auto-injection
3. **TURN → GAMEPLAY Rename** - Mechanic-agnostic gameplay events
4. **Built-in Spectators** - Event object signature for Recorder and StatsTracker
5. **Examples & Documentation** - AuctionGame, BidAnalyzer, and guides
6. **Integration Testing** - Replay parity verification
7. **Cleanup & Documentation** - Final polish and migration guide

Implementation history is preserved in git; this spec is the current contract.

---

## 14. Examples

### 14.1 Minimal domain event flow

```python
with AgentDeck(game=AuctionGame(), spectators=[SessionStats()]) as deck:
    # Session spectators always active (recording, stats)
    deck.play(players=[alice, bob], matches=3)  # no extra spectators

    visualizer = AuctionVisualizer()
    deck.play(players=[alice, bob], matches=1, spectators=[visualizer])
```

### 14.2 Multi-level analytics (session + execution)

```python
session_spectators = [SessionStatsAggregator(), DecisionHighlightCollector()]
deck = AgentDeck(game=FixedDamageGame(), spectators=session_spectators)

match_spectators = [MatchStatsTracker(), TurnHighlightSpectator(), ASCIIVisualizer()]

deck.play(players=[alice, bob], matches=5, spectators=match_spectators)
# Session spectators accumulate across runs; execution spectators apply only once.
```

### 14.3 Player lifecycle event handlers

```python
class LifecycleTracker:
    """Track three-phase player lifecycle: handshake → turn → conclusion."""

    def on_player_handshake_start(self, event: Event) -> None:
        """Emitted when handshake begins for a player."""
        print(f"[HANDSHAKE START] {event.data['player']} in {event.data['match_id']}")

    def on_player_handshake_complete(self, event: Event) -> None:
        """Emitted when player acknowledges successfully."""
        data = event.data
        print(f"[HANDSHAKE OK] {data['player']}: {data['normalized_response']}")
        print(f"  Prompt length: {len(data['prompt_text'])} chars")
        print(f"  Prompt blocks: {len(data['prompt_blocks'])} placeholders")

    def on_player_handshake_abort(self, event: Event) -> None:
        """Emitted when player rejects handshake."""
        data = event.data
        print(f"[HANDSHAKE ABORT] {data['player']}: {data['reason']}")
        print(f"  Response: {data['normalized_response']}")

    def on_player_conclusion(self, event: Event) -> None:
        """Emitted when player completes post-match reflection."""
        data = event.data
        print(f"[CONCLUSION] {data['player']} reflects on {data['outcome']}")
        print(f"  {data['reflection_text']}")

# Use with AgentDeck
deck = AgentDeck(game=MyGame(), spectators=[LifecycleTracker()])
deck.play(players=[alice, bob])
```

### 14.4 Prompt metadata analysis

```python
class PromptAnalyzer:
    """Analyze LLM prompts and responses across all lifecycle phases."""

    def __init__(self):
        self.prompt_log = []

    def _capture_prompt(self, event: Event, phase: str) -> None:
        """Extract prompt metadata from any player lifecycle event."""
        data = event.data
        self.prompt_log.append({
            "phase": phase,
            "player": data["player"],
            "match_id": data.get("match_id"),
            "prompt_text": data.get("prompt_text"),
            "prompt_blocks": data.get("prompt_blocks"),
            "response_text": data.get("response_text"),
            "renderer_output": data.get("renderer_output"),
            "controller_format": data.get("controller_format"),
            "controller_metadata": data.get("controller_metadata"),
        })

    def on_player_handshake_complete(self, event: Event) -> None:
        self._capture_prompt(event, "handshake")

    def on_player_handshake_abort(self, event: Event) -> None:
        self._capture_prompt(event, "handshake_abort")

    def on_player_conclusion(self, event: Event) -> None:
        self._capture_prompt(event, "conclusion")

    def analyze(self):
        """Compute stats on prompts across all phases."""
        total_prompts = len(self.prompt_log)
        avg_prompt_length = sum(len(d["prompt_text"]) for d in self.prompt_log if d["prompt_text"]) / total_prompts
        phases = {d["phase"] for d in self.prompt_log}
        return {
            "total_prompts": total_prompts,
            "avg_prompt_length": avg_prompt_length,
            "phases_captured": list(phases),
        }
```

---

## 15. Testing Strategy

| Area | Tests |
|------|-------|
| **EventBus** | Accepts `EventType` & `str`; constructs `Event`; routes to handlers; handles subscription churn. |
| **GameEventEmitter** | Injects match context; sets/clears phase index; refuses to emit when unbound. |
| **Execution helpers** | `TurnLoop` sets phase index correctly; emits `GAMEPLAY` with zero-based counter; binds/unbinds helpers in `finally`. |
| **Player Lifecycle Events** | Emits `PLAYER_HANDSHAKE_START` → `PLAYER_HANDSHAKE_COMPLETE|ABORT` before first turn; emits `PLAYER_ACTION_PARSE_FAILED` on parsing failures; emits `PLAYER_CONCLUSION` before `MATCH_END` when enabled; includes full prompt metadata and failure diagnostics. |
| **Recorder/Replay** | Round-trip structural + domain events; ensure replay emits the same canonical payloads live spectators received; verify interaction/prompt metadata preserved. |
| **Spectators** | Example spectators receive both structural and domain events; `event.context` contains expected metadata; JSON serialization validated. |

Automated tests should cover:

- Multiple custom events per phase; correct `phase_index`.
- Spectator errors (ensure logging via `EventBus`).
- Missing JSON serialization raises early (e.g., by validating in recorder).
- Replay integrity: recorded stream matches live stream with deep structural comparison of `GAMEPLAY` data.
- **Handshake phase**: Verify `PLAYER_HANDSHAKE_START` emitted before `PLAYER_HANDSHAKE_COMPLETE|ABORT`; verify prompt metadata fields (`prompt_text`, `prompt_blocks`, `response_text`, `renderer_output`, `controller_format`, `controller_metadata`) present in COMPLETE/ABORT events.
- **Parse failure phase**: Validate `PLAYER_ACTION_PARSE_FAILED` is emitted before policy resolution, includes serialized ParseResult, policy outcome, and optional prompt snapshot.
- **Conclusion phase**: Verify `PLAYER_CONCLUSION` emitted for policy-selected players (even if reflection is empty); verify prompt metadata present.
- **Prompt metadata integrity**: Verify `prompt_blocks` accurately represents PromptBuilder composition; verify `renderer_output` includes RenderResult metadata when applicable.
- **Player ordering metadata**: Verify `MATCH_START` and `MATCH_END` include `player_order`, `player_order_source`, `first_player` fields; verify same seed produces identical player_order; verify metadata schema consistency across events and MatchResult.metadata.

---

## 16. Resolved Decisions

| Topic | Decision |
|-------|----------|
| Spectator handler signature | Single `Event` object. |
| Domain event emission | Use `GameEventEmitter`; auto-inject match + phase context. |
| Phase index base | Zero-based canonical `phase_index`; human-readable counters remain in payload. |
| Event naming | Recommend snake_case, past-tense (documented, not enforced). |
| EventBus API | Accept `EventType` enums and raw string types; construct `Event` objects for handlers. |

---

## 17. References

- `SPEC.md` — Vision, architecture overview, success criteria.
- `CONTRIBUTING.md` — Engineering philosophy and workflow guidelines.
- `SPEC-GAMEPLAY-EVENT-DATA.md` — Canonical structural gameplay payload.
- `SPEC-GAME-MECHANIC-TURN-BASED.md` — TurnLoop orchestration, EventFactory integration, StateAdapter, parse failure propagation.
- `SPEC-CONSOLE.md` — Match orchestration, lifecycle event emission, parse failure handling, logger injection.
- `SPEC-SPECTATOR.md` — Spectator contract, logger injection, error isolation.
- `SPEC-GAME.md` — Game base classes, domain event emission via GameEventEmitter, parse-failure policy hook.
- `src/agentdeck/core/event_bus.py` — EventBus implementation.
- `src/agentdeck/core/turn_loop.py` — TurnLoop execution helper with EventFactory.
- `src/agentdeck/core/event_factory.py` — EventFactory for standardized GAMEPLAY events.
- `src/agentdeck/core/base/game.py` — Game base classes (`Game`, `TurnBasedGame`, etc.).
- `replay_recent_match.py` / `replay.py` — Replay scripts (will adopt new event model).

---

**Ready for implementation.**  
This specification supersedes previous drafts and should be kept in sync with the codebase as the source of truth for event emission and observability.
