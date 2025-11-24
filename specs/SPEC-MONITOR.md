# SPEC-MONITOR: Console Observation Contract

> Status: Draft v1.0.0
> Version: 1.0.0
> Last Updated: 2025-10-29
> Implementation: ⬜ Not Started
> Authors: Diego ZoracKy, Codex, Claude (consensus)
> Audience: Monitor authors, system observability engineers, core contributors

## 1. Purpose
- Define the observer interface for monitoring console/system-level events (progress, worker status, hardware metrics) independent of match narrative.
- Establish a two-tier observation system: **Spectators** (match events) and **Monitors** (console events).
- Enable researchers to track execution progress during parallel batch runs without modifying existing spectator semantics.
- Preserve the gaming console analogy: spectators watch matches (fans in arena), monitors watch system (production crew/scoreboard).

## 2. Scope & Philosophy Alignment
- **Separation of Concerns (AGENTS §2.1):** Monitors observe console machinery without interpreting match semantics; spectators observe match narrative without accessing system internals.
- **Simplicity (AGENTS §2.2):** Default monitor (ProgressMonitor) provides zero-config UX for parallel execution; researchers opt out via `monitors=[]`.
- **Research-first (SPEC §1):** Addresses "silent execution" problem during long parallel batches where researchers lack visibility into completion status.
- **Clean slate design:** Two distinct event pipelines (match EventBus vs console EventBus) with clear boundaries; no legacy compatibility burden.
- **Composition over inheritance:** Both Spectators and Monitors share base event handler patterns (`on_<event>`) but observe different event buses.
- Non-goals: match narrative (SPEC-SPECTATOR), recording (SPEC-RECORDER), gameplay events (SPEC-OBSERVABILITY).

## 3. Responsibilities

### 3.1 Architecture: Two-Tier Observation System

```
┌─────────────────────────────────────────────┐
│         AgentDeck Console Architecture      │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐       ┌──────────────┐   │
│  │ Match        │──────▶│ Spectators   │   │
│  │ EventBus     │       │ (match tier) │   │
│  │ (buffered)   │       └──────────────┘   │
│  └──────────────┘                           │
│       ▲                                     │
│       │ Replay after worker completes       │
│       │ (preserves event order)             │
│                                             │
│  ┌──────────────┐       ┌──────────────┐   │
│  │ Console      │──────▶│ Monitors     │   │
│  │ EventBus     │ Live  │ (system tier)│   │
│  │ (immediate)  │       └──────────────┘   │
│  └──────────────┘                           │
│                                             │
└─────────────────────────────────────────────┘
```

**Layer Responsibilities:**

| Layer | Observes | Event Timing | Examples |
|-------|----------|--------------|----------|
| **Spectators** | Match narrative (handshakes, turns, conclusions) | Buffered, replayed in order (preserves determinism) | MatchNarrator, StatsTracker, TokenUsageTracker |
| **Monitors** | Console/system events (progress, workers, hardware) | Live, immediate (enables real-time feedback) | ProgressMonitor, HardwareMonitor, CheckpointMonitor |

### 3.2 Monitor Base Class
- Provides duck-typed `on_console_*` event handlers (similar to Spectator's `on_*` handlers).
- Receives live console events without buffering or replay semantics.
- Observes system-level metadata: batch progress, worker lifecycle, execution metrics.
- Does NOT receive match narrative events (MATCH_START, TURN_START, GAMEPLAY, etc.).

### 3.3 Console Integration
- Console creates **two EventBus instances**: match bus (existing) + console bus (new).
- Console emits console events to console bus (immediate, not buffered).
- Monitors subscribe to console bus; spectators subscribe to match bus.
- Console attaches default ProgressMonitor when `concurrency > 1` and `monitors` not explicitly provided.

### 3.4 ProgressMonitor (Default Implementation)
- Tracks batch/worker progress during parallel execution.
- Provides three output modes: quiet (progress bar), normal (status updates), verbose (detailed worker logs).
- Displays: completed/total matches, worker status, ETA, failure counts.
- Auto-attached when `concurrency > 1` unless user provides explicit `monitors` list.

## 4. Data Structures

### 4.1 AgentDeckConfig (Extended)
```python
@dataclass
class AgentDeckConfig:
    seed: Optional[int] = None
    concurrency: int = 1
    monitors: Optional[List[Monitor]] = None  # Console-level observers
    # ... existing fields ...
```

**Guarantees:**
- When `monitors is None` and `concurrency > 1`: Console auto-attaches `ProgressMonitor(mode="normal")`.
- When `monitors is None` and `concurrency == 1`: No monitors attached (sequential execution needs no progress reporting).
- When `monitors = []`: Explicit opt-out (no monitors attached, even during parallel execution).
- When `monitors = [CustomMonitor(), ...]`: User-provided monitors replace default.

### 4.2 Monitor Base Class
```python
class Monitor:
    """
    Base class for console/system-level observers.

    Monitors observe console EventBus (live, immediate events).
    Spectators observe match EventBus (buffered, replayed events).
    """

    def __init__(self, *, logger: Optional[AgentDeckLogger] = None):
        """
        Initialize monitor with optional logger.

        Console MUST inject logger via late-binding if not provided,
        following same pattern as Spectator (SPEC-SPECTATOR §5.5 LI1-LI5).
        """
        self.logger = logger

    # All handlers optional (duck-typed, similar to Spectator)

    def on_console_batch_start(self, event: Event) -> None:
        """Called when batch execution begins (sequential or parallel)."""
        pass

    def on_console_batch_progress(self, event: Event) -> None:
        """Called periodically with batch progress updates."""
        pass

    def on_console_worker_start(self, event: Event) -> None:
        """Called when a parallel worker begins executing a match."""
        pass

    def on_console_worker_complete(self, event: Event) -> None:
        """Called when a parallel worker completes successfully."""
        pass

    def on_console_worker_failed(self, event: Event) -> None:
        """Called when a parallel worker encounters an error."""
        pass

    def on_console_batch_complete(self, event: Event) -> None:
        """Called when batch execution completes (all matches done)."""
        pass
```

### 4.3 Console Event Types (Added to EventType enum)
```python
class EventType(str, Enum):
    # ... existing match events ...

    # Console events (live, not replayed)
    CONSOLE_BATCH_START = "console_batch_start"
    CONSOLE_BATCH_PROGRESS = "console_batch_progress"
    CONSOLE_WORKER_START = "console_worker_start"
    CONSOLE_WORKER_COMPLETE = "console_worker_complete"
    CONSOLE_WORKER_FAILED = "console_worker_failed"
    CONSOLE_BATCH_COMPLETE = "console_batch_complete"
```

### 4.4 Console Event Payloads
```python
# CONSOLE_BATCH_START
{
    "batch_id": str,
    "total_matches": int,
    "concurrency": int,
    "mode": Literal["sequential", "parallel"],
    "base_seed": Optional[int]
}

# CONSOLE_BATCH_PROGRESS
{
    "batch_id": str,
    "completed": int,
    "total": int,
    "in_progress": int,  # Number of workers currently executing
    "failed": int,
    "elapsed_time": float,
    "estimated_remaining": Optional[float]  # None until first match completes
}

# CONSOLE_WORKER_START
{
    "worker_id": int,  # match_index
    "match_index": int,
    "seed": Optional[int],
    "started_at": float
}

# CONSOLE_WORKER_COMPLETE
{
    "worker_id": int,
    "match_index": int,
    "duration": float,
    "winner": Optional[str],
    "turns": int,
    "completed_at": float
}

# CONSOLE_WORKER_FAILED
{
    "worker_id": int,
    "match_index": int,
    "error_type": str,  # Exception class name
    "error_message": str,
    "failed_at": float
}

# CONSOLE_BATCH_COMPLETE
{
    "batch_id": str,
    "completed": int,
    "total": int,
    "failed": int,
    "duration": float,
    "avg_match_duration": float,
    "seeds_used": List[Optional[int]]
}
```

## 5. Public API

### 5.1 AgentDeck API (Updated)
```python
class AgentDeck:
    def __init__(
        self,
        game: Optional[Game] = None,
        spectators: Optional[List[Spectator]] = None,  # Match-level observers
        recorder: Optional[Recorder] = None,
        session: Optional[AgentDeckConfig] = None,
    ):
        """
        Construct AgentDeck instance.

        Args:
            spectators: Match-level observers (watch game narrative)
            session: Configuration with optional monitors field

        Session config monitors field:
            - monitors: Optional[List[Monitor]] = None
              Console-level observers (watch system events)
        """
```

### 5.2 Monitor Usage Patterns
```python
# Pattern 1: Zero-config (default ProgressMonitor)
config = AgentDeckConfig(concurrency=10)  # Auto-attaches ProgressMonitor
deck = AgentDeck(game=game, session=config)

# Pattern 2: Custom monitors
config = AgentDeckConfig(
    concurrency=10,
    monitors=[
        ProgressMonitor(mode="verbose"),
        HardwareMonitor(poll_interval=5),
        SlackNotifier(webhook_url="...")
    ]
)

# Pattern 3: Opt-out (silent execution)
config = AgentDeckConfig(concurrency=10, monitors=[])

# Pattern 4: Sequential execution (no monitors needed)
config = AgentDeckConfig(concurrency=1)  # No default monitor
```

### 5.3 ProgressMonitor (Concrete Implementation)
```python
class ProgressMonitor(Monitor):
    """
    Default console monitor for tracking batch execution progress.

    Modes:
        - quiet: Single-line progress bar (minimal output)
        - normal: Status updates per completion milestone (default)
        - verbose: Detailed worker start/complete/fail logs
    """

    def __init__(self, mode: Literal["quiet", "normal", "verbose"] = "normal"):
        super().__init__()
        self.mode = mode
        self._batch_start_time: Optional[float] = None
        self._completed: int = 0
        self._total: int = 0
        self._failed: int = 0

    def on_console_batch_start(self, event: Event) -> None:
        """Display batch start message."""
        data = event.data
        self._batch_start_time = time.time()
        self._completed = 0
        self._total = data["total_matches"]
        self._failed = 0

        if self.mode == "quiet":
            pass  # Progress bar updates in on_console_batch_progress
        elif self.mode in ("normal", "verbose"):
            mode = data["mode"]
            concurrency = data.get("concurrency", 1)
            msg = f"🚀 Starting batch: {self._total} matches"
            if mode == "parallel":
                msg += f" (concurrency={concurrency})"
            print(msg)

    def on_console_batch_progress(self, event: Event) -> None:
        """Update progress display."""
        data = event.data
        self._completed = data["completed"]

        if self.mode == "quiet":
            # Progress bar: [████████░░] 42/100 (42%)
            pct = (self._completed / self._total) * 100
            bar_width = 20
            filled = int((self._completed / self._total) * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            print(f"\r[{bar}] {self._completed}/{self._total} ({pct:.0f}%)", end="", flush=True)

    def on_console_worker_start(self, event: Event) -> None:
        """Log worker start (verbose mode only)."""
        if self.mode == "verbose":
            data = event.data
            print(f"  ▶ Worker {data['worker_id']}: Starting match {data['match_index']}")

    def on_console_worker_complete(self, event: Event) -> None:
        """Log worker completion."""
        data = event.data
        self._completed += 1

        if self.mode == "normal":
            # Update every 10% or final match
            milestone = self._total // 10 or 1
            if self._completed % milestone == 0 or self._completed == self._total:
                pct = (self._completed / self._total) * 100
                elapsed = time.time() - self._batch_start_time
                avg = elapsed / self._completed
                eta = avg * (self._total - self._completed)
                print(f"  ✓ {self._completed}/{self._total} ({pct:.0f}%) | "
                      f"ETA: {self._format_duration(eta)}")

        elif self.mode == "verbose":
            winner = data.get("winner", "Draw")
            duration = data["duration"]
            turns = data.get("turns", "?")
            print(f"  ✓ Worker {data['worker_id']}: Complete | "
                  f"Winner: {winner} | {turns} turns | {duration:.2f}s")

    def on_console_worker_failed(self, event: Event) -> None:
        """Log worker failure."""
        data = event.data
        self._failed += 1

        if self.mode != "quiet":
            error_type = data["error_type"]
            error_msg = data["error_message"]
            print(f"  ✗ Worker {data['worker_id']}: FAILED | "
                  f"{error_type}: {error_msg}")

    def on_console_batch_complete(self, event: Event) -> None:
        """Display batch completion summary."""
        data = event.data
        duration = data["duration"]
        avg_duration = data.get("avg_match_duration", 0)

        if self.mode == "quiet":
            # Newline after progress bar
            print()

        print(f"🎉 Batch complete: {data['completed']}/{data['total']} matches | "
              f"Duration: {self._format_duration(duration)} | "
              f"Avg: {avg_duration:.2f}s/match")

        if data['failed'] > 0:
            print(f"⚠️  {data['failed']} match(es) failed")

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m"
```

## 6. Invariants & Guarantees

### 6.1 Monitor Lifecycle (ML)
1. **ML1**: Console MUST create separate EventBus for console events (distinct from match EventBus).
2. **ML2**: Console MUST attach default ProgressMonitor when `concurrency > 1` and `config.monitors is None`.
3. **ML3**: Console MUST NOT attach default monitor when `concurrency == 1` (sequential execution).
4. **ML4**: Console MUST respect explicit `monitors=[]` (opt-out) even when `concurrency > 1`.
5. **ML5**: Console MUST inject logger into monitors before subscription (same pattern as spectators, SPEC-SPECTATOR §5.5).

### 6.2 Event Emission (EM)
6. **EM1**: Console MUST emit console events to console EventBus (NOT match EventBus).
7. **EM2**: Console events MUST be emitted immediately (live), NOT buffered for replay.
8. **EM3**: Console MUST emit `CONSOLE_BATCH_START` before first match execution.
9. **EM4**: Console MUST emit `CONSOLE_BATCH_COMPLETE` after last match completes.
10. **EM5**: Console MUST emit `CONSOLE_WORKER_*` events only during parallel execution (`concurrency > 1`).
11. **EM6**: Console MUST emit `CONSOLE_BATCH_PROGRESS` at least once per completed match.

### 6.3 Event Isolation (EI)
12. **EI1**: Monitors MUST NOT receive match events (MATCH_START, GAMEPLAY, TURN_START, etc.).
13. **EI2**: Spectators MUST NOT receive console events (CONSOLE_BATCH_START, CONSOLE_WORKER_*, etc.).
14. **EI3**: Monitor exceptions MUST NOT crash batch execution (isolated via EventBus error handling).
15. **EI4**: Monitor failures MUST be logged via AgentDeckLogger without propagating to caller.

### 6.4 Progress Reporting Accuracy (PA)
16. **PA1**: ProgressMonitor MUST display accurate completed/total counts at all times.
17. **PA2**: ProgressMonitor MUST calculate ETA based on average match duration (not available until first match completes).
18. **PA3**: ProgressMonitor MUST update progress atomically (no race conditions during parallel execution).
19. **PA4**: ProgressMonitor MUST handle worker failures gracefully (increment failed count, continue reporting).

### 6.5 Backward Compatibility (BC)
20. **BC1**: Existing code without `monitors` field MUST work unchanged (default behavior applies).
21. **BC2**: Sequential execution (`concurrency=1`) MUST NOT show progress output unless monitors explicitly provided.
22. **BC3**: Spectator behavior MUST remain unchanged (match EventBus unaffected by console EventBus).

## 7. Data Flow & Interaction

### 7.1 Initialization Flow
```
1. User creates AgentDeckConfig(concurrency=10, monitors=None)
2. AgentDeck.__init__ passes config to Console
3. Console reads config.concurrency and config.monitors
4. If concurrency > 1 and monitors is None:
     Console attaches ProgressMonitor(mode="normal")
5. Console creates console EventBus (separate from match EventBus)
6. Console subscribes monitors to console EventBus
7. Console injects logger into monitors (if monitor.logger is None)
```

### 7.2 Execution Flow (Parallel)
```
1. Console.run() emits CONSOLE_BATCH_START → monitors
2. For each match (via ThreadPoolExecutor):
     a. Console emits CONSOLE_WORKER_START → monitors
     b. Worker executes match (on separate thread)
     c. Worker completes:
          - Console emits CONSOLE_WORKER_COMPLETE → monitors
          - Console emits CONSOLE_BATCH_PROGRESS → monitors
          - Console replays match events to match EventBus → spectators
3. Console emits CONSOLE_BATCH_COMPLETE → monitors
4. Console returns MatchResults to facade
```

### 7.3 Execution Flow (Sequential)
```
1. Console.run() emits CONSOLE_BATCH_START → monitors (if any)
2. For each match (synchronous loop):
     a. Console executes match (no worker)
     b. Console emits match events to match EventBus → spectators
     c. Console emits CONSOLE_BATCH_PROGRESS → monitors (if any)
3. Console emits CONSOLE_BATCH_COMPLETE → monitors (if any)
4. Console returns MatchResults to facade
```

## 8. Error Handling & Edge Cases

### 8.1 Monitor Exceptions
- Console MUST catch monitor exceptions during event handling.
- Console MUST log monitor exceptions via AgentDeckLogger.
- Console MUST continue execution (monitor failures are isolated).
- Console MUST NOT propagate monitor exceptions to caller.

### 8.2 Console EventBus Creation
- Console MUST create console EventBus even when no monitors attached (for future extensibility).
- Console MAY skip console event emission when no monitors subscribed (optimization).

### 8.3 Progress Display Edge Cases
- **Zero matches**: CONSOLE_BATCH_COMPLETE fired immediately with completed=0.
- **Single match**: Progress bar shows 0% → 100% (two states).
- **Worker faster than progress updates**: Acceptable; progress reflects eventual consistency.
- **Long-running spectators**: Progress updates continue; spectator backpressure doesn't block monitors.

### 8.4 Logger Injection
- Console MUST inject logger even if monitor already has logger (respect existing logger, don't overwrite).
- Console MUST handle monitors without logger attribute gracefully (skip injection, don't crash).

## 9. Examples

### Example 1: Default Progress Reporting (Zero-Config)
```python
from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.games import FixedDamageGame
from agentdeck.players import GPTPlayer
from agentdeck.controllers import ActionOnlyController

# Default: ProgressMonitor auto-attached when concurrency > 1
config = AgentDeckConfig(seed=42, concurrency=5)

players = [
    GPTPlayer("Alice", controller=ActionOnlyController()),
    GPTPlayer("Bob", controller=ActionOnlyController())
]

with AgentDeck(game=FixedDamageGame(), session=config) as deck:
    results = deck.play(players, matches=50)

# Output:
# 🚀 Starting batch: 50 matches (concurrency=5)
#   ✓ 5/50 (10%) | ETA: 2m 15s
#   ✓ 10/50 (20%) | ETA: 1m 48s
#   ...
# 🎉 Batch complete: 50/50 matches | Duration: 2m 30s | Avg: 3.0s/match
```

### Example 2: Custom Monitor (Slack Notifications)
```python
from agentdeck.monitors import Monitor
from agentdeck.core.types import Event
import requests

class SlackMonitor(Monitor):
    """Send batch progress to Slack webhook."""

    def __init__(self, webhook_url: str):
        super().__init__()
        self.webhook_url = webhook_url

    def on_console_batch_start(self, event: Event) -> None:
        data = event.data
        msg = f"🚀 Batch started: {data['total_matches']} matches"
        self._send_message(msg)

    def on_console_batch_complete(self, event: Event) -> None:
        data = event.data
        duration = data['duration']
        msg = f"✅ Batch complete: {data['completed']}/{data['total']} matches in {duration:.1f}s"
        self._send_message(msg)

    def on_console_worker_failed(self, event: Event) -> None:
        data = event.data
        msg = f"⚠️ Worker {data['worker_id']} failed: {data['error_message']}"
        self._send_message(msg)

    def _send_message(self, text: str) -> None:
        try:
            requests.post(self.webhook_url, json={"text": text}, timeout=5)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to send Slack notification: {e}")

# Usage
config = AgentDeckConfig(
    concurrency=10,
    monitors=[
        ProgressMonitor(mode="quiet"),  # Console progress bar
        SlackMonitor(webhook_url="https://hooks.slack.com/...")
    ]
)

deck = AgentDeck(game=game, session=config)
deck.play(players, matches=100)
```

### Example 3: Opt-Out (Silent Execution)
```python
# Explicit opt-out: no progress reporting
config = AgentDeckConfig(concurrency=10, monitors=[])

deck = AgentDeck(game=game, session=config)
results = deck.play(players, matches=100)

# Output: (none - silent execution)
```

### Example 4: Hardware Monitoring (Future)
```python
from agentdeck.monitors import ProgressMonitor, HardwareMonitor

config = AgentDeckConfig(
    concurrency=20,
    monitors=[
        ProgressMonitor(mode="normal"),
        HardwareMonitor(poll_interval=10)  # Log CPU/GPU/memory every 10s
    ]
)

# HardwareMonitor emits custom events (e.g., CONSOLE_HARDWARE_SAMPLE)
# that can be captured by other monitors or logged
```

### Example 5: Sequential Execution (No Progress by Default)
```python
# Sequential execution: no default progress monitor
config = AgentDeckConfig(concurrency=1)  # or omit (defaults to 1)

deck = AgentDeck(game=game, session=config)
results = deck.play(players, matches=10)

# Output: (no progress reporting - sequential is fast enough)
```

## 10. Testing Strategy

| Focus | Invariants | Verification Goal |
|-------|------------|-------------------|
| Monitor lifecycle | ML1-ML5 | Verify console EventBus created, default monitor attached when concurrency>1, logger injected |
| Event emission | EM1-EM6 | Capture console events, verify timing/content, ensure isolation from match EventBus |
| Event isolation | EI1-EI4 | Verify monitors don't receive match events, spectators don't receive console events, exceptions isolated |
| Progress accuracy | PA1-PA4 | Verify counts accurate, ETA calculation correct, atomic updates, failure handling |
| Backward compat | BC1-BC3 | Run existing code without monitors field, verify spectators unchanged, sequential execution silent |
| Default behavior | ML2-ML4 | Test concurrency=1 (no monitor), concurrency>1 (auto-attach), explicit monitors=[] (opt-out) |
| Custom monitors | - | Implement custom monitor, verify events received, logger injected, exceptions isolated |
| ProgressMonitor modes | PA1-PA4 | Test quiet/normal/verbose modes, verify output formatting, ETA accuracy |

### Concrete Test Examples

#### Test 1: Default ProgressMonitor attachment
```python
def test_default_progress_monitor():
    """Verify ProgressMonitor auto-attached when concurrency > 1."""
    config = AgentDeckConfig(concurrency=5)

    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        # Verify console created console EventBus
        assert hasattr(deck.console, 'console_bus')

        # Verify ProgressMonitor attached
        monitors = [
            sub for sub in deck.console.console_bus._subscribers
            if isinstance(sub, ProgressMonitor)
        ]
        assert len(monitors) == 1
        assert monitors[0].mode == "normal"

def test_no_default_monitor_sequential():
    """Verify no default monitor for sequential execution."""
    config = AgentDeckConfig(concurrency=1)

    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        # Console EventBus created, but no monitors attached
        monitors = [
            sub for sub in deck.console.console_bus._subscribers
            if isinstance(sub, ProgressMonitor)
        ]
        assert len(monitors) == 0

def test_explicit_opt_out():
    """Verify monitors=[] opts out of default monitor."""
    config = AgentDeckConfig(concurrency=10, monitors=[])

    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        # No monitors attached (explicit opt-out)
        assert len(deck.console.console_bus._subscribers) == 0
```

#### Test 2: Console event emission
```python
def test_console_events_emitted():
    """Verify console events emitted during parallel execution."""
    class EventCollector(Monitor):
        def __init__(self):
            super().__init__()
            self.events = []

        def on_console_batch_start(self, event):
            self.events.append(("batch_start", event.data))

        def on_console_worker_complete(self, event):
            self.events.append(("worker_complete", event.data))

        def on_console_batch_complete(self, event):
            self.events.append(("batch_complete", event.data))

    collector = EventCollector()
    config = AgentDeckConfig(concurrency=3, monitors=[collector])

    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        deck.play(players, matches=5)

    # Verify event sequence
    event_types = [e[0] for e in collector.events]
    assert event_types[0] == "batch_start"
    assert event_types[-1] == "batch_complete"
    assert event_types.count("worker_complete") == 5

    # Verify batch_complete payload
    batch_complete = collector.events[-1][1]
    assert batch_complete["completed"] == 5
    assert batch_complete["total"] == 5
    assert "duration" in batch_complete
```

#### Test 3: Event isolation
```python
def test_event_isolation():
    """Verify monitors don't receive match events, spectators don't receive console events."""
    class MonitorSpy(Monitor):
        def __init__(self):
            super().__init__()
            self.received_events = []

        def __getattribute__(self, name):
            # Track all on_* method calls
            attr = object.__getattribute__(self, name)
            if name.startswith("on_") and callable(attr):
                def wrapper(*args, **kwargs):
                    self.received_events.append(name)
                    return attr(*args, **kwargs)
                return wrapper
            return attr

    class SpectatorSpy(Spectator):
        def __init__(self):
            super().__init__()
            self.received_events = []

        def __getattribute__(self, name):
            # Track all on_* method calls
            attr = object.__getattribute__(self, name)
            if name.startswith("on_") and callable(attr):
                def wrapper(*args, **kwargs):
                    self.received_events.append(name)
                    return attr(*args, **kwargs)
                return wrapper
            return attr

    monitor = MonitorSpy()
    spectator = SpectatorSpy()

    config = AgentDeckConfig(concurrency=2, monitors=[monitor])
    with AgentDeck(game=FixedDamageGame(), spectators=[spectator], session=config) as deck:
        deck.play(players, matches=2)

    # Monitor receives only console events
    assert all(evt.startswith("on_console_") for evt in monitor.received_events)

    # Spectator receives only match events (no console events)
    assert not any(evt.startswith("on_console_") for evt in spectator.received_events)
    assert any(evt in ("on_batch_start", "on_match_start") for evt in spectator.received_events)
```

#### Test 4: ProgressMonitor output modes
```python
def test_progress_monitor_modes(capsys):
    """Verify ProgressMonitor quiet/normal/verbose modes produce correct output."""

    # Test quiet mode
    config = AgentDeckConfig(concurrency=2, monitors=[ProgressMonitor(mode="quiet")])
    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        deck.play(players, matches=10)

    captured = capsys.readouterr()
    assert "[████████████████████]" in captured.out  # Progress bar
    assert "10/10 (100%)" in captured.out

    # Test normal mode
    config = AgentDeckConfig(concurrency=2, monitors=[ProgressMonitor(mode="normal")])
    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        deck.play(players, matches=10)

    captured = capsys.readouterr()
    assert "🚀 Starting batch" in captured.out
    assert "✓" in captured.out  # Completion markers
    assert "🎉 Batch complete" in captured.out

    # Test verbose mode
    config = AgentDeckConfig(concurrency=2, monitors=[ProgressMonitor(mode="verbose")])
    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        deck.play(players, matches=10)

    captured = capsys.readouterr()
    assert "▶ Worker" in captured.out  # Worker start logs
    assert "✓ Worker" in captured.out  # Worker complete logs
```

#### Test 5: Monitor exception isolation
```python
def test_monitor_exception_isolation():
    """Verify monitor exceptions don't crash execution."""
    class CrashingMonitor(Monitor):
        def on_console_batch_start(self, event):
            raise RuntimeError("Monitor crashed!")

    class HealthyMonitor(Monitor):
        def __init__(self):
            super().__init__()
            self.events_received = 0

        def on_console_batch_start(self, event):
            self.events_received += 1

    crashing = CrashingMonitor()
    healthy = HealthyMonitor()

    config = AgentDeckConfig(concurrency=2, monitors=[crashing, healthy])

    with AgentDeck(game=FixedDamageGame(), session=config) as deck:
        results = deck.play(players, matches=5)

    # Execution completed despite crashing monitor
    assert len(results) == 5

    # Healthy monitor received events
    assert healthy.events_received > 0
```

## 11. Open Questions / Future Work

### Hardware Monitoring
- Should framework provide built-in `HardwareMonitor` for CPU/GPU/memory tracking?
- What polling interval and event format best serve researchers?

### Checkpoint Integration
- Should `CheckpointMonitor` handle save/resume automatically, or require explicit user hooks?
- How to represent partial batch progress for resumption?

### Distributed Execution
- How should monitors aggregate progress across distributed workers (multi-host)?
- Should console emit distributed-specific events (NODE_START, NODE_FAILED)?

### Monitor Composition
- Should framework support monitor pipelines (one monitor feeds another)?
- How to handle inter-monitor dependencies?

### Dynamic Attach/Detach
- Should monitors be attachable mid-batch (e.g., attach HardwareMonitor after 50 matches)?
- What semantics govern late-attached monitors (receive backlog vs start fresh)?

### Progress Persistence
- Should ProgressMonitor write progress to file for external monitoring tools?
- What format (JSON lines, structured logs, custom)?

### Console Event Filtering
- Should monitors declare which console events they care about (avoid unnecessary calls)?
- Performance impact assessment needed.

## 12. Design Rationale

### Two-Tier Event System
- **Separation preserves existing semantics:** Match EventBus (buffered, replayed) unchanged; console EventBus (live, immediate) added without conflict.
- **Clear responsibility boundaries:** Spectators observe "what happened in the game," monitors observe "how the system is executing."
- **Analogy alignment:** Spectators = fans watching match, monitors = production crew managing system. Distinct roles, distinct observation points.

### Auto-Attach Default Monitor
- **Zero-config UX:** Researchers running parallel batches get progress visibility by default without code changes.
- **Opt-out available:** Explicit `monitors=[]` provides escape hatch for silent execution.
- **Sequential execution unchanged:** `concurrency=1` remains fast and quiet (no progress overhead).

### Duck-Typed Handlers
- **Consistency with spectators:** Same `on_<event>` pattern, familiar to existing users.
- **Flexibility:** Implement only needed handlers, skip rest without boilerplate.
- **Testability:** Mock specific handlers easily, verify event routing.

### Live Event Emission (Not Buffered)
- **Real-time feedback:** Researchers see progress as it happens (critical for long-running batches).
- **No replay semantics needed:** Progress is ephemeral; replay focuses on match narrative.
- **Performance:** Skip buffering overhead for events that don't need ordering guarantees.

### ProgressMonitor Modes
- **Quiet:** Minimal output for CI/scripts (progress bar only).
- **Normal:** Balance of visibility and verbosity for interactive sessions.
- **Verbose:** Detailed diagnostics for debugging slow matches or worker failures.

### Module Naming: `monitors` (not `console_spectators`)
- **Avoids overloading "spectator":** Preserves strong association between spectators and match watching.
- **Product clarity:** "Monitor" aligns with production crew/scoreboard analogy (system oversight).
- **Engineering clarity:** "Monitor" is standard term for system observability (familiar to developers).

## 13. References

### Specifications
- [SPEC-SPECTATOR.md](./SPEC-SPECTATOR.md) v1.2.0 (Match-level observation contract, logger injection pattern)
- [SPEC-CONSOLE.md](./SPEC-CONSOLE.md) v0.4.0 (Console responsibilities, EventBus ownership, lifecycle events)
- [SPEC-PARALLEL.md](./SPEC-PARALLEL.md) v0.1.0 (Parallel execution semantics, worker lifecycle, event replay)
- [SPEC-OBSERVABILITY.md](./SPEC-OBSERVABILITY.md) (Event types, EventContext structure, emission boundaries)
- [SPEC-AGENTDECK.md](./SPEC-AGENTDECK.md) (Facade contract, spectator attachment scopes)
- [AGENTS.md](./AGENTS.md) §2.1 (Separation of concerns), §2.2 (Simplicity)
- [SPEC.md](./SPEC.md) §1 (Research-first design), §2.4 (Observability)

### Implementation References (Planned)
- `src/agentdeck/monitors/__init__.py`
- `src/agentdeck/monitors/progress.py` (ProgressMonitor implementation)
- `src/agentdeck/core/console.py` (Console EventBus creation, monitor attachment)
- `src/agentdeck/core/types.py` (Console event types)
- `src/agentdeck/core/session.py` (AgentDeckConfig.monitors field)
