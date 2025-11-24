from __future__ import annotations

"""Generic text renderer for AgentDeck games.

This renderer provides minimal, game-agnostic text formatting for any turn-based
game that follows the AgentDeck spec contracts. It makes no assumptions about
specific game mechanics and renders state dicts based purely on structure.
"""

from typing import Any, Dict, List

from ..core.base.renderer import Renderer
from ..core.types import RenderResult, TurnContext


class TextRenderer(Renderer):
    """
    Generic text renderer for turn-based games.

    Renders game state in a minimal, deterministic format without making
    game-specific assumptions. Works by walking the view dict and pretty-printing
    common data structures.

    Features:
    - Deterministic key ordering for consistent output
    - Conditional rendering (only shows keys present in view)
    - Configurable empty value handling
    - Handles arbitrary state keys gracefully

    Design Philosophy:
    - Minimal: Only renders what's in the view dict
    - Generic: No game-specific logic or assumptions
    - Robust: Handles unknown keys without breaking

    Games requiring richer domain-specific output (e.g., ASCII board diagrams,
    detailed combat logs) can provide their own custom renderer by subclassing
    Renderer or creating a game-specific renderer class.
    """

    def __init__(self, show_empty: bool = False):
        """
        Initialize the text renderer.

        Args:
            show_empty: If True, render keys with None/empty values.
                       If False, skip empty values (default).
        """
        self.show_empty = show_empty

    def render(
        self,
        state: Dict[str, Any],
        player: str,
        *,
        turn_context: TurnContext | None = None,
    ) -> RenderResult:
        """
        Render game state as human-readable text.

        Walks the state dict and renders all keys generically based on structure,
        without making game-specific assumptions.

        Args:
            state: Player-specific view of game state (from game.get_view())
            player: Name of the player viewing this state
            turn_context: Optional turn context for metadata

        Returns:
            RenderResult with formatted text and lightweight metadata
        """
        sections: List[str] = []
        lines = ["=== Current Game State ==="]
        lines.append(f"You are: {player}")

        # Use turn_context if available, fallback to state["turn"]
        turn_number = None
        if turn_context:
            turn_number = turn_context.turn_number
        elif "turn" in state:
            turn_number = state["turn"]

        if turn_number is not None:
            lines.append(f"Turn: {turn_number}")
            sections.append("turn")

        lines.append("")  # Blank line after header

        # MB1: Preserve insertion order from Game.get_view() without filtering
        # Per SPEC-RENDERER §3: "preserve narrative/tutorial fields from Game
        # without re-ordering or filtering semantics"
        for key, value in state.items():
            # Skip turn if already rendered in header
            if key == "turn" and turn_number is not None:
                continue

            # MB1: Must NOT filter keys (no underscore filtering, no empty filtering)
            # Games deliberately use all keys (_tutorial, empty structures) to signal state
            sections.append(key)

            # Render based on value type
            if isinstance(value, dict):
                lines.append(f"{key.replace('_', ' ').title()}:")
                lines.extend(self._render_dict(value, player, indent="  "))
            elif isinstance(value, list):
                lines.append(f"{key.replace('_', ' ').title()}:")
                lines.extend(self._render_list(value, indent="  "))
            else:
                # Scalar value
                lines.append(f"{key.replace('_', ' ').title()}: {value}")

            lines.append("")  # Blank line between sections

        lines.append("=" * 25)

        metadata = {
            "player": player,
            "sections": sections,
        }
        if turn_context:
            metadata["turn_number"] = turn_context.turn_number

        return RenderResult(text="\n".join(lines), metadata=metadata)

    def _is_empty(self, value: Any) -> bool:
        """Check if a value should be considered empty."""
        if value is None:
            return True
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            return True
        return False

    def _render_dict(self, d: Dict[str, Any], player: str, indent: str = "") -> List[str]:
        """
        Render a dictionary preserving insertion order (MB1).

        Per SPEC-RENDERER §3 MB1: Must not filter or remove data supplied by game.
        """
        lines: List[str] = []

        # MB1: Preserve insertion order from game - no sorting, no filtering
        for key, value in d.items():
            # Show "You:" label for player's own key (UX improvement)
            label = "You" if key == player else key

            # Format entry
            if isinstance(value, (dict, list)):
                lines.append(f"{indent}{label}:")
                if isinstance(value, dict):
                    lines.extend(self._render_dict(value, player, indent=indent + "  "))
                else:
                    lines.extend(self._render_list(value, indent=indent + "  "))
            else:
                lines.append(f"{indent}{label}: {value}")

        return lines

    def _render_list(self, lst: List[Any], indent: str = "") -> List[str]:
        """Render a list, with special handling for 2D grids."""
        lines: List[str] = []

        # Check if this is a 2D grid (list of lists)
        if lst and isinstance(lst[0], list):
            # 2D grid: render as rows
            for row in lst:
                lines.append(f"{indent}" + " ".join(str(cell) for cell in row))
        else:
            # 1D list: render as bullet points
            for item in lst:
                lines.append(f"{indent}- {item}")

        return lines

    def describe(self) -> Dict[str, Any]:
        """
        Return renderer identity and configuration (per SPEC-RENDERER v0.3.0 MO2).

        Returns:
            Dict with name, version, and metadata keys for recorder consumption
        """
        return {
            "name": "TextRenderer",
            "version": "1.0.0",
            "metadata": {"show_empty": self.show_empty, "style": "generic"},
        }
