"""Utility helpers for replay scheduling and mock reconstruction."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Sequence

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
        "timestamp": stored.get("timestamp"),
        "monotonic_time": stored.get("monotonic_time"),
    }
    return SpectatorContext.from_event(context)


class _RehydratedPlayer:
    """Minimal recorded Player identity for spectator-compatible replay."""

    def __init__(self, summary: Mapping[str, Any]) -> None:
        self._summary: Dict[str, Any] = copy.deepcopy(dict(summary))
        self._summary.pop("total_cost", None)
        self.name = str(self._summary.get("name") or "UnknownPlayer")

    def get_summary(self) -> Dict[str, Any]:
        return copy.deepcopy(self._summary)


def rehydrate_players(players: Sequence[str | Mapping[str, Any]]) -> List[Any]:
    rehydrated: List[Any] = []
    for player in players:
        summary = player if isinstance(player, Mapping) else {"name": str(player)}
        rehydrated.append(_RehydratedPlayer(summary))
    return rehydrated
