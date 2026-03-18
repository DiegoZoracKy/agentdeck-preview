"""FixedDamageGame - Example turn-based combat game."""

from .bots import AttackBot, FixedDamagePolicyBot, PotionAt80Bot
from .game import FixedDamageGame

__all__ = ["FixedDamageGame", "FixedDamagePolicyBot", "AttackBot", "PotionAt80Bot"]
