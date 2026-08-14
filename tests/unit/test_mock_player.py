from agentdeck.players.mock import MockPlayer


def test_mock_player_handshake_returns_ok() -> None:
    player = MockPlayer(name="Tester")
    player._active_phase = "handshake"

    response = player.get_response("Respond with OK.")

    assert response == "OK"


def test_mock_player_cycles_through_actions() -> None:
    player = MockPlayer(name="Tester", actions=["ATTACK", "POTION"])

    first = player.get_response("Turn 1 prompt")
    second = player.get_response("Turn 2 prompt")
    third = player.get_response("Turn 3 prompt")

    assert [first, second, third] == [
        "ACTION: ATTACK",
        "ACTION: POTION",
        "ACTION: ATTACK",
    ]


def test_mock_player_default_model_is_honest() -> None:
    player = MockPlayer(name="Tester")

    assert player.get_summary()["model"] == "mock"


def test_mock_player_summary_retains_model_provenance() -> None:
    player = MockPlayer(name="Tester", model="deterministic-smoke")

    assert player.get_summary()["model"] == "deterministic-smoke"
