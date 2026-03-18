"""Game-local calibration bots for FixedDamage release experiments."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agentdeck.controllers import ActionOnlyController
from agentdeck.core.base.player import Player


class FixedDamagePolicyBot(Player):
    """
    Deterministic FixedDamage bot that derives actions from the rendered view text.

    This is intentionally game-specific. It exists so release-facing calibration
    cells can use first-class AgentDeck players without relying on test-only
    scaffolding or ad hoc prompt processing outside the player contract.
    """

    def __init__(self, name: str, *, controller=None, model: str = "fixed-damage-policy", **config):
        if controller is None:
            controller = ActionOnlyController()
        super().__init__(name=name, controller=controller, model=model, **config)

    def get_response(self, prompt: str) -> str:
        if getattr(self, "_active_phase", None) == "handshake":
            return "OK"

        action = self.choose_action(self._extract_view_state(prompt))
        controller_name = self.controller.__class__.__name__
        if "Reasoning" in controller_name:
            return f"REASONING: Deterministic FixedDamage policy\nACTION: {action}"
        return f"ACTION: {action}"

    def choose_action(self, view_state: Dict[str, int]) -> str:
        raise NotImplementedError

    def _extract_view_state(self, prompt: str) -> Dict[str, int]:
        section: Optional[str] = None
        health: Optional[int] = None
        potions: Optional[int] = None

        for line in prompt.splitlines():
            stripped = line.strip()

            if stripped == "Health:":
                section = "health"
                continue
            if stripped == "Potions:":
                section = "potions"
                continue
            if not stripped:
                continue

            if section == "health" and stripped.startswith("You:"):
                health = int(stripped.split(":", 1)[1].strip())
                section = None
                continue

            if section == "potions" and stripped.startswith("You:"):
                potions = int(stripped.split(":", 1)[1].strip())
                section = None

        if health is None or potions is None:
            raise ValueError(
                "FixedDamagePolicyBot could not parse player health/potions from rendered prompt"
            )

        return {"health": health, "potions": potions}

    def get_summary(self) -> Dict[str, Any]:
        summary = super().get_summary()
        summary["type"] = self.__class__.__name__
        return summary


class AttackBot(FixedDamagePolicyBot):
    """Always attacks."""

    def choose_action(self, view_state: Dict[str, int]) -> str:
        return "ATTACK"


class PotionAt80Bot(FixedDamagePolicyBot):
    """Heals whenever current HP is 80 or lower and a potion remains."""

    def __init__(self, name: str, *, threshold: int = 80, **kwargs):
        super().__init__(name=name, **kwargs)
        self.threshold = threshold

    def choose_action(self, view_state: Dict[str, int]) -> str:
        if view_state["potions"] > 0 and view_state["health"] <= self.threshold:
            return "POTION"
        return "ATTACK"

    def get_summary(self) -> Dict[str, Any]:
        summary = super().get_summary()
        summary["threshold"] = self.threshold
        return summary
