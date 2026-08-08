"""Deterministic offline certification participants."""

from __future__ import annotations

from typing import List

from agentdeck import MockPlayer


def create_players() -> List[MockPlayer]:
    return [
        MockPlayer(name="Alpha", actions=["GAIN"]),
        MockPlayer(name="Beta", actions=["HOLD"]),
    ]
