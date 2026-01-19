# SPEC-SPECTATOR: Observer Contract

> Status: Draft v1.2.0 (Logger Injection)
> Version: 1.2.0
> Last Updated: 2025-10-31
> Implementation: ✅ Complete (Console & ReplayEngine logger injection)
> Authors: Diego ZoracKy, Codex, Claude (consensus)
> Audience: Spectator authors, analytics engineers, observability contributors

## 1. Purpose
- Define the observer interface for monitoring live and replayed matches via event handlers.
- Guarantee read-only, fault-isolated spectators that compose via duck-typed `on_<event>` methods.
- Specify scope semantics (session vs execution), context access patterns, and error handling for production analytics.

## 2. Scope & Philosophy Alignment
- Upholds `SPEC.md` §3.2 separation: spectators observe, never mutate. Framework owns execution, spectators own analysis.
- Reinforces `SPEC-OBSERVABILITY.md`: spectators consume Event objects with EventContext envelopes for consistent metadata access.
- Aligns with `SPEC.md` §1.2: enable custom spectators in <20 lines while scaling to production dashboards and analytics pipelines.
- **Clean slate design**: v1.0.0 assumes modern event system (SPEC-OBSERVABILITY §3) with three-phase player lifecycle—no legacy event formats, no backward compatibility shims.
- **Error isolation**: Spectator exceptions MUST NOT crash matches. Framework logs errors and continues execution.
- Non-goals: event emission (`SPEC-CONSOLE.md`, `SPEC-GAME.md`), recording (`SPEC-RECORDER.md`), or replay logic (`SPEC-REPLAY.md`).

## 3. Responsibilities
- **Event handling**: Implement `on_<event>` methods to react to lifecycle, gameplay, or domain events emitted by console/replay engine.
- **Read-only analysis**: Inspect event payloads/context without mutating shared state or returning values to the engine.
- **Scope awareness**: Respect session vs execution attachment semantics (session spectators persistent; execution spectators per `play`/`replay` call).
- **Context access**: Use `event.context` or `context` parameter to access `session_id`, `batch_id`, `match_id`, `phase_index`, timestamps.
- **Stateful analysis**: Maintain internal state across events (cumulative stats, win rates, turn-by-turn logs) with explicit resets as needed.
- **Logging/reporting**: Optionally use the injected `logger` for structured output; avoid stdout unless explicitly desired.

## 4. Public API
- `class Spectator`
  - Constructor: `__init__(*, logger=None)` accepts optional logger (framework may inject late-bound).
  - Event handlers (all optional, duck-typed):
    - **Session lifecycle**: `on_session_start(deck, context=None)`, `on_session_end(deck, context=None)`
    - **Batch lifecycle**: `on_batch_start(batch_id, game, players, matches, context=None)`, `on_batch_end(batch_id, results, context=None)`
    - **Match lifecycle**: `on_match_start(game, players, match_id=None, context=None)`, `on_match_end(result, context=None)`
    - **Player lifecycle** (Recorder schema v1.3): `on_player_handshake_start(event: Event)`, `on_player_handshake_complete(event: Event)`, `on_player_handshake_abort(event: Event)`, `on_player_conclusion(event: Event)`
    - **Gameplay**: `on_gameplay(event: Event)` (Event contains data + context)
    - **Domain events**: `on_event(event: Event, context=None)`, `on_<custom_event>(event: Event)` (game-specific)
    - **Logging**: `on_log(message, level, log_context, context=None)`
  - Helper: `context_from(context) -> SpectatorContext` (convert EventContext dict to typed object)
- Spectators MAY override any subset of handlers; unimplemented handlers are silently skipped (duck-typing).
- Prompt metadata for handshake/turn/conclusion/parse_failure events is exposed via `event.data["prompt"]` (Recorder schema v1.3). Spectators SHOULD read prompt transcripts from this payload rather than expecting separate dialogue callbacks.

## 5. Reference Spectators

### MatchNarrator (Auto-Attached by Default)

- **Purpose**: Provide turn-by-turn narration (handshake, actions, state deltas, reflections) so researchers see the full story of each match without needing to attach spectators manually.
- **Default Behavior**: When callers omit the `spectators` parameter, Console auto-attaches `MatchNarrator` (see SPEC-CONSOLE §5 "Default Session Spectators"). Output flows through the session logger at INFO level, appearing in the console and `info.log`.
- **Opt-Out**: Researchers silence the narration by supplying their own spectator list. Passing `spectators=[]` yields a quiet run; passing `spectators=[CustomSpectator(...)]` entirely replaces the default narrator.
- **Usage**: MatchNarrator remains available for explicit attachment (`spectators=[MatchNarrator(mode=...)]`) when researchers want to control verbosity, enrich output, or use it alongside other observers.

### [v1.1.0] Research Spectators (SPEC-RESEARCH.md v1.1.0)

**StatisticalAnalysisSpectator**
- **Purpose**: Auto-run post-hoc statistical analysis when batch completes.
- **Implementation**: Thin wrapper that calls `StatisticalAnalysis.from_session()` on `on_batch_end()`.
- **Usage**: `spectators=[StatisticalAnalysisSpectator(print_on_complete=True, save_report=True)]`
- **Output**: Automatically prints win rates, confidence intervals, p-values, effect sizes, and cross-player comparisons.

**PerformanceTrackerSpectator**
- **Purpose**: Auto-run performance analysis (duration, throughput, speedup) when batch completes.
- **Implementation**: Thin wrapper that calls `PerformanceAnalysis.from_session()` on `on_batch_end()`.
- **Usage**: `spectators=[PerformanceTrackerSpectator(baseline_duration=300.0)]`

**CostAnalysisSpectator**
- **Purpose**: Auto-run cost analysis (total cost, cost per match, cost efficiency) when batch completes.
- **Implementation**: Thin wrapper that calls `CostAnalysis.from_session()` on `on_batch_end()`.
- **Usage**: `spectators=[CostAnalysisSpectator(baseline_cost=0.04)]`

**Note**: These spectators require recordings to exist. They read from `agentdeck_runs/session_id/` after matches complete. All analysis logic lives in `agentdeck.research` module; spectators are convenience wrappers only.

## 6. Invariants & Guarantees
### 6.1 Handler Contract (HC)
1. **HC1**: All event handlers MUST be optional (default no-op in base class). Framework routes via duck-typing (`hasattr` check), not `isinstance`.
2. **HC2**: Handlers MUST accept the exact signature documented (extra positional args not passed). Lifecycle handlers accept individual parameters; event-based handlers accept `Event` object.
3. **HC3**: Handlers MUST NOT mutate event payloads or context dictionaries (treat as read-only). Framework may reuse objects across spectators.
4. **HC4**: Handlers SHOULD complete quickly. Long-running work SHOULD defer to external workers to avoid blocking console/replay.

### 6.2 Scope & State (SS)
5. **SS1**: Session spectators MUST receive all events (session, batch, match, gameplay) across deck lifetime until `on_session_end`.
6. **SS2**: Execution spectators MUST receive only batch/match/gameplay events for the current `play`/`replay` call. Framework MUST unsubscribe after `on_batch_end`.
7. **SS3**: Spectators MUST manage their own state resets between executions (e.g., clear counters in `on_batch_start` or `on_match_start`).
8. **SS4**: Spectators MUST tolerate missing context fields (legacy recordings or early lifecycle events may omit `phase_index`, `match_id`, etc.). Use `.get()` or `SpectatorContext` helper.

### 6.3 Error Isolation (EI)
9. **EI1**: Spectator exceptions MUST be caught and logged by framework. Execution MUST continue with remaining spectators (fail gracefully, not globally).
10. **EI2**: Spectators SHOULD avoid raising in `on_session_end`/`on_batch_end` to prevent cleanup noise. Log warnings instead.
11. **EI3**: Spectators MUST NOT attempt to modify player/game state or call console methods that affect execution (read-only contract).

### 5.4 Logging & Output (LO)
12. **LO1**: When logger supplied, spectators SHOULD use `logger` instead of `print` for structured logging.
13. **LO2**: Spectators writing to disk or network MUST handle failures gracefully and surface informative errors.

### 5.5 Logger Injection (LI)
14. **LI1**: Console and ReplayEngine MUST inject logger into spectators if spectator has no logger (late-binding pattern). Check `if getattr(spectator, "logger", None) is None` before subscription.
15. **LI2**: Injected logger MUST be the same `AgentDeckLogger` instance used by Console/ReplayEngine (shared logging context).
16. **LI3**: Spectators MAY receive logger via constructor (`__init__(logger=logger)`), bypassing late-binding injection.
17. **LI4**: Logger injection MUST occur for BOTH session spectators (attached at Console construction) AND execution spectators (attached during `play`/`replay` call).
18. **LI5**: When spectator uses logger, it WRITES to core log streams (info.log, debug.log, console) via `logger.info()`, `logger.debug()`, etc.

### 5.6 Context Access (CA)
19. **CA1**: EventContext MUST include `session_id` (except early construction events before session initialization).
20. **CA2**: EventContext MUST include `match_id` during match execution (between `MATCH_START` and `MATCH_END`).
21. **CA3**: EventContext MUST include `phase_index` during GAMEPLAY events and domain events emitted during gameplay. Player lifecycle events (handshake, conclusion) MAY omit `phase_index` per SPEC-OBSERVABILITY §4.1.

## 6. Data Flow & Interaction
- **Registration**: AgentDeck/Console attaches session spectators during construction; execution spectators added per `play`/`replay` call.
- **Logger injection**: Console/ReplayEngine injects logger into spectators before EventBus subscription if `spectator.logger is None` (late-binding pattern per LI1-LI4).
- **Event dispatch**: EventBus inspects spectators for `on_<event>` methods; calls them with event payloads and context copies.
- **Event ordering**:
  - **Session scope**: SESSION_START → BATCH_START → PLAYER_HANDSHAKE_* → MATCH_START → GAMEPLAY → PLAYER_CONCLUSION (optional) → MATCH_END → BATCH_END → SESSION_END
  - **Execution scope**: BATCH_START → PLAYER_HANDSHAKE_* → MATCH_START → GAMEPLAY → PLAYER_CONCLUSION (optional) → MATCH_END → BATCH_END
  - Per SPEC-CONSOLE §6.6 E1, handshake events precede MATCH_START to ensure players acknowledge before match begins
- **Context usage**: Spectators call `context_from(context)` to access typed fields (`session_id`, `batch_id`, `match_id`, `phase_index`, timestamps).
- **Replay**: ReplayEngine reuses the same spectator API, ensuring replayed events trigger identical handlers.

## 7. Error Handling & Edge Cases
- Spectators MUST handle missing context fields (e.g., `match_id` absent on session events) without crashing.
- For replay, event payloads may include `ActionResult` objects; spectators should treat them as immutable.
- Spectators should anticipate duplicate events if attached to both session and execution scope (avoid double-counting by referencing `batch_id` / `match_id`).
- When long-running analysis is required, spectators should queue work asynchronously rather than blocking the main loop.
- Spectators SHOULD use defensive copies when storing event data (e.g., `copy.deepcopy(event.data)`).

## 8. Examples

### Example 1: Simple Win Rate Tracker (Session Scope)
```python
class WinRateTracker(Spectator):
    def __init__(self):
        super().__init__()
        self.wins = {}
        self.matches = 0

    def on_match_end(self, result, context=None):
        self.matches += 1
        winner = result.winner or "draw"
        self.wins[winner] = self.wins.get(winner, 0) + 1

    def summary(self):
        if self.matches == 0:
            return {}
        return {p: wins / self.matches for p, wins in self.wins.items()}

# Usage: Session scope (persistent across all play() calls)
with AgentDeck(spectators=[WinRateTracker()]) as deck:
    deck.play(game, players, matches=10)
    tracker = deck.spectators[0]
    print(tracker.summary())  # {"Alice": 0.6, "Bob": 0.4}
```

### Example 2: Turn-by-Turn Logger (Execution Scope)
```python
class TurnLogger(Spectator):
    def __init__(self):
        super().__init__()
        self.turn_count = 0

    def on_gameplay(self, event):
        ctx = self.context_from(event.context)
        data = event.data
        self.turn_count += 1
        print(f"[Turn {ctx.phase_index}] {data['player']} → {data['action'].action}")

    def on_batch_end(self, batch_id, results, context=None):
        print(f"Total turns logged: {self.turn_count}")

# Usage: Execution scope (attached per play() call)
deck.play(game, players, matches=1, spectators=[TurnLogger()])
# Output:
# [Turn 0] Alice → ATTACK
# [Turn 1] Bob → DEFEND
# ...
# Total turns logged: 42
```

### Example 3: Domain Event Handler (Card Game)
```python
class CardTracker(Spectator):
    def __init__(self):
        super().__init__()
        self.cards_drawn = []

    def on_card_drawn(self, event):
        # Automatically called when game emits "card_drawn" event
        # Framework routes based on event.type (snake_case → on_snake_case)
        data = event.data
        ctx = self.context_from(event.context)
        self.cards_drawn.append({
            "player": data['player'],
            "card": data['card'],
            "turn": ctx.phase_index,
            "match": ctx.match_id
        })

    def on_batch_end(self, batch_id, results, context=None):
        # Analyze card distribution across matches
        from collections import Counter
        card_counts = Counter(card['card'] for card in self.cards_drawn)
        print(f"Most drawn cards: {card_counts.most_common(5)}")

# Game emits:
# self.emit_event("card_drawn", player="Alice", card="Ace of Spades")

# Spectator receives via on_card_drawn()
```

### Example 4: Batch Summary Logger with Context Helper
```python
class BatchLogger(Spectator):
    def on_batch_end(self, batch_id, results, context=None):
        ctx = self.context_from(context)

        # Aggregate results
        winners = [r.winner for r in results if r.winner]
        total_turns = sum(len(r.events) for r in results)

        self.logger.info(
            "Batch complete",
            extra={
                "session_id": ctx.session_id,
                "batch_id": batch_id,
                "matches_completed": len(results),
                "total_turns": total_turns,
                "winners": winners,
            },
        )
```

### Example 5: Player Lifecycle Tracker (v1.0.0)
```python
class PlayerLifecycleTracker(Spectator):
    def __init__(self):
        super().__init__()
        self.handshake_starts = []
        self.handshake_results = []
        self.conclusions = []

    def on_player_handshake_start(self, event: Event):
        """Called when handshake begins (before LLM call)."""
        data = event.data
        self.handshake_starts.append({
            "player": data['player'],
            "match_id": data['match_id'],
            "prompt_text": data.get('prompt_text')
        })

    def on_player_handshake_complete(self, event: Event):
        """Called when player acknowledges successfully."""
        data = event.data
        self.handshake_results.append({
            "player": data['player'],
            "normalized": data['normalized_response'],
            "accepted": True
        })

    def on_player_handshake_abort(self, event: Event):
        """Called when player rejects handshake."""
        data = event.data
        self.handshake_results.append({
            "player": data['player'],
            "reason": data['reason'],
            "accepted": False
        })

    def on_player_conclusion(self, event: Event):
        """Called when player completes post-match reflection."""
        data = event.data
        self.conclusions.append({
            "player": data['player'],
            "reflection": data['reflection_text']
        })

    def summary(self):
        accepted = sum(1 for h in self.handshake_results if h['accepted'])
        return {
            "handshake_starts": len(self.handshake_starts),
            "handshakes": len(self.handshake_results),
            "accepted": accepted,
            "rejected": len(self.handshake_results) - accepted,
            "conclusions": len(self.conclusions)
        }
```

### Example 6: Logger Usage (Logger Injection - LI1-LI5)
```python
class MatchNarrativeLogger(Spectator):
    """
    Spectator that writes turn-by-turn narrative to INFO log.

    Demonstrates LI1-LI5:
    - LI1: Console injects logger automatically (no logger in __init__)
    - LI5: Uses logger.info() to write to core log streams (info.log + console)
    """

    def __init__(self):
        super().__init__()
        # LI1: No logger parameter - Console will inject it
        # After Console construction, self.logger will be AgentDeckLogger instance

    def on_batch_start(self, batch_id, game, players, matches, context=None):
        """Log batch start at INFO level."""
        if self.logger:
            # LI5: Writes to info.log and console (if INFO enabled)
            self.logger.info(f"Starting batch {batch_id[:8]} with {matches} matches")

    def on_gameplay(self, event):
        """Log each turn at INFO level with state deltas."""
        data = event.data
        ctx = self.context_from(event.context)

        player = data.get('player')
        action_dict = data.get('action', {})
        action = action_dict.get('action') if isinstance(action_dict, dict) else str(action_dict)

        # Extract state delta
        state_before = data.get('state_before', {})
        state_after = data.get('state_after', {})
        delta = self._format_state_diff(state_before, state_after)

        # Extract token usage if available
        metadata = action_dict.get('metadata', {}) if isinstance(action_dict, dict) else {}
        usage_info = metadata.get('usage_info', {})
        token_str = ""
        if usage_info:
            tokens = usage_info.get('tokens', 0)
            prompt = usage_info.get('prompt_tokens', 0)
            completion = usage_info.get('completion_tokens', 0)
            token_str = f" | tokens={tokens} (prompt={prompt}, completion={completion})"

        # LI5: Write rich INFO-level narrative to core log streams
        if self.logger:
            self.logger.info(
                f"Turn {ctx.phase_index}: {player}\n"
                f"  Action: {action}{token_str}\n"
                f"  State Δ: {delta}"
            )

    def _format_state_diff(self, before, after):
        """Generic state delta formatter."""
        changes = []
        all_keys = set(before.keys()) | set(after.keys())

        for key in sorted(all_keys):
            if key not in before:
                changes.append(f"{key}=new")
            elif key not in after:
                changes.append(f"{key}=removed")
            elif before[key] != after[key]:
                changes.append(f"{key}:{before[key]}->{after[key]}")

        return ", ".join(changes) if changes else "no change"

# Usage: Session scope
with AgentDeck(spectators=[MatchNarrativeLogger()]) as deck:
    deck.play(game, players, matches=1)

# Output in info.log and console (if INFO level):
# [2025-10-25 13:45:12] Starting batch a1b2c3d4 with 1 matches
# [2025-10-25 13:45:13] Turn 0: Player-1
#   Action: ATTACK | tokens=155 (prompt=153, completion=2)
#   State Δ: health.Player-2:100->80, last_action.Player-1:None->ATTACK
# [2025-10-25 13:45:14] Turn 1: Player-2
#   Action: POTION | tokens=148 (prompt=146, completion=2)
#   State Δ: health.Player-2:80->100, potions.Player-2:3->2, last_action.Player-2:None->POTION
# ...
```

### Example 7: TokenUsageTracker (Pricing Integration)
```python
from agentdeck.spectators import Spectator
from agentdeck.utils.pricing import calculate_cost

class TokenUsageTracker(Spectator):
    """
    Track LLM token usage and costs per player/model.

    Integration Requirements (SPEC-PRICING § 8):
    - T1: Defensive extraction - validate usage_info is dict before accessing
    - T2: Graceful fallback - skip cost calculation if usage_info missing
    - T3: Zero-cost tolerance - display $0.00 if pricing data missing
    """

    def __init__(self):
        super().__init__()
        self._costs = {}       # {player_name: total_cost}
        self._tokens = {}      # {player_name: {prompt: int, completion: int}}
        self._player_cache = {}  # {player_name: player_object}

    def on_batch_start(self, batch_id, game, players, matches, context=None):
        """Reset state for new batch."""
        self._costs = {p.name: 0.0 for p in players}
        self._tokens = {p.name: {"prompt": 0, "completion": 0} for p in players}
        self._player_cache = {p.name: p for p in players}

    def on_gameplay(self, event):
        """
        Extract usage_info from GAMEPLAY events and calculate costs.

        Metadata Flow (SPEC-PRICING § 7):
        - M1: LLMPlayer captures usage_info in ActionResult.metadata
        - M2: usage_info flows through ActionResult.metadata
        - M3: usage_info preserved in GAMEPLAY events
        """
        data = event.data
        player_name = data.get("player")
        action = data.get("action")

        if not player_name or not action:
            return

        # T1: Defensive extraction (validate usage_info is dict)
        if isinstance(action, dict):
            metadata = action.get("metadata", {})
        elif hasattr(action, "metadata"):
            metadata = action.metadata
        else:
            return  # T2: Graceful fallback

        usage_info = metadata.get("usage_info")

        # T1: Validate usage_info is dict before accessing fields
        if not usage_info or not isinstance(usage_info, dict):
            return  # T2: Graceful fallback (skip cost calculation)

        prompt_tokens = usage_info.get("prompt_tokens", 0)
        completion_tokens = usage_info.get("completion_tokens", 0)

        if prompt_tokens == 0 and completion_tokens == 0:
            return  # No usage to track

        # Update token counts
        self._tokens[player_name]["prompt"] += prompt_tokens
        self._tokens[player_name]["completion"] += completion_tokens

        # Calculate cost (SPEC-PRICING § 6.1)
        player = self._player_cache.get(player_name)
        if player and hasattr(player, "PROVIDER"):
            provider = player.PROVIDER  # P1: PROVIDER constant required
            model = player.model        # P2: Model from player.model attribute

            try:
                cost = calculate_cost(provider, model, prompt_tokens, completion_tokens)
                self._costs[player_name] += cost
            except Exception as e:
                # T3: Zero-cost tolerance (pricing.calculate_cost logs ERROR, returns 0.0)
                self.logger.warning(f"Cost calculation failed for {player_name}: {e}")

    def on_batch_end(self, batch_id, results, context=None):
        """Display summary of token usage and costs."""
        print("\n=== Token Usage Summary ===")
        for player_name in sorted(self._costs.keys()):
            prompt = self._tokens[player_name]["prompt"]
            completion = self._tokens[player_name]["completion"]
            total = prompt + completion
            cost = self._costs[player_name]

            # T3: Display $0.00 if pricing data missing (not error)
            print(f"{player_name:20s} │ {prompt:8,d} in │ {completion:8,d} out │ "
                  f"{total:8,d} total │ ${cost:.4f}")

        total_cost = sum(self._costs.values())
        print(f"{'Total':20s} │ {' '*8s} │ {' '*8s} │ {' '*8s} │ ${total_cost:.4f}")
        print()

    def get_summary(self):
        """Return structured summary for programmatic access."""
        return {
            "costs": dict(self._costs),
            "tokens": dict(self._tokens),
            "total_cost": sum(self._costs.values()),
            "total_tokens": sum(
                t["prompt"] + t["completion"]
                for t in self._tokens.values()
            )
        }

# Usage: Session scope (track costs across all play() calls)
tracker = TokenUsageTracker()
with AgentDeck(spectators=[tracker]) as deck:
    deck.play(game, players, matches=10)
    summary = tracker.get_summary()
    print(f"Total experiment cost: ${summary['total_cost']:.2f}")

# Output example:
# === Token Usage Summary ===
# Alice (gpt-4o-mini)  │    1,234 in │    5,678 out │    6,912 total │ $0.0035
# Bob (claude-3-5-ha…) │    2,345 in │    6,789 out │    9,134 total │ $0.0289
# Total                │          │          │          │ $0.0324
```

## 9. Testing Strategy
| Focus | Invariants | Verification |
|-------|------------|--------------|
| Handler signatures | HC1-HC4 | Attach spectator with mocked handlers; ensure events invoke correct methods without mutation. Verify duck-typing (missing handlers don't crash). |
| Scope behaviour | SS1-SS4 | Combine session + execution spectators; verify state resets correctly and context tolerates missing fields. |
| Error isolation | EI1-EI3 | Force spectator exceptions; confirm framework logs error without crashing remaining spectators or execution. |
| Logging/output | LO1-LO2 | Provide mock logger; assert log calls executed and disk/network writes handle failures gracefully. |
| Logger injection | LI1-LI5 | Verify Console/ReplayEngine injects logger into spectators before subscription. Test both session and execution scope injection. Confirm spectator logger writes to core log streams. |
| Context access | CA1-CA3 | Inspect EventContext in handlers; verify required fields present for each event type. |

### Concrete Test Examples

#### Test 1: Duck-typed handlers (HC1)
```python
def test_duck_typed_handlers():
    class MinimalSpectator(Spectator):
        def __init__(self):
            super().__init__()
            self.match_starts = 0

        def on_match_start(self, game, players, match_id=None, context=None):
            self.match_starts += 1

    spectator = MinimalSpectator()
    deck = AgentDeck(spectators=[spectator])

    deck.play(game, players, matches=3)

    # Verify only implemented handler was called
    assert spectator.match_starts == 3
    # Missing handlers (on_gameplay, etc.) silently skipped
```

#### Test 2: Session vs execution scope (SS1, SS2)
```python
def test_spectator_scopes():
    class ScopeTracker(Spectator):
        def __init__(self, name):
            super().__init__()
            self.name = name
            self.events = []

        def on_batch_start(self, batch_id, game, players, matches, context=None):
            self.events.append(f"{self.name}:batch_start:{batch_id}")

        def on_batch_end(self, batch_id, results, context=None):
            self.events.append(f"{self.name}:batch_end:{batch_id}")

    session_spec = ScopeTracker("session")
    exec_spec_1 = ScopeTracker("exec1")
    exec_spec_2 = ScopeTracker("exec2")

    deck = AgentDeck(spectators=[session_spec])

    # First execution
    deck.play(game, players, matches=2, spectators=[exec_spec_1])

    # Second execution
    deck.play(game, players, matches=2, spectators=[exec_spec_2])

    # Session spectator sees both executions
    assert len(session_spec.events) == 4  # 2 start + 2 end

    # Execution spectators see only their execution
    assert len(exec_spec_1.events) == 2  # 1 start + 1 end
    assert len(exec_spec_2.events) == 2  # 1 start + 1 end
```

#### Test 3: Error isolation (EI1)
```python
def test_spectator_error_isolation():
    class CrashingSpectator(Spectator):
        def on_match_start(self, game, players, match_id=None, context=None):
            raise RuntimeError("Spectator crashed!")

    class HealthySpectator(Spectator):
        def __init__(self):
            super().__init__()
            self.match_starts = 0

        def on_match_start(self, game, players, match_id=None, context=None):
            self.match_starts += 1

    crashing = CrashingSpectator()
    healthy = HealthySpectator()

    deck = AgentDeck(spectators=[crashing, healthy])

    # Execution continues despite crashing spectator
    results = deck.play(game, players, matches=2)

    assert len(results) == 2  # Both matches completed
    assert healthy.match_starts == 2  # Healthy spectator received events
```

#### Test 4: Context field tolerance (SS4)
```python
def test_missing_context_fields():
    class RobustSpectator(Spectator):
        def __init__(self):
            super().__init__()
            self.events = []

        def on_match_start(self, game, players, match_id=None, context=None):
            ctx = self.context_from(context)
            # Gracefully handle missing fields
            self.events.append({
                "session_id": ctx.session_id,  # May be None
                "match_id": ctx.match_id,      # May be None
                "phase_index": ctx.phase_index  # May be None
            })

    spectator = RobustSpectator()

    # Call with minimal context
    spectator.on_match_start(game, players, context={"batch_id": "test"})

    # Should not crash, fields should be None
    assert spectator.events[0]["session_id"] is None
    assert spectator.events[0]["phase_index"] is None
```

#### Test 5: State reset between executions (SS3)
```python
def test_state_reset():
    class StatefulSpectator(Spectator):
        def __init__(self):
            super().__init__()
            self.match_count = 0

        def on_batch_start(self, batch_id, game, players, matches, context=None):
            # Explicitly reset state at batch start
            self.match_count = 0

        def on_match_end(self, result, context=None):
            self.match_count += 1

    spectator = StatefulSpectator()
    deck = AgentDeck(spectators=[spectator])

    # First execution
    deck.play(game, players, matches=3)
    assert spectator.match_count == 3

    # Second execution - state resets in on_batch_start
    deck.play(game, players, matches=2)
    assert spectator.match_count == 2  # Reset to 0, then counted 2
```

#### Test 6: Read-only event data (HC3)
```python
def test_readonly_event_data():
    class MutatingSpectator(Spectator):
        def on_gameplay(self, event):
            # Attempt to mutate event data (SHOULD NOT DO THIS)
            event.data['player'] = "HACKER"

    class ReadingSpectator(Spectator):
        def __init__(self):
            super().__init__()
            self.player_names = []

        def on_gameplay(self, event):
            self.player_names.append(event.data['player'])

    mutating = MutatingSpectator()
    reading = ReadingSpectator()

    # Framework should isolate mutations (defensive copies)
    # This test verifies framework implementation, not spectator contract
    deck = AgentDeck(spectators=[mutating, reading])
    deck.play(game, players, matches=1)

    # Reading spectator should see original data (if framework uses defensive copies)
    # In practice, spectators MUST NOT mutate; framework MAY enforce via copies
```

#### Test 7: Logger injection (LI1-LI4)
```python
def test_logger_injection():
    """Verify Console/ReplayEngine injects logger into spectators."""
    class LoggingSpectator(Spectator):
        def __init__(self):
            super().__init__()
            self.logger_injected = False
            self.log_calls = []

        def on_batch_start(self, batch_id, game, players, matches, context=None):
            # Verify logger was injected
            self.logger_injected = (self.logger is not None)
            if self.logger:
                self.logger.info(f"Batch {batch_id} starting")
                self.log_calls.append(f"batch_start:{batch_id}")

    # Session spectator (no logger in constructor)
    session_spec = LoggingSpectator()
    assert session_spec.logger is None  # Not injected yet

    # Execution spectator (no logger in constructor)
    exec_spec = LoggingSpectator()

    deck = AgentDeck(spectators=[session_spec])

    # LI1: Console MUST inject logger during construction
    # LI2: Injected logger MUST be AgentDeckLogger instance
    assert session_spec.logger is deck.logger
    assert session_spec.logger is not None

    # LI4: Execute with execution spectator
    deck.play(game, players, matches=1, spectators=[exec_spec])

    # LI1/LI4: Console MUST inject logger for execution spectators too
    assert exec_spec.logger is deck.logger
    assert exec_spec.logger is not None

    # Verify spectators could use logger
    assert session_spec.logger_injected
    assert exec_spec.logger_injected
    assert len(session_spec.log_calls) > 0
    assert len(exec_spec.log_calls) > 0

def test_logger_injection_with_constructor_logger():
    """Verify LI3: spectator with logger in constructor bypasses injection."""
    from agentdeck.core.logging import NullLogger

    class PreConfiguredSpectator(Spectator):
        def __init__(self, logger):
            super().__init__(logger=logger)
            self.logger_changed = False

        def on_batch_start(self, batch_id, game, players, matches, context=None):
            # Check if logger was replaced
            self.logger_changed = (self.logger != self.original_logger)

    custom_logger = NullLogger()
    spectator = PreConfiguredSpectator(logger=custom_logger)
    spectator.original_logger = custom_logger

    deck = AgentDeck(spectators=[spectator])
    deck.play(game, players, matches=1)

    # LI3: Spectator with logger MUST NOT have it replaced
    assert spectator.logger is custom_logger
    assert not spectator.logger_changed

def test_logger_writes_to_core_streams():
    """Verify LI5: logger writes to core log streams."""
    from agentdeck.core.logging import InMemoryLogHandler, LoggingConfig

    class InfoLoggingSpectator(Spectator):
        def on_batch_start(self, batch_id, game, players, matches, context=None):
            if self.logger:
                self.logger.info(f"[SPECTATOR] Batch {batch_id} starting")

    spectator = InfoLoggingSpectator()

    # Create deck with in-memory logger to capture output
    handler = InMemoryLogHandler()
    config = LoggingConfig(
        console_level=None,
        file_levels=(),
        extra_handlers=(handler,)
    )

    deck = AgentDeck(spectators=[spectator])
    deck.play(game, players, matches=1)

    # LI5: Spectator log calls MUST appear in core log stream
    log_messages = [record.getMessage() for record in handler.records]
    spectator_logs = [msg for msg in log_messages if "[SPECTATOR]" in msg]
    assert len(spectator_logs) > 0
```

## 10. Open Questions / Future Work

### Async Handler Support
- Should spectators support **async event handlers** for external API calls (e.g., `async def on_match_end`)?
- How to handle async cleanup in `on_session_end` / `on_batch_end`?

### Spectator Priority/Ordering
- Should framework support **priority levels** for deterministic spectator execution order?
- How to handle dependencies between spectators (e.g., MatchRecorder must run before StatsAggregator)?

### Dynamic Attach/Detach
- Should framework provide **SpectatorRegistry** for attaching/detaching spectators mid-session?
- How to handle unsubscribe semantics (immediate vs deferred to batch end)?

### Base Classes for Common Patterns
- Should framework provide **base classes** for common patterns (rolling averages, histograms, exporters)?
- How to balance convenience vs framework bloat?

### Selective Event Routing
- How should spectators **declare event subscriptions** (e.g., only GAMEPLAY events, skip DIALOGUE)?
- Should framework skip handler checks for unsubscribed events to improve performance?

### Metadata Discovery
- Should `Spectator.describe()` return metadata (supported events, description, version) for session logs?
- How to enable automatic spectator documentation generation?

### Spectator Composition
- Should framework support **spectator composition** (combine multiple spectators into pipeline)?
- How to handle error propagation in spectator chains?

### Streaming Spectators
- Should spectators support **streaming output** (e.g., WebSocket push for live dashboards)?
- How to handle backpressure when spectators can't keep up with event rate?

## 11. Design Rationale
- **Duck-typed handlers** keep the API flexible while preserving familiar naming (`on_<event>`), enabling minimal boilerplate (implement only needed handlers).
- **SpectatorContext helper** centralises context parsing, avoiding repetitive guard code for missing fields.
- **Late-binding logger injection** (LI1-LI4) enables structured logging pipelines without forcing dependencies on spectators. Console/ReplayEngine inject logger after spectator construction but before first event, allowing spectators to write to core log streams (info.log, debug.log, console) without explicit configuration.
- **Unified Event object** simplifies spectator API (type, data, context in one structure).
- **Scope separation** (session vs execution) enables both persistent and ad-hoc observation patterns.
- **Error isolation** ensures spectator failures don't crash matches (critical for production analytics).

## 12. References

### Specifications
- [SPEC.md](./SPEC.md) §1.2 (Ease of use), §2.4 (Observability)
- [SPEC.md](./SPEC.md) §3.2 (Separation of concerns: observers never mutate)
- [SPEC-OBSERVABILITY.md](./SPEC-OBSERVABILITY.md) v1.0.0 (Event types, EventContext structure, player lifecycle events §3.1.1)
- [SPEC-AGENTDECK.md](./SPEC-AGENTDECK.md) v0.3.0 (Spectator attachment scopes, session vs execution)
- [SPEC-CONSOLE.md](./SPEC-CONSOLE.md) v0.3.0 (Event emission timing, match orchestration)
- [SPEC-RECORDER.md](./SPEC-RECORDER.md) v1.0.0 (Recording is a special spectator implementation)
- [SPEC-REPLAY.md](./SPEC-REPLAY.md) v1.0.0 (ReplayEngine reuses spectator API with isolated EventBus)
- [SPEC-PLAYER.md](./SPEC-PLAYER.md) v1.0.0 (Three-phase lifecycle: handshake → turn → conclusion)
- [SPEC-PRICING.md](./SPEC-PRICING.md) v1.0.0 (TokenUsageTracker pricing integration requirements § 8)
