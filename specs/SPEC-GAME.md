# SPEC-GAME: Game Author Contract

> Status: Final
> Version: 0.6.0 (Draft)
> Last Updated: 2025-11-03
> Implementation: ✅ Ready for Phase 1B (TurnLoop integration)
> Authors: Codex, Diego Zoracky, Claude
> Approvals: ✅ Codex (2025-01-24)
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
- Control all instructional and narrative content by mutating `game_state` and views; console never times or delivers narrative.
- Emit domain events describing game semantics through the injected `GameEventEmitter`.
- Provide deterministic outputs by consuming console-provided RNG forks only.
- Expose filtered per-player views without leaking hidden information.
- Provide a default handshake template (`default_handshake_template`) for player onboarding before turn 1.
- Implement (or inherit) the `run(runtime, players)` contract so mechanics stay encapsulated within games while console orchestration remains generic.

## 4. Public API

### instructions -> str
- Role: Reference-only description of rules, objectives, and research notes.
- Return: Plain string suitable for docs, lobby UIs, or researcher tooling (may be empty).
- MUST: Avoid exposing hidden information that is not also surfaced via `get_view`.
- NOTE: Console never reads or delivers this property; games decide when to surface narrative through state.

### allowed_actions -> List[str]
- Role: Canonical list of valid action strings for this game.
- Return: List of action identifiers (e.g., `["ATTACK", "POTION", "FLEE"]`).
- MUST: Return all actions that players may legally attempt during gameplay.
- Usage: Console binds this to action controllers during match setup via `controller.bind_game(game)`.

### setup(players: List[str]) -> Dict[str, Any]
- Accept: Ordered player roster as negotiated by the console.
- Perform: Build canonical `game_state` dictionary containing all data required for subsequent turns.
- Return: JSON-serialisable dict (keys/values ready for recorder, renderer, and replay).
- Emit: MAY emit domain events via `emit_event` during setup.
- MUST: Persist deterministic seed usage or derived randomness in `game_state` when relevant.

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
- SHOULD: Include narrative/tutorial content by injecting into the returned view when required.

### validate_state(game_state: Dict[str, Any]) -> None
- Role: Optional guardrail invoked after `setup` and every `update`.
- Raise: MUST raise `ValueError` with descriptive message when invariants break.
- MUST NOT: Mutate the provided `game_state`.
- Default: No-op; games opt in for stronger integrity checks.

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
- Usage: Called by `Console._play_match()` immediately after MATCH_START/handshake phases.
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
- **Default Behavior**: Returns `None`, indicating no preference. Console applies fair randomization (Fisher-Yates shuffle using match RNG).
- **When to Override**:
  - Auction/bidding systems (highest bidder goes first)
  - Asymmetric roles (attacker vs defender assignment)
  - State-dependent ordering (previous winner advantage, tournament seeding)
  - Fixed role assignments (player order matters for game balance)
- Accept: Original player list as provided to `Console.run()`, match-specific RNG for reproducibility, match context with seed/match_id/previous_match_result.
- Return:
  - `None`: Console applies default fair ordering (Fisher-Yates shuffle) — **recommended for 99% of games**
  - `List[Player]`: Custom ordering; Console validates and uses as-is (MUST be same player instances, same length, no duplicates)
- MUST: If returning custom list, include exact same `Player` instances from input (no additions, removals, or duplicates). Console validates and raises `ValueError` on mismatch.
- MUST: Use provided `rng` for any random decisions (maintains reproducibility). Do NOT create own `RandomGenerator` instance.
- MAY: Access `match_context.seed`, `match_context.match_id`, `match_context.previous_match_result` for state-based decisions.
- MAY: Return `players` unchanged to preserve Console.run() order (useful for fixed asymmetric roles).
- NOTE: Called by Console before each match. Console records effective order in `MatchResult.metadata["player_order"]`, `metadata["player_order_source"]`, and `metadata["first_player"]`.

**Examples**:
```python
# Example 1: Default (no override needed) - Console randomizes
class TicTacToe(Game):
    pass  # get_player_order() returns None → Console applies Fisher-Yates shuffle

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
- Accept: failing `player_name`, structured `ActionParseError` (with embedded `ParseResult`), and immutable `TurnContext` snapshot.
- Default implementation: return `ParseFailurePolicy.FORFEIT` so the opponent wins and the match continues.
- Games MAY override to implement domain-specific policies (skip turn, forfeit, retry once).
- MUST be deterministic given identical state and inputs.
- MAY use `error.parse_result.metadata` (candidates, reasoning flags, allowed actions) to tailor penalties.
- MUST avoid mutating match state; state changes occur only through Console/TurnLoop policy application.

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
20. **IV3**: When `information_level="partial"`, `get_view()` SHOULD include only player's own stats and observable actions (no opponent private data).
21. **IV4**: Games MAY define custom information levels beyond "full"/"partial" for research purposes.
22. **IV5**: `information_level` MUST be captured in game configuration metadata for reproducibility.

### 5.8 Player Ordering (PO)
23. **PO1**: Games MAY override `get_player_order()` to customize pre-match player ordering; default returns `None` (Console applies fairness via Fisher-Yates shuffle).
24. **PO2**: Games MUST return same `Player` instances from input if overriding (no additions, removals, or duplicates). Console validates and raises `ValueError` on mismatch.
25. **PO3**: Games MUST use provided `rng` parameter for any random decisions in `get_player_order()` (maintains reproducibility). Games MUST NOT create own `RandomGenerator` instances.
26. **PO4**: When `get_player_order()` returns `None`, Console MUST apply Fisher-Yates shuffle using match-specific RNG (eliminates first-player bias, guarantees reproducibility).

### 5.9 Mechanic Execution (ME)
27. **ME1**: `run(runtime, players)` MUST be the only entry point used by the console. Games MUST treat `runtime` as the exclusive gateway for event emission, recorder writes, RNG usage, parse-failure handling, and state validation.
28. **ME2**: Games inheriting the stock mechanic classes (e.g., `TurnBasedGame`) MUST NOT override `run()` unless implementing a fundamentally new execution model. Authors creating custom mechanics MUST document behaviour and reference the relevant mechanic spec.
29. **ME3**: Every successful player decision MUST result in a call to `runtime.record_turn(...)` (even if the action later fails validation). Every action or round MUST emit at least one `GAMEPLAY` event through `runtime.emit_event(...)`.
30. **ME4**: `run()` MUST return a JSON-serialisable final state and MUST signal truncation via the boolean flag when runtime’s `max_turns` limit or a mechanic-level termination triggers.
31. **ME5**: `run()` MUST propagate unhandled exceptions; runtime/console attach `match_context` metadata for logging and replay. Mechanics MAY raise domain-specific exceptions, but they MUST include the acting player/turn in the error message for diagnostics.

## 6. Data Flow & Interaction
- **Session init**: Facade → Console (game, players, seed) → game.setup(players) → canonical `game_state`.
- **Player ordering**: Console.run() → **game.get_player_order(players, rng=match_rng, match_context)** → returns None or custom list → Console applies shuffle or validates custom order → records `player_order`, `player_order_source`, `first_player` in metadata.
- **Match execution**: Console._play_match() → constructs `MatchRuntime` → **game.run(runtime, ordered_players)** → mechanic helper (TurnLoop, etc.) → (final_state, events, truncated).
- **Turn sequencing**: TurnLoop._execute_turn() → **game.get_current_player(game_state, players)** → identify acting player → proceed with turn.
- **View generation**: Console → game.get_view(game_state, player) → Renderer.format(view) → Player.decide().
- **Turn loop**: TurnLoop → game.update(game_state, player, action, rng) → validate_state → status → GAMEPLAY events.
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

    def setup(self, players):
        return {"round": 0, "coin": None, "winner": None}

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

    def setup(self, players):
        return {
            "health": {p: self.max_health for p in players},
            "potions": {p: 3 for p in players},
            "last_action": {p: None for p in players},
            "turn": 1
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

    def setup(self, players):
        return {"phase": 0, "board": empty_board(), "last_action": None}

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
  - Example: `"{game_instructions}\n\nRespond 'OK' to begin."`
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
| Player ordering | PO1-PO4 | Run same seed twice, assert identical player_order metadata; test custom override validation (reject invalid lists); verify default None triggers Console shuffle. |

## 10. Design Rationale
- Dict-based `game_state` keeps recorder, renderer, and replay pipelines simple and language-agnostic.
- Narrative ownership (G15) prevents console mission creep and supports dynamic tutorials.
- Optional hooks (`validate_state`, `get_events`) let games opt into richer observability without burdening simple prototypes.
- Infrastructure bindings (event emitter/factory) follow Null-object patterns so games can emit events safely even when recorder is absent.
- **Always-on handshake**: LLMs need instructions to play effectively. Front-loading in handshake reduces turn prompt costs (63% token savings vs repeating instructions every turn). No policy enum needed - handshake is mandatory.
- **run() delegation pattern**: Centralizing mechanics inside `game.run(runtime, players)` keeps the console generic while ensuring games use the shared runtime for events, recorder, RNG, and parse-failure handling. The stock `TurnBasedGame` implementation delegates to TurnLoop so all sequential games follow an identical execution lifecycle.
- **get_current_player() override point**: Provides clean extension for custom turn order (auction bidding, simultaneous phases) while maintaining round-robin default for 90% of games. TurnLoop validates returned player name prevents runtime errors from mismatched names.
- **get_player_order() optional hook**: Console is the source of fairness by default (Fisher-Yates shuffle), removing burden from 99% of games. Games override only when ordering is semantically meaningful (auction winners, asymmetric roles, previous-winner advantage). Optional return (None vs List) makes intent explicit and keeps game authors from feeling obligated to implement custom logic.

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
