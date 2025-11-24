"""Factories for producing structured game events."""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional, cast

from .types import ActionResult, Event, EventContext, TurnContext


class EventFactory:
    """Build canonical event payloads for recordings and spectators."""

    def __init__(self, match_id: str):
        self.match_id = match_id

    def turn(
        self,
        *,
        player: str,
        action: ActionResult,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        turn_context: TurnContext,
    ) -> Event:
        """Create the standardized turn event payload."""
        turn_payload = {
            "match_id": self.match_id,
            "player": player,
            "action": action.action,
            "reasoning": action.reasoning,
            "metadata": copy.deepcopy(action.metadata) if action.metadata else None,
            "state_before": copy.deepcopy(state_before),
            "state_after": copy.deepcopy(state_after),
            "turn_context": turn_context.to_dict(),
        }
        context: EventContext = cast(
            EventContext,
            {
                "match_id": self.match_id,
                "phase_index": turn_context.turn_index,
                "turn_index": turn_context.turn_index,
            },
        )
        turn_payload["mechanic"] = "turn_based"
        turn_payload["phase_index"] = turn_context.turn_index
        return Event(type="gameplay", data=turn_payload, context=context)

    def custom(
        self,
        event_type: str,
        payload: Dict[str, Any],
        *,
        turn_context: Optional[TurnContext] = None,
    ) -> Event:
        """Attach shared metadata to arbitrary game events."""
        data = copy.deepcopy(payload)
        data.setdefault("match_id", self.match_id)
        if turn_context is not None:
            data.setdefault("turn_context", turn_context.to_dict())
        context_dict: Dict[str, Any] = {"match_id": self.match_id}
        if turn_context is not None:
            context_dict["phase_index"] = turn_context.turn_index
            context_dict["turn_index"] = turn_context.turn_index
        context = cast(EventContext, context_dict)
        return Event(type=event_type, data=data, context=context)
