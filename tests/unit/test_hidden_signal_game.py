"""Contract tests for SPEC-GAME-HIDDEN-SIGNAL."""

from __future__ import annotations

import copy
import json

import pytest

from agentdeck.core.types import ActionResult
from agentdeck.games.examples.hidden_signal import HiddenSignalGame


class _UnusedRng:
    """The Game accepts the runtime RNG but has no update-time randomness."""


def _action(value: str) -> ActionResult:
    return ActionResult(action=value, raw_response=f"ACTION: {value}")


def test_hs1_setup_requires_exactly_one_player() -> None:
    game = HiddenSignalGame()

    with pytest.raises(ValueError, match="exactly 1 player"):
        game.setup([], seed=1)
    with pytest.raises(ValueError, match="exactly 1 player"):
        game.setup(["A", "B"], seed=1)


def test_hs2_setup_is_seeded_and_deterministic() -> None:
    game = HiddenSignalGame()

    assert game.setup(["Observer"], seed=42) == game.setup(["Observer"], seed=42)
    assert {game.setup(["Observer"], seed=seed)["signal"] for seed in range(20)} == {"RED", "BLUE"}


def test_hs3_state_and_views_are_portable() -> None:
    game = HiddenSignalGame()
    state = game.setup(["Observer"], seed=42)
    view = game.get_view(state, "Observer")

    assert json.loads(json.dumps(state)) == state
    assert json.loads(json.dumps(view)) == view
    assert copy.deepcopy(state) == state


def test_hs4_hidden_signal_is_revealed_only_after_inspection() -> None:
    game = HiddenSignalGame(signal_visibility="hidden")
    state = game.setup(["Observer"], seed=42)

    assert state["signal"] in {"RED", "BLUE"}
    assert game.get_view(state, "Observer")["signal"] == "HIDDEN"

    inspected = game.update(state, "Observer", _action("INSPECT"), rng=_UnusedRng())
    assert game.get_view(inspected, "Observer")["signal"] == state["signal"]
    assert state["revealed_signal"] is None


def test_visible_mode_exposes_signal_without_inspection() -> None:
    game = HiddenSignalGame(signal_visibility="visible")
    state = game.setup(["Observer"], seed=7)

    assert state["revealed_signal"] == state["signal"]
    assert game.get_view(state, "Observer")["signal"] == state["signal"]
    assert game.get_view(state, "Observer")["inspection_available"] is True


def test_hs5_inspection_is_single_use_and_failed_action_is_immutable() -> None:
    game = HiddenSignalGame()
    state = game.setup(["Observer"], seed=3)
    inspected = game.update(state, "Observer", _action("inspect"), rng=_UnusedRng())
    snapshot = copy.deepcopy(inspected)

    with pytest.raises(ValueError, match="at most one inspection"):
        game.update(inspected, "Observer", _action("INSPECT"), rng=_UnusedRng())

    assert inspected == snapshot


def test_hs6_updates_increment_turn_and_apply_cost_once() -> None:
    game = HiddenSignalGame(inspection_cost=3)
    state = game.setup(["Observer"], seed=3)
    inspected = game.update(state, "Observer", _action("INSPECT"), rng=_UnusedRng())
    committed = game.update(
        inspected,
        "Observer",
        _action(f"CHOOSE_{inspected['signal']}"),
        rng=_UnusedRng(),
    )

    assert state["turn"] == 1
    assert inspected["turn"] == 2
    assert inspected["inspection_cost_total"] == 3
    assert inspected["score"] == -3
    assert committed["turn"] == 3
    assert committed["score"] == -1


@pytest.mark.parametrize("correct", [True, False])
def test_hs7_commitment_terminates_without_winner(correct: bool) -> None:
    game = HiddenSignalGame(correct_reward=4)
    state = game.setup(["Observer"], seed=11)
    choice = state["signal"] if correct else ({"RED", "BLUE"} - {state["signal"]}).pop()

    committed = game.update(state, "Observer", _action(f"CHOOSE_{choice}"), rng=_UnusedRng())
    status = game.status(committed)

    assert committed["correct"] is correct
    assert committed["score"] == (4 if correct else 0)
    assert status.is_over is True
    assert status.winner is None


def test_hs8_invalid_and_post_terminal_updates_are_immutable() -> None:
    game = HiddenSignalGame()
    state = game.setup(["Observer"], seed=5)

    for player, action, message in (
        ("Other", "INSPECT", "Unknown Player"),
        ("Observer", "WAIT", "Invalid action"),
    ):
        snapshot = copy.deepcopy(state)
        with pytest.raises(ValueError, match=message):
            game.update(state, player, _action(action), rng=_UnusedRng())
        assert state == snapshot

    committed = game.update(
        state, "Observer", _action(f"CHOOSE_{state['signal']}"), rng=_UnusedRng()
    )
    snapshot = copy.deepcopy(committed)
    with pytest.raises(ValueError, match="already complete"):
        game.update(committed, "Observer", _action("INSPECT"), rng=_UnusedRng())
    assert committed == snapshot


def test_hs9_view_is_pure_and_rejects_unknown_player() -> None:
    game = HiddenSignalGame()
    state = game.setup(["Observer"], seed=13)
    snapshot = copy.deepcopy(state)

    assert game.get_view(state, "Observer") == game.get_view(state, "Observer")
    assert state == snapshot
    with pytest.raises(ValueError, match="Unknown Player"):
        game.get_view(state, "Other")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"signal_visibility": "partial"}, "signal_visibility"),
        ({"inspection_cost": -1}, "non-negative"),
        ({"correct_reward": 0}, "positive"),
    ],
)
def test_invalid_configuration_fails_fast(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        HiddenSignalGame(**kwargs)  # type: ignore[arg-type]


def test_state_validation_rejects_cross_field_drift() -> None:
    game = HiddenSignalGame()
    state = game.setup(["Observer"], seed=17)

    broken = copy.deepcopy(state)
    broken["revealed_signal"] = broken["signal"]
    with pytest.raises(ValueError, match="revealed signal"):
        game.validate_state(broken)

    broken = copy.deepcopy(state)
    broken["score"] = 99
    with pytest.raises(ValueError, match="score"):
        game.validate_state(broken)


def test_contract_surface_and_handshake_are_explicit() -> None:
    game = HiddenSignalGame()

    assert game.allowed_actions == ["INSPECT", "CHOOSE_RED", "CHOOSE_BLUE"]
    assert "no opponent" in game.instructions
    for placeholder in (
        "{game_instructions}",
        "{controller_format}",
        "{handshake_controller_format}",
    ):
        assert placeholder in game.default_handshake_template
