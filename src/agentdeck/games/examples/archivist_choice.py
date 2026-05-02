"""ArchivistChoiceGame: non-combat benchmark-style example for AgentDeck."""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.core.types import ActionResult, GameStatus, RandomGenerator


class ArchivistChoiceGame(TurnBasedGame):
    """
    Two archivists independently triage the same manuscript queue.

    Each player sees the current manuscript, chooses a preservation action, and
    earns points based on fit. Both players receive the same queue, so outcomes
    reflect policy quality rather than seat order.
    """

    MANUSCRIPTS = [
        {
            "id": "field-journal",
            "title": "Water-damaged field journal",
            "condition": "fragile",
            "risk": "low contamination",
            "best_action": "RESTORE",
            "scores": {"CATALOG": 1, "RESTORE": 3, "QUARANTINE": 0},
        },
        {
            "id": "port-ledger",
            "title": "Mold-spotted port ledger",
            "condition": "unstable",
            "risk": "high contamination",
            "best_action": "QUARANTINE",
            "scores": {"CATALOG": -1, "RESTORE": -2, "QUARANTINE": 3},
        },
        {
            "id": "letters",
            "title": "Stable correspondence bundle",
            "condition": "stable",
            "risk": "low handling risk",
            "best_action": "CATALOG",
            "scores": {"CATALOG": 2, "RESTORE": 0, "QUARANTINE": -1},
        },
        {
            "id": "treaty-draft",
            "title": "Faded treaty draft",
            "condition": "fragile",
            "risk": "historically significant",
            "best_action": "RESTORE",
            "scores": {"CATALOG": 1, "RESTORE": 3, "QUARANTINE": 0},
        },
    ]

    @property
    def instructions(self) -> str:
        return """
Archivist Choice

You are triaging manuscripts for a public archive. Each turn shows one manuscript.

Actions:
- CATALOG: document the item and move it into normal access
- RESTORE: preserve fragile high-value material before access
- QUARANTINE: isolate material that may contaminate the collection

Goal:
- Choose the best preservation action for each manuscript
- Highest archive quality score after all manuscripts wins
        """.strip()

    @property
    def allowed_actions(self) -> List[str]:
        return ["CATALOG", "RESTORE", "QUARANTINE"]

    @property
    def default_handshake_template(self) -> str:
        return (
            "{game_instructions}\n\n"
            "When gameplay begins, use this response format:\n"
            "{controller_format}\n\n"
            "{handshake_controller_format}"
        )

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        if len(players) != 2:
            raise ValueError("ArchivistChoiceGame requires exactly 2 players")
        return {
            "turn": 1,
            "scores": {player: 0 for player in players},
            "case_index": {player: 0 for player in players},
            "processed": {player: [] for player in players},
            "last_action": {player: None for player in players},
            "manuscripts": copy.deepcopy(self.MANUSCRIPTS),
        }

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        case_index = game_state["case_index"][player]
        current = None
        if case_index < len(game_state["manuscripts"]):
            current = game_state["manuscripts"][case_index]

        return {
            "turn": game_state["turn"],
            "player": player,
            "your_score": game_state["scores"][player],
            "cases_completed": case_index,
            "cases_total": len(game_state["manuscripts"]),
            "current_manuscript": current,
            "allowed_actions": self.allowed_actions,
        }

    def update(
        self,
        game_state: Dict[str, Any],
        player: str,
        action: ActionResult,
        *,
        rng: RandomGenerator,
    ) -> Dict[str, Any]:
        state = copy.deepcopy(game_state)
        action_token = (action.action or "").strip().upper()
        if action_token not in self.allowed_actions:
            raise ValueError(
                f"Invalid action '{action_token}'. Allowed actions: {self.allowed_actions}"
            )

        case_index = state["case_index"][player]
        if case_index >= len(state["manuscripts"]):
            raise ValueError(f"{player} has no remaining manuscripts to process")

        manuscript = state["manuscripts"][case_index]
        delta = manuscript["scores"][action_token]
        state["scores"][player] += delta
        state["case_index"][player] += 1
        state["last_action"][player] = action_token
        state["processed"][player].append(
            {
                "manuscript_id": manuscript["id"],
                "action": action_token,
                "best_action": manuscript["best_action"],
                "score_delta": delta,
            }
        )
        state["turn"] += 1
        return state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        total_cases = len(game_state["manuscripts"])
        if any(index < total_cases for index in game_state["case_index"].values()):
            return GameStatus(is_over=False)

        scores = game_state["scores"]
        high_score = max(scores.values())
        winners = [player for player, score in scores.items() if score == high_score]
        return GameStatus(is_over=True, winner=winners[0] if len(winners) == 1 else None)
