"""Utility helpers for spectator implementations."""

from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List


class CounterMap:
    """Two-level counter helper used for player/action tallies."""

    def __init__(self) -> None:
        self._data: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))

    def increment(self, owner: str, key: str, *, amount: int = 1) -> None:
        self._data[owner][key] += amount

    def total(self, owner: str) -> int:
        return sum(self._data[owner].values())

    def totals(self) -> Dict[str, int]:
        return {owner: self.total(owner) for owner in self._data}

    def as_dict(self) -> Dict[str, Dict[str, int]]:
        return {owner: dict(actions) for owner, actions in self._data.items()}

    def clear(self) -> None:
        self._data.clear()

    def owners(self) -> Iterable[str]:
        return self._data.keys()


class DurationTracker:
    """Helper for tracking durations per key."""

    def __init__(self) -> None:
        self._durations: DefaultDict[str, List[float]] = defaultdict(list)

    def record(self, key: str, duration: float) -> None:
        self._durations[key].append(duration)

    def average(self, key: str) -> float:
        samples = self._durations.get(key)
        if not samples:
            return 0.0
        return sum(samples) / len(samples)

    def values(self, key: str) -> List[float]:
        return list(self._durations.get(key, []))

    def clear(self) -> None:
        self._durations.clear()

    def as_dict(self) -> Dict[str, List[float]]:
        return {key: list(values) for key, values in self._durations.items()}
