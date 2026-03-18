# SPEC-MATCH-RUNTIME: Match Infrastructure Context

> Status: Final
> Version: 1.0.0
> Last Updated: 2026-03-17
> Implementation: ✅ Complete (Phase 6-8 compliance verified)
> Authors: Codex, Diego Zoracky, Claude
> Audience: Core contributors, mechanic authors, researchers extending execution loops

## 1. Purpose
- Define the `MatchRuntime` object that the console passes to `game.run(runtime, players)` so mechanics can use all console facilities without duplicating orchestration logic.
- Guarantee consistent routing of events, recorder writes, RNG usage, cost tracking, and parse-failure handling across every mechanic (turn-based, simultaneous, real-time).
- Provide a single surface that future cross-cutting features (checkpoint/resume, advanced monitors) can hook into without modifying mechanics.

## 2. Scope & Philosophy Alignment
- Extends the spec-driven workflow described in `CONTRIBUTING.md`: all mechanics consume the same runtime contract.  
- Complements `SPEC-GAME.md` (game responsibilities) and `SPEC-CONSOLE.md` (orchestration) by defining the glue between them.  
- Non-goals: Recorder schema (`SPEC-RECORDER.md`), event payload definitions (`SPEC-OBSERVABILITY.md`), controller behaviour (`SPEC-CONTROLLER.md`).

## 3. Responsibilities
- Encapsulate per-match state (session_id, batch_id, match_id, seed, RNG) and expose deterministic RNG forks.
- Emit lifecycle + gameplay events on behalf of mechanics, ensuring spectators/recorders receive consistent metadata.
- Collect prompt/response/action metadata for recorder and cost tracking.
- Execute parse-failure policies defined by games (`game.on_action_parse_failure`) and controllers.
- Provide helpers for validation, logging, and future features (checkpointing, metrics).

## 4. Public API

```python
class MatchRuntime:
    def __init__(
        self,
        *,
        console: Console,
        game: Game,
        match_id: str,
        session_id: str,
        batch_id: str,
        seed: int,
        max_turns: int,
        recorder: Recorder,
        logger: AgentDeckLogger,
        rng: RandomGenerator,
        previous_match_result: Optional[MatchResult] = None,
        events_list: Optional[list[Event]] = None,
        initial_state: Optional[dict[str, Any]] = None,
    ): ...

    @property
    def match_id(self) -> str: ...
    @property
    def session_id(self) -> str: ...
    @property
    def batch_id(self) -> str: ...
    @property
    def seed(self) -> int: ...
    @property
    def max_turns(self) -> int: ...
    @property
    def previous_match_result(self) -> Optional[MatchResult]: ...
    @property
    def events(self) -> list[Event]: ...
    @property
    def initial_state(self) -> Optional[dict[str, Any]]: ...
    @initial_state.setter
    def initial_state(self, state: Optional[dict[str, Any]]) -> None: ...

    def emit_event(self, event_type: str, /, **data) -> None: ...
    def record_turn(
        self,
        *,
        player: str,
        state_before: dict[str, Any],
        state_after: dict[str, Any],
        action: ActionResult,
        turn_context: TurnContext,
        prompt_blocks: Optional[list[PromptBlock]] = None,
    ) -> None: ...
    def handle_parse_failure(self, player: Player, error: ActionParseError, *, turn_context: TurnContext) -> ParseFailurePolicy: ...
    def fork_rng(self, label: str) -> RandomGenerator: ...
    def validate_state(self, state: dict[str, Any]) -> None: ...
    def log(self, message: str, level: LogLevel = LogLevel.INFO, **extra) -> None: ...
    def checkpoint(self, state: dict[str, Any]) -> None: ...
```

### 4.1 Constructor
- Console creates a new runtime per match.  
- MUST be immutable from mechanic perspective apart from the explicit `initial_state` handoff used between handshake and mechanic execution.  
- MUST capture:
  - flattened match metadata (`session_id`, `batch_id`, `match_id`, `seed`, `max_turns`, `previous_match_result`) rather than a single `MatchContext` wrapper.  
  - `recorder`, `logger`, `rng`, and a reference back to the console for EventBus routing / parse-failure handling. Mechanics never touch EventBus directly—runtime forwards everything via console.
  - optional `events_list` for replay parity and optional `initial_state` when Console has already executed setup + handshake before calling `game.run(...)`.

### 4.2 `emit_event`
- Wraps console `_emit_event` with pre-populated context (session_id/batch_id/match_id, timestamps, mechanic info).  
- Mechanics MUST use `emit_event` for all GAMEPLAY + custom events; direct EventBus usage is prohibited.  
- Automatically enforces `SPEC-OBSERVABILITY` payload requirements (phase_index, mechanic name, etc.).

### 4.3 `record_turn`
- Builds the canonical `EventType.GAMEPLAY` payload (per `SPEC-OBSERVABILITY` + PM1–PM6 requirements) and emits it through the runtime’s event bus.  
- Ensures JSON-serialisability and guarantees that Recorder/spectators receive the full prompt/response/action transcript via events (aligned with `SPEC-RECORDER v1.3.0`).  
- Mechanics MUST call this whenever an LLM player produces a response that leads to an action (even if the action later fails validation or gets skipped).  
- `TurnContext` contains `turn_number`, `player_name`, `phase_index`, `rng_label`, `started_at`, `duration`, `match_id` (see `SPEC-GAME-MECHANIC-TURN-BASED.md` §4.2). Mechanics supply the context; runtime includes it in the emitted event for downstream consumers.
- `state_before` and `state_after` are the canonical state snapshots associated with the action. `response_text` is derived from `action.raw_response`; prompt metadata is derived from `action.metadata` plus any explicit `prompt_blocks`.

### 4.4 `handle_parse_failure`
- Invokes the shared parse-failure policy pipeline (events, recorder, logging, `game.on_action_parse_failure`).  
- Returns a `ParseFailurePolicy` enum so the mechanic can decide whether to retry, skip, forfeit, or abort.  
- Mechanics MUST use the runtime helper rather than reaching into console internals themselves. Runtime may delegate to an internal console helper as part of that implementation.

### 4.5 `fork_rng`
- Returns a deterministic RNG fork (child of match RNG) tagged by label for debugging.  
- Mechanics MUST call `fork_rng` whenever randomness is required (setup, per-turn, tie-breakers).  
- Ensures reproducibility across sequential and parallel runs (SPEC-PARALLEL).

### 4.6 `validate_state`
- Calls `game.validate_state` when provided; raises `ValueError` on failure and logs context.  
- Mechanics SHOULD call after setup and each update; runtime may enforce periodic validation (configurable via console).

### 4.7 `log`
- Writes structured log entries and emits `LOG` events.  
- Mechanics MAY attach `player`, `turn_number`, or custom fields (e.g., phase, outcome).

### 4.8 `checkpoint`
- Hook for future checkpoint/resume.  
- Currently a no-op; mechanics MAY call without worrying about implementation details.  
- Console can override to persist state snapshots for long-running experiments (runtime automatically forwards to console helper).

## 5. Invariants & Guarantees
1. **Runtime Isolation (MR1)**: One runtime per match. No shared mutable state across matches or workers.
2. **Recorder Consistency (MR2)**: `record_turn` emits `GAMEPLAY` events in execution order so Recorder captures an ordered transcript directly from the event stream.
3. **Parse Failure Integrity (MR3)**: `handle_parse_failure` MUST emit `PLAYER_ACTION_PARSE_FAILED`, log warning, update recorder, and return a policy outcome.
4. **RNG Traceability (MR4)**: Every RNG fork label is recorded in debug logs so researchers can trace randomness sources.

> **Note**: Event ordering (lifecycle ordering, mechanic metadata injection) and exception-safety bindings are handled by mechanics (e.g., TurnLoop) rather than enforced by MatchRuntime. Backward compatibility is a versioning policy, not a runtime invariant.

## 6. Usage Pattern
```python
# Console._play_match (simplified)
runtime = MatchRuntime(
    console=self,
    game=game,
    match_id=match_id,
    session_id=session_id,
    batch_id=batch_id,
    seed=match_seed,
    max_turns=max_turns,
    recorder=self.recorder,
    logger=self.logger,
    rng=match_rng,
    previous_match_result=previous_match_result,
    events_list=events,
    initial_state=handshake_state,
)
final_state, mechanic_events, truncated = game.run(runtime, ordered_players)
```

1. Console handles session + batch lifecycle.  
2. Console constructs `MatchRuntime(...)` per match (as above).  
3. Console calls `game.run(runtime, players)`; runtime becomes the sole interface for events/recorder/RNG.  
4. Mechanic (TurnLoop or custom) uses runtime to emit events, record turns, handle failures, fork RNG, etc.  
5. Console wraps the returned `(final_state, events, truncated)` into `MatchResult` and finishes batch.

## 7. References
- `SPEC-GAME.md` – `run(runtime, players)` contract and parse-failure policies.  
- `SPEC-GAME-MECHANIC-TURN-BASED.md` – Default mechanic implementation using runtime.  
- `SPEC-CONSOLE.md` – Lifecycle orchestration and runtime creation.  
- `SPEC-RECORDER.md` – Dialogue array format used by `record_turn`.  
- `SPEC-OBSERVABILITY.md` – Event payload schema enforced by `emit_event`.  
- `SPEC-PARALLEL.md` – Seed derivation and RNG requirements satisfied by `fork_rng`.
