"""Deterministic offline certification participants."""

from agentdeck import MockPlayer


def create_players():
    return [
        MockPlayer(name="Alpha", actions=["GAIN"]),
        MockPlayer(name="Beta", actions=["HOLD"]),
    ]
