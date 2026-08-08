# SPEC-MATCH-RUNTIME: Match Infrastructure Context

> Status: Final
> Version: 1.3.0
> Last Updated: 2026-08-07
> Implementation: Complete
> Review State: Consensus-approved
> Audience: Core contributors, mechanic authors, researchers extending execution loops

## 1. Purpose
- Define the `MatchRuntime` object that the console passes to `game.run(runtime, players)` so mechanics can use all console facilities without duplicating orchestration logic.
- Guarantee consistent routing of events, recorder writes, RNG usage, cost tracking, and parse-failure handling across every mechanic (turn-based, simultaneous, real-time).
- Provide a single surface that future cross-cutting features (checkpoint/resume, advanced monitors) can hook into without modifying mechanics.

## 2. Scope & Philosophy Alignment
- Extends the spec-driven workflow described in `CONTRIBUTING.md`: all mechanics consume the same runtime contract.  
- Complements `SPEC-GAME.md` (game responsibilities) and `SPEC-CONSOLE.md` (orchestration) by defining the glue between them.  
- Non-goals: Recorder schema (`SPEC-RECORDER.md`), canonical gameplay payload definitions (`SPEC-GAMEPLAY-EVENT-DATA.md`), controller behaviour (`SPEC-CONTROLLER.md`).

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
    def create_game_event_emitter(self) -> GameEventEmitter: ...
    def set_first_player(self, *, name: str, index: int) -> None: ...
    def get_player_action(
        self,
        player_view: dict[str, Any],
        player: Player,
        *,
        turn_context: TurnContext,
        extras: Optional[dict[str, Any]] = None,
    ) -> ActionResult: ...
    def log_turn(
        self,
        *,
        turn_number: int,
        player: str,
        action: Any,
        reasoning: Optional[str],
        state_before: dict[str, Any],
        state_after: dict[str, Any],
        duration: float,
        usage_info: Optional[dict[str, Any]] = None,
    ) -> None: ...
    def warn(self, message: str) -> None: ...
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
- Wraps console `_dispatch_event` when available, otherwise falls back to direct `EventBus` emission, with pre-populated context (session_id/batch_id/match_id, timestamps, mechanic info).  
- Mechanics MUST use `emit_event` for all GAMEPLAY + custom events; direct EventBus usage is prohibited.  
- Automatically enforces `SPEC-OBSERVABILITY` payload requirements (phase_index, mechanic name, etc.).

### 4.3 `record_turn`
- Builds the canonical `EventType.GAMEPLAY` payload by delegating to the shared builder defined in `SPEC-GAMEPLAY-EVENT-DATA.md`, then emits it through the runtime’s event bus.
- Ensures JSON-serialisability and guarantees that Recorder/spectators receive the full action + interaction transcript via events (aligned with `SPEC-RECORDER v2.0.0`).
- Mechanics MUST call this whenever an LLM player produces a response that leads to an action (even if the action later fails validation or gets skipped).  
- `TurnContext` contains `turn_number`, `player_name`, `phase_index`, `rng_label`, `started_at`, `duration`, `match_id` (see `SPEC-GAME-MECHANIC-TURN-BASED.md` §4.2). Mechanics supply the context; runtime includes it in the emitted event for downstream consumers.
- `state_before` and `state_after` are the canonical state snapshots associated with the action. The parsed decision is serialized as `action.value`; raw model output is serialized once as `interaction.response_text`.
- `record_turn` MUST NOT hand-build a second gameplay payload shape. One builder owns live, recorded, and replayed `GAMEPLAY` data.

### 4.4 `handle_parse_failure`
- Invokes the shared parse-failure policy pipeline (events, recorder, logging, `game.on_action_parse_failure`).  
- Returns a `ParseFailurePolicy` enum so the mechanic can decide whether to retry, skip, forfeit, or abort.  
- Mechanics MUST use the runtime helper rather than reaching into console internals themselves. Runtime may delegate to an internal console helper as part of that implementation.

### 4.5 `fork_rng`
- Returns a deterministic RNG fork (child of match RNG) tagged by label for debugging.  
- Mechanics MUST call `fork_rng` whenever randomness is required (setup, per-turn, tie-breakers).  
- Ensures reproducibility across sequential and parallel runs (SPEC-PARALLEL).

### 4.5.1 Mechanic infrastructure helpers

- `create_game_event_emitter` returns a match-scoped emitter for Game hooks without
  exposing the Console EventBus.
- `set_first_player` records the resolved first Player for canonical match metadata.
- `get_player_action` invokes the configured Player and the shared parse-failure policy.
- `log_turn` writes the canonical structured turn log when logging is configured.
- `warn` records a mechanic-authoring warning when logging is configured.
- Stock mechanics MUST use these public helpers and MUST NOT read or mutate
  `runtime._console` or any other private runtime attribute.

### 4.6 `validate_state`
- Requires a dict, verifies strict JSON serialisability without fallback coercion, then
  calls `game.validate_state`; raises `ValueError` with match context on failure.
- Mechanics MUST call after setup and each update. Stock mechanics enforce this.

### 4.6.1 `validate_view`

- Requires a dict and verifies strict JSON serialisability without fallback coercion.
- Stock mechanics MUST call it after `game.get_view()` and before renderer/player use.
- It does not decide visibility correctness; Game/package fixtures own oracle-leak tests.

### 4.7 `log`
- Writes structured log entries and emits `LOG` events.  
- Mechanics MAY attach `player`, `turn_number`, or custom fields (e.g., phase, outcome).

### 4.8 `checkpoint`
- Hook for future checkpoint/resume.  
- Currently a no-op; mechanics MAY call without worrying about implementation details.  
- Console can override to persist state snapshots for long-running experiments (runtime automatically forwards to console helper).

## 5. Invariants & Guarantees
1. **MR1 Runtime Isolation**: One runtime per match. No shared mutable state across matches or workers.
2. **MR2 Recorder Consistency**: `record_turn` emits `GAMEPLAY` events in execution order so Recorder captures an ordered transcript directly from the event stream.
3. **MR3 Parse Failure Integrity**: `handle_parse_failure` MUST emit `PLAYER_ACTION_PARSE_FAILED`, log warning, update recorder, and return a policy outcome.
4. **MR4 RNG Traceability**: Every RNG fork label is recorded in debug logs so researchers can trace randomness sources.
5. **MR5 Canonical State Enforcement**: `validate_state` MUST reject non-dict or non-strict-JSON state before it reaches Recorder, replay, or spectators.
6. **MR6 Visible View Enforcement**: Stock mechanics MUST reject non-dict or non-strict-JSON player views before rendering or model invocation.
7. **MR7 No Coercive Evidence**: Runtime validation MUST NOT stringify, drop, or otherwise normalize an unsupported value to make it serialisable.
8. **MR8 Public Mechanics Boundary**: Stock mechanics MUST access orchestration, events, Player invocation, match metadata, and logging only through public `MatchRuntime` methods. Direct access to `runtime._console` is prohibited outside `MatchRuntime` itself.

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
- `SPEC-GAMEPLAY-EVENT-DATA.md` – Canonical gameplay payload emitted by `record_turn`.
- `SPEC-RECORDER.md` – Recording schema used by `record_turn`.
- `SPEC-OBSERVABILITY.md` – Event envelope and routing schema enforced by `emit_event`.
- `SPEC-PARALLEL.md` – Seed derivation and RNG requirements satisfied by `fork_rng`.
