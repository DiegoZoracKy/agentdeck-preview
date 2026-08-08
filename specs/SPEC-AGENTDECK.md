# SPEC-AGENTDECK: AgentDeck Facade Contract

> Status: Final
> Version: 0.3.1
> Last Updated: 2026-03-31
> Implementation: Complete (Phase 6-8 compliance verified)
> Review State: Legacy-approved
> Audience: Researchers, framework contributors

## 1. Purpose
- Provide a single entry point for running AgentDeck experiments without exposing internal orchestration.
- Guarantee reproducible batch execution, lifecycle signaling, and aggregated match reporting to researchers.
- Offer contributors a stable contract for configuration, replay, and session inspection.

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC.md` §1.2 by enabling experiments in a handful of lines while scaling to advanced runs.
- Upholds `AGENTS.md` §2.1 separation of concerns: AgentDeck configures and delegates; Console executes.
- Reinforces reproducibility focus from `SPEC.md` §2.4 through deterministic seed derivation and replay parity.
- Non-goals: Match orchestration internals (`SPEC-CONSOLE`), recorder persistence rules (`SPEC-RECORDER`), or spectator behavior beyond attachment semantics.

## 3. Responsibilities
- **Engine Construction**: Construct the default execution console, pass the resolved session context into it, and retain the console/session handles.
- **Input Validation & Delegation**: Validate researcher inputs (games, players, matches, seeds), resolve spectator scopes/seeds, then delegate batch execution to the console which owns lifecycle events, player ordering, and match aggregation. Player order is randomized per match (Console applies Fisher-Yates shuffle by default, games may override via `get_player_order()` hook per SPEC-GAME §4).
- **Spectator Scoping**: Maintain additive session vs execution spectator scopes and forward them to the console for both live play and replay. When researchers omit the spectator list, AgentDeck MUST rely on the console's default auto-attachment (MatchReporter) so structured match reporting is available out of the box. Supplying any spectator list (including `[]`) MUST override the default.
- **Result Aggregation**: Collect `MatchResult` outputs from the console into `MatchResults` and surface researcher-facing helpers (win rates, summaries, stats).
- **Metrics Exposure**: Surface session metadata and live counters through read-only properties (`session`, `total_matches`, `elapsed_time`) plus lightweight snapshot helpers.
- **Safe Shutdown**: Provide deterministic teardown via context manager exit and best-effort cleanup on destruction.
- **Error Surfacing**: Translate validation failures into documented exceptions and enrich console-raised errors with researcher-relevant context.

## 4. Data Structures
### SessionConfig

```python
@dataclass
class SessionConfig:
    seed: Optional[int] = None
    run_dir: str = "agentdeck_runs"
    max_turns: int = 1000
    log_level: Optional[LogLevel] = LogLevel.INFO
    log_file_levels: Optional[List[LogLevel]] = None
    log_format: str = "simple"
    concurrency: int = 1
    monitors: Optional[List[Monitor]] = None
    pairing_policy: str = "none"
    first_player_policy: str = "random"
    fixed_first_player_index: int = 0
    conclusion: ConclusionPolicy = field(default_factory=ConclusionPolicy)

@dataclass
class ConclusionPolicy:
    """Policy for post-match conclusion phase."""

    enabled: bool = True
    mode: str = "all"  # one of: all, winner, loser, specific
    player: Optional[str] = None  # required when mode == "specific"
```

**Guarantees**: `run_dir` is the console template for per-session directories. Console MUST create a run root at `{run_dir}/{session_id}/` and provision `logs/` + `records/` subdirectories within it. Custom recording/logging paths come from injecting alternative Recorder implementations. Session seeds are supplied through `session=AgentDeckConfig(...)` and may be overridden per batch via `play(..., seed=...)`. `conclusion` controls whether and which players participate in the conclusion phase (SPEC-CONSOLE).

**Logging Defaults**:
- `log_level`: Controls stdout/console output. Defaults to `LogLevel.INFO` (match summaries, turn progress).
  - `LogLevel.INFO`: Show match/turn summaries on console
  - `LogLevel.DEBUG`: Show detailed output including API calls
  - `None`: Quiet mode - no console output (useful for batch experiments)
- `log_file_levels`: Controls file logging. Defaults to `None`, which automatically creates both `info.log` and `debug.log` files.
  - `None` (default): Creates both `info.log` and `debug.log`
  - `[LogLevel.INFO]`: Only `info.log`
  - `[LogLevel.DEBUG]`: Only `debug.log`
  - `[LogLevel.INFO, LogLevel.DEBUG]`: Explicit both (same as default)
  - `[]`: No file logging

**Console and file logging are independent**: You can have quiet stdout (`log_level=None`) while still creating debug files (`log_file_levels=None` creates both info.log and debug.log by default). Files MUST live under `{run_dir}/{session_id}/logs/`.

### SessionState

```python
@dataclass
class SessionState:
    config: SessionConfig
    session_id: str
    seed: int
    started_at: float
    finished_at: Optional[float] = None
    log_directory: str
    record_directory: str
    log_file_levels: List[LogLevel]
```

**Guarantees**: Produced by the console from the provided configuration and session-wide seed. If the researcher omits a seed, the console MUST generate one and record it for reproducibility. The console MUST ensure `{run_dir}/{session_id}/`, `{run_dir}/{session_id}/logs/`, and `{run_dir}/{session_id}/records/` exist before creating the state. The state MUST expose read-only values (including `finished_at`) so the facade can surface session metadata via `deck.session`.

### MatchResult & MatchResults

```python
@dataclass
class MatchResult:
    winner: Optional[str]
    final_state: Dict[str, Any]
    events: List[Event]
    seed: Optional[int]
    metadata: Dict[str, Any]

@dataclass
class MatchResults:
    matches: List[MatchResult]

    @property
    def single(self) -> MatchResult: ...

    @property
    def win_rates(self) -> Dict[str, float]: ...

    @property
    def summary(self) -> str: ...
```

**Guarantees**: `MatchResult` MUST capture per-match seed, events, and metadata. `MatchResults` MUST retain all matches and expose helper accessors (`single`, `win_rates`, `summary`) for downstream analysis.

## 5. Public API
- `AgentDeck(game=None, spectators=None, recorder=None, session=None)`
  - `game`: Optional default game used when `play()` omits `game`.
  - `spectators`: Session-wide spectators for every execution.
  - `recorder`: Recorder instance (console default when `None`).
  - `session`: `AgentDeckConfig` for seeding/logging/limits (set seed here, not on the facade).
  - Guarantees:
    - MUST construct the default console and pass the resolved session context into it.
    - MUST obtain the console's session handle and only return once the console signals readiness (including `SESSION_START` emission).
    - MUST register session-level spectators with the console so they participate in all subsequent executions.
- `play(players, game=None, matches=1, seed=None, spectators=None) -> MatchResults`
  - `players`: List of `Player` implementations. Player order is deterministic given the seed (console shuffle or game override via `get_player_order()` per SPEC-GAME §4).
  - `game`: Game instance to execute (optional if a default game was provided to the facade).
  - `matches`: Match count (default `1`).
  - `seed`: Batch seed overriding `session.seed` when provided (controls per-match seeds and ordering).
  - `spectators`: Execution-level spectators (additive).
  - Guarantees:
    - MUST validate inputs (game instance, non-empty unique player names, `matches ≥ 1`, integer seed when provided).
    - MUST delegate to `console.run(game, players, matches=matches, seed=seed, spectators=...)`, which emits `BATCH_START`/`BATCH_END` and executes exactly `matches` games with deterministic seeds and player ordering when available.
    - MUST return `MatchResults` wrapping the list of `MatchResult` objects supplied by the console, including seeds and player_order metadata recorded for each match.
- `replay(match=None, *, path=None, spectators=None, speed=1.0) -> None`
  - `match`: A `MatchResult` or dict (mutually exclusive with `path`).
  - `path`: File path to a single recorded match JSON (mutually exclusive with `match`).
  - `spectators`: Execution-level spectators observing the replay.
  - `speed`: Playback speed multiplier.
  - Guarantees:
    - MUST require exactly one of `match` or `path`.
    - MUST load/normalise into a single match and replay it sequentially.
    - MUST raise `TypeError` / `ValueError` when inputs are of an unsupported type.
    - MUST stream recorded events in order using provided or session spectators, respecting the supplied `speed`.
- `replay_batch(matches, spectators=None, speed=1.0) -> None`
  - `matches`: Ordered list of recorded matches (`MatchResult` or serialized dict payloads).
  - `spectators`: Execution-level spectators observing the replay.
  - `speed`: Playback speed multiplier.
  - Guarantees:
    - MUST replay the supplied matches sequentially by delegating to `replay(...)`.
- `get_session_stats() -> Dict[str, Any]`
  - Guarantees:
    - MUST return a lightweight snapshot containing `session_id`, `total_matches`, `elapsed_time`, output directories, seed, and max-turns configuration.
- Read-only properties
  - `session -> SessionState`: MUST expose the console-supplied session state without allowing mutation.
  - `total_matches -> int`: MUST reflect the cumulative number of matches executed during the session.
  - `elapsed_time -> float`: MUST report wall-clock seconds since `SESSION_START` using the session timestamp.
- Context manager protocol (`__enter__`, `__exit__`)
  - Guarantees:
    - MUST return the AgentDeck instance on entry.
    - MUST delegate cleanup to the console on exit, ensuring `SESSION_END` is emitted while allowing exceptions to propagate.

## 6. Invariants & Guarantees
### 6.1 Engine Integration (E)
1. **E1**: MUST construct the default console from the resolved session configuration and retain the console-provided session handle.
2. **E2**: MUST pass the resolved `SessionContext` and recorder/spectator dependencies to the console and retain the console-provided session handle.
3. **E3**: MUST surface console-supplied session metadata (identifier, directories, seed, duration) via researcher-facing helpers without alteration. The seed MUST always be present in SessionState, whether provided by researcher or generated by console.

### 6.2 Lifecycle (L)
4. **L1**: MUST complete construction only after console signals readiness (after `SESSION_START` emission). Console guarantees `SESSION_START` is emitted during construction before returning control to facade.
5. **L2**: MUST delegate cleanup to console, which emits `SESSION_END` exactly once when the session closes, regardless of success or failure.
6. **L3**: MUST ensure cleanup idempotence by delegating to console's idempotent cleanup routine.
7. **L4**: MUST expose console-stamped `finished_at` timestamp via session state for duration reporting.

### 6.3 Batch Execution (B)
8. **B1**: MUST reject empty player lists, duplicate player names, or non-positive `matches`.
9. **B2**: MUST reject non-integer seeds with a `TypeError`.
10. **B3**: MUST delegate batch execution to `console.run`, which emits `BATCH_START`/`BATCH_END`, derives per-match seeds as `base_seed + match_index` when a base seed exists, and randomizes player order per match (Console shuffles by default, game may override).
11. **B4**: MUST return `MatchResults` populated with the seeds, player ordering metadata (`player_order`, `player_order_source`, `first_player`), and other metadata recorded by the console for each match.
12. **B5**: MUST return `MatchResults` containing exactly the number of `MatchResult` entries yielded by the console (which equals the requested `matches` when execution succeeds).

### 6.4 Spectator Scoping (S)
13. **S1**: MUST treat session spectators as persistent across all batches and replays.
14. **S2**: MUST append execution-level spectators without removing or mutating session spectators.
15. **S3**: MUST forward the effective spectator set to the console for both live play and replay.
16. **S4**: MUST allow the console to auto-attach default session spectators when the caller omits the spectator list (`spectators is None`), and MUST ensure that supplying any explicit spectator list (including `[]`) bypasses the default attachment.

### 6.5 Replay (R)
17. **R1**: MUST accept exactly one of `match` (MatchResult/dict) or `path` (single match file path) and reject unsupported or combined inputs with a descriptive error.
18. **R2**: MUST reproduce recorded events in their original order for every replayed match by delegating to the console/replay engine.

## 7. Data Flow & Interaction
- **Session init**: Facade resolves session configuration, creates `SessionContext`, passes session/recorder/spectators to the default console → console creates `SessionState`, binds observers, emits `SESSION_START`.
- **Batch execution**: Facade validates inputs, resolves spectators/seed → calls `console.run` with matches count → console emits `BATCH_START`, loops through matches with `MATCH_*` events, emits `BATCH_END`, returns list of `MatchResult` → facade wraps into `MatchResults` and updates counters.
- **Replay**: Facade loads matches/paths → console/replay engine streams events to active spectators.
- **Metrics**: Facade exposes console counters via `session`, `total_matches`, `elapsed_time`, and `get_session_stats()`.

## 8. Error Handling & Edge Cases
- Error contracts are summarized below:

| Condition | Exception | Guarantee | Message Characteristics |
|-----------|-----------|-----------|--------------------------|
| Empty players list | `ValueError` | Enforces B1 | States players cannot be empty |
| Duplicate player names | `ValueError` | Enforces B1 | Lists offending names |
| `matches < 1` | `ValueError` | Enforces B1 | Includes provided value |
| Non-integer seed | `TypeError` | Enforces B2 | States seed must be integer or None |
| Invalid replay source | `TypeError`/`ValueError` | Enforces R1 | Describes expected match/path types |
| Match execution failure | `RuntimeError` | Ensures enriched debugging | Includes game, players, seed, and match index |

- MUST suppress cleanup errors so destruction never propagates exceptions.

## 9. Examples
```python
# Minimal experiment (game passed at play time)
from agentdeck import AgentDeck, AgentDeckConfig, FixedDamageGame, MockPlayer

config = AgentDeckConfig()
with AgentDeck(session=config) as deck:
    result = deck.play(game=FixedDamageGame(), players=[MockPlayer("Alice"), MockPlayer("Bob")])
    print(result.single.winner)
```
```python
# Reproducible batch with custom spectators
from agentdeck import AgentDeck, AgentDeckConfig, FixedDamageGame, MockPlayer
from agentdeck.spectators import StatsTracker

players = [MockPlayer("Alpha"), MockPlayer("Beta")]
config = AgentDeckConfig(seed=42)

with AgentDeck(session=config, spectators=[StatsTracker()]) as deck:
    batch = deck.play(game=FixedDamageGame(), players=players, matches=10)
    print(batch.win_rates)
```
```python
# Replay recorded matches from disk
from pathlib import Path
from agentdeck import AgentDeck, AgentDeckConfig, FixedDamageGame, MockPlayer

players = [MockPlayer("Red"), MockPlayer("Blue")]
config = AgentDeckConfig(seed=7)

with AgentDeck(session=config) as deck:
    results = deck.play(game=FixedDamageGame(), players=players, matches=3)
    recording_dir = Path(deck.session.record_directory)
    match_files = sorted(recording_dir.glob("match_*.json"))
    print(f"Ran {deck.total_matches} matches")

deck = AgentDeck()
deck.replay(path=match_files[-1], speed=1.5)  # Replay a single recorded match
```
```python
# Logging configurations
from agentdeck import AgentDeck, AgentDeckConfig, LogLevel

# Default: INFO on stdout, both info.log and debug.log created
config = AgentDeckConfig()  # log_level=LogLevel.INFO, log_file_levels=None
deck = AgentDeck(session=config)

# Quiet stdout, but still create debug files (useful for batch experiments)
config = AgentDeckConfig(log_level=None)  # Creates info.log + debug.log by default
deck = AgentDeck(session=config)

# Verbose console output with API call details
config = AgentDeckConfig(log_level=LogLevel.DEBUG)
deck = AgentDeck(session=config)

# Quiet stdout, only debug.log file (no info.log)
config = AgentDeckConfig(log_level=None, log_file_levels=[LogLevel.DEBUG])
deck = AgentDeck(session=config)

# Totally silent (no console, no files) - not recommended
config = AgentDeckConfig(log_level=None, log_file_levels=[])
deck = AgentDeck(session=config)
```

## 10. Testing Strategy

| Focus | Invariants | Verification Goal |
|-------|------------|-------------------|
| Lifecycle sequencing | L1, L2, L3 | Observe event emission order and cleanup idempotence via spectator or logger instrumentation. |
| Engine integration | E1, E2, E3 | Verify default console selection, configuration pass-through, and exposure of console-provided session metadata. |
| Input validation | B1, B2, R1 | Confirm the documented exceptions and messages occur for each invalid input combination. |
| Deterministic execution | B3, B4 | Re-run batches with identical seeds and validate identical `MatchResult` seeds and outcomes. |
| Aggregation integrity | B5 | Ensure `MatchResults` length equals requested matches and helper properties operate correctly. |
| Spectator scoping | S1, S2, S3 | Track event delivery to session vs execution spectators during play and replay. |
| Replay fidelity | R2 | Compare live vs replayed event streams for order and payload parity. |
| Metrics exposure | E3, L4 | Verify `session`, `total_matches`, and `elapsed_time` mirror console state (including finished timestamps) and remain read-only. |
| Failure propagation | Runtime error guarantee | Inject Console failure to verify enriched `RuntimeError` message and retention of completed matches. |

## 11. Design Rationale
- **Seed as first-class**: Keeps reproducibility obvious while advanced knobs stay in `SessionConfig`.
- **Always-present seed**: Console generates one when absent so `deck.session.seed` always enables replay.
- **SessionConfig focus**: Bundles logging/directories/limits, leaving constructor parameters lean.
- **MatchResults container**: Uniform return avoids single vs multi-match branching and still surfaces summaries.
- **Additive spectators**: Preserves persistent observers while allowing per-run instrumentation.
- **Player ordering delegation**: AgentDeck delegates player ordering to Console (Fisher-Yates shuffle) and Game hook (`get_player_order()`), removing ordering concerns from researcher code. Seed controls shuffling for reproducibility. Metadata (`player_order_source`) enables analysis of ordering strategies.

## 12. Open Questions / Future Work
- Do we need first-class hooks for progress callbacks during long batches, or should observers rely on spectators alone?
- What policy governs session metrics persistence beyond in-memory inspection (e.g., exposing a structured metrics endpoint)?

## 13. References
- `SPEC.md` §1.1, §1.2, §2.4
- `AGENTS.md` §2.1–§2.3
- `SPEC-OBSERVABILITY.md`
- Implementation references: `src/agentdeck/core/agentdeck.py`, `src/agentdeck/core/session.py`, `src/agentdeck/core/types.py`
