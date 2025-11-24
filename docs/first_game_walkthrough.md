# Build Your First Game & Debug with Replay

This walkthrough mirrors `examples/first_game_walkthrough.py` and requires **no API keys**. It shows how to author a tiny game, run a deterministic match, record it, and replay the artifact for debugging.

## 1) Author a Tiny Turn-Based Game

```python
from agentdeck import GameStatus, TurnBasedGame

class TinyBattleGame(TurnBasedGame):
    MAX_HEALTH = 3

    def setup(self, players):
        return {"health": {p: self.MAX_HEALTH for p in players}, "_turn_count": 1}

    def get_view(self, state, player):
        opponent = next(name for name in state["health"] if name != player)
        return (
            f"Your HP: {state['health'][player]} | "
            f"Opponent HP: {state['health'][opponent]}\n"
            "Choose ATTACK or DEFEND."
        )

    def update(self, state, player, action, *, rng, match_context):
        action = (action or "").strip().upper()
        opponent = next(name for name in state["health"] if name != player)
        if action == "ATTACK":
            state["health"][opponent] -= 1
        elif action == "DEFEND":
            state["health"][player] = min(self.MAX_HEALTH, state["health"][player] + 1)
        else:
            raise ValueError("Use ATTACK or DEFEND")
        state["_turn_count"] = state.get("_turn_count", 0) + 1
        return state

    def status(self, state):
        alive = [p for p, hp in state["health"].items() if hp > 0]
        if len(alive) == 1:
            return GameStatus(is_over=True, winner=alive[0])
        if not alive or state.get("_turn_count", 0) >= 12:
            return GameStatus(is_over=True, winner=None)
        return GameStatus(is_over=False)
```

## 2) Run a Match with Mock Players (records automatically)

```bash
python examples/first_game_walkthrough.py
```

What happens:
- Uses deterministic `MockPlayer` instances (no network calls, no API keys)
- Records to `agentdeck_records/first_game/.../match_XXX.json`
- Streams narration via `MatchNarrator` and aggregates stats via `StatsTracker`

## 3) Replay the Recording for Debugging

`examples/first_game_walkthrough.py` automatically replays the latest recording. To replay a specific file:

```python
from pathlib import Path
import json
from agentdeck import MatchNarrator, ReplayEngine

latest = sorted(Path("agentdeck_records/first_game").rglob("match_*.json"))[-1]
with latest.open() as handle:
    match_data = json.load(handle)

ReplayEngine(match_data).replay(spectators=[MatchNarrator()], speed=0.0)
```

This emits the exact event stream from the recorded match (handshake → gameplay → conclusion), making it easy to debug controller parsing, renderer output, and game logic.
