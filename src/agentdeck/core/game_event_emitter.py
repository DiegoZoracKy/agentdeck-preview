"""Helper for emitting game-defined events with automatic context injection."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .event_bus import EventBus


class GameEventEmitter:
    """Injects structural context before forwarding custom events to the EventBus."""

    def __init__(self, event_bus: EventBus, match_id: Optional[str]) -> None:
        self._event_bus = event_bus
        self._match_id = match_id
        self._phase_index: Optional[int] = None

    def set_phase_index(self, phase_index: int) -> None:
        """Record the current zero-based phase index."""
        self._phase_index = phase_index

    def clear_phase_index(self) -> None:
        """Clear the currently tracked phase index."""
        self._phase_index = None

    def emit(self, event_type: str, **payload: Any) -> None:
        """Emit a domain event with automatically injected context."""
        data: Dict[str, Any] = dict(payload)

        if self._match_id is not None:
            data.setdefault("match_id", self._match_id)

        if self._phase_index is not None:
            data.setdefault("phase_index", self._phase_index)
            data.setdefault("turn_index", self._phase_index)  # Legacy alias for compatibility

        self._event_bus.emit(event_type, **data)
