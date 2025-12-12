"""Utility helpers for replay scheduling and mock reconstruction."""

from __future__ import annotations

from typing import List

from .types import Event, EventContext, SpectatorContext


class ReplayScheduler:
    """Flexible scheduler that translates recorded timestamps into delays."""

    def __init__(
        self, *, speed: float = 1.0, min_delay: float = 0.0, max_delay: float = 1.0
    ) -> None:
        self.speed = max(speed, 0.0)
        self.min_delay = max(min_delay, 0.0)
        self.max_delay = max(max_delay, 0.0)

    def compute_delay(self, previous: Event | None, current: Event) -> float:
        if previous is None or self.speed == 0:
            return 0.0
        delta = (current.timestamp - previous.timestamp) / self.speed
        if delta <= 0:
            return 0.0
        return min(self.max_delay, max(self.min_delay, delta))


def rehydrate_context(stored: dict | None) -> SpectatorContext:
    if stored is None:
        return SpectatorContext.from_event(None)
    context: EventContext = {
        "session_id": stored.get("session_id"),
        "batch_id": stored.get("batch_id"),
        "match_id": stored.get("match_id"),
        "phase_index": stored.get("phase_index"),
        "phase_index": stored.get("phase_index"),
        "turn_index": stored.get("turn_index"),
        "timestamp": stored.get("timestamp"),
        "monotonic_time": stored.get("monotonic_time"),
    }
    if context["phase_index"] is None and context["turn_index"] is not None:
        context["phase_index"] = context["turn_index"]
    return SpectatorContext.from_event(context)


def rehydrate_players(players: List[str]):
    return [type("Player", (), {"name": name})() for name in players]
