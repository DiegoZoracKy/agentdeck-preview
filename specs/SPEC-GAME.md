# SPEC-GAME: Game Author Contract v0.10.0

> Status: Final
> Version: 0.10.0
> Last Updated: 2026-09-03
> Base Version: 0.6.0 (Final)
> Implementation: ✅ Complete (Phase 6-8 compliance verified)
> Review State: Consensus-approved
> Audience: Game authors, framework contributors, researcher tool builders

## 1. Purpose
- Define the canonical contract for games plugged into AgentDeck’s console-driven execution loop.
- Ensure every game offers deterministic, reproducible behaviour while owning its narrative, rules, and win conditions.
- Provide a common language for researchers, renderer authors, and recorder tooling to inspect game outcomes.

## 2. Scope & Philosophy Alignment
- Upholds `AGENTS.md` §2.1 modularity: Games own rules and state; console orchestrates without interpreting mechanics.
- Reinforces `SPEC.md` §2.4 reproducibility: deterministic RNG flow, serialisable state snapshots, and replay parity.
- Applies lean authoring guidance from `GUIDELINES.md` §2c: concise contracts, numbered invariants, examples grounded in state machines.
- Non-goals: Turn loop mechanics (moved to mechanic-specific specs), player decision parsing (`SPEC-PLAYER.md`), renderer formatting details (`SPEC-RENDERER.md`).

## 3. Responsibilities
- Own the complete game state machine: initialisation, action application, terminal evaluation.
- Own all instructional and narrative content. Console may deliver `instructions` and `default_handshake_template` during onboarding, but games define that content and how views evolve across play.
- Emit domain events describing game semantics through the injected `GameEventEmitter`.
- Provide deterministic outputs by consuming console-provided RNG forks only.
- Expose filtered per-player views without leaking hidden information.
- Provide a default handshake template (`default_handshake_template`) for player onboarding before turn 1.
- Implement (or inherit) the `run(runtime, players)` contract so mechanics stay encapsulated within games while console orchestration remains generic.

## 4. Public API

### instructions -> str
- Role: Canonical description of rules, objectives, and research notes.
- Return: Plain string suitable for docs, lobby UIs, or researcher tooling (may be empty).
- MUST: Avoid exposing hidden information that is not also surfaced via `get_view`.
- NOTE: Console may inject this property into handshake prompt composition via `{game_instructions}`. Games still own the content and may additionally surface instructional/narrative material through state and views.

### allowed_actions -> List[str]
- Role: Canonical list of valid action strings for this game.
- Return: List of action identifiers (e.g., `["ATTACK", "POTION", "FLEE"]`).
- MUST: Return all actions that players may legally attempt during gameplay.
- Usage: Console binds this to action controllers during match setup via `controller.bind_game(game)`.

### setup(players: List[str], seed: int) -> Dict[str, Any]
- Accept: Ordered player roster as negotiated by the console.
- Perform: Build canonical `game_state` dictionary containing all data required for handshake, subsequent turns, and final observability.
- Return: JSON-serialisable dict (keys/values ready for recorder, renderer, and replay).
- Emit: MAY emit domain events via `emit_event` during setup.
- MUST: Persist deterministic seed usage or derived randomness in `game_state` when relevant.
- NOTE: Console may call `setup()` before the handshake phase so the initial state can inform onboarding. Mechanics may later receive that same state via `runtime.initial_state`.

### update(game_state: Dict[str, Any], player: str, action: ActionResult, *, rng: RandomGenerator) -> Dict[str, Any]
- Accept: Current `game_state`, acting player name, parsed action, deterministic RNG fork.
- Perform: Apply action to evolve game state; may mutate in place or return a new dict.
- Return: Updated JSON-serialisable dict representing canonical state after the action.
- Emit: MAY emit domain events via `emit_event` for semantic milestones (card_drawn, bid_placed).
- Raise: SHOULD raise `ValueError` (or domain-specific exception) when action is invalid and cannot be repaired.
- MUST: Use `rng` for all randomness; MUST NOT touch global randomness.

### status(game_state: Dict[str, Any]) -> GameStatus
- Accept: Latest canonical state.
- Perform: Evaluate whether play continues and, if finished, determine the winner.
- Return: `GameStatus(is_over: bool, winner: Optional[str])`.
- MUST: Set `winner=None` for draws or ongoing games; MUST freeze `is_over=True` once terminal.

### get_view(game_state: Dict[str, Any], player: str) -> Dict[str, Any]
- Accept: Canonical state, requesting player identity.
- Perform: Produce filtered view containing only information the player may observe; filtering determined by game's `information_level` configuration.
- Return: JSON-serialisable dict consumed by renderers and prompt builders.
- MUST: Avoid mutating the supplied `game_state`; MUST use deep copy or derived structures when enrichment is needed.
- MUST: Respect `information_level` configuration ("full", "partial", or game-specific levels).
- MUST: Explicitly document any game-specific public signals that remain visible in partial modes (e.g., global `last_action` history or a public opponent `last_action` field).
- SHOULD: Include narrative/tutorial content by injecting into the returned view when required.

### validate_state(game_state: Dict[str, Any]) -> None
- Role: Optional guardrail invoked after `setup` and every `update`.
- Raise: MUST raise `ValueError` with descriptive message when invariants break.
- MUST NOT: Mutate the provided `game_state`.
- Default: No-op; games opt in for stronger integrity checks.

### describe() -> Dict[str, Any]
- Role: Return the effective JSON Game configuration used by execution.
- Return: Name, module, allowed actions, and serializable public instance configuration.
- MUST: Exclude runtime bindings and non-JSON values.

### describe_version() -> Dict[str, Any]
- Role: Return portable implementation identity with explicit fingerprint scope.
- Return: Descriptor defined by `SPEC-GAME-VERSION-PROVENANCE`.
- MUST NOT: Claim full implementation coverage when only class source is available.

### get_events(game_state: Dict[str, Any], player: str, action: ActionResult) -> List[Event]
- Role: Optional hook to publish additional observability events besides structural gameplay events.
- Return: List of domain events (JSON-serialisable payloads) to be emitted via `emit_event`.
- SHOULD: Use when the game can derive richer analytics after an action (e.g., scoring breakdowns).
- Default: Return empty list (no additional events).

### emit_event(event_type: str, **payload: Any) -> None
- Accept: Snake_case event name plus JSON-serialisable payload.
- Perform: Forward event to bound `GameEventEmitter`; console enriches with match metadata.
- MUST: Only be called after `bind_event_emitter` injection (handled by console).
- NOTE: Helper is provided so games stay decoupled from EventBus internals.

### bind_event_emitter(emitter: GameEventEmitter) -> None / bind_event_factory(factory: EventFactory) -> None
- Role: Infrastructure hooks installed by console prior to gameplay.
- MUST NOT: Be called by game authors directly; provided for framework integration.

### run(runtime: MatchRuntime, players: List[Player]) -> TurnResult
- **Role**: Execute the mechanic using the infrastructure exposed by `MatchRuntime`.
- Accept: `runtime` (per-match context created by console) and ordered player list.
- Perform: Drive gameplay (sequential, simultaneous, real-time) while using runtime for **all** infrastructure interactions (events, recorder, RNG, parse-failure handling, logging, checkpointing).
- Return: `TurnResult(final_state, mechanic_events, truncated_by_max_turns)`; helpers MAY return a simple tuple with the same structure, but the dataclass defined in `SPEC-GAME-MECHANIC-TURN-BASED.md` is the canonical type.
- MUST: Use runtime helpers instead of accessing console directly:
  - `runtime.emit_event` for lifecycle/gameplay/custom events
  - `runtime.record_turn` for prompt/response/action capture
  - `runtime.handle_parse_failure` for controller failures
  - `runtime.fork_rng(label)` for deterministic randomness
  - `runtime.validate_state` after setup/update (when implemented)
- SHOULD: Inherit base implementations (`TurnBasedGame.run(...)`) unless building a brand-new mechanic. Overriding `run()` is reserved for experts and MUST still respect this contract.
- Usage: Called by `Console._play_match()` after handshake completes and MATCH_START emits.
- Reference: `SPEC-GAME-MECHANIC-TURN-BASED.md` and future mechanic specs define concrete behaviour.
- Example (simultaneous mechanic skeleton):
```python
class SimultaneousAuctionGame(Game):
    def run(self, runtime, players):
        state = self.setup([p.name for p in players])
        while not self.status(state).is_over:
            actions = self._collect_bids(runtime, players, state)
            state = self.resolve_round(state, actions, rng=runtime.fork_rng("round"))
            runtime.validate_state(state)
        return TurnResult(final_state=state, events=[], truncated_by_max_turns=False)
```

### get_current_player(game_state, players, *, rng: RandomGenerator, match_context: MatchContext) -> str
- **Role**: Determine which player should act on the current turn. Override for custom turn order logic.
- Accept: Current canonical game state, ordered list of player names, mechanic RNG fork, and match context (match_id, previous results).  
- Return: Name of the player who should act next (MUST be from `players` list).
- MUST: Return a name that exists in the `players` list (mechanic helper validates and raises if mismatch).
- MAY: Use state metadata (`_turn_count`, `_first_player_idx`, `match_context.previous_match_result`) for sequencing logic.
- MAY: Be overridden for custom turn order (auction bidding, phase-based rotation, dynamic initiatives).
- Default Implementation (round-robin): `players[(first_player_idx + turn_number - 1) % len(players)]`
- Usage: Called by turn-based helper (`SPEC-GAME-MECHANIC-TURN-BASED.md` §4.2) before each turn. Simultaneous mechanics MAY raise `NotImplementedError` if no single actor exists.
- Override Examples:
  - Auction game: `return game_state["next_bidder"]`
  - Phase-based: `return game_state["phase_leader"] if game_state["phase"] == "bidding" else super().get_current_player(...)`
  - State-dependent: Use `rng` to break ties deterministically

### get_player_order(players: List[Player], *, rng: RandomGenerator, match_context: MatchContext) -> Optional[List[Player]]
- **Role**: Override to provide custom player ordering logic. Determines which players go first in a match.
- **Default Behavior**: Returns `None`, indicating no preference. Console applies its configured fairness policy (`pairing_policy` / `first_player_policy`).
- **When to Override**:
  - Auction/bidding systems (highest bidder goes first)
  - Asymmetric roles (attacker vs defender assignment)
  - State-dependent ordering (previous winner advantage, tournament seeding)
  - Fixed role assignments (player order matters for game balance)
- Accept: Original player list as provided to `Console.run()`, match-specific RNG for reproducibility, match context with seed/match_id/previous_match_result.
- Return:
  - `None`: Console applies default fair ordering from session configuration — **recommended for 99% of games**
  - `List[Player]`: Custom ordering; Console validates and uses as-is (MUST be same player instances, same length, no duplicates)
- MUST: If returning custom list, include exact same `Player` instances from input (no additions, removals, or duplicates). Console validates and raises `ValueError` on mismatch.
- MUST: Use provided `rng` for any random decisions (maintains reproducibility). Do NOT create own `RandomGenerator` instance.
- MAY: Access `match_context.seed`, `match_context.match_id`, `match_context.previous_match_result` for state-based decisions.
- MAY: Return `players` unchanged to preserve Console.run() order (useful for fixed asymmetric roles).
- NOTE: Called by Console before each match. Console records effective order in `MatchResult.metadata["player_order"]`, `metadata["player_order_source"]`, and `metadata["first_player"]`.

**Examples**:
```python
# Example 1: Default (no override needed) - Console applies configured fairness
class TicTacToe(Game):
    pass  # get_player_order() returns None → Console applies session fairness policy

# Example 2: Auction-based ordering
class AuctionGame(Game):
    def get_player_order(self, players, *, rng, match_context):
        # Run pre-match auction with provided RNG
        bids = {p: self._auction_bid(p, rng) for p in players}
        # Highest bidder goes first
        return sorted(players, key=lambda p: bids[p], reverse=True)

# Example 3: Fixed asymmetric roles (preserve order)
class CaptureTheFlagGame(Game):
    def get_player_order(self, players, *, rng, match_context):
        # Player 0 = Attacker, Player 1 = Defender (roles matter)
        return players  # Use order as provided to Console.run()

# Example 4: State-dependent (previous winner advantage)
class TournamentGame(Game):
    def get_player_order(self, players, *, rng, match_context):
        # First match: random
        if match_context.previous_match_result is None:
            return None  # Let Console randomize

        # Winner of previous match goes first
        prev_winner = match_context.previous_match_result.winner
        if prev_winner:
            winner_player = next(p for p in players if p.name == prev_winner)
            other_players = [p for p in players if p.name != prev_winner]
            return [winner_player] + other_players

        return None  # Draw: let Console randomize
```

### ParseFailurePolicy Enum *(new in v0.6.0)*

```python
class ParseFailurePolicy(Enum):
    ABORT_MATCH = "abort"      # Terminate match immediately
    SKIP_TURN = "skip"         # Consume the failing player's turn, continue match
    FORFEIT = "forfeit"        # Failing player loses immediately (default)
    RETRY_ONCE = "retry"       # Console re-issues prompt exactly once
```

Games SHOULD use these canonical outcomes when deciding how to handle controller parsing failures.

### on_action_parse_failure(self, player_name: str, error: ActionParseError, turn_context: TurnContext) -> ParseFailurePolicy *(new in v0.6.0)*
- A single-player Game MUST explicitly override this policy hook; inherited FORFEIT requires an opponent. Use ABORT_MATCH when an invalid response should stop the batch after preserving its Record.
- Accept: failing `player_name`, structured `ActionParseError` (with embedded `ParseResult`), and immutable `TurnContext` snapshot.
- Default implementation: return `ParseFailurePolicy.FORFEIT` so the opponent wins and the match continues.
- Games MAY override to implement domain-specific policies (skip turn, forfeit, retry once).
- MUST be deterministic given identical state and inputs.
- MAY use `error.parse_result.metadata` (candidates, reasoning flags, allowed actions) to tailor penalties.
- MUST avoid mutating match state; state changes occur only through Console/TurnLoop policy application.

### on_match_forfeited(game_state, player_name, error, policy) -> Dict[str, Any] *(new in v0.7.0)*
- **Role**: Enrich terminal state after forfeit decision, before MATCH_END event emission.
- Accept: Current `game_state`, failing `player_name`, `ActionParseError`, applied `ParseFailurePolicy`.
- Perform: Optionally update state to record terminal condition (e.g., `resolution_status="invalid_response"`).
- Return: Updated JSON-serializable dict (canonical state for recording).
- Emit: MAY emit diagnostic events via `emit_event` (emitter remains bound through this hook).
- MUST NOT: Raise exceptions (already in error path).
- Default implementation: Return `game_state` unchanged (backward compatible).

**Lifecycle**: Called by TurnLoop after `MatchForfeitedError` caught, before event emitter unbind.

**Example**:
```python
def on_match_forfeited(self, game_state, player_name, error, policy):
    state = dict(game_state)  # Copy for safety
    state["resolution_status"] = "invalid_response"
    state["failed_player"] = player_name
    state["failure_reason"] = str(error)
    self.emit_event("parse_failure_terminal", player=player_name)
    return state
```

### Conclusion Phase Hooks *(new in v0.7.0)*

Three-hook system for post-match reflections. Conclusion execution is controlled by
the Console conclusion policy (SPEC-CONSOLE). These hooks are optional overlays for
custom prompts and state capture.

#### requires_conclusion(game_state) -> Optional[str]
- **Role**: Identify the player that should receive a game-defined conclusion prompt
  and whose response should be parsed/stored.
- Accept: Final `game_state` after `status.is_over == True`.
- Return: Player name for game-specific conclusion handling, or `None` to use default
  player templates for all policy-selected conclusions.
- Default implementation: Return `None` (no game-specific prompt/state mutation).
- MUST: Return player name from match roster, or None.
- Note: Conclusion still runs for policy-selected players even when this returns None.

**Example**:
```python
def requires_conclusion(self, game_state):
    # Winner provides reflection
    winner = self.status(game_state).winner
    return winner if winner else None

    # Or: support agent provides post-escalation summary
    if game_state["resolution_status"] == "escalated":
        return "support"
    return None
```

#### get_conclusion_prompt(player, game_state) -> str
- **Role**: Generate a game-defined conclusion prompt for the specified player.
- Accept: Player name (from `requires_conclusion`), final `game_state`.
- Return: Prompt string for player's `conclude()` call.
- Called only for the player returned by `requires_conclusion()`.
- Default implementation: Generic reflection prompt.

**Example**:
```python
def get_conclusion_prompt(self, player, game_state):
    if game_state["resolution_status"] == "escalated":
        return (
            "The client escalated. Provide a summary in JSON:\\n"
            '{"summary": "...", "why_escalated": "...", "next_steps": "..."}'
        )
    return "Reflect on the match outcome."
```

#### parse_conclusion(player, response) -> Dict[str, Any]
- **Role**: Parse conclusion response into structured data.
- Accept: Player name, raw conclusion response.
- Return: JSON-serializable dict with conclusion data.
- Default implementation: `json.loads(response)` with error handling.
- MAY: Override for custom parsing logic.

#### on_conclusion_received(game_state, player, conclusion) -> Dict[str, Any]
- **Role**: Store conclusion data in final state.
- Accept: Current `game_state`, player name, parsed `conclusion` dict.
- Return: Updated state with conclusion embedded.
- Default implementation: Return `game_state` unchanged (backward compatible).

**Example**:
```python
def on_conclusion_received(self, game_state, player, conclusion):
    state = dict(game_state)
    if player == "support":
        state["support_conclusion"] = conclusion
    else:
        state["client_conclusion"] = conclusion
    return state
```

**Lifecycle**: After game ends → Console selects concluding players via policy →
`requires_conclusion()` (optional overlay) → if game-selected player is in policy set:
prompt player → `parse_conclusion()` → `on_conclusion_received()` → emit PLAYER_CONCLUSION →
MATCH_END.

### on_handshake_complete(game_state, player, handshake_result) -> Dict[str, Any] *(new in v0.7.0)*
- **Role**: Process handshake metadata after successful validation and MATCH_START, before gameplay.
- Accept: Initial `game_state` (from `setup`), player name, `HandshakeResult` from controller.
- Perform: Extract and store metadata (e.g., persona, initial strategy) into state.
- Return: Updated JSON-serializable dict.
- Default implementation: Return `game_state` unchanged (backward compatible).
- MUST NOT: Raise exceptions (match setup already in progress).

**Lifecycle**: After `player.execute_handshake()` → controller validates → **this hook** → gameplay starts.

**HandshakeResult structure** (typed dataclass in v0.7.0):
```python
@dataclass
class HandshakeResult:
    accepted: bool
    raw_response: str
    normalized_response: str
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # Always dict, never None
```

**Example**:
```python
def on_handshake_complete(self, game_state, player, handshake_result):
    state = dict(game_state)
    # Extract persona from client handshake
    if player == "client" and "persona" in handshake_result.metadata:
        state["client_persona"] = handshake_result.metadata["persona"]
    # Extract initial strategy
    if "strategy" in handshake_result.metadata:
        state["initial_strategies"] = state.get("initial_strategies", {})
        state["initial_strategies"][player] = handshake_result.metadata["strategy"]
    return state
```

**Note**: This hook was documented in SPEC-PLAYER v1.1.0 but Console did not invoke it (bug). v0.7.0 fixes this omission.

### Hook Stability Guarantee *(new principle in v0.7.0)*

**Principle**: New hooks introduced in minor versions MUST preserve backward compatibility via safe defaults.

**Requirements**:
1. **HS1**: Default implementations MUST return unchanged inputs or None.
2. **HS2**: Game-level conclusion hooks MUST default to no-op behavior; LLM calls are governed by Console policy, not by game hook defaults.
3. **HS3**: Default implementations MUST NOT mutate provided state.
4. **HS4**: Existing games (e.g., FixedDamageGame) MUST continue exact behavior after hook additions.
5. **HS5**: Every new hook MUST include regression test proving FixedDamageGame unchanged.

**Validation**: Before merging hook additions, verify FixedDamageGame produces identical results (winner, turn count, events) in v0.6.0 vs v0.7.0.

**Rationale**: Enables AgentDeck to evolve observability/metadata capabilities without breaking 100+ existing games in the ecosystem. Researchers expect deterministic behavior across minor versions.

## 5. Invariants & Guarantees

### 5.1 Game State Data (GS)
1. **GS1**: `setup` MUST return a JSON-serialisable dict that contains every key required for gameplay and observability.
2. **GS2**: `update` MUST return a dict representing the new canonical `game_state`; in-place mutation is allowed, but the returned object MUST reflect the authoritative data for the next turn.
3. **GS3**: `game_state` MUST remain free of unserialised objects or callable handles; derived caches MAY live on the Game instance but cannot influence behaviour unless reflected in the dict.
4. **GS4**: `get_view` and recorder snapshots MUST be able to deep copy `game_state` without raising.

### 5.2 Determinism (DT)
5. **DT1**: All randomness inside `update` (and helpers it calls) MUST come from the provided `rng` fork.
6. **DT2**: Given identical players, initial `game_state`, seed, and action sequence, the game MUST produce identical future states and `GameStatus` outputs.
7. **DT3**: `get_view` MUST be a pure projection; repeated calls with identical inputs MUST yield identical outputs.

### 5.3 Narrative & Views (G)
8. **G15**: Game owns ALL narrative and instructional delivery by controlling `game_state` and per-player views. Console remains a mechanics-agnostic broker and NEVER delivers instructions.
9. **G16**: Games MAY inject tutorial or contextual content in `setup` or `get_view`, and MUST clear or advance that content through their own state machine.

### 5.4 Observability & Events (OB)
10. **OB1**: `emit_event` payloads MUST be JSON-serialisable and omit structural gameplay events already emitted by the console’s turn loop.
11. **OB2**: Games MUST NOT emit events before `bind_event_emitter` is invoked; doing so has no effect and MUST be treated as a defect.
12. **OB3**: `get_view` MUST hide hidden-information content for non-owning players while keeping recorder snapshots truthful (full canonical state).

### 5.5 Validation & Errors (V)
13. **V1**: When implemented, `validate_state` MUST detect invariant violations immediately after `setup` and `update`, raising descriptive errors.
14. **V2**: Validation MUST be side-effect free so failures leave console-owned state snapshots untouched for debugging.

### 5.6 Parse Failure Policy (PF) — *New in v0.6.0*
15. **PF1**: Default implementation of `on_action_parse_failure` MUST return `ParseFailurePolicy.FORFEIT`.
16. **PF2**: Custom overrides MUST return one of the defined enum values and MUST NOT mutate game state.
17. **PF3**: Overrides MUST be deterministic based on current game state, player name, and provided `ParseResult` metadata.
18. **PF4**: Games opting for `SKIP_TURN`, `FORFEIT`, or `RETRY_ONCE` MUST document the behaviour in game instructions for replay transparency. Runtime invokes this hook via `runtime.handle_parse_failure` (see `SPEC-MATCH-RUNTIME.md`).

### 5.6 Handshake Template (HT)
15. **HT1**: Games MUST provide `default_handshake_template` property. Console MUST run handshake before turn 1 using this template (or player override).
16. **HT2**: Handshake template SHOULD include game instructions, rules, and expected response format. LLM uses this for onboarding before gameplay begins.
17. **HT3**: When handshake acknowledgement fails validation, console MUST abort match. Games cannot opt-out of handshake validation.

### 5.7 Information Visibility (IV)
18. **IV1**: Games MAY implement `information_level` parameter (e.g., "full", "partial") to control what players observe via `get_view()`.
19. **IV2**: When `information_level="full"`, `get_view()` SHOULD include all observable information (opponent stats, public state, etc.).
20. **IV3**: When `information_level="partial"`, `get_view()` SHOULD include only player's own stats and observable public actions (for example opponent `last_action` when the game defines that as public), and MUST exclude opponent private state such as hidden HP or inventory.
21. **IV4**: Games MAY define custom information levels beyond "full"/"partial" for research purposes.
22. **IV5**: `information_level` MUST be captured in game configuration metadata for reproducibility.

### 5.8 Player Ordering (PO)
23. **PO1**: Games MAY override `get_player_order()` to customize pre-match player ordering; default returns `None` (Console applies session fairness policy).
24. **PO2**: Games MUST return same `Player` instances from input if overriding (no additions, removals, or duplicates). Console validates and raises `ValueError` on mismatch.
25. **PO3**: Games MUST use provided `rng` parameter for any random decisions in `get_player_order()` (maintains reproducibility). Games MUST NOT create own `RandomGenerator` instances.
26. **PO4**: When `get_player_order()` returns `None`, Console MUST apply its configured fairness policy using match-specific context and RNG where needed (eliminates hidden ordering drift and preserves reproducibility).

### 5.9 Mechanic Execution (ME)
27. **ME1**: `run(runtime, players)` MUST be the only entry point used by the console. Games MUST treat `runtime` as the exclusive gateway for event emission, recorder writes, RNG usage, parse-failure handling, and state validation.
28. **ME2**: Games inheriting the stock mechanic classes (e.g., `TurnBasedGame`) MUST NOT override `run()` unless implementing a fundamentally new execution model. Authors creating custom mechanics MUST document behaviour and reference the relevant mechanic spec.
29. **ME3**: Every successful player decision MUST result in a call to `runtime.record_turn(...)` (even if the action later fails validation). Every action or round MUST emit at least one `GAMEPLAY` event through `runtime.emit_event(...)`.
30. **ME4**: `run()` MUST return a JSON-serialisable final state and MUST signal truncation via the boolean flag when runtime’s `max_turns` limit or a mechanic-level termination triggers.
31. **ME5**: `run()` MUST propagate unhandled exceptions; runtime/console attach `match_context` metadata for logging and replay. Mechanics MAY raise domain-specific exceptions, but they MUST include the acting player/turn in the error message for diagnostics.

### 5.10 Hook Stability (HS) — *New in v0.7.0*
32. **HS1**: Default implementations of all hooks MUST return unchanged inputs (game_state) or None.
33. **HS2**: Game-level conclusion hooks MUST default to no-op behavior (return None, do not mutate state) so games remain compatible when conclusion policies are enabled.
34. **HS3**: Default hook implementations MUST NOT mutate provided state dictionaries.
35. **HS4**: Hook additions in minor versions MUST NOT change behavior of existing games (e.g., FixedDamageGame).
36. **HS5**: Every new hook MUST include regression test proving FixedDamageGame produces identical results.

### 5.11 Lifecycle Hooks (LH) — *New in v0.7.0*
37. **LH1**: `on_handshake_complete()` MUST be called after successful handshake validation and after MATCH_START, before any turn or `game.run()` delegation.
38. **LH2**: `on_match_forfeited()` MUST be called after forfeit decision, before MATCH_END event, with emitter still bound.
39. **LH3**: `requires_conclusion()` MUST be called after `status.is_over == True` and only when the Console conclusion policy is enabled.
40. **LH4**: Game-specific conclusion handling (prompt + `on_conclusion_received`) MUST only execute if `requires_conclusion()` returns a player included in the policy-selected conclusion set.
41. **LH5**: Games MUST NOT call conclusion hooks directly; Console/TurnLoop orchestrates lifecycle.

### 5.12 Typed Contracts (TC) — *New in v0.7.0*
42. **TC1**: `HandshakeResult.metadata` MUST always be a dict (never None), enabling safe access without defensive checks.
43. **TC2**: Games receiving `HandshakeResult` MAY assume `metadata` field exists and is dict-like.
44. **TC3**: Controllers producing `HandshakeResult` MUST populate `metadata` field (empty dict if no metadata).

### 5.13 Execution Identity (EI) — *New in v0.8.0*

45. **EI1**: `describe()` MUST expose effective Game configuration independently from implementation identity.
46. **EI2**: `describe_version()` MUST expose content identity and assurance scope according to `SPEC-GAME-VERSION-PROVENANCE`.
47. **EI3**: Missing source bytes MUST be represented as unresolved and MUST NOT prevent otherwise valid execution.

## 6. Data Flow & Interaction
- **Session init**: Facade → Console (game, players, seed) → game.setup(players, seed) → canonical `game_state`.
- **Player ordering**: Console.run() → **game.get_player_order(players, rng=match_rng, match_context)** → returns None or custom list → Console applies configured fairness policy or validates custom order → records `player_order`, `player_order_source`, `first_player`, and fairness metadata.
- **Handshake phase** *(updated in v0.9.0)*: provider-free `game.setup()` → MATCH_START opens the canonical recording envelope → Console._run_handshake() → Player.build_handshake_bundle() → PLAYER_HANDSHAKE_START → Player.execute_handshake() → Controller.validate_handshake() → on success, **game.on_handshake_complete(state, player, handshake_result)** and PLAYER_HANDSHAKE_COMPLETE; on rejection, PLAYER_HANDSHAKE_ABORT → canonical incomplete MATCH_END with no `game.run()`.
- **Match execution**: Console._play_match() → constructs `MatchRuntime` → **game.run(runtime, ordered_players)** → mechanic helper (TurnLoop, etc.) → (final_state, events, truncated).
- **Turn sequencing**: TurnLoop._execute_turn() → **game.get_current_player(game_state, players)** → identify acting player → proceed with turn.
- **View generation**: Console → game.get_view(game_state, player) → Renderer.format(view) → Player.decide().
- **Turn loop**: TurnLoop → game.update(game_state, player, action, rng) → validate_state → status → GAMEPLAY events.
- **Parse failure → forfeit** *(updated in v0.7.0)*: Controller.parse() fails → TurnLoop catches → game.on_action_parse_failure() → policy=FORFEIT → **game.on_match_forfeited(state, player, error, policy)** → enriched state captured → MatchForfeitedError raised → MATCH_END.
- **Conclusion phase** *(new in v0.7.0)*: status.is_over → **game.requires_conclusion(state)** → if player returned: prompt player.conclude() → **game.parse_conclusion()** → **game.on_conclusion_received(state, player, conclusion)** → updated final_state → PLAYER_CONCLUSION event → MATCH_END.
- **Narrative**: Game mutates `game_state` / view → Renderer surfaces content → Player experiences narrative.
- **Domain events**: Game.emit_event(...) → GameEventEmitter → EventBus → Recorder/Spectators.
- **Validation failures**: game.validate_state(...) raises ValueError → Console propagates → match abort / diagnostic logging.

## 7. Error Handling & Edge Cases
- Invalid actions SHOULD raise `ValueError` (or custom exception) from `update`; console propagates and records failure.
- Validation failures MUST stop the match immediately; console emits `MATCH_END` with failure metadata.
- Games MUST guard against missing keys in `game_state`; prefer explicit errors over silent defaults.
- Hidden-information games MUST ensure `get_view` never leaks secret data—even under replay or spectator inspection.
- Games MAY implement recovery logic (e.g., auto-pass) but MUST emit events describing the corrective action.

## 8. Examples

```python
# Example 1: Minimal perfect-information game
class CoinFlipGame(Game):
    @property
    def instructions(self) -> str:
        return "Guess heads or tails. First correct guess wins."

    def setup(self, players, seed):
        return {"round": 0, "coin": None, "winner": None, "seed": seed}

    def update(self, game_state, player, action, *, rng):
        game_state = dict(game_state)  # copy for clarity
        game_state["round"] += 1
        game_state["coin"] = rng.choice(["heads", "tails"])
        if action.output == game_state["coin"]:
            game_state["winner"] = player
        return game_state

    def status(self, game_state):
        return GameStatus(is_over=game_state["winner"] is not None, winner=game_state["winner"])
```

```python
# Example 2: Information level control for A/B testing
class FixedDamageGame(Game):
    def __init__(self, max_health=100, attack_damage=20, information_level="full"):
        self.max_health = max_health
        self.attack_damage = attack_damage
        self.information_level = information_level  # "full" or "partial"

    def setup(self, players, seed):
        return {
            "health": {p: self.max_health for p in players},
            "potions": {p: 3 for p in players},
            "last_action": {p: None for p in players},
            "turn": 1,
            "seed": seed,
        }

    def get_view(self, game_state, player):
        # Always include player's own stats
        view = {
            "health": {player: game_state["health"][player]},
            "potions": {player: game_state["potions"][player]},
            "last_action": game_state["last_action"],
            "turn": game_state["turn"]
        }

        # Conditionally include opponent stats based on information_level
        if self.information_level == "full":
            opponents = [p for p in game_state["health"] if p != player]
            for opp in opponents:
                view["health"][opp] = game_state["health"][opp]
                view["potions"][opp] = game_state["potions"][opp]

        return view
```

```python
# Example 3: Narrative progression controlled by game state
class TutorialGame(Game):
    tutorial_steps = [
        "Welcome! Place your first piece on the board.",
        "Great start. Now block your opponent.",
        "Advanced tip: control the center squares.",
    ]

    def setup(self, players, seed):
        return {"phase": 0, "board": empty_board(), "last_action": None, "seed": seed}

    def get_view(self, game_state, player):
        view = copy.deepcopy(game_state)
        if game_state["phase"] < len(self.tutorial_steps):
            view["tutorial"] = self.tutorial_steps[game_state["phase"]]
        return view

    def update(self, game_state, player, action, *, rng):
        game_state = copy.deepcopy(game_state)
        apply_move(game_state["board"], player, action.output)
        game_state["last_action"] = {"player": player, "move": action.output}
        if should_advance(game_state):
            game_state["phase"] += 1
        return game_state
```

## 8. Handshake Template
- **default_handshake_template**
  - Required property on `Game` returning a template string.
  - Used when player doesn't provide custom `handshake_template`.
  - Should contain game instructions, rules, and response format.
  - Example: `"{game_instructions}\n\n{controller_format}\n\n{handshake_controller_format}"`
  - Rationale: Front-loading instructions in handshake reduces token cost in turn prompts (LLM remembers via conversation history).

## 9. Testing Strategy
| Focus | Invariants | Verification |
|-------|------------|--------------|
| Game state integrity | GS1-GS4 | Run setup/update, assert returned dict is JSON-serialisable, deep-copyable, and contains expected keys. |
| Determinism | DT1-DT3 | Execute same seed + action sequence twice; diff snapshots, views, and status results. |
| Narrative control | G15-G16 | Verify tutorial content appears/advances only through game-managed state. |
| Hidden information | OB3 | Ensure non-owning players never receive secret data in `get_view`; recorder retains full canonical state. |
| Domain events | OB1-OB2 | Emit sample events and confirm recorder logs metadata; ensure premature calls no-op. |
| Validation guardrails | V1-V2 | Trigger invalid transitions; expect ValueError without state mutation. |
| Handshake template | HT1-HT3 | Assert game provides default_handshake_template; verify console runs handshake before turn 1. |
| Player ordering | PO1-PO4 | Run same seed twice, assert identical player_order metadata; test custom override validation (reject invalid lists); verify default None triggers configured console fairness. |
| Hook stability | HS1-HS5 | Verify FixedDamageGame produces identical results (winner, turns, events) after hook additions; assert default hooks return unchanged inputs. |
| Lifecycle hooks | LH1-LH5 | Trigger forfeit → verify `on_match_forfeited()` called with emitter alive; verify `on_handshake_complete()` called after validation; verify conclusion hooks run only when policy-enabled and player is selected. |
| Typed contracts | TC1-TC3 | Assert `HandshakeResult.metadata` is always dict (never None); verify safe access without defensive checks. |

## 10. Design Rationale
- Dict-based `game_state` keeps recorder, renderer, and replay pipelines simple and language-agnostic.
- Narrative ownership (G15) prevents console mission creep and supports dynamic tutorials.
- Optional hooks (`validate_state`, `get_events`) let games opt into richer observability without burdening simple prototypes.
- Infrastructure bindings (event emitter/factory) follow Null-object patterns so games can emit events safely even when recorder is absent.
- **Always-on handshake**: LLMs need instructions to play effectively. Front-loading in handshake reduces turn prompt costs (63% token savings vs repeating instructions every turn). No policy enum needed - handshake is mandatory.
- **run() delegation pattern**: Centralizing mechanics inside `game.run(runtime, players)` keeps the console generic while ensuring games use the shared runtime for events, recorder, RNG, and parse-failure handling. The stock `TurnBasedGame` implementation delegates to TurnLoop so all sequential games follow an identical execution lifecycle.
- **get_current_player() override point**: Provides clean extension for custom turn order (auction bidding, simultaneous phases) while maintaining round-robin default for 90% of games. TurnLoop validates returned player name prevents runtime errors from mismatched names.
- **get_player_order() optional hook**: Console is the source of fairness by default, removing burden from 99% of games. Games override only when ordering is semantically meaningful (auction winners, asymmetric roles, previous-winner advantage). Optional return (None vs List) makes intent explicit and keeps game authors from feeling obligated to implement custom logic.
- **on_match_forfeited() hook** *(v0.7.0)*: Parse failures are terminal conditions that should be recorded accurately. Allowing games to enrich state (e.g., `resolution_status="invalid_response"`) enables filtering/analysis in benchmark datasets. Keeping emitter alive enables diagnostic events for debugging format adherence issues.
- **Conclusion phase policy** *(v0.7.0)*: Post-match reflections capture valuable behavioral data (AI self-assessment, failure attribution, satisfaction prediction) while keeping games decoupled. Console policy controls whether conclusions run and who concludes; game hooks (requires/prompt/store) are optional overlays for domain-specific prompts and state capture.
- **on_handshake_complete() invocation** *(v0.7.0)*: This was a bug - the hook existed in spec but Console never called it. Fixing enables games to extract metadata (personas, initial strategies) from handshake responses, critical for behavioral research (e.g., Support CS persona inference).
- **HandshakeResult typing** *(v0.7.0)*: Explicit dataclass with `metadata: Dict` (never None) eliminates defensive `getattr()`/`isinstance()` checks, reduces bugs, and makes contracts self-documenting.
- **Hook Stability Guarantee** *(v0.7.0)*: AgentDeck's promise to researchers: minor versions preserve deterministic behavior. No-op defaults ensure 100+ existing games continue working exactly as before. Every hook addition requires backward compatibility regression test.

### Relationship to Existing Architecture *(v0.7.0)*

**on_handshake_complete()** complements PLAYER_HANDSHAKE_COMPLETE event (SPEC-OBSERVABILITY §3.1.1):
- **Event**: Read-only observation of handshake via Spectators - observers track handshake success/failure without affecting gameplay
- **Hook**: Game-driven state mutation for gameplay use (e.g., storing persona extracted from handshake to customize game views)
- **Both serve different purposes**: Event enables observation/analytics; hook enables game logic that depends on handshake metadata. Hook is not redundant with event system.

**Conclusion hooks** extend existing Console._run_conclusion() orchestration:
- **Policy-driven**: Console policy selects which players conclude; conclusion is a standard lifecycle step when enabled.
- **Game overlay**: `requires_conclusion()` selects a player for a custom prompt and state capture; `get_conclusion_prompt()` and `on_conclusion_received()` only apply to that player.
- **No-op defaults**: Default implementations return None / no-op, keeping games lightweight while allowing policy-enabled conclusions without custom logic.
- **Relationship to events**: PLAYER_CONCLUSION event (SPEC-OBSERVABILITY §3.1.1) enables spectators to observe reflections; hooks enable game-specific prompts and state capture.

**on_match_forfeited()** enriches state alongside PLAYER_ACTION_PARSE_FAILED event:
- **Event**: Spectators observe parse failures via read-only PLAYER_ACTION_PARSE_FAILED event (includes player, error, policy)
- **Hook**: Game enriches terminal state for filtering/analysis (e.g., setting `resolution_status="invalid_response"` enables benchmark filtering)
- **Alternative considered**: Console could set `_forfeit_metadata` flag for `game.status()` to check, but hook provides cleaner game-controlled state management
- **Event remains authoritative**: Spectators/Recorder capture complete forfeit context via event; hook enables game-specific terminal state representation

## 11. Open Questions / Future Work
- Define mechanic-specific specs (e.g., `SPEC-MECHANIC-TURNBASED.md`) that document helper classes like `TurnBasedGame`.
- Explore schema helpers or dataclass validators for complex game_state definitions.
- Investigate ergonomics for large hidden-information games (view diff tooling, per-player state compression).

## 12. References
- `specs/SPEC.md` §5.10 Game
- `specs/SPEC-AGENTDECK.md`
- `specs/SPEC-CONSOLE.md`
- `specs/SPEC-OBSERVABILITY.md`
- `specs/SPEC-PLAYER.md`
- `specs/SPEC-RENDERER.md`
- `specs/SPEC-GAME-CRITIQUES.md`
- `specs/SPEC-GAME-MECHANIC-TURN-BASED.md`
