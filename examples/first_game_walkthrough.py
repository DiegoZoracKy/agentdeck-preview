"""
Build-your-first-game walkthrough (mock-friendly).

This example shows how to:
1) Author a small TurnBasedGame
2) Run a match with deterministic MockPlayers (no API keys)
3) Record the match and replay it for debugging
"""

import json
from pathlib import Path

from agentdeck import (
    ActionOnlyController,
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

    def setup(self, players):
        return {"health": {player: self.MAX_HEALTH for player in players}, "_turn_count": 1}

    def get_view(self, state, player):
        opponent = next(name for name in state["health"] if name != player)
        return (
            f"Your HP: {state['health'][player]} | "
            f"Opponent HP: {state['health'][opponent]}\n"
            "Choose ATTACK (deal 1 damage) or DEFEND (recover 1 HP)."
        )

    def update(self, state, player, action, *, rng, match_context):
        action = (action or "").strip().upper()
        opponent = next(name for name in state["health"] if name != player)

        if action not in {"ATTACK", "DEFEND"}:
            raise ValueError(f"Invalid action '{action}'. Choose ATTACK or DEFEND.")

        if action == "ATTACK":
            state["health"][opponent] -= 1
        else:
            state["health"][player] = min(self.MAX_HEALTH, state["health"][player] + 1)

        state["_turn_count"] = state.get("_turn_count", 0) + 1
        return state

    def status(self, state):
        alive = [player for player, hp in state["health"].items() if hp > 0]
        if len(alive) == 1:
            return GameStatus(is_over=True, winner=alive[0])
        if not alive:
            return GameStatus(is_over=True, winner=None)
        if state.get("_turn_count", 0) >= 12:
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
