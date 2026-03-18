"""Unit tests for FixedDamage calibration bots."""

import pytest

from agentdeck.games.examples.fixed_damage import AttackBot, PotionAt80Bot


TURN_PROMPT = """=== Current Game State ===
You are: Alice
Turn: 3

Health:
  You: {health}

Potions:
  You: {potions}

Last Action:
  You: ATTACK
  Bob: ATTACK

========================="""


def test_attack_bot_always_attacks():
    bot = AttackBot("Alice")

    response = bot.get_response(TURN_PROMPT.format(health=100, potions=3))

    assert response == "ACTION: ATTACK"


def test_potion_at_80_bot_uses_potion_at_threshold():
    bot = PotionAt80Bot("Alice")

    response = bot.get_response(TURN_PROMPT.format(health=80, potions=2))

    assert response == "ACTION: POTION"


def test_potion_at_80_bot_attacks_above_threshold():
    bot = PotionAt80Bot("Alice")

    response = bot.get_response(TURN_PROMPT.format(health=100, potions=2))

    assert response == "ACTION: ATTACK"


def test_potion_at_80_bot_attacks_when_out_of_potions():
    bot = PotionAt80Bot("Alice")

    response = bot.get_response(TURN_PROMPT.format(health=60, potions=0))

    assert response == "ACTION: ATTACK"


def test_fixed_damage_policy_bot_fails_loudly_on_unparseable_prompt():
    bot = AttackBot("Alice")

    with pytest.raises(ValueError, match="could not parse player health/potions"):
        bot.get_response("not a FixedDamage view")
