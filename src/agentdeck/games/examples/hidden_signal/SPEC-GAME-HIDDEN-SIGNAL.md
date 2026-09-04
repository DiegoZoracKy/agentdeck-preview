# SPEC-GAME-HIDDEN-SIGNAL v1.0.0

> Status: Final  
> Version: 1.0.0  
> Last Updated: 2026-08-29  
> Implementation: Complete (`game.py`)
> Review State: Approved for the private Miningames Gate A acceptance wave  
> Audience: game authors, Research authors, renderer authors

## 1. Purpose

Hidden Signal is a small single-Player Game in which the Player must either
inspect a concealed signal at a declared cost or commit directly to one of two
choices. It provides a reusable no-winner example for execution, replay, and
Research acceptance without introducing Research meaning into the Game.

## 2. Scope and philosophy alignment

- The Game owns rules, canonical state, visibility, actions, costs, and
  termination.
- The execution kernel records what happened; downstream Research decides
  whether inspection behavior is meaningful for a particular Study.
- Identical configuration, roster, seed, and actions MUST produce identical
  state transitions.
- The Game MUST remain independent of Miningames product terminology,
  Measures, Evidence, Findings, and presentation-specific epistemic labels.

Hidden Signal implements [`SPEC-GAME`](../../../../../specs/SPEC-GAME.md) over
the sequential loop in
[`SPEC-GAME-MECHANIC-TURN-BASED`](../../../../../specs/SPEC-GAME-MECHANIC-TURN-BASED.md).

Non-goals:

- claiming that inspection measures curiosity, planning, or information seeking
  outside this world;
- supporting multiple Players, competition, ranking, or a winner;
- generalized clue systems, arbitrary signal alphabets, or multiple inspections;
- defining a Study, Measure, viewer, or product experience.

## 3. Configuration and canonical state

`HiddenSignalGame` accepts:

- `signal_visibility: str = "hidden"`, one of `"hidden"` or `"visible"`;
- `inspection_cost: int = 1`, required to be non-negative;
- `correct_reward: int = 2`, required to be positive.

`setup()` returns this game-owned canonical state:

```python
{
    "player": str,
    "signal": "RED" | "BLUE",
    "revealed_signal": "RED" | "BLUE" | None,
    "signal_visibility": "hidden" | "visible",
    "inspections": int,
    "inspection_cost_total": int,
    "choice": "RED" | "BLUE" | None,
    "correct": bool | None,
    "score": int,
    "done": bool,
    "turn": int,
}
```

The canonical `signal` is execution truth and MUST remain present even when the
Player view hides it.

## 4. Public contract

### 4.1 Actions

`allowed_actions` MUST return:

```python
["INSPECT", "CHOOSE_RED", "CHOOSE_BLUE"]
```

- `INSPECT` reveals the signal, increments `inspections`, adds
  `inspection_cost` to `inspection_cost_total`, subtracts that cost from
  `score`, and leaves the Game active.
- `CHOOSE_RED` and `CHOOSE_BLUE` commit to a signal, set `correct`, add
  `correct_reward` to `score` only when correct, and terminate the Game.
- A second `INSPECT`, any action after termination, or an unknown action MUST
  raise `ValueError` without changing the supplied state.

### 4.2 `setup(players, seed)`

- MUST require exactly one Player.
- MUST choose `RED` or `BLUE` deterministically from `seed`.
- MUST begin at turn `1`, with zero inspections and cost, zero score, no
  choice, no correctness result, and `done=False`.
- In visible mode, `revealed_signal` MUST equal the canonical signal at setup.
- In hidden mode, `revealed_signal` MUST be `None` at setup.

### 4.3 `get_view(game_state, player)`

The view MUST contain:

```python
{
    "player": str,
    "signal": "RED" | "BLUE" | "HIDDEN",
    "signal_visibility": "hidden" | "visible",
    "inspection_available": bool,
    "inspections": int,
    "inspection_cost_total": int,
    "choice": "RED" | "BLUE" | None,
    "correct": bool | None,
    "score": int,
    "done": bool,
    "turn": int,
    "allowed_actions": list[str],
}
```

- Hidden mode MUST expose `"HIDDEN"` until an inspection occurs.
- Visible mode and an inspected hidden game MUST expose the actual signal.
- `inspection_available` MUST be false after inspection or termination.
- The view MUST NOT expose a second source of truth or mutate canonical state.

### 4.4 `status(game_state)`

- Before commitment: `GameStatus(is_over=False, winner=None)`.
- After commitment: `GameStatus(is_over=True, winner=None)`.
- `winner` MUST always be `None`; correctness and score are observations, not
  winner semantics.

### 4.5 Instructions and handshake

- `instructions` MUST explain visibility, inspection cost, choice reward, and
  the absence of a competitive winner.
- `default_handshake_template` MUST include `{game_instructions}`,
  `{controller_format}`, and `{handshake_controller_format}`.

## 5. Invariants

- `HS1`: the roster contains exactly one Player.
- `HS2`: setup randomness is a deterministic function of `seed`.
- `HS3`: canonical state and views are JSON-serializable and deep-copyable.
- `HS4`: hidden views never expose `signal` before inspection.
- `HS5`: at most one inspection succeeds per Match.
- `HS6`: a successful update increments `turn` by exactly one.
- `HS7`: committing terminates the Game and never assigns a winner.
- `HS8`: failed updates do not mutate the supplied state.
- `HS9`: `get_view()` is a pure projection of canonical state.
- `HS10`: Game code contains no Research or Miningames product authority.

## 6. Errors

- Invalid visibility, negative inspection cost, or non-positive reward fails at
  construction with `ValueError`.
- Invalid roster fails during setup with `ValueError`.
- Invalid, repeated, or post-terminal actions fail with `ValueError`.
- State validation MUST fail noisily when required keys, types, or cross-field
  relationships violate this contract.

## 7. Testing strategy

Tests MUST cover every invariant, including:

- deterministic signal selection across seeds;
- hidden and visible views;
- inspection and both correct/incorrect commitments;
- no-winner terminal status;
- invalid configuration, roster, state, repeated inspection, and post-terminal
  action failures;
- immutability after both successful and failed updates;
- execution through the standard turn-based runtime to canonical Records.

## 8. Example

```python
game = HiddenSignalGame(signal_visibility="hidden")
state = game.setup(["Observer"], seed=42)

state = game.update(state, "Observer", inspect_action, rng=rng)
assert game.get_view(state, "Observer")["signal"] in {"RED", "BLUE"}

state = game.update(state, "Observer", choose_action, rng=rng)
assert game.status(state).is_over
assert game.status(state).winner is None
```

## 9. Design rationale

- One optional inspection creates a consequential sequential decision while
  keeping the state machine legible.
- Correctness and score preserve useful factual outcomes without importing
  competition or winner assumptions.
- Visibility is configuration because the exact world differs; Research may
  compare those configurations through prepared Assemblies without redefining
  them in a Study.
- The Game deliberately stops short of naming a behavioral construct. A Game
  Research Profile can later explain scoped opportunities downstream.

## 10. References

- [`SPEC-GAME`](../../../../../specs/SPEC-GAME.md)
- [`SPEC-GAME-MECHANIC-TURN-BASED`](../../../../../specs/SPEC-GAME-MECHANIC-TURN-BASED.md)
- [`SPEC-RESEARCH`](../../../../../specs/SPEC-RESEARCH.md)
