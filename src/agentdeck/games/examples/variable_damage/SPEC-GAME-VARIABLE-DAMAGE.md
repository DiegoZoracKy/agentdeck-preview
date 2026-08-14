# SPEC-GAME-VARIABLE-DAMAGE v0.1.0

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-03-26
> Implementation: ✅ Complete (`src/agentdeck/games/examples/variable_damage/game.py`)
> Audience: game authors, renderer authors, and execution-system contributors

## 1. Purpose
- Provide a small stochastic combat game that preserves the simplicity of FixedDamage while introducing controlled uncertainty.
- Let researchers test whether strategy-stack findings from `FixedDamageGame` transfer when outcomes can no longer be solved by exact fixed-damage arithmetic.
- Serve as a bundled reference game for studying risk handling, survival margin, and policy robustness under seeded randomness.

## 2. Scope & Philosophy Alignment
- Follows `SPEC.md` separation principles: the game owns rules, state, visibility, RNG consumption, and terminal conditions; players and controllers remain generic.
- Follows `CONTRIBUTING.md` spec-first workflow: this spec locks the Game contract before downstream use.
- Preserves the FixedDamage mental model where possible:
  - same actions
  - same turn loop
  - same visibility modes
  - same two-player release scope
- Adds only one new core mechanic:
  - `ATTACK` damage is sampled from a configured inclusive integer range
- Non-goals:
  - prompt strategy design
  - downstream metric design
  - experiment package design
  - non-uniform damage distributions in `v0.1.0`

## 3. Responsibilities
- Own a seeded two-player combat state machine with actions `ATTACK` and `POTION`.
- Expose a small configuration surface for HP, healing, starting potions, damage range, and visibility.
- Consume RNG deterministically and explicitly during `ATTACK`.
- Preserve a player-view surface close to `FixedDamageGame` so cross-game comparison is clean.
- Keep uncertainty real in partial mode by not exposing explicit damage-roll fields in the public view.

## 4. Data Structures

### 4.1 Game Configuration
`VariableDamageGame` accepts these constructor parameters:
- `max_health: int = 100`
- `min_attack_damage: int = 15`
- `max_attack_damage: int = 25`
- `potion_heal: int = 30`
- `starting_potions: int = 3`
- `information_level: str = "full"`

Supported `information_level` values for this spec are:
- `"full"`: all players' HP and potion counts are visible in `get_view()`
- `"partial"`: only the requesting player's HP and potion counts are visible in `get_view()`

Validation rules:
- `min_attack_damage` and `max_attack_damage` MUST be positive integers.
- `min_attack_damage` MUST be less than or equal to `max_attack_damage`.
- Unsupported `information_level` values MUST raise `ValueError` at construction time.

### 4.2 Canonical Game State
`setup()` and `update()` produce a JSON-serializable canonical state with these game-owned keys:

```python
{
    "health": {player_name: int},
    "potions": {player_name: int},
    "last_action": {player_name: str | None},
    "turn": int,
}
```

Notes:
- This intentionally matches the FixedDamage state shape.
- `v0.1.0` does **not** add a `last_damage` field to canonical state.
- Realized damage remains recoverable from canonical HP deltas and recorder events.
- Turn-based mechanic bookkeeping keys such as `_turn_count` and `_first_player_idx` remain outside this game spec.

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

Visibility behavior:
- `health` and `potions` are filtered by `information_level`.
- `last_action` and `turn` remain visible in all supported modes.
- `last_damage` is intentionally omitted from the public view in `v0.1.0`.

Rationale for omitting `last_damage`:
- the damage information is inferable from HP deltas by a model that tracks state over time
- explicitly exposing it would collapse part of the intended uncertainty condition
- this omission is deliberate, not an oversight

## 5. Public API

### 5.1 `instructions -> str`
- MUST describe:
  - starting health and potion count
  - `ATTACK` as variable damage in the configured inclusive range
  - `POTION` healing amount
  - win condition
  - configured information level

### 5.2 `allowed_actions -> List[str]`
- MUST return `["ATTACK", "POTION"]`.

### 5.3 `default_handshake_template -> str`
- MUST include:
  - `{game_instructions}`
  - `{controller_format}`
  - `{handshake_controller_format}`
- SHOULD keep the turn prompt state-focused, same as the bundled FixedDamage game.

### 5.4 `setup(players: List[str], seed: int) -> Dict[str, Any]`
- MUST reject any roster whose length is not exactly `2` by raising `ValueError`.
- MUST return a JSON-serializable state using the structure in §4.2.
- MUST initialize every listed player to:
  - `health[player] = max_health`
  - `potions[player] = starting_potions`
  - `last_action[player] = None`
  - `turn = 1`
- MUST be deterministic for identical players and config.
- MAY ignore `seed` during setup if no setup-time randomness exists.

### 5.5 `update(game_state, player, action, *, rng) -> Dict[str, Any]`
- MUST normalize `action.action` to uppercase before execution.
- MUST reject actions outside `allowed_actions` with `ValueError`.
- MUST record the resolved action in `last_action[player]`.
- MUST increment `turn` by exactly `1` after each successful update.
- MUST accept and use the provided `rng` exactly as defined below.

Action semantics:
- `ATTACK`
  - MUST identify the opponent in the two-player roster.
  - MUST consume `rng` exactly once to sample an integer damage value:
    - `damage = rng.randint(min_attack_damage, max_attack_damage)`
  - Sampling MUST be inclusive at both ends of the configured range.
  - No other randomness may be consumed during that `ATTACK` resolution.
  - MUST reduce the opponent's HP by the sampled damage.
  - MUST clamp resulting HP at `0`.
- `POTION`
  - If the acting player has at least one potion remaining, MUST:
    - increase the acting player's HP by `potion_heal`, capped at `max_health`
    - decrement that player's potion count by `1`
  - If the acting player has zero potions remaining, MUST perform a silent no-op on HP and potion count.

RNG contract:
- `ATTACK` is the only gameplay action that consumes RNG in `v0.1.0`.
- `POTION`, `status()`, and `get_view()` MUST NOT consume RNG.
- This contract exists to preserve replayability and mid-match reasoning about seed flow.

### 5.6 `status(game_state) -> GameStatus`
- MUST return `GameStatus(is_over=False, winner=None)` while two or more players have HP greater than `0`.
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
- MUST NOT expose `last_damage` or any explicit realized damage field in `v0.1.0`.
- MUST NOT mutate the supplied `game_state`.

## 6. Invariants & Guarantees
- `VD1`: `setup()`, `update()`, and `get_view()` outputs MUST be JSON-serializable and deep-copyable.
- `VD2`: Canonical state MUST retain truthful full information even when `information_level="partial"`.
- `VD3`: `get_view()` MUST enforce visibility filtering without mutating canonical state.
- `VD4`: `ATTACK` MUST sample uniformly from the inclusive integer range `[min_attack_damage, max_attack_damage]`.
- `VD5`: `ATTACK` MUST consume RNG exactly once per resolved attack and nowhere else in the game contract.
- `VD6`: `ATTACK` MUST never drive HP below `0`.
- `VD7`: `POTION` MUST never raise HP above `max_health`.
- `VD8`: `turn` MUST begin at `1` and increase by exactly `1` per successful update.
- `VD9`: `last_action` MUST reflect the latest resolved action for the acting player.
- `VD10`: `last_action` MUST remain visible even in partial-information mode.
- `VD11`: `last_damage` MUST remain absent from the public view in `v0.1.0`.
- `VD12`: For identical config, seed forks, and action sequences, the game MUST be replayable deterministically.

## 7. Data Flow & Interaction
- Init: Researcher/Game author -> `VariableDamageGame(config)` -> deterministic rules + visibility contract
- Match start: Turn-based mechanic -> `setup(players, seed)` -> canonical initial state
- Turn execution: Mechanic -> `get_view()` -> player/controller -> `update(..., rng=turn_rng)` -> new canonical state
- Replay: Recorder -> canonical state transitions + seeded event order -> deterministic re-read of realized damage
- Downstream analysis can derive risk-band measurements from recorder events and HP deltas without explicit `last_damage` view fields.

## 8. Error Handling & Edge Cases
- Unsupported `information_level` values MUST raise `ValueError` at construction time.
- Invalid damage ranges (`min_attack_damage > max_attack_damage`, non-positive values) MUST raise `ValueError`.
- Invalid action strings MUST raise `ValueError`.
- `ATTACK` with no available opponent MUST raise `ValueError`.
- `setup()` MUST reject any roster whose length is not exactly `2`.
- Exhausted-potion `POTION` remains a silent no-op in `v0.1.0`, matching FixedDamage behavior.

## 9. Examples

### 9.1 Default Setup
```python
game = VariableDamageGame()
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
- `Bob` loses an integer amount of HP in `[min_attack_damage, max_attack_damage]`
- `last_action["Alice"] == "ATTACK"`
- `turn` increments by `1`

### 9.3 Partial View
```python
game = VariableDamageGame(information_level="partial")
view = game.get_view(state, "Alice")
```

Expected properties:
- `view["health"]` includes `"Alice"` but not `"Bob"`
- `view["potions"]` includes `"Alice"` but not `"Bob"`
- `view["last_action"]` includes both players
- no explicit realized-damage field is present

## 10. Testing Strategy
- Unit tests MUST cover:
  - constructor validation for damage ranges and visibility mode
  - serializability and deep-copyability of state and views
  - deterministic replay for identical RNG inputs
  - inclusive RNG sampling bounds for `ATTACK`
  - exact single-consumption RNG behavior per `ATTACK`
  - HP floor at zero for `ATTACK`
  - healing cap at `max_health` for `POTION`
  - partial vs full visibility behavior
  - absence of `last_damage` in public view
  - `status()` terminal cases

## 11. Design Rationale
- The `[15, 25]` default preserves expected damage `20`, making comparison with FixedDamage cleaner.
- Keeping the state and view shape close to FixedDamage reduces cross-game prompt and renderer churn.
- Omitting `last_damage` preserves uncertainty more cleanly than explicitly surfacing the roll.
- Locking exact RNG-consumption semantics now prevents replay drift and ambiguous scorer assumptions later.

## 12. Open Questions / Future Work
- Should future versions expose alternative damage distributions beyond uniform integer sampling?
- Should a later version surface explicit realized-damage metadata to observers while still hiding it from players?
- Should VariableDamage get its own bundled conservative bot and risk-seeking bot for calibration?

## 13. References
- [`CONTRIBUTING.md`](../../../../../CONTRIBUTING.md)
- [`SPEC-GAME`](../../../../../specs/SPEC-GAME.md)
- [`SPEC-GAME-MECHANIC-TURN-BASED`](../../../../../specs/SPEC-GAME-MECHANIC-TURN-BASED.md)
- [`SPEC-GAME-FIXED-DAMAGE`](../fixed_damage/SPEC-GAME-FIXED-DAMAGE.md)
- [`FixedDamage Arc 1`](../../../../../research/2026-03-23-fixed-damage-arc-1/README.md)
