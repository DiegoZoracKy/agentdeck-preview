"""Conversation management utilities for players."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .types import TurnContext


@dataclass
class DialogueTurn:
    """Snapshot of a single dialogue exchange."""

    user: str
    assistant: str
    turn_context: Optional[TurnContext] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_event_payload(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "prompt": self.user,
            "response": self.assistant,
        }
        if self.turn_context is not None:
            payload["turn_context"] = self.turn_context.to_dict()
            payload["turn_index"] = self.turn_context.turn_index
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


class ConversationManager:
    """Maintain dialogue history and publish optional events."""

    def __init__(
        self,
        *,
        player_name: str,
        event_bus=None,
    ) -> None:
        self.player_name = player_name
        self._event_bus = event_bus
        self._history: List[Dict[str, str]] = []

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._history.clear()

    def history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def append(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})

    def record_turn(
        self,
        *,
        user_message: str,
        assistant_message: str,
        turn_context: Optional[TurnContext],
        prompt_metadata: List[dict],
        response_metadata: Dict[str, object],
        phase: str = "turn",
        prompt_blocks: Optional[List[Dict]] = None,
        controller_format: Optional[str] = None,
        renderer_output: Optional[Dict] = None,
    ) -> None:
        """
        Store the exchange and optionally notify spectators with PM1-PM6 metadata.

        Args:
            user_message: Prompt sent to LLM (PM1: prompt_text)
            assistant_message: Response from LLM (PM3: response_text)
            turn_context: Turn timing/sequencing metadata
            prompt_metadata: Legacy parameter for prompt blocks
            response_metadata: Metadata from LLM response (PM4: usage_info)
            phase: Lifecycle phase (handshake, turn, conclusion)
            prompt_blocks: Structured prompt components from PromptBuilder (PM2)
            controller_format: Controller type used (PM5)
            renderer_output: Rendered view metadata (PM6)
        """
        self.append("user", user_message)
        self.append("assistant", assistant_message)

        # Note: DIALOGUE_TURN events removed in schema v1.3
        # Prompt metadata is now embedded directly in lifecycle events
        # (PLAYER_HANDSHAKE_COMPLETE, GAMEPLAY, PLAYER_CONCLUSION, etc.)
        # via Recorder._extract_prompt_payload()
