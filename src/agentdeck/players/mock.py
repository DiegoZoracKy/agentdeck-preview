"""Mock player for testing."""

from typing import List, Optional

from ..core.base.player import Player


class MockPlayer(Player):
    """Deterministic player for testing."""

    def __init__(self, name: str, actions: Optional[List[str]] = None, controller=None, **kwargs):
        """
        Initialize mock player.

        Args:
            name: Player name
            actions: List of actions to cycle through
            controller: Unified controller (required by Player v1.0.0)
            **kwargs: Additional player configuration
        """
        # Default to ActionOnlyController if not provided
        if controller is None:
            from ..controllers.action_only import ActionOnlyController

            controller = ActionOnlyController()

        super().__init__(name, controller=controller, **kwargs)
        self.actions = actions or ["ATTACK"]
        self.action_index = 0

    def get_response(self, prompt: str) -> str:
        """Return predetermined response."""
        # Handshake phase: detect by checking if prompt mentions game instructions
        # (handshake template includes game_name and game_instructions)
        if "You are playing" in prompt or "game_name" in prompt.lower():
            return "OK"  # Valid handshake response

        # Turn phase: return cycled action
        action = self.actions[self.action_index % len(self.actions)]
        self.action_index += 1

        # Check controller type for appropriate response format
        controller_name = self.controller.__class__.__name__

        if "Reasoning" in controller_name:
            return f"REASONING: Test reasoning for action {action}\nACTION: {action}"
        elif "JSON" in controller_name or "Json" in controller_name:
            import json

            return json.dumps({"action": action, "reasoning": "Test reasoning"})

        # Default: just return the action
        return action

    def conclude(self, result, *, match_context):
        """
        Execute conclusion phase - provide mock reflection.

        This method records an empty conclusion dialogue entry to mirror
        real-world behavior where players are prompted for reflections
        even if they return None or empty responses.

        Args:
            result: Match outcome (winner, final_state, etc.)
            match_context: Match execution metadata

        Returns:
            None (mock players don't provide reflections)
        """
        # Record empty dialogue for replay parity
        # This ensures PLAYER_CONCLUSION events are emitted during replay
        self._record_exchange(
            prompt="Match concluded.",  # Minimal prompt
            response="",  # Empty response
            phase="conclusion",
            turn_context=None,
            prompt_blocks=[
                {
                    "key": "outcome",
                    "content": self._format_outcome(result),
                    "metadata": {},
                }
            ],
            controller_format="",  # No controller format for conclusions
            renderer_output={},
            usage_info=None,  # Mock players have no usage info
        )

        return None  # Mock players don't provide reflections

    def _format_outcome(self, result) -> str:
        """Helper to generate human-readable outcome string."""
        if result.winner is None:
            return "Draw"
        if result.winner == self.name:
            return f"You ({self.name}) won the match."
        return f"{result.winner} won the match."

    def get_summary(self):
        """Return configuration summary for logging."""
        return {
            "name": self.name,
            "type": "MockPlayer",
            "actions": self.actions,
            "controller": self.controller.__class__.__name__,
            "renderer": self.renderer.__class__.__name__,
        }
