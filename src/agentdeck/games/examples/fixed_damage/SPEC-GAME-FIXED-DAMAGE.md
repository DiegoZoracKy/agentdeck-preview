# SPEC-GAME-FIXED-DAMAGE v0.1.0

> Status: Draft
> Version: 0.1.0
> Last Updated: 2026-03-18
> Implementation: ✅ Existing component (`src/agentdeck/games/examples/fixed_damage/game.py`)
> Audience: game authors, researchers, renderer authors

## 1. Purpose
- Provide a small deterministic combat game that makes agent behavior easy to observe, compare, and replay.
- Serve as a bundled reference game for tutorials, tests, and release-facing behavioral experiments.
- Keep the ruleset simple enough that policy quality, visibility choices, and prompt-contract effects can be studied without hidden mechanics.

## 2. Scope & Philosophy Alignment
- Upholds `SPEC.md` separation principles: the game owns rules, state, visibility, and win conditions; console and players remain generic.
- Supports `SPEC.md` reproducibility and observability principles through deterministic transitions, JSON-serializable state, and truthful canonical state for recorder/replay.
- `FixedDamageGame` is a concrete game built on top of [`SPEC-GAME`](../../../../../specs/SPEC-GAME.md) and the turn loop in [`SPEC-GAME-MECHANIC-TURN-BASED`](../../../../../specs/SPEC-GAME-MECHANIC-TURN-BASED.md).
- This spec defines the game's own configuration surface, canonical state, action semantics, visibility rules, and terminal conditions.
- Non-goals:
  - experiment design, hypothesis framing, or benchmark matrices
  - provider-specific prompting strategy
  - viewer styling or presentation details
- The release-supported use case is two-player competitive play. Other roster sizes are out of scope for this spec.

## 3. Responsibilities
- Own a deterministic combat state machine with exactly two gameplay actions: `ATTACK` and `POTION`.
- Expose a small configurable parameter set for health, damage, healing, starting potions, and information visibility.
- Produce player-specific views that preserve hidden information rules while keeping public trajectory signals legible.
- Provide default instructions and handshake text so AgentDeck can run the game without custom prompt glue.

## 4. Data Structures

### 4.1 Game Configuration
`FixedDamageGame` accepts these constructor parameters:
- `max_health: int = 100`
- `attack_damage: int = 20`
- `potion_heal: int = 30`
- `starting_potions: int = 3`
- `information_level: str = "full"`

Supported `information_level` values for this spec are:
- `"full"`: all players' HP and potion counts are visible in `get_view()`
- `"partial"`: only the requesting player's HP and potion counts are visible in `get_view()`

Unsupported `information_level` values MUST raise `ValueError` at construction time.

### 4.2 Game-Owned Canonical State
`setup()` and `update()` produce a JSON-serializable state with these game-owned keys:

```python
{
    "health": {player_name: int},
    "potions": {player_name: int},
    "last_action": {player_name: str | None},
    "turn": int,
}
```

Notes:
- `health` stores current HP for each player.
- `potions` stores remaining potion count for each player.
- `last_action` stores the most recent resolved action for each player, or `None` before that player has acted.
- `turn` is the game-owned turn counter starting at `1`.
- The turn-based mechanic MAY add internal bookkeeping keys such as `_turn_count` and `_first_player_idx`. Those keys are not owned by this game spec.

### 4.3 Player View
`get_view(game_state, player)` returns a JSON-serializable dict with this shape:

```python
{
    "health": {...},
    "potions": {...},
    "last_action": {player_name: str | None},
    "turn": int,
}
```

The `health` and `potions` sub-dicts are filtered by `information_level`. `last_action` and `turn` remain visible in all supported modes.

## 5. Public API

### 5.1 `instructions -> str`
- MUST return a plain-text summary of:
  - starting conditions
  - action semantics
  - win condition
  - configured information level
- SHOULD remain consistent with the configured constructor values.

### 5.2 `allowed_actions -> List[str]`
- MUST return `["ATTACK", "POTION"]`.
- MUST represent the canonical gameplay action vocabulary for controllers and researcher tooling.

### 5.3 `default_handshake_template -> str`
- MUST include:
  - `{game_instructions}`
  - `{controller_format}`
  - `{handshake_controller_format}`
- MUST front-load gameplay response instructions during handshake so the default turn prompt can remain state-focused.

### 5.4 `setup(players: List[str], seed: int) -> Dict[str, Any]`
- MUST reject any roster whose length is not exactly `2` by raising `ValueError`.
- MUST return a JSON-serializable canonical state using the structure in §4.2.
- MUST initialize every listed player to:
  - `health[player] = max_health`
  - `potions[player] = starting_potions`
  - `last_action[player] = None`
  - `turn = 1`
- MUST be deterministic for identical `players` and config.
- MAY ignore `seed`; the current implementation is deterministic without setup-time randomness.

### 5.5 `update(game_state, player, action, *, rng) -> Dict[str, Any]`
- MUST normalize `action.action` to uppercase before execution.
- MUST reject actions outside `allowed_actions` with `ValueError`.
- MUST record the resolved action in `last_action[player]`.
- MUST increment `turn` by exactly `1` after each successful update.
- MUST accept the provided `rng` parameter even when unused.

Action semantics:
- `ATTACK`
  - In the release-supported two-player case, MUST reduce the opponent's HP by exactly `attack_damage`.
  - MUST clamp resulting HP at `0`.
- `POTION`
  - If the acting player has at least one potion remaining, MUST:
    - increase the acting player's HP by `potion_heal`, capped at `max_health`
    - decrement that player's potion count by `1`
  - If the acting player has zero potions remaining, MUST perform a silent no-op on HP and potion count.

### 5.6 `status(game_state) -> GameStatus`
- MUST return `GameStatus(is_over=False, winner=None)` while two or more players remain alive.
- MUST return `GameStatus(is_over=True, winner=<player>)` when exactly one player has HP greater than `0`.
- MUST return `GameStatus(is_over=True, winner=None)` when no players have HP greater than `0`.

### 5.7 `get_view(game_state, player) -> Dict[str, Any]`
- MUST return a JSON-serializable player-specific view using the structure in §4.3.
- MUST always include:
  - the requesting player's own HP
  - the requesting player's own potion count
  - the full `last_action` mapping
  - the current `turn`
- If `information_level == "full"`, MUST include all players' HP and potion counts.
- If `information_level == "partial"`, MUST omit opponents' HP and potion counts.
- MUST NOT mutate the supplied `game_state`.

## 6. Invariants & Guarantees
- `FD1`: `setup()`, `update()`, and `get_view()` outputs MUST be JSON-serializable and deep-copyable.
- `FD2`: Canonical state MUST retain truthful full information even when `information_level="partial"`.
- `FD3`: `get_view()` MUST enforce visibility filtering without mutating canonical state.
- `FD4`: `ATTACK` MUST never drive HP below `0`.
- `FD5`: `POTION` MUST never raise HP above `max_health`.
- `FD6`: `turn` MUST begin at `1` and increase by exactly `1` per successful update.
- `FD7`: `last_action` MUST reflect the latest resolved action for the acting player.
- `FD8`: The game MUST remain deterministic for identical config, setup inputs, and action sequences.
- `FD9`: Partial-information mode MUST still expose `last_action` as a public signal.
- `FD10`: Handshake onboarding MUST be sufficient for a default state-only turn prompt.

## 7. Data Flow & Interaction
1. Console constructs `FixedDamageGame` with chosen configuration.
2. `setup(players, seed)` creates the initial canonical state.
3. AgentDeck may use `instructions` and `default_handshake_template` during the handshake phase.
4. During play, the turn-based mechanic calls `get_view()` for the acting player and `update()` after controller parsing succeeds.
5. Recorder and replay operate on canonical state, not filtered views.
6. `status()` determines whether the match continues or ends.

## 8. Error Handling & Edge Cases
- Unsupported `information_level` values MUST raise `ValueError` at construction time.
- Invalid action strings MUST raise `ValueError`.
- `ATTACK` with no available opponent MUST raise `ValueError`.
- `setup()` MUST reject any roster whose length is not exactly `2`.
- Supported visibility modes for public use are `"full"` and `"partial"`.
- Research packages and examples SHOULD use explicit supported values.

## 9. Examples

### 9.1 Default Setup
```python
game = FixedDamageGame()
state = game.setup(["Alice", "Bob"], seed=42)
```

Expected initial state:

```python
{
    "health": {"Alice": 100, "Bob": 100},
    "potions": {"Alice": 3, "Bob": 3},
    "last_action": {"Alice": None, "Bob": None},
    "turn": 1,
}
```

### 9.2 Attack Update
```python
state = game.update(
    state,
    "Alice",
    ActionResult(action="ATTACK", raw_response="ACTION: ATTACK"),
    rng=rng,
)
```

Expected effect:
- `state["health"]["Bob"]` decreases by `attack_damage`, floored at `0`
- `state["last_action"]["Alice"] == "ATTACK"`
- `state["turn"]` increments by `1`

### 9.3 Partial View
```python
game = FixedDamageGame(information_level="partial")
view = game.get_view(state, "Alice")
```

Expected properties:
- `view["health"]` includes `"Alice"` but not `"Bob"`
- `view["potions"]` includes `"Alice"` but not `"Bob"`
- `view["last_action"]` includes both players

## 10. Testing Strategy
- Unit tests MUST cover:
  - serializability and deep-copyability of state and views
  - deterministic setup/update behavior
  - HP floor at zero for `ATTACK`
  - healing cap at `max_health` for `POTION`
  - partial vs full visibility behavior
  - handshake-template placeholders
  - `status()` terminal cases
  - `allowed_actions` contract
- Reference coverage currently lives primarily in [`tests/unit/test_game.py`](../../../../../tests/unit/test_game.py).

## 11. Design Rationale
- Fixed math and low state complexity make match trajectories easy to inspect in recordings, replays, and research packages.
- Keeping `last_action` visible even in partial mode preserves public temporal context without exposing full opponent state.
- Silent exhausted-potion handling keeps the game focused on policy quality rather than introducing a second invalid-action path beyond controller parsing.
- Handshake-heavy, turn-light prompting keeps the default runtime simple and makes turn-level reinforcement an explicit experimental variable instead of a hidden baseline behavior.

## 12. Open Questions / Future Work
- Should exhausted-potion no-ops emit an explicit event or remain silent?

## 13. References
- [`SPEC-GAME`](../../../../../specs/SPEC-GAME.md)
- [`SPEC-GAME-MECHANIC-TURN-BASED`](../../../../../specs/SPEC-GAME-MECHANIC-TURN-BASED.md)
- [`SPEC-CONTROLLER`](../../../../../specs/SPEC-CONTROLLER.md)
- [`SPEC-PROMPT-BUILDER`](../../../../../specs/SPEC-PROMPT-BUILDER.md)
- [`tests/unit/test_game.py`](../../../../../tests/unit/test_game.py)
