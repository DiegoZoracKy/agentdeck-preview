import copy
import json

import pytest

from agentdeck.core.types import ActionResult, RandomGenerator
from agentdeck.games.examples.variable_damage import VariableDamageGame


class CountingRNG:
    def __init__(self, value: int):
        self.value = value
        self.randint_calls = []

    def randint(self, a: int, b: int) -> int:
        self.randint_calls.append((a, b))
        return self.value


def test_variable_damage_setup_returns_json_serializable_state():
    game = VariableDamageGame()
    state = game.setup(["Alice", "Bob"], seed=42)

    payload = json.loads(json.dumps(state))
    assert payload["health"] == {"Alice": 100, "Bob": 100}
    assert payload["potions"] == {"Alice": 3, "Bob": 3}
    assert payload["last_action"] == {"Alice": None, "Bob": None}
    assert payload["turn"] == 1


def test_variable_damage_rejects_invalid_information_level():
    with pytest.raises(ValueError, match="information_level must be 'full' or 'partial'"):
        VariableDamageGame(information_level="parital")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"min_attack_damage": 0, "max_attack_damage": 25}, "positive integers"),
        ({"min_attack_damage": 15, "max_attack_damage": 0}, "positive integers"),
        ({"min_attack_damage": 30, "max_attack_damage": 25}, "min_attack_damage must be <= max_attack_damage"),
    ],
)
def test_variable_damage_rejects_invalid_damage_ranges(kwargs, message):
    with pytest.raises(ValueError, match=message):
        VariableDamageGame(**kwargs)


def test_variable_damage_attack_consumes_rng_exactly_once():
    game = VariableDamageGame(min_attack_damage=15, max_attack_damage=25)
    state = game.setup(["Alice", "Bob"], seed=42)
    rng = CountingRNG(value=19)

    updated = game.update(
        state,
        "Alice",
        ActionResult(action="ATTACK", raw_response="ACTION: ATTACK"),
        rng=rng,
    )

    assert rng.randint_calls == [(15, 25)]
    assert updated["health"]["Bob"] == 81
    assert updated["last_action"]["Alice"] == "ATTACK"
    assert updated["turn"] == 2


def test_variable_damage_potion_does_not_consume_rng():
    game = VariableDamageGame()
    state = game.setup(["Alice", "Bob"], seed=42)
    state["health"]["Alice"] = 40
    rng = CountingRNG(value=17)

    updated = game.update(
        state,
        "Alice",
        ActionResult(action="POTION", raw_response="ACTION: POTION"),
        rng=rng,
    )

    assert rng.randint_calls == []
    assert updated["health"]["Alice"] == 70
    assert updated["potions"]["Alice"] == 2
    assert updated["turn"] == 2


def test_variable_damage_identical_rng_inputs_produce_identical_states():
    game1 = VariableDamageGame()
    game2 = VariableDamageGame()
    state1 = game1.setup(["Alice", "Bob"], seed=42)
    state2 = game2.setup(["Alice", "Bob"], seed=42)

    rng1 = RandomGenerator(seed=123)
    rng2 = RandomGenerator(seed=123)
    sequence = [
        ("Alice", "ATTACK"),
        ("Bob", "ATTACK"),
        ("Alice", "POTION"),
        ("Bob", "ATTACK"),
        ("Alice", "ATTACK"),
    ]

    for player, action in sequence:
        action_result = ActionResult(action=action, raw_response=f"ACTION: {action}")
        state1 = game1.update(state1, player, action_result, rng=rng1)
        state2 = game2.update(state2, player, action_result, rng=rng2)

    assert state1 == state2


def test_variable_damage_partial_view_hides_opponent_and_last_damage():
    game = VariableDamageGame(information_level="partial")
    state = game.setup(["Alice", "Bob"], seed=42)
    state["last_action"]["Bob"] = "ATTACK"

    view = game.get_view(state, "Alice")

    assert view["health"] == {"Alice": 100}
    assert view["potions"] == {"Alice": 3}
    assert view["last_action"]["Bob"] == "ATTACK"
    assert "last_damage" not in view


def test_variable_damage_full_view_shows_all_players_but_not_last_damage():
    game = VariableDamageGame(information_level="full")
    state = game.setup(["Alice", "Bob"], seed=42)

    view = game.get_view(state, "Alice")

    assert view["health"] == {"Alice": 100, "Bob": 100}
    assert view["potions"] == {"Alice": 3, "Bob": 3}
    assert "last_damage" not in view


def test_variable_damage_attack_clamps_health_to_zero():
    game = VariableDamageGame(min_attack_damage=40, max_attack_damage=40, max_health=30)
    state = game.setup(["Alice", "Bob"], seed=42)

    updated = game.update(
        state,
        "Alice",
        ActionResult(action="ATTACK", raw_response="ACTION: ATTACK"),
        rng=RandomGenerator(seed=42),
    )

    assert updated["health"]["Bob"] == 0


def test_variable_damage_status_terminal_cases():
    game = VariableDamageGame()
    state = game.setup(["Alice", "Bob"], seed=42)

    assert game.status(state).is_over is False

    alice_wins = copy.deepcopy(state)
    alice_wins["health"]["Bob"] = 0
    assert game.status(alice_wins).winner == "Alice"

    draw = copy.deepcopy(state)
    draw["health"]["Alice"] = 0
    draw["health"]["Bob"] = 0
    assert game.status(draw).is_over is True
    assert game.status(draw).winner is None
