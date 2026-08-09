# SPEC-CONSOLE: Execution Engine Contract

> Status: Final
> Version: 0.7.3
> Last Updated: 2026-08-08
> Implementation: Planned
> Review State: Legacy-approved
> Audience: Core contributors, engine implementers

## 1. Purpose
- Define the contract for console implementations that own session lifecycle, orchestrate matches, and emit observability signals for AgentDeck experiments.
- Ensure any console (Python default, lightweight variant, Rust-backed engine, etc.) can be swapped beneath the `AgentDeck` facade without breaking researcher workflows.
- Capture invariants around deterministic execution, spectator routing, and match metadata so testing and replay parity remain consistent across engines.

## 2. Scope & Philosophy Alignment
- Grounded in `SPEC.md` §2.1: the console is the execution engine inside the AgentDeck "console" metaphor, responsible for turning researcher configuration into running sessions.
- Follows `AGENTS.md` §2.1 separation of concerns: AgentDeck validates and delegates; the console manages lifecycle, event emission, and turn-by-turn execution.
- Reinforces reproducibility mandates from `SPEC.md` §2.4 by deriving deterministic seeds, recording them in ALL observability artifacts, and ensuring replay parity.
- **Mechanics-Agnostic Principle**: Console orchestrates Game → Player → ActionResult flow without interpreting game semantics, state content, or decision logic. It coordinates execution without making game-logic decisions.
- Non-goals: researcher-facing API design (`SPEC-AGENTDECK.md`), player/controller contracts (`SPEC-PLAYER.md`), or recorder storage policies (`SPEC-RECORDER.md`).

## 3. Responsibilities

### 3.1 Architecture Layers

Console operates at two architectural layers, both mechanics-agnostic:

1. **Orchestration Layer** (`run()` method):
   - Manages session and batch lifecycle
   - Emits `SESSION_*`, `BATCH_*`, `CLEANUP_*` events
   - Coordinates multiple matches
   - Returns aggregated results

2. **Match Execution Layer** (`play_match()` method):
   - Emits `MATCH_START` / `MATCH_END` and manages handshakes + conclusion
   - Creates a `MatchRuntime` per match and delegates execution to `game.run(runtime, players)` (mechanic-agnostic)
   - Returns a single `MatchResult`

### 3.2 Core Responsibilities

- **Session Lifecycle**: Resolve the session seed, prepare directories, create `SessionState`, bind recorder/spectators, emit `SESSION_START` / `SESSION_END`, stamp `finished_at`, and guarantee idempotent cleanup.
- **Execution Lifecycle**: For every `run` call emit `BATCH_START` / `BATCH_END`, derive base seeds, loop through requested matches (including size-1 runs), and scope execution spectators.
- **Player Order Management**: Console is the source of fairness by default. Before each match, call `game.get_player_order(players, rng=match_rng, match_context)`. When game returns `None` (default), apply console fairness policy using `AgentDeckConfig.pairing_policy` and `AgentDeckConfig.first_player_policy`. `paired_side_swap` MUST reuse the same match seed for each paired AB/BA run and MUST swap sides only after the base order is chosen. When game returns custom list, validate (same players, no duplicates, correct length) and raise `ValueError` on mismatch; non-default console fairness policies are incompatible with custom game ordering. Record effective order, actual first actor, and selected fairness policy in observability artifacts (MatchResult.metadata, events, logs, recorder). Log player order at DEBUG level (see §6.5 invariants).
- **Match Orchestration**: Manage match-level lifecycle (handshakes → MATCH_START → `game.run(runtime, players)` → conclusion phase → MATCH_END), reset per-match state, and package outcomes into `MatchResult` objects with complete reproducibility metadata.
- **Conclusion Policy**: Apply the session conclusion policy to decide whether the conclusion phase runs and which players conclude. For the default Player template, derive each concluding Player's final state through `game.get_view(canonical_final_state, player.name)` without mutating the canonical `MatchResult`. Game hooks may override prompts/state for a single player, but do not gate conclusion execution.
- **Handshake Management**: Run handshake build+execute before turn 1, emit `PLAYER_HANDSHAKE_START` using the exact prompt bundle, validate acknowledgements via controller, and abort on rejection.
- **Runtime Provisioning**: Create a fresh `MatchRuntime` per match exposing recorder, event emitter, RNG forks, parse-failure helper, and validation utilities so mechanics stay decoupled from console internals (see `SPEC-MATCH-RUNTIME.md`).
- **Parse Failure Handling** (new in v0.5.0): When `player.decide()` raises `ActionParseError`, the console MUST capture the embedded `ParseResult`, emit a `PLAYER_ACTION_PARSE_FAILED` event, record the failure, and invoke the game's parse-failure policy hook. Console interprets the returned `ParseFailurePolicy` (abort, skip turn, forfeit, retry) and applies it deterministically.
- **Deterministic Randomness**: Maintain session-level RNG state, derive per-match RNGs deterministically, and persist seeds in ALL observability artifacts (events, logs, recorder, MatchResult). Pairing policies that promise side-swap parity MUST also preserve pair-level seed reuse.
- **EventBus Lifecycle**: Create, configure, and inject EventBus into components. Subscribe/unsubscribe observers as needed. MUST NOT implement routing logic (EventBus internal responsibility).
- **Event Emission Boundaries**:
  - **Console emits**: `SESSION_*`, `BATCH_*`, `MATCH_START`, `PLAYER_CONCLUSION`, `MATCH_END`, `CLEANUP_*` (orchestration lifecycle)
  - **Mechanics emit**: `GAMEPLAY` events via runtime helpers (turn execution, see `SPEC-GAME-MECHANIC-TURN-BASED.md` / future mechanic specs)
  - **Game emits**: Domain-specific custom events via runtime helpers or GameEventEmitter (game semantics)
  - **Player emits**: `LLM_*`, `PARSE_*` (decision pipeline)
- **Logging & Diagnostics**: Integrate with `AgentDeckLogger` when provided and emit `LOG` events for spectators.
- **Recording**: Integrate with `Recorder` when provided so match artifacts and replay files are captured.

### 3.3 Parallel Execution (optional)

When `AgentDeckConfig.concurrency > 1`, the console MAY execute matches concurrently using `_MatchWorker` instances. The console MUST:

- Clone inputs: invoke `Player.clone()` for every player and deepcopy the game so each worker owns isolated state. Players with non-serialisable state MUST provide a working clone (SPEC-PLAYER §4, SPEC-LLM §5.7); failures raise `ParallelExecutionError` before scheduling work.
- Capture dual event streams: workers record sanitised snapshots for recorder parity (`MatchArtifact.events`) and replay-ready payloads with original Player/Game objects (`MatchArtifact.replay_events`). The console replays the latter on the main EventBus in match-index order so spectators observe the same payloads as sequential execution.
- Preserve determinism: derive per-match seeds from `(base_seed + match_index)` when base seed provided; otherwise use the session RNG forked per worker. Seeds MUST be persisted exactly as in sequential execution (see §6.3/6.4).
- Synchronise metrics: after each worker completes, copy aggregate metrics (total cost, total tokens, latency samples, etc.) from the cloned players back to the original player instances so researchers see consolidated statistics.
- Enforce limitations: if a game relies on `previous_match_result` (via `get_player_order`), the console MUST fall back to sequential execution and log a diagnostic message.

## 4. Data Structures
### SessionState

```python
@dataclass
class SessionState:
    config: SessionConfig
    session_id: str
    seed: int  # Non-optional: always resolved from param > config > entropy
    started_at: float
    finished_at: Optional[float] = None
    log_directory: str
    record_directory: str
    log_file_levels: List[LogLevel]

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return self.finished_at - self.started_at
```

**Guarantees**: Console MUST create (not receive pre-built) `SessionState` via session_factory or default factory. Before instantiation it MUST create `{run_dir}/{session_id}/`, `{run_dir}/{session_id}/logs/`, and `{run_dir}/{session_id}/records/` directories and record their paths in `log_directory` / `record_directory`. It MUST stamp `finished_at` on cleanup and expose immutable state (including the non-null resolved `seed`) to the facade for researcher inspection. When no seed is supplied, the console MUST draw one from system entropy, persist it in `SessionState.seed`, and reuse it for deterministic derivations.

### MatchContext

```python
@dataclass
class MatchContext:
    match_id: str
    rng: RandomGenerator
    seed: int  # Non-optional: always present for every match
    start_time: float
    handshake_completed: bool = False
    previous_match_result: Optional[MatchResult] = None  # Result of previous match in batch
```

**Guarantees**: Created anew for every match, capturing the RNG instance, actual seed used, unique identifier, and timing baseline. `handshake_completed` MUST reflect whether all players acknowledged successfully. Seed MUST be persisted in MatchContext, MatchResult, events, logs, and recorder files. MatchContext MUST remain immutable to game authors.

**Previous Match Result**: `previous_match_result` contains the `MatchResult` from the immediately preceding match **within the current batch** (enables state-dependent player ordering, e.g., "winner goes first"). First match in batch has `previous_match_result=None`. Cross-batch state is NOT preserved (batches are independent).

### EventBus
- Provides subscribe / unsubscribe / emit capabilities for spectators and recorder.
- MUST attach session identifiers and timestamps to emitted events per `SPEC-OBSERVABILITY.md`.
- Console owns EventBus instance but MUST NOT implement routing logic (EventBus handles routing internally).

## 5. Public API

### Console(*, config: Optional[SessionConfig] = None, session: Optional[SessionContext] = None, seed: Optional[int] = None, recorder: Optional[Recorder] = None, spectators: Optional[List[Spectator]] = None, logger: Optional[AgentDeckLogger] = None, session_factory: Optional[Callable[[SessionConfig, SessionContext, int], SessionState]] = None) -> None

Create Console instance and initialize session lifecycle.

**Contract**:
- Accept: SessionConfig for paths/logging/defaults or a pre-built `SessionContext`, optional seed override (precedence: seed param > session/config.seed > entropy), optional recorder, spectators list, optional logger, optional session factory for testing
- Perform: Reuse or create `SessionContext`, create SessionState via session_factory or default, resolve seed precedence, instantiate EventBus, subscribe recorder/spectators
- Emit: `SESSION_START` (synchronously during construction, before returning)
- Raise: ValueError if directories cannot be created, TypeError if components have invalid types
- MUST: Create and expose SessionState via `console.session_state`
- MUST: Subscribe recorder/spectators before SESSION_START emission
- MAY operate without recorder or logger; when omitted, recording/log writes are skipped but event emission and execution semantics remain intact

#### Default Session Spectators

- **Auto-Attach MatchReporter**: When the console is constructed with `spectators is None`, it MUST instantiate `MatchReporter()` and subscribe it prior to emitting `SESSION_START`. This guarantees structured match reporting is available for first-run experiences without any additional configuration.
- **Explicit Override**: When the caller supplies any spectators list (including an empty list), the console MUST respect that list verbatim and MUST NOT auto-attach `MatchReporter`. Researchers silence the default reporting via `spectators=[]` or provide bespoke observers via `spectators=[...]`.
- **Logger Injection**: Auto-attached spectators MUST follow the logger-injection rules in §6.5 (P4) so their output flows through the session logger (console + info.log).

### run(game: Game, players: List[Player], matches: int = 1, seed: Optional[int] = None, spectators: Optional[List[Spectator]] = None) -> List[MatchResult]

Execute batch of matches and return results.

**Contract**:
- Accept: Game instance, ordered player list, match count (≥1), optional base seed override (precedence: seed param > session.seed), optional execution-scoped spectators.
- Perform:
  1. Validate `matches >= 1`, resolve base seed, generate `batch_id`, attach execution spectators.
  2. Emit `BATCH_START` (with `batch_id`, `matches_planned`, seed info).
  3. For each match index:
     - Derive match seed deterministically and build per-match execution context.
     - Resolve effective player order via `game.get_player_order`, falling back to configured console fairness policy when the game returns `None`.
     - Execute handshakes before `MATCH_START` (build prompt → emit `PLAYER_HANDSHAKE_START` → execute LLM call → validate → emit `PLAYER_HANDSHAKE_COMPLETE|ABORT`).
     - Emit `MATCH_START` after successful handshake completion.
     - Create `MatchRuntime(console=self, game=game, match_id=..., session_id=..., batch_id=..., seed=..., max_turns=..., recorder=..., logger=..., rng=match_rng, previous_match_result=..., events_list=...)` and call `game.run(runtime, ordered_players)`.
     - Emit `MATCH_END`, store `MatchResult` (final state, metadata, runtime events).
  4. Emit `BATCH_END` (include `seeds_used`, duration, `matches_completed`), detach execution spectators.
- Return: `List[MatchResult]` (length == matches) with complete metadata.
- Emit: `BATCH_START` (before first match), `BATCH_END` (after last match, includes `seeds_used` list).
- Raise: `ValueError` if `matches < 1`.
- MUST: Emit BATCH lifecycle events even when `matches == 1` (treat as size-1 batch).
- MUST: Include aggregate metadata in `BATCH_END` payload: matches_played, `seeds_used`, `duration`, `batch_id`.
- MUST: Attach/detach execution spectators scoped to this batch.

### ~~get_player_action()~~ → REMOVED (Delegated to TurnLoop)

**DEPRECATED**: Console no longer brokers individual player decisions. Mechanics handle execution via `game.run(runtime, players)` (see `SPEC-GAME-MECHANIC-TURN-BASED.md` for the default implementation).

### ~~emit_turn()~~ → REMOVED (Delegated to TurnLoop)

**DEPRECATED**: Console no longer emits turn-level events. Mechanics use runtime helpers/EventFactory to create standardized gameplay events. See `SPEC-GAME-MECHANIC-TURN-BASED.md` and `SPEC-OBSERVABILITY.md` for event creation patterns.

### emit_event(event: Event) -> None

Forward custom game events through EventBus.

**Contract**:
- Accept: Event from game (custom domain events)
- Perform: Wrap with console metadata (session_id, match_id, timestamps)
- Emit: Enriched event to spectators via EventBus

### log(message: str, level: LogLevel = LogLevel.INFO, *, player: Optional[str] = None, match_id: Optional[str] = None, turn_number: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> None

Write structured log and emit LOG event.

**Contract**:
- Accept: Log message, level, optional player name, match_id, turn_number, extra context dict
- Perform: Write through to AgentDeckLogger when one is configured
- Emit: `LOG` event for spectators
- MUST: Emit `LOG` events even when no logger is configured

### _handle_parse_failure(player: Player, error: ActionParseError, turn_context: TurnContext) -> ParseFailurePolicy *(new helper in v0.5.0)*

Internal helper invoked by TurnLoop when a controller fails to parse an action.

**Contract**:
- Accept: failing `player`, `ActionParseError` (with embedded `ParseResult`), immutable `TurnContext` snapshot.
- Perform the following steps in order:
  1. Emit `PLAYER_ACTION_PARSE_FAILED` with payload containing player name, match/batch/session identifiers, `turn_number`, serialized `parse_result`, optional `prompt_text`/`prompt_blocks`, and `candidates` metadata.
  2. Append failure entry to Recorder (canonical event payload) and flush immediately.
  3. Log warning-level message summarizing failure and candidates.
  4. Call `game.on_action_parse_failure(player.name, error, turn_context)` to obtain a `ParseFailurePolicy` value.
  5. Return the policy outcome to TurnLoop.
- Interpret policy outcome:
  - `ABORT_MATCH`: raise match-termination exception after logging.
  - `SKIP_TURN`: instruct TurnLoop to advance without applying an action.
  - `FORFEIT`: mark failing player as loser (console finalises match).
  - `RETRY_ONCE`: allow a single deterministic retry (console tracks retry budget).
- MUST include `policy_outcome` in the emitted failure event for observability.
- MUST guarantee retries occur at most once per failure to preserve deterministic execution.

### close() -> None

Cleanup session and emit SESSION_END (context manager protocol).

**Contract**:
- Perform: Emit `SESSION_END`, stamp `finished_at`, and unsubscribe recorder/spectators
- Emit: `SESSION_END` exactly once
- MUST: Be idempotent (repeated calls do not replay events or raise)
- MUST: Suppress internal cleanup errors (recorder/logger/spectator failures), gameplay exceptions propagate unchanged

## 6. Invariants & Guarantees

### 6.1 Session Lifecycle (S)
1. **S1**: MUST emit `SESSION_START` exactly once after subscribing recorder and spectators and before accepting gameplay calls.
2. **S2**: MUST emit `SESSION_END` exactly once during cleanup, even if no matches were executed.
3. **S3**: MUST ensure cleanup is idempotent; repeated invocations do not replay lifecycle events or raise errors.
4. **S4**: MUST create and expose `SessionState` (with resolved paths, non-null seed, and finished timestamps) through an immutable interface for the facade.
5. **S5**: MUST suppress internal cleanup errors (recorder flush, spectator detachment, logger flush) so teardown never raises; gameplay exceptions MUST propagate to the caller unchanged.

### 6.2 Execution Lifecycle (X)
6. **X1**: MUST emit `BATCH_START` exactly once at the beginning of each `run`, even when `matches == 1`.
7. **X2**: MUST emit `BATCH_END` exactly once after the run completes, including failure paths where an exception is raised to the caller.
8. **X3**: MUST generate a unique `batch_id` per run and include it in all emitted execution and match events.
9. **X4**: MUST return a list of `MatchResult` objects whose length equals the requested `matches` count when the run completes successfully.

### 6.3 Player Order (PO)
10. **PO1**: Before each match, console MUST call `game.get_player_order(players, rng, match_context)`; when it returns `None`, console MUST apply the configured fairness policy. `first_player_policy="random"` uses match-RNG shuffling, `fixed` pins the configured original index first, and `alternating` rotates the roster by match index. `pairing_policy="paired_side_swap"` overlays AB/BA swapping for exactly two players after the base order is chosen.  
11. **PO2**: When a custom list is returned, console MUST validate it contains the exact same player instances (no additions/removals/duplicates) and raise `ValueError` on mismatch.  
12. **PO3**: Console MUST persist the effective order, order source ("console" vs "game"), first player, and selected fairness policy in `MatchResult.metadata` and emitted events.  
13. **PO4**: Consoles MUST log player-order decisions at DEBUG level to aid researchers (seed, permutation, custom ordering rationale).

### 6.3 Deterministic Randomness (R)
10. **R1**: MUST resolve a session seed (constructor argument > config.seed) and generate one from system entropy when none is supplied, persisting it in `SessionState.seed`.
11. **R2**: MUST resolve a base seed for each run (`run(seed=...)` > session seed) and derive per-match seeds deterministically when a base seed exists. Default derivation is `base_seed + match_index`; `pairing_policy="paired_side_swap"` MUST instead reuse `base_seed + pair_index` for each AB/BA pair.
12. **R3**: MUST fall back to entropy-derived RNG when no base seed is available while still recording the actual seed chosen.
13. **R4**: MUST persist the actual seed used for each match in ALL observability artifacts: MatchContext (runtime access), MatchResult (researcher access), MATCH_START/END event payloads (spectators/replay), Logger output (diagnostics), Recorder files (replay/analysis), BATCH_END aggregate metadata (batch-level traceability).

### 6.4 Seed Traceability (T)
14. **T1**: MUST persist session seed in: SessionState.seed (always non-null after construction), SESSION_START event payload, Logger output (session initialization), Console.session (exposed to facade).
15. **T2**: MUST persist per-match seed in: MatchContext.seed (passed to game), MatchResult metadata, MATCH_START event payload (before game execution), MATCH_END event payload (for correlation), Logger output (match start/end), Recorder files (for replay).
16. **T3**: MUST persist batch-level seed metadata in: BATCH_END event payload (list of seeds_used), Logger output (batch summary).
17. **T4**: When seed is derived (not explicitly provided), MUST log the derivation method: "Generated session seed: {seed} from system entropy" or "Match {match_index} seed: {seed} (derived from base seed {base_seed})".

### 6.5 Handshake Lifecycle (H)
18. **H1**: Console MUST run handshake before the first turn of every match using the two-step Player API (`build_handshake_bundle` → `execute_handshake`) and MUST abort (`HandshakeRejectedError`) on the first rejection.
19. **H2**: Console MUST emit `PLAYER_HANDSHAKE_START` before the LLM call, using the exact `PromptBundle` returned by `build_handshake_bundle` (prompt_text + prompt_blocks) and the controller handshake format.
20. **H3**: Console MUST call `execute_handshake` with the exact bundle returned by `build_handshake_bundle` and then validate via `controller.validate_handshake(raw, context)`.
21. **H4**: Console MUST emit `PLAYER_HANDSHAKE_COMPLETE` or `PLAYER_HANDSHAKE_ABORT` for every player with `accepted`, `normalized_response`, `response_text`, `controller_metadata`, and prompt metadata (prompt_text, prompt_blocks, controller_format, renderer_output, usage_info when available).
22. **H5**: `MatchContext.handshake_completed` MUST be `True` only when all players acknowledged successfully and MUST remain `False` otherwise (match aborted).
23. **H6**: Upon successful handshake, console MUST ensure the handshake exchange remains available to subsequent `player.decide` calls unless a player explicitly resets conversation history.

### 6.6 Conclusion Visibility (CV)

24. **CV1**: Before invoking a policy-selected Player through its default conclusion template, Console MUST derive that Player's terminal view with `game.get_view(match_result.final_state, player.name)` and pass a distinct `MatchResult` whose `final_state` is the derived view. Console MUST preserve the canonical `MatchResult.final_state` for recording, replay, game hooks, and the caller.
25. **CV2**: A prompt returned by `game.get_conclusion_prompt(...)` is an explicit Game-owned override. Console MUST pass that prompt verbatim and MUST NOT reinterpret or redact it; Game authors own the visibility of that prompt under `SPEC-GAME`.

### 6.7 Event Ordering & Delivery (E)
25. **E1**: MUST emit lifecycle events in order: `SESSION_START` → (`BATCH_START` → (`PLAYER_HANDSHAKE_*`)* → (`MATCH_START` / **TurnLoop execution** (+ optional `PLAYER_ACTION_PARSE_FAILED`) / **PLAYER_CONCLUSION** (per policy) / `MATCH_END`)+ → `BATCH_END`)* → `SESSION_END`.
26. **E2**: MUST attach session/match identifiers, phase indices, monotonic timestamps, and turn indices to events per `SPEC-OBSERVABILITY.md`.
27. **E3**: Console MUST emit orchestration lifecycle events (SESSION, BATCH, MATCH_START, MATCH_END, CLEANUP) plus parse-failure events. Turn execution events remain TurnLoop responsibility; domain events remain Game responsibility.
28. **E4**: `PLAYER_ACTION_PARSE_FAILED` MUST be emitted exactly once per parsing failure before any policy action is applied.
29. **E5**: Console MUST own the EventBus instance but MUST NOT implement routing logic. All event routing is internal to EventBus.

### 6.8 Match Metadata (M)
30. **M1**: MUST populate `MatchResult.metadata` with game name, player names, duration, turn count, and truncation info.
31. **M2**: MUST reset conversation managers and player logging hooks before each match to avoid leakage across matches.
32. **M3**: Console MUST record player order metadata in ALL observability artifacts: MatchResult.metadata["player_names"] (ordered list post-ordering), MatchResult.metadata["player_order"] (0-based indices showing original positions), MATCH_START/END event payload (player_names ordered list), Logger output (ordered player list in match start/end logs), Recorder files (ordered player list). Rationale: Player order is objective data. Some mechanics may use this order directly, while others may select the first acting player at runtime. Console records both ordering and first-player metadata for analysis.
33. **M4** (Player Ordering): Console MUST call `game.get_player_order(players, rng=match_rng, match_context)` before each match. If game returns `None`, Console MUST apply the configured fairness policy. If game returns custom list, Console MUST validate (same `Player` instances, same length, no duplicates) and raise `ValueError` on mismatch. Console MUST record in `MatchResult.metadata` and events: `player_order` (List[int] of original indices, e.g., [1, 0, 2] means original player 1 is first in ordered list), `player_order_source` (Literal["console", "game"]), `first_player` (Dict with {"name": str, "index": int, "ordered_index": int}), and `fairness_policy` (selected pairing / first-player policy metadata). `first_player` MUST reflect the actual first acting player when runtime selection metadata is available; otherwise it MUST fall back to the first player in ordered list. Console MUST log player order at DEBUG level without exposing to INFO/console output.

### 6.9 Spectator & Recorder Integration (P)
33. **P1**: MUST subscribe recorder and all spectator instances prior to emitting `SESSION_START`.
34. **P2**: MUST propagate execution-level spectators supplied during `run` across the entire run and remove them after `BATCH_END`.
35. **P3**: MUST tolerate spectators raising exceptions by logging/reporting without destabilizing the console.
36. **P4** (Logger Injection): MUST inject logger into spectators before EventBus subscription if `spectator.logger is None`. Check `if getattr(spectator, "logger", None) is None` and assign `spectator.logger = self.logger` for both session spectators (during construction) and execution spectators (during `run`). This enables spectators to write to core log streams (info.log, debug.log, console) via `logger.info()`, `logger.debug()`, etc., per SPEC-SPECTATOR §5.5 (LI1-LI5).

### 6.10 Logging & Recording (L)
37. **L1**: Console MUST tolerate `logger=None` and `recorder=None` in direct-construction scenarios. `AgentDeck` typically supplies both, but Console MUST still preserve lifecycle/event semantics when either dependency is omitted.

### 6.11 Error Handling (H)

**Defense in Depth Model**: Console provides final validation layer AFTER Player/Controller pipeline:
- **Controller** (primary): Parses LLM response, extracts action, validates game-specific semantics
- **Console** (safety net): Verifies controller didn't return empty/invalid results, ensures type correctness
- **Game** (logic): Applies action to state, detects illegal moves in game context

This layered approach prevents silent failures while maintaining separation of concerns.

### 6.11 Parse Failure Handling (PF) — *New in v0.5.0*
30. **PF1**: TurnLoop MUST propagate `ActionParseError` raised by `player.decide()` back to Console without modification.
31. **PF2**: Console MUST handle parsing failures via helper `_handle_parse_failure(player, error, turn_context)` (or equivalent). The helper MUST:
    1. Extract the `ParseResult` from `error.parse_result`.
    2. Emit `PLAYER_ACTION_PARSE_FAILED` with payload including player name, match_id, turn_number, raw_response, candidates, metadata, and controller error message.
    3. Append a failure record to Recorder (see SPEC-RECORDER §6.8).
    4. Invoke `game.on_action_parse_failure(player.name, error, turn_context)` to determine policy.
    5. Interpret the returned `ParseFailurePolicy` and inform TurnLoop of the outcome.
32. **PF3**: Console MUST support at least the following policy outcomes (enum defined in SPEC-GAME):
    - `ABORT_MATCH`: terminate match immediately.
    - `SKIP_TURN`: consume the failing player's turn and continue.
    - `FORFEIT`: declare the failing player the loser and end match (default outcome when a game does not override `on_action_parse_failure`).
    - `RETRY_ONCE`: re-issue the prompt one additional time (Console MUST ensure a single retry per failure to preserve determinism).
33. **PF4**: If `ABORT_MATCH` is returned (default), Console MUST emit `MATCH_END`, call `Recorder.on_match_end()` with failure metadata (e.g., `match.metadata["outcome"] = "aborted"`), and only then raise `MatchTerminationError` (or propagate a descriptive exception) so recordings persist the partial match.
34. **PF5**: Console MUST document the chosen policy in logs and in the failure event payload (`policy_outcome` field) for observability, explicitly noting when the default FORFEIT outcome was applied.
35. **PF6**: Policy outcomes MUST be deterministic and dependent solely on current game state, the failing player, and the provided ParseResult metadata.
36. **PF7**: Console MUST NOT provide a global fallback configuration flag; all graceful degradation MUST be implemented via the game policy hook or custom controllers.

38. **H1**: MUST raise `NotImplementedError` if a game lacks the required execution interface.
39. **H2**: MUST raise `TypeError` if player decisions do not return `ActionResult`.
40. **H3** (Defense in Depth): MUST provide final validation guardrail: raise ValueError if ActionResult.action is None, empty string, or whitespace-only; raise ValueError if ActionResult.success is False but action was not rejected during player pipeline. Rationale: Controller performs primary parsing/validation, Console provides safety net if controller fails silently. Console MUST NOT parse action semantics (e.g., "e2-e4" format) - that is Controller responsibility.
41. **H4** (Player Order Validation): MUST raise `ValueError` when `game.get_player_order()` returns invalid list: different `Player` instances than input, wrong length, duplicate players, or contains non-Player objects. Error message MUST describe validation failure (e.g., "Game returned player list with 3 players but expected 2" or "Game returned duplicate player: Alice").

### 6.11 Parallel Execution (PE)
42. **PE1**: When concurrency > 1, Console MUST create `_MatchWorker` instances that invoke `Player.clone()` for each player and deepcopy the game. Failures MUST surface as `ParallelExecutionError` before any worker starts.
43. **PE2**: Workers MUST capture dual event streams: sanitised snapshots for recorder parity and replay payloads containing original Player/Game objects. Console MUST replay the latter strictly in match-index order so spectators observe the same payloads as sequential execution.
44. **PE3**: After each worker completes (sequential or parallel path), Console MUST synchronise aggregate player metrics (e.g., `total_cost`, `total_tokens`, latency samples) from cloned players back to the original instances.
45. **PE4**: Console MUST fall back to sequential execution when the game overrides `get_player_order` in a way that may depend on `previous_match_result`, logging a diagnostic message to aid researchers.

## 7. Data Flow & Interaction
- **Initialization**
  1. Receive SessionConfig, seed override, recorder, spectators, and logger from facade.
  2. Resolve seed precedence (seed param > config.seed > entropy), create `{run_dir}/{session_id}/` with `logs/` + `records/` subdirectories, instantiate `SessionState` (timestamped ID, log levels, resolved seed).
  3. Instantiate `EventBus`, subscribe recorder/spectators, emit `SESSION_START` before returning.
- **Execution run**
  1. Receive request from facade with game, players, matches count, optional base seed, and execution spectators.
  2. Resolve base seed, allocate batch identifier, subscribe execution spectators, emit `BATCH_START`.
  3. **Bind controllers to game**: For all players, call `player.controller.bind_game(game)` to provide `allowed_actions` for validation (per SPEC-CONTROLLER v1.3.0 GB1).
  4. For each match:
     a. Derive per-match seed deterministically from the configured fairness mode (`base_seed + match_index` by default, `base_seed + pair_index` for paired side-swap)
     b. Create `MatchContext` with seed, match_id, RNG, and `previous_match_result` (None for first match, previous MatchResult for subsequent matches in batch)
     c. **Determine player order**: Call `game.get_player_order(players, rng=match_rng, match_context)`
        - If returns `None`: Apply configured console fairness policy
        - If returns `List[Player]`: Validate (same players, correct length, no duplicates), raise `ValueError` on failure
        - Record `player_order` (original indices), `player_order_source` ("console" or "game"), `first_player` (name + original index + ordered_index), and `fairness_policy`
        - Log at DEBUG level: "Player order determined: [names] (source: console/game)"
     d. Execute handshake phase with ordered players (build prompt → emit `PLAYER_HANDSHAKE_START` with prompt_text/prompt_blocks + controller_format → execute LLM call → validate → emit `PLAYER_HANDSHAKE_COMPLETE|ABORT`, update `MatchContext.handshake_completed`)
     e. Reset player conversations/logging
     f. Emit `MATCH_START` (with seed, ordered player_names, player_order, player_order_source, first_player, fairness_policy)
     g. **Create MatchRuntime & delegate to mechanic**:
        ```python
        match_runtime = MatchRuntime(
            console=self,
            game=game,
            match_context=match_context,
            recorder=self.recorder,
            logger=self.logger,
            rng=match_context.rng,
        )
        final_state, mechanic_events, truncated = game.run(match_runtime, ordered_players)
        ```
     h. Collect metadata (seed, player_names, player_order, player_order_source, first_player, fairness_policy, handshake status, turn count, truncation, duration)
     i. Execute conclusion phase per policy: derive a terminal `game.get_view(...)` for each default Player template while preserving canonical state; emit `PLAYER_CONCLUSION` for selected players
     j. Emit `MATCH_END` (with same metadata as MATCH_START for correlation)
  5. Emit `BATCH_END` with accumulated results and seeds_used list, detach execution spectators, return list of `MatchResult`.
- **Replay**
  - Replay engine consumes recorded events (from recorder or in-memory) and replays them through the same `EventBus`, honoring spectator scopes.
- **Cleanup**
  - Upon facade close, the console flushes recorder, flushes logger, emits `SESSION_END`, and marks itself closed for idempotence.

## 8. Error Handling & Edge Cases
- `NotImplementedError` when game lacks required interface (H1).
- `RuntimeError` wrapping player decision failures with player/game/match context.
- `TypeError` when player returns incorrect type or metadata structure (H2).
- `ValueError` when player returns empty action strings (H3 - defense in depth, controller should catch first).
- Cleanup (`close()` / context manager exit) MUST swallow recorder/logger/spectator teardown failures while still emitting `SESSION_END`. Exceptions raised during match execution propagate back to the facade.
- Recorder/spectator errors MUST be logged, and execution continues unless the failure compromises core execution (facade decides on escalation).
- Replay events with missing context MUST surface descriptive errors and abort the replay gracefully.
- When batch execution fails mid-stream, consoles SHOULD retain previously completed matches (recordings and metadata) to support partial analysis.

## 9. Examples
```python
# Standalone console usage
from agentdeck import AgentDeckConfig, FixedDamageGame, MockPlayer
from agentdeck.core.console import Console

console = Console(config=AgentDeckConfig(), seed=123)

game = FixedDamageGame()
players = [MockPlayer("A"), MockPlayer("B")]

try:
    results = console.run(game, players)
    print(console.session_state.seed, results[0].metadata["duration"])
    print(results[0].metadata["player_names"])  # ["A", "B"] - ordered
finally:
    console.close()
```
```python
# Deterministic seed derivation and traceability
from agentdeck.core.console import Console
from agentdeck import AgentDeckConfig, FixedDamageGame, MockPlayer

console = Console(config=AgentDeckConfig(), seed=42)

players = [MockPlayer("Alpha"), MockPlayer("Beta")]

try:
    batch = console.run(FixedDamageGame(), players, matches=2)  # Uses seeds 42, 43
    override = console.run(FixedDamageGame(), players, seed=99)  # Uses seed 99

    # Verify seed traceability
    assert batch[0].metadata["seed"] == 42
    assert batch[1].metadata["seed"] == 43
    assert override[0].metadata["seed"] == 99

    # Verify player order metadata (post-shuffling)
    assert "player_names" in batch[0].metadata  # Ordered list (may be shuffled)
    assert "player_order" in batch[0].metadata  # Original indices, e.g., [1, 0]
    assert batch[0].metadata["player_order_source"] in ["console", "game"]
    assert "first_player" in batch[0].metadata  # {"name": str, "index": int, "ordered_index": int}
finally:
    console.close()
```

## 10. Testing Strategy
| Focus | Invariants | Verification Goal |
|-------|------------|-------------------|
| Session lifecycle | S1-S5 | Confirm directories created, recorder subscribed, SESSION_START/END emitted once, cleanup idempotent, SessionState exposed with non-null seed. |
| Execution lifecycle | X1-X4 | Capture event stream: BATCH_START/END fire once per run, batch IDs propagate, result counts match, BATCH_END includes seeds_used. |
| RNG determinism | R1-R4, T1-T4 | Verify seed precedence, deterministic derivation, entropy fallback, seed in ALL artifacts (MatchResult, events, logs, recorder). |
| Event ordering | E1, E3-E5 | Capture stream: lifecycle sequence, TurnLoop delegation, event origination boundaries (Console/TurnLoop/Game/Player). |
| Match metadata | M1-M4 | Assert MatchResult includes metadata, conversation reset, player_order/player_order_source/first_player in all artifacts. |
| Player ordering | M4, H4 | Verify same seed → identical player_order; test game override validation (reject invalid lists); verify DEBUG logging; test previous_match_result propagation. |
| Spectator integration | P1-P3 | Ensure recorder/spectators receive events, execution spectators scoped, failures contained. |
| Optional logger/recorder | L1 | Verify lifecycle/event semantics hold with `logger=None` or `recorder=None`; verify AgentDeck still supplies both by default. |
| Player decision validation | H1-H3 | Trigger error paths: missing game interface, wrong return types, empty actions (defense-in-depth). |
| Replay fidelity | R1-R4, E1 | Record + replay: verify event parity, seed reproduction, error handling for malformed recordings. |

## 11. Design Rationale
- **TurnLoop Delegation**: Console delegates turn-by-turn execution to TurnLoop to keep execution responsibilities modular and testable. Console owns match lifecycle (handshake → TurnLoop → conclusion), TurnLoop owns turn execution (state management, event creation, player decisions).
- **Separation of Concerns**: Console orchestrates matches, TurnLoop executes turns, Game defines rules, Player makes decisions. Clear boundaries enable independent evolution and testing.
- **Mechanics-Agnostic Orchestration**: Console coordinates matches without interpreting game semantics, enabling support for any game type (turn-based, simultaneous, real-time) without modification.
- **Engine abstraction**: Isolating lifecycle and execution logic allows AgentDeck to swap consoles (Python, Rust, cloud) without API changes.
- **SessionState ownership**: Console creates (not receives) SessionState, centralizing directory creation and session IDs to prevent duplication across facades.
- **Deterministic RNG with complete traceability**: Seed precedence (param > config > entropy) combined with persistence in ALL observability artifacts ensures full reproducibility.
- **EventBus integration**: Console owns EventBus instance but delegates routing logic to EventBus component, keeping spectators decoupled while preserving ordering.
- **Optional integration**: Console stays usable as a lower-level engine even when constructed without recorder/logger, while the higher-level `AgentDeck` facade provides the richer default researcher experience.
- **Player Order Recording**: Always recording player order (not "when applicable") provides objective data for all game types without interpreting semantics.
- **Player Order Fairness**: Console is the default source of fairness, removing burden from game authors. Games override `get_player_order()` only when ordering is semantically meaningful (auction winners, asymmetric roles, state-based advantage). Recording `player_order_source`, `first_player`, and `fairness_policy` enables researchers to distinguish console-managed fairness from game-controlled ordering for analysis purposes.

## 12. Open Questions / Future Work
- Should consoles expose explicit health metrics (queue lengths, lag) for long-running sessions?
- How should consoles report spectator failures—status codes, aggregated diagnostics, or facade callbacks?
- Do we support pooled consoles (warm session contexts) for rapid batch execution, and how does that affect lifecycle guarantees?
- What compatibility layer is needed for consoles implemented in other languages (e.g., Rust) to satisfy this contract?
- Should replay requests be routed through the console (`console.replay`) or continue delegating directly to a dedicated `ReplayEngine`? (Deferred to `SPEC-REPLAY.md`.)

## 13. References
- `SPEC.md` §2 (Architecture), §2.4 (Reproducibility)
- `SPEC-AGENTDECK.md` (Facade contract)
- `SPEC-GAME.md` v0.6.0 (Narrative flow ownership, parse-failure policy hook)
- `SPEC-PLAYER.md` v1.1.0 (Decision pipeline, ActionResult contract)
- `SPEC-CONTROLLER.md` v1.2.0 (Primary action parsing/validation, ActionParseError semantics)
- `SPEC-GAME-MECHANIC-TURN-BASED.md` v2.0.0 (TurnBasedGame + TurnLoop + MatchRuntime integration, EventFactory usage, parse failure propagation)
- `SPEC-MATCH-RUNTIME.md` v1.0.0 (Runtime contract provided to `game.run`)
- `SPEC-OBSERVABILITY.md` v1.2.0 (Event types, payloads, emission boundaries, parse failure events)
- `SPEC-RECORDER.md` v2.0.0 (Recording contract, parse failure capture)
- `SPEC-SPECTATOR.md` v1.2.0 (Logger injection contract §5.5 LI1-LI5, spectator lifecycle)
- `GUIDELINES.md` §4.4 (Public API documentation format)
- Implementation references: `src/agentdeck/core/console.py`, `src/agentdeck/core/event_bus.py`, `src/agentdeck/core/session.py`, `src/agentdeck/core/turn_loop.py`
