"""Helpers for managing turn state snapshots."""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional


class StateAdapter:
    """Utility to provide immutability-friendly state snapshots per turn."""

    def __init__(self, state: Dict[str, Any]):
        # Keep independent copies so games cannot mutate shared references.
        self._before = copy.deepcopy(state)
        self._working = copy.deepcopy(state)
        self._after: Optional[Dict[str, Any]] = None

    @property
    def before(self) -> Dict[str, Any]:
        """Return the turn's starting state snapshot."""
        return self._before

    @property
    def working(self) -> Dict[str, Any]:
        """Provide a mutable copy for game logic to update."""
        return self._working

    def commit(self, new_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Record the resulting state after a turn finishes."""
        if new_state is None:
            new_state = self._working
        self._after = copy.deepcopy(new_state)
        return self._after

    @property
    def after(self) -> Dict[str, Any]:
        """Access the finalized post-turn state."""
        if self._after is None:
            raise RuntimeError("StateAdapter.after accessed before commit().")
        return self._after
