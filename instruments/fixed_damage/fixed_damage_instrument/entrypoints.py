"""Package-local entry points backed by public AgentDeck components."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from agentdeck import FixedDamageGame
from agentdeck.games.examples.fixed_damage.behavioral import FixedDamageBehavioralScorer
from agentdeck.games.examples.fixed_damage.bots import AttackBot, PotionAt80Bot


def create_players():
    """Return deterministic offline calibration Players."""
    return [AttackBot("Alpha"), PotionAt80Bot("Beta")]


def visible_state(
    state: Mapping[str, Any], player: str, game_config: Mapping[str, Any]
) -> Dict[str, Any]:
    """Apply the exact configured Game visibility boundary."""
    game = FixedDamageGame(**dict(game_config))
    return game.get_view(dict(state), player)


__all__ = [
    "FixedDamageBehavioralScorer",
    "FixedDamageGame",
    "create_players",
    "visible_state",
]
