"""
Renderer base class for AgentDeck v1.0.0 framework.

Implements rendering contract per:
- SPEC-RENDERER v0.3.0 §4 (Public API)
- SPEC-RENDERER v0.3.0 §5 (Invariants & Guarantees)
- SPEC.md §5.7

Key responsibilities:
- Format per-player game views into text for prompt composition
- Preserve narrative/tutorial fields from Game without filtering
- Capture deterministic metadata for recorder/spectators
- Provide describe() for renderer configuration tracking

Critical invariants:
- DF1-DF2: Deterministic formatting (identical inputs → identical outputs, read-only)
- MB1-MB2: Mechanics-agnostic boundaries (no hidden info injection, no global state)
- MO1-MO3: Metadata & observability (JSON-serializable, describe() contract)
- EH1-EH2: Error handling (descriptive errors, tolerate missing turn_context)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..types import RenderResult, TurnContext


class Renderer(ABC):
    """
    Abstract base for game view renderers (per SPEC-RENDERER v0.3.0 §4).

    Renderers transform per-player game views (returned by Game.get_view()) into
    text or structured outputs for PromptBuilder, spectators, or UIs.

    Lifecycle:
        1. Console calls Game.get_view(game_state, player) → filtered game_view
        2. Console calls renderer.render(game_view, player, turn_context) → RenderResult
        3. PromptBuilder uses RenderResult.text for {game_view} placeholder
        4. Recorder captures RenderResult.metadata for observability

    Example minimal renderer:
        >>> class SimpleRenderer(Renderer):
        ...     def render(self, game_view, player, *, turn_context=None):
        ...         lines = [f"Player: {player}"]
        ...         for key, value in sorted(game_view.items()):
        ...             lines.append(f"{key}: {value}")
        ...         text = "\\n".join(lines)
        ...         return RenderResult(text=text, metadata={"format": "simple"})
        ...
        ...     def describe(self):
        ...         return {"name": "SimpleRenderer", "version": "1.0.0", "metadata": {}}

    See also:
        - TextRenderer: Generic implementation for any game
        - SPEC-RENDERER.md §8: Additional examples (PokerTextRenderer)
    """

    @abstractmethod
    def render(
        self,
        game_view: Dict[str, Any],
        player: str,
        *,
        turn_context: Optional[TurnContext] = None,
    ) -> RenderResult:
        """
        Format game view into text for prompt composition (per DF1-DF2, MB1-MB2).

        Args:
            game_view: Per-player view from Game.get_view() (already filtered)
            player: Acting player name (for labeling in output)
            turn_context: Optional turn metadata (turn_number, phase_index, etc.)

        Returns:
            RenderResult with .text (for prompts) and .metadata (for recorder)

        Requirements (DF1-DF2):
            - DF1: MUST return identical output for identical inputs (deterministic)
            - DF2: MUST treat game_view and turn_context as read-only (no mutations)

        Requirements (MB1-MB2):
            - MB1: MUST NOT introduce hidden information absent from game_view
            - MB2: MUST NOT rely on global state (all behavior from inputs/config)

        Requirements (MO1-MO3, EH1-EH2):
            - MO1: RenderResult.metadata MUST be JSON-serializable
            - MO3: SHOULD expose turn_context fields in metadata when provided
            - EH1: MUST raise ValueError for missing required fields in game_view
            - EH2: MUST tolerate absent turn_context (use defaults)

        Example:
            >>> result = renderer.render(game_view, "Alice", turn_context=turn_ctx)
            >>> result.text
            '=== Current Game State ===\\nYou are: Alice\\nTurn: 5\\n...'
            >>> result.metadata
            {'format': 'text', 'turn_number': 5, 'sections': ['header', 'health', 'actions']}

        Note: This method is called by Console during turn phase. Player receives
              RenderResult.text via PromptBuilder template substitution.
        """

    def describe(self) -> Dict[str, Any]:
        """
        Return renderer identity and configuration for observability (per MO2).

        Returns:
            Dict with name, version, and metadata keys (JSON-serializable)

        Requirements (MO2):
            - MUST include keys: name, version, metadata
            - name: Human-friendly renderer name (defaults to class name)
            - version: Renderer revision (defaults to "1.0.0" or package version)
            - metadata: Renderer-specific settings (JSON-serializable dict)

        Default implementation: Returns class name, version "1.0.0", empty metadata.
        Subclasses SHOULD override to expose configuration parameters.

        Example:
            >>> def describe(self):
            ...     return {
            ...         "name": "TextRenderer",
            ...         "version": "1.0.0",
            ...         "metadata": {"show_empty": self.show_empty, "style": "compact"}
            ...     }

        Note: Recorder stores this output in match metadata for reproducibility.
        """
        return {"name": self.__class__.__name__, "version": "1.0.0", "metadata": {}}
