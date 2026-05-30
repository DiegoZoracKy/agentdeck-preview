"""Factories for producing structured game events."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, cast

from .types import ActionResult, Event, EventContext, TurnContext


class EventFactory:
    """Build canonical event payloads for recordings and spectators."""

    _INTERACTION_METADATA_KEYS = {
        "raw_prompt",
        "prompt_text",
        "prompt_blocks",
        "raw_response",
        "response_text",
        "usage_info",
        "renderer_output",
        "controller_format",
        "controller_metadata",
        "prompt_length",
        "template_id",
        "call_id",
        "duration",
        "turn_number",
        "turn_context",
    }

    def __init__(self, match_id: str):
        self.match_id = match_id

    @staticmethod
    def _public_state_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-copy game state while omitting engine-internal keys."""
        return {
            key: copy.deepcopy(value)
            for key, value in state.items()
            if not (isinstance(key, str) and key.startswith("_"))
        }

    def turn(
        self,
        *,
        player: str,
        action: ActionResult,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        turn_context: TurnContext,
        prompt_blocks: Optional[List[Any]] = None,
    ) -> Event:
        """Create the standardized turn event payload."""
        metadata = copy.deepcopy(action.metadata) if action.metadata else {}
        action_metadata = {
            key: copy.deepcopy(value)
            for key, value in metadata.items()
            if key not in self._INTERACTION_METADATA_KEYS
        }
        serialized_prompt_blocks: List[Any]
        if prompt_blocks is not None:
            serialized_prompt_blocks = copy.deepcopy(
                [block.to_dict() if hasattr(block, "to_dict") else block for block in prompt_blocks]
            )
        else:
            serialized_prompt_blocks = copy.deepcopy(metadata.get("prompt_blocks", []))
        interaction = {
            "prompt_text": metadata.get("prompt_text") or metadata.get("raw_prompt"),
            "prompt_blocks": serialized_prompt_blocks,
            "response_text": metadata.get("response_text")
            or metadata.get("raw_response")
            or action.raw_response,
            "usage_info": copy.deepcopy(metadata.get("usage_info")),
            "renderer_output": copy.deepcopy(metadata.get("renderer_output")),
            "controller_format": metadata.get("controller_format"),
            "controller_metadata": copy.deepcopy(metadata.get("controller_metadata")),
        }
        turn_payload = {
            "match_id": self.match_id,
            "mechanic": "turn_based",
            "phase_index": turn_context.phase_index,
            "player": player,
            "action": {
                "value": action.action,
                "reasoning": action.reasoning,
                "metadata": action_metadata,
            },
            "interaction": interaction,
            "state_before": self._public_state_snapshot(state_before),
            "state_after": self._public_state_snapshot(state_after),
            "turn_context": turn_context.to_dict(),
        }
        context: EventContext = cast(
            EventContext,
            {
                "match_id": self.match_id,
                "phase_index": turn_context.phase_index,
            },
        )
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
            context_dict["phase_index"] = turn_context.phase_index
        context = cast(EventContext, context_dict)
        return Event(type=event_type, data=data, context=context)
