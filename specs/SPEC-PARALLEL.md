# SPEC-PARALLEL: Console Parallel Match Execution

> Status: Draft v0.1.0  
> Version: 0.1.0  
> Last Updated: 2025-03-29  
> Implementation: ⬜ Not Started  
> Authors: Codex, Claude, Diego  
> Audience: Contributors, Research Engineers, Observability Maintainers

## 1. Purpose
- **Primary users:** researchers who run large match batches, contributors maintaining console orchestration.  
- **Problem:** sequential execution makes 100–1000 match experiments slow and opaque during long runs.  
- **Goal:** allow researchers to opt into parallel match execution without sacrificing determinism, spectator fidelity, or recorder parity; keep console ergonomics unchanged when concurrency is not requested.

## 2. Scope & Philosophy Alignment
- **Simplicity (AGENTS §2.2):** default behaviour stays sequential; parallelism is additive via a single config knob.  
- **Separation & Composition (AGENTS §2.1):** worker abstraction encapsulates per-match execution; main console remains the coordination surface.  
- **Reproducibility (SPEC §2.4):** spec mandates seed derivation per match and ordered event replay so recordings match sequential runs.  
- **Research-first (SPEC §1):** no API churn—research scripts continue to call `deck.play(...)`; opting in is via session config.

## 3. Responsibilities
- **Console (updated):** orchestrate matches sequentially or through a worker pool while preserving lifecycle events, recorder output, and spectator semantics.  
- **Worker abstraction (new internal):** execute a single match on cloned game/players, capture event snapshots, and return artifacts for replay.  
- **AgentDeckConfig (extended):** carry an optional `concurrency` hint that gates worker creation.

## 4. Data Structures
- **AgentDeckConfig** (new field):  
  - `concurrency: int = 1` — number of concurrent worker slots; `1` keeps legacy behaviour.  
  - Must be positive; values > available matches clamp to `matches`.
- **MatchArtifact** (new dataclass in `core.types`):
  - `match_index: int` — original ordering within the batch.
  - `seed: int | None` — effective seed used for the match.
  - `result: MatchResult` — existing match outcome container.
  - `events: List[Event]` — sanitized snapshots (Player/Game objects converted to string identifiers; payload JSON-serialisable) captured via the worker’s isolated EventBus and persisted into `MatchResult.events` for recorder parity.
  - `replay_events: List[tuple[EventType, Dict, Dict]]` — original payloads plus context captured during live execution; the console replays these on the main EventBus so spectators receive the same Player/Game objects as sequential runs.
- **ParallelExecutionError** (new exception class, internal): raised when cloning game/players fails; instructs users to run sequentially (`concurrency=1`) or refactor non-serializable state. Message template lives alongside the implementation.

## 5. Public API
- `AgentDeckConfig(concurrency: int = 1, ...)`  
  - Preconditions: `concurrency >= 1`; raising `ValueError` otherwise.  
  - Postconditions: stored on `SessionContext`; `AgentDeck` reads once at init.
- `AgentDeck.play(..., matches: int, seed: Optional[int] = None)` (unchanged signature)  
  - Behaviour: uses session config to decide sequential vs parallel scheduling.  
  - Success: returns `MatchResults` identical to sequential output for same seed/matches.  
  - Side effects: logs continue to stream per match in submission order; spectators notified through existing EventBus.  
- `_MatchWorker` (internal class in `agentdeck/core/console.py`): private helper used by both sequential and parallel schedulers; clones inputs via `Player.clone()` / `Game` deepcopy, runs the extracted match pipeline, captures events, and returns `MatchArtifact`. No public export.
- `Player.clone()` (SPEC-PLAYER v1.1 update): players MUST override the default clone when they hold non-serialisable state (e.g., LLM SDK clients) so workers can construct isolated instances. Default implementation falls back to `copy.deepcopy`.

## 6. Invariants & Guarantees
- **Backward compatibility:** when `concurrency == 1`, behaviour (ordering, timing, event payloads) is byte-for-byte identical to current implementation.  
- **Deterministic seeding:** worker scheduler MUST derive per-match seeds from `(base_seed + match_index)`; absence of seed keeps prior entropy semantics.  
- **Event ordering:** spectators and recorder observe events replayed strictly by `match_index` (MATCH 0 → MATCH 1 → …) regardless of worker completion. Console MAY buffer early-completing matches until preceding indices have replayed, preserving live progress semantics.
- **Session integrity:** console emits a single `SESSION_START`/`BATCH_START`/`MATCH_*` sequence even when matches execute in parallel.  
- **Player order hook (v1.0 limitation):** games that depend on `previous_match_result` inside an overridden `get_player_order` are incompatible with parallel execution. Console MUST detect overrides of the base implementation and fall back to sequential execution with a warning.  
- **Isolation:** each worker runs on deep-copied game and player instances with dedicated RNG; no mutable state is shared across matches.  
- **Failure propagation:** first worker failure cancels remaining work, emits `BATCH_END` with partial results + error payload, and raises to caller (matching current semantics).  
- **Cloning failure:** if deep-copy fails for game or any player, console raises `ParallelExecutionError` before launching workers.
- **Metric propagation:** console MUST synchronise aggregate player metrics (token usage, cost, latency samples) from worker clones back to the original player instances after each match so researchers observe consolidated statistics.
- **Recorder compatibility:** recorder output (`agentdeck_runs/session_id/records/…`) MUST match sequential execution for identical seeds, except for wall-clock timestamps and aggregate durations.
- **Performance considerations:** Parallel execution delivers the largest gains when run against local or self-hosted models without strict rate limits. Cloud APIs may queue or throttle concurrent requests, which can negate speedups; researchers SHOULD benchmark their workload before selecting a `concurrency` value.

## 7. Data Flow & Interaction
- **Config path:** Research script → `AgentDeckConfig(concurrency=N)` → `AgentDeck` → `Console` (session state).  
- **Execution (sequential):** Facade → Console scheduler (`concurrency=1`) → `_MatchWorker` (sync) → EventBus/Recorder/Spectators.  
- **Execution (parallel):** Facade → Console scheduler (`concurrency>1`) → Thread pool of `_MatchWorker` instances → Event artifacts → Console replay loop → EventBus/Recorder/Spectators.  
- **Repro playback:** Recorder JSON remains compatible; Replay engine consumes captured events exactly as before.

## 8. Error Handling & Edge Cases
- **Invalid concurrency (<1):** raise `ValueError` at config creation with guidance (`"concurrency must be >= 1 (use 1 for sequential execution)"`).  
- **Clone failure:** raise `ParallelExecutionError` with message:
  ```
  Failed to clone <ClassName> for parallel execution.

  Error: <original exception>

  Solutions:
    1. Set concurrency=1 to disable parallel execution.
    2. Ensure <ClassName> avoids non-serializable state (database handles, sockets, thread locks).
    3. (Future) Implement custom cloning support when available.
  ```
- **Worker exception:** cancel outstanding futures, emit `BATCH_END` with `error`, rethrow root exception.  
- **Parallel-incompatible game:** when `get_player_order` is present, log a warning and execute batch sequentially (effective concurrency=1) without raising.  
- **Spectator exceptions:** no change—EventBus still isolates them.  
- **Low match counts (< concurrency):** scheduler clamps worker count to number of matches; events replay once per completed match.  
- **No seed:** matches inherit entropy-driven seeds as today; scheduler preserves recorded seeds in artifacts.  
- **Long-running spectators:** replay loop honours back-pressure; if spectator blocks, execution mirrors sequential behaviour.

## 9. Examples
1. **Opt-in via session config**
   ```python
   from agentdeck import AgentDeck, AgentDeckConfig, FixedDamageGame, GPTPlayer
   from agentdeck.controllers import ActionOnlyController

   config = AgentDeckConfig(seed=42, concurrency=4)
   players = [GPTPlayer("A", controller=ActionOnlyController()),
              GPTPlayer("B", controller=ActionOnlyController())]

   with AgentDeck(game=FixedDamageGame(), session=config) as deck:
       results = deck.play(players, matches=40)
   ```
2. **Detecting cloning limitations**
   ```python
   config = AgentDeckConfig(concurrency=8)
   try:
       deck = AgentDeck(game=my_stateful_game, session=config)
       deck.play(players, matches=20)
   except ParallelExecutionError as exc:
       print("Parallel disabled:", exc)
   ```
3. **Parity check in tests**
   ```python
   sequential = run_batch(concurrency=1)
   parallel = run_batch(concurrency=4)
   assert sequential.win_rates == parallel.win_rates
   assert sequential.matches[0].seed == parallel.matches[0].seed
   ```

## 10. Testing Strategy
- **Determinism parity (`test_parallel_determinism`):** run `FixedDamageGame` with `seed=42`, `matches=20` sequential vs parallel (`concurrency=4`). Assert per-match winners, seeds, and final states match; ensure event list lengths and each event’s `type` and `data` (excluding timestamp fields) align.
- **Player-order fallback:** craft a game whose `get_player_order` inspects `previous_match_result`; request `concurrency=4` and assert console emits warning and executes sequentially (only one worker active).
- **Spectator parity:** attach a collecting spectator (e.g., capturing event names) and confirm sequential vs parallel replay produce identical ordered sequences.
- **Clone failure path:** provide a player with non-deepcopyable attribute; expect `ParallelExecutionError` and no matches executed.
- **Failure propagation:** force worker to raise mid-batch; verify `BATCH_END` includes completed count, seeds, error string, and that the exception bubbles to caller.
- **No-seed entropy:** omit seed, run sequential vs parallel, and confirm each `MatchResult.seed` remains stable within respective runs and is recorded in artifacts.

## 11. Design Rationale
- **Internal workers vs auxiliary orchestrator:** preserves single session/batch narrative, keeps spectators/recorder behaviour intact, and avoids duplicating console logic externally.  
- **Event replay instead of concurrent emission:** guarantees spectators remain single-threaded consumers, maintaining ordering and existing UX.  
- **Deep-copy isolation:** safest path for stateful games/players without requiring immediate refactors for thread safety.  
- **Thread pool choice:** leverages LLM SDKs’ GIL release while avoiding pickle requirements inherent to process pools.

## 12. Open Questions / Future Work
- Adaptive concurrency based on observed match duration or player cost.  
- Worker reuse / warm pools to minimise deepcopy overhead for large objects.  
- Hooks for user-defined cloning strategies (e.g., `Player.clone()` opt-in).  
- Distributed execution (multi-host) building atop the same worker contract.

## 13. References
- [GUIDELINES.md](GUIDELINES.md) — specification authoring conventions.  
- [SPEC-CONSOLE.md](SPEC-CONSOLE.md) — baseline console responsibilities.  
- [SPEC-OBSERVABILITY.md](SPEC-OBSERVABILITY.md) — event ordering and replay guarantees.  
- [README.md](../README.md) — researcher quick start for match execution.  
- [research/README.md](../research/README.md) — running batches and analysing results.
