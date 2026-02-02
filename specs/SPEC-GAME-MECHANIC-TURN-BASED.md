# SPEC-GAME-MECHANIC-TURN-BASED: Turn-Based Game Mechanic Contract

> Status: Final  
> Version: 2.0.0  
> Last Updated: 2026-01-27  
> Implementation: ✅ Complete (Phase 6-8 compliance verified)  
> Authors: Codex, Diego Zoracky, Claude  
> Audience: Game authors implementing turn-based mechanics, core contributors, tooling authors

## 1. Purpose
- Define the canonical contract for `TurnBasedGame` and the shared `TurnLoop` helper that executes sequential turns using the new `MatchRuntime`.
- Ensure every turn-based game reuses the same infrastructure for observability (events, recorder, transcripts), reproducibility (RNG forks), and failure handling (parse-failure policies).
- Provide the playground for custom turn-based mechanics without forcing console changes or per-game duplication.

## 2. Scope & Philosophy Alignment
- Builds on `SPEC-GAME.md`: Games own rules/state; mechanics own execution.  
- Extends `SPEC-CONSOLE.md`: Console orchestrates handshakes + lifecycle, then delegates to `game.run(runtime, players)`.  
- Relies on `SPEC-MATCH-RUNTIME.md`: runtime object exposes event emission, recorder access, RNG, parse-failure helper, validation utilities.  
- Non-goals: Simultaneous or real-time mechanics (future specs), player decision logic (`SPEC-PLAYER.md`), recorder schema (`SPEC-RECORDER.md`).

## 3. Responsibilities
- **TurnBasedGame class**  
  - Provide the default `run(runtime, players)` implementation that the console invokes.  
  - Expose overridable hooks (`get_current_player`, `on_turn_start`, `on_turn_end`) without requiring authors to touch runtime internals.  
  - Reject direct `run()` overrides unless author is building a brand-new turn-based variant (documented in §6.1).
- **TurnLoop helper**  
  - Execute deterministic turns until the game reports terminal status or runtime indicates truncation.  
  - Use `StateAdapter` for before/after snapshots; emit GAMEPLAY events and custom events through runtime.  
  - Apply parse-failure policies by invoking `runtime.handle_parse_failure`.  
  - Fork RNG for each turn via `runtime.fork_rng("turn_X")`.  
  - Record prompts/responses through `runtime.record_turn`.  
  - Call `game.update()` and `game.validate_state()` with full error context.

## 4. Public API

### 4.1 `class TurnBasedGame(Game)`

```python
class TurnBasedGame(Game):
    """Default base class for sequential turn games."""

    def run(self, runtime: MatchRuntime, players: list[Player]) -> TurnResult:
        """Execute the mechanic using TurnLoop helper."""
        return TurnLoop(self, runtime, players).run()

    def get_current_player(
        self,
        state: dict[str, Any],
        player_names: list[str],
        *,
        rng: RandomGenerator,
        match_context: MatchContext,
    ) -> str:
        """Return acting player name for the next turn (defaults to round-robin)."""

    def on_turn_start(self, turn_context: TurnContext) -> None:
        """Optional hook invoked before each turn (default no-op)."""

    def on_turn_end(self, turn_context: TurnContext, mechanic_events: list[Event]) -> None:
        """Optional hook invoked after each turn (default no-op)."""
```

**Contract**:
- Game authors SHOULD inherit from `TurnBasedGame` and MUST NOT override `run()` unless they are implementing a brand new sequential mechanic.  
- `run()` MUST call `TurnLoop(self, runtime, players).run()` so all infrastructure hooks remain active.  
- Hooks available:  
  - `get_current_player(...)` – override to implement asymmetric turn order or dynamic scheduling.  
  - `on_turn_start(turn_context)` / `on_turn_end(turn_context, events)` *(optional, see §5.4)*.  
  - `on_action_parse_failure(...)` – already defined in `SPEC-GAME.md`, used by runtime.

### 4.2 `class TurnLoop`

```python
class TurnLoop:
    def __init__(
        self,
        game: TurnBasedGame,
        runtime: MatchRuntime,
        players: list[Player],
    ) -> None: ...

    def run(self) -> TurnResult: ...
```

**Contract**:
1. `run()` MUST perform the following steps:
   1.1 Call `game.setup()` with ordered player names.  
   1.2 Call `game.validate_state(initial_state)` if implemented.  
   1.3 Loop until `game.status(state).is_over` or runtime signals truncation:  
       - Build `TurnContext` (turn_number, acting player, RNG fork, timestamps).  
       - Render state via `game.get_view()` for the current player.  
       - Invoke `player.decide(...)` and pass transcripts maintained by runtime.  
       - On `ActionParseError`, call `runtime.handle_parse_failure` and follow returned policy.  
       - On success, call `game.update(state, player_name, action, rng=turn_rng)`; state MAY mutate in place or return new dict.  
       - Emit GAMEPLAY event via `runtime.emit_event` before applying domain events.  
       - Call `runtime.record_turn` with prompt/response/action metadata.  
       - Call `game.get_events(...)` and emit each via runtime.  
       - Call `game.validate_state` after update.  
   1.4 Return `TurnResult(final_state, events, truncated_by_max_turns)`.
2. `TurnLoop` MUST respect runtime.max_turns; when exceeded, set `truncated_by_max_turns=True`.
3. `TurnLoop` MUST restore any temporary bindings (EventFactory/GameEventEmitter) even on error.

### 4.3 `TurnResult`

```python
@dataclass
class TurnResult:
    """Solid return type used by TurnBasedGame.run() (lives in agentdeck.core.mechanics.turn_based)."""
    final_state: dict[str, Any]
    events: list[Event]
    truncated_by_max_turns: bool = False
```

Returned to `TurnBasedGame.run()` and subsequently to the console. Console wraps this into `MatchResult`.

## 5. Invariants & Guarantees

### TL1 – Deterministic Setup
- TurnLoop MUST call `runtime.fork_rng("setup")` before invoking `game.setup`.  
- `game.setup` MUST NOT touch global randomness; any randomness comes from the forked RNG passed in.

### TL2 – Single Acting Player Per Turn
- `get_current_player` MUST return a name present in `player_names`.  
- TurnLoop MUST raise `ValueError` if the hook returns unknown player or duplicates.

### TL3 – Runtime Usage
- TurnLoop MUST use `runtime.emit_event`, `runtime.record_turn`, and `runtime.validate_state` for event emission, recording, and validation.
- Parse-failure handling MAY use console helpers (e.g., `console.get_player_action`) as long as the parse-failure policy is correctly applied and turns are recorded via `runtime.record_turn`.

### TL4 – Prompt/Response Capture
- After every successful `player.decide`, mechanics MUST call `runtime.record_turn(...)` with the turn’s prompt metadata (prompt blocks, raw response, normalized action result, usage/cost data, and `TurnContext`).  
- `runtime.record_turn` is responsible for emitting the canonical `EventType.GAMEPLAY` payload via the runtime’s event bus so Recorder (and any spectators) can persist the transcript per `SPEC-RECORDER v1.3.0`.  
- GAMEPLAY payloads MUST contain all PM1–PM6 fields (see `SPEC-RECORDER` §6.7) so recordings remain self-contained; no direct recorder API is permitted.

### TL5 – Error Propagation
- `ActionParseError` handling MUST follow policies defined in `SPEC-GAME.md` §7.  
- Other exceptions bubble up to the console; TurnLoop MUST annotate them with `turn_number`, `player_name`, and `match_context.match_id`.

### TL6 – Replay Fidelity
- TurnLoop MUST attach `phase_index` and `turn_number` to every GAMEPLAY event.  
- `events` returned in `TurnResult` MUST be JSON-serialisable; runtime will append them to recorder outputs to guarantee replay parity.

## 6. Mechanic Customisation Guidance

### 6.1 When to Override `run()`
- Only override `TurnBasedGame.run()` when creating a fundamentally new sequential mechanic (e.g., simultaneous declarations but sequential resolution).  
- Overriding `run()` MUST still use `MatchRuntime`; failure to do so is undefined behaviour.  
- Custom implementations SHOULD delegate to `TurnLoop` for common steps and only customise what is necessary.

### 6.2 Simultaneous / Future Mechanics
- Non-turn-based games SHOULD inherit directly from `Game` and implement their own `run(runtime, players)` method.  
- Such mechanics MUST depend on `MatchRuntime` in the same way TurnLoop does: all events, recorder writes, RNG, and parse failure policies flow through runtime.  
- A future `SPEC-SIMULTANEOUS.md` will codify these rules; until then, refer to `SPEC-MATCH-RUNTIME.md`.

## 7. References
- `SPEC-GAME.md` – Game author contract and parse-failure policies  
- `SPEC-MATCH-RUNTIME.md` – Runtime infrastructure available to mechanics  
- `SPEC-CONSOLE.md` – Orchestration lifecycle and runtime creation  
- `SPEC-OBSERVABILITY.md` – Event payload requirements  
- `SPEC-PROMPT-BUILDER.md` – Prompt metadata captured via `runtime.record_turn`

### 4.4 `TurnContext`

```python
@dataclass(frozen=True)
class TurnContext:
    turn_number: int                # 1-indexed turn/round number
    player_name: str                # Acting player
    match_id: str                   # From MatchContext
    phase_index: int                # Zero-based phase counter (used for replay)
    rng_label: str                  # Label passed to runtime.fork_rng
    started_at: float               # Timestamp when turn began
    duration: float                 # Seconds spent executing the turn
```

- Built by `TurnLoop` and passed to runtime hooks (`record_turn`, `handle_parse_failure`, `validate_state`).  
- Mechanics overriding `run()` MUST produce an equivalent structure so recorder/replay remain consistent.  
- Future fields may be added; consumers must treat unknown attributes defensively.
