# Build Your First Game & Debug with Replay

This walkthrough mirrors `examples/first_game_walkthrough.py` and requires **no API keys**. It shows how to author a tiny game, run a deterministic match, record it, and replay the artifact for debugging.

## 1) Author a Tiny Turn-Based Game

The code below is kept in lockstep with `examples/first_game_walkthrough.py`.

```python
# DOCS_SNIPPET_START

import json
from pathlib import Path
from typing import Any, Dict, List

from agentdeck import (
    ActionOnlyController,
    ActionResult,
    AgentDeck,
    GameStatus,
    MatchNarrator,
    MockPlayer,
    Recorder,
    ReplayEngine,
    StatsTracker,
    TurnBasedGame,
)

class TinyBattleGame(TurnBasedGame):
    """Simple duel: ATTACK deals 1 damage, DEFEND heals 1 (max 3 HP)."""

    MAX_HEALTH = 3
    MAX_TURNS = 12

    @property
    def instructions(self) -> str:
        return (
            "Tiny Battle Game\n\n"
            "Actions:\n"
            "- ATTACK: deal 1 damage to the opponent\n"
            "- DEFEND: recover 1 HP (max 3)\n\n"
            "Win by reducing the opponent to 0 HP."
        )

    @property
    def allowed_actions(self) -> List[str]:
        return ["ATTACK", "DEFEND"]

    @property
    def default_handshake_template(self) -> str:
        return (
            "{game_instructions}\n\n"
            "Reply with 'OK' when you understand and are ready to begin.\n\n"
            "{handshake_controller_format}"
        )

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        return {"health": {player: self.MAX_HEALTH for player in players}, "_turn_count": 1}

    def get_view(self, state: Dict[str, Any], player: str) -> Dict[str, Any]:
        opponent = next(name for name in state["health"] if name != player)
        return {
            "turn": state.get("_turn_count", 1),
            "player": player,
            "opponent": opponent,
            "health": {
                player: state["health"][player],
                opponent: state["health"][opponent],
            },
            "prompt": "Choose ATTACK (deal 1 damage) or DEFEND (recover 1 HP).",
        }

    def update(
        self,
        state: Dict[str, Any],
        player: str,
        action: ActionResult,
        *,
        rng,
    ) -> Dict[str, Any]:
        opponent = next(name for name in state["health"] if name != player)
        action_token = (action.action or "").strip().upper()

        if action_token not in self.allowed_actions:
            raise ValueError(f"Invalid action '{action_token}'. Choose ATTACK or DEFEND.")

        if action_token == "ATTACK":
            state["health"][opponent] -= 1
        else:
            state["health"][player] = min(self.MAX_HEALTH, state["health"][player] + 1)

        return state

    def status(self, state: Dict[str, Any]) -> GameStatus:
        alive = [player for player, hp in state["health"].items() if hp > 0]
        if len(alive) == 1:
            return GameStatus(is_over=True, winner=alive[0])
        if not alive:
            return GameStatus(is_over=True, winner=None)
        if state.get("_turn_count", 0) > self.MAX_TURNS:
            return GameStatus(is_over=True, winner=None)
        return GameStatus(is_over=False)


def build_mock_players():
    """Deterministic players keep the walkthrough reproducible."""
    controller = ActionOnlyController()
    return [
        MockPlayer(name="Alice", actions=["ATTACK", "ATTACK", "DEFEND"], controller=controller),
        MockPlayer(name="Bob", actions=["DEFEND", "ATTACK", "ATTACK"], controller=controller),
    ]


def run_and_replay():
    game = TinyBattleGame()
    recorder = Recorder(output_dir="agentdeck_records/first_game")
    stats = StatsTracker()
    players = build_mock_players()

    # Record a single match with narration
    with AgentDeck(game=game, spectators=[recorder, MatchNarrator(), stats]) as deck:
        results = deck.play(players=players, matches=1, seed=7)

    summary = stats.get_stats()
    print(f"\nWin rates: {results.win_rates}")
    print(f"Avg match duration: {summary.get('avg_match_duration', 0):.2f}s")

    latest_recording = sorted(Path(recorder.output_dir).rglob("match_*.json"))[-1]
    print(f"\nReplaying latest recording from: {latest_recording}")

    with latest_recording.open("r", encoding="utf-8") as handle:
        match_data = json.load(handle)

    ReplayEngine(match_data).replay(spectators=[MatchNarrator()], speed=0.0)


if __name__ == "__main__":
    run_and_replay()

# DOCS_SNIPPET_END
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
