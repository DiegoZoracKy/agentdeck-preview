# SPEC-RENDERER: Game View Formatting Contract

> Status: Final
> Version: 0.3.1
> Last Updated: 2026-03-17
> Implementation: ✅ Complete (Phase 6-8 compliance verified)
> Authors: Codex, Diego Zoracky
> Audience: Renderer implementers, player authors, observability contributors

## 1. Purpose
- Define the contract renderers must follow when transforming per-player game views into model-ready text (or structured) outputs.
- Preserve mechanics-agnostic architecture by keeping renderers focused on presentation while games own information access.
- Enable reproducible research by standardising renderer metadata capture for recorder and spectator tooling.

## 2. Scope & Philosophy Alignment
- Follows `SPEC.md` §3.1 separation: Game decides what each player can see; Renderer formats that view without injecting logic.
- Reinforces `SPEC.md` §2.4 reproducibility: deterministic rendering given identical inputs; renderer configuration captured for every turn.
- Applies lean-spec guidance (`GUIDELINES.md` §2c): concise contracts, arrow-style data flows, numbered invariants.
- Non-goals: Prompt assembly (SPEC-PLAYER), action parsing (SPEC-CONTROLLER), or state mutation (SPEC-GAME).

## 3. Responsibilities
- Format the per-player view returned by `Game.get_view()` into text or structured payloads consumed by PromptBuilder, spectators, or UIs.
- Preserve narrative/tutorial fields supplied by the Game without re-ordering or filtering semantics.
- Attach deterministic metadata via `RenderResult` so recorder/spectators can reason about rendered sections.
- Surface renderer configuration through `describe()` so experiments can be reproduced and audited.
- Provide a **generic `TextRenderer`** implementation that works with any game following spec contracts; games MAY ship custom renderers for richer domain-specific output.

## 4. Public API

### RenderResult Dataclass
```python
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass(frozen=True)
class RenderResult:
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
```
- `text`: Primary rendered output passed to PromptBuilder.
- `metadata`: JSON-serialisable dict describing sections, formatting hints, token estimates, etc.
- MUST: Remain immutable once instantiated so recorder hashes remain stable.

### render(game_view: Dict[str, Any], player: str, *, turn_context: Optional[TurnContext] = None) -> RenderResult
- Accept: `game_view` already filtered by the Game; acting `player` name for convenience; optional `turn_context` injected by console (turn number, match id, max turns, etc.).
- Perform: Format the view into text and metadata; MUST treat `game_view` as read-only.
- Return: `RenderResult` with `.text` payload and JSON-serialisable `.metadata`.
- MUST: Produce deterministic output for identical inputs; MUST NOT reintroduce hidden data absent from `game_view`.
- SHOULD: Surface `turn_context` inside metadata when present (e.g., `{"turn": turn_context.turn_number}`).

### describe() -> Dict[str, Any]
- Return: Renderer identity and configuration snapshot captured by recorder/spectators.
- MUST: Include keys `name`, `version`, and `metadata`.
  - `name`: Human-friendly name (defaults to class name).
  - `version`: Renderer revision (defaults to package/module version or `"unknown"`).
  - `metadata`: Renderer-specific settings (JSON-serialisable dict).
- MAY: Expose additional keys (e.g., `supports_diff`, `template`) but MUST remain serialisable.

## 5. Invariants & Guarantees

### 5.1 Deterministic Formatting (DF)
1. **DF1**: `render` MUST return identical `RenderResult` (text + metadata) when invoked with the same `game_view`, `player`, and `turn_context`.
2. **DF2**: `render` MUST treat `game_view` and `turn_context` as read-only; any enrichment MUST use copies.

### 5.2 Mechanics-Agnostic Boundaries (MB)
3. **MB1**: Renderers MUST NOT introduce or infer hidden information absent from `game_view`; filtering authority lives exclusively in `Game.get_view`.
4. **MB2**: Renderers MUST NOT mutate or rely on global state; all behaviour derives from inputs and internal configuration.

### 5.3 Metadata & Observability (MO)
5. **MO1**: `RenderResult.metadata` MUST be JSON-serialisable and SHOULD include format hints (e.g., `{"format": "text"}`) and relevant sections.
6. **MO2**: `describe()` outputs MUST contain `name`, `version`, and `metadata` keys for recorder consumption.
7. **MO3**: When `turn_context` is provided, renderers SHOULD expose relevant fields inside metadata (turn number, phase, deadlines) for downstream tooling.

### 5.4 Error Handling (EH)
8. **EH1**: Schema-specific renderers (e.g., custom game renderers) MAY raise descriptive `ValueError` when required fields are missing. Generic renderers (e.g., `TextRenderer`) SHOULD render whatever data is provided without strict validation.
9. **EH2**: Renderers MUST tolerate absent `turn_context` and continue rendering using defaults.

## 6. Data Flow & Interaction
- **Turn rendering**: Console → `Game.get_view(game_state, player)` → renderer.render(game_view, player, turn_context) → `RenderResult` → PromptBuilder → Player model invocation → Controller parse.
- **Recorder metadata**: Renderer.describe() → recorder stores renderer identity alongside Match metadata → replay tooling reconstructs prompt environment.
- **Spectator usage**: Spectators consume `RenderResult.metadata` to build overlays (e.g., turn labels, score tables).

## 7. Error Handling & Edge Cases
- Missing keys: Schema-specific renderers MAY raise `ValueError`; generic renderers SHOULD render available data.
- Unknown players: SHOULD handle gracefully (e.g., default messaging) but MAY raise if view is malformed.
- Heavy processing: SHOULD precompute or cache within renderer instance; MUST NOT mutate `game_view`.
- Multimodal outputs: Represent via metadata (e.g., `{"sections": {"board_ascii": "...", "board_matrix": board}}`) while keeping `.text` meaningful for prompt pipelines.
- **Conditional rendering**: Renderers SHOULD conditionally render fields that may be `None` or empty on early turns (e.g., `last_action` on turn 1) to avoid confusing output like "Opponent's last action: (none)". Only show fields when they contain meaningful data.

## 8. Examples

```python
# Example 1: Generic TextRenderer (framework provided)
# Ships with agentdeck.renderers.TextRenderer - works with any game
class TextRenderer(Renderer):
    """
    Generic text renderer for turn-based games.

    Renders state dicts without game-specific assumptions:
    - Preserves game-provided insertion order
    - Renders unknown keys generically with type-based formatting
    - Avoids filtering underscore or empty fields from game-provided views
    - Exposes simple renderer metadata for observability

    Games requiring richer output (ASCII diagrams, combat logs, card displays)
    can provide custom renderers in their game module.
    """

    def render(self, game_view, player, *, turn_context=None):
        lines = ["=== Current Game State ==="]
        lines.append(f"You are: {player}")

        # Render turn number (prefer turn_context)
        if turn_context:
            lines.append(f"Turn: {turn_context.turn_number}")
        elif "turn" in game_view:
            lines.append(f"Turn: {game_view['turn']}")

        # Render common patterns: health, scores, board, etc.
        # (See src/agentdeck/renderers/text.py for full implementation)

        # Preserve insertion order from the game view.
        for key, value in game_view.items():
            if key != "turn":
                lines.append(f"\n{key.title()}: {value}")

        lines.append("=" * 25)

        metadata = {"format": "text", "sections": [...]}
        if turn_context:
            metadata["turn_number"] = turn_context.turn_number

        return RenderResult(text="\n".join(lines), metadata=metadata)

    def describe(self):
        return {
            "name": "TextRenderer",
            "version": "1.0.0",
            "metadata": {"style": "generic"},
        }
```

```python
# Example 2: Game-specific renderer for richer domain output
# Located in: src/agentdeck/games/examples/poker/renderers/poker_text.py
class PokerTextRenderer(Renderer):
    """
    Custom renderer for poker games with rich card/hand display.

    Generic TextRenderer would show cards as lists, but this renderer
    provides ASCII art, hand rankings, and pot calculations.
    """

    def render(self, game_view, player, *, turn_context=None):
        lines = ["=== POKER TABLE ==="]
        lines.append(f"Player: {player}")
        lines.append(f"Pot: ${game_view['pot']}")

        # Render hand with ASCII card art
        hand = game_view["hands"][player]
        lines.append("\nYour Hand:")
        lines.extend(self._render_cards_ascii(hand))

        # Show community cards if revealed
        if game_view.get("community_cards"):
            lines.append("\nCommunity Cards:")
            lines.extend(self._render_cards_ascii(game_view["community_cards"]))

        # Show betting actions
        if game_view.get("betting_round"):
            lines.append(f"\nBetting Round: {game_view['betting_round']}")
            lines.append(f"Current Bet: ${game_view['current_bet']}")

        text = "\n".join(lines)
        metadata = {"format": "poker_text", "hand_strength": self._evaluate_hand(hand)}
        return RenderResult(text=text, metadata=metadata)

    def _render_cards_ascii(self, cards):
        # Returns ASCII art for cards (implementation omitted)
        return [f"  {card}" for card in cards]

    def describe(self):
        return {
            "name": "PokerTextRenderer",
            "version": "1.0.0",
            "metadata": {"style": "ascii_art"},
        }
```

## 9. Testing Strategy
| Focus | Invariants | Verification |
|-------|------------|--------------|
| Determinism | DF1-DF2 | Invoke `render` twice with identical inputs; assert text/metadata equality and confirm `game_view` untouched. |
| Mechanics boundary | MB1-MB2 | Provide filtered `game_view` missing hidden data; ensure renderer output does not reintroduce secret fields. |
| Metadata capture | MO1-MO3 | Validate `RenderResult.metadata` JSON dumps cleanly and includes turn info when provided; confirm `describe()` fields present. |
| Error handling | EH1-EH2 | Remove required keys to assert descriptive errors; call render with `turn_context=None` to ensure graceful fallback. |

## 10. Design Rationale
- Mandatory `RenderResult` return type simplifies PromptBuilder and recorder integration—mirrors ActionResult pattern.
- Separate `turn_context` preserves console-owned execution metadata without polluting game state.
- `describe()` schema (name/version/metadata) provides experiment traceability beyond raw prompt text.
- **Generic TextRenderer**: Ships a single minimal, parameterizable renderer that works with any game following spec contracts. Games can ship custom renderers when they need richer domain-specific output (e.g., ASCII board diagrams, card art, combat logs). This avoids coupling the framework to specific game mechanics while providing good out-of-the-box UX.

## 11. Open Questions / Future Work
- Should we provide helper mixins for diff/highlight rendering across turns?
- Explore renderer capability flags (e.g., `supports_rich_text`) for UI selection.
- Investigate performance profiling hooks for renderers handling large game views.

## 12. References
- `specs/SPEC-GAME.md`
- `specs/SPEC-PLAYER.md`
- `specs/SPEC-CONSOLE.md`
- `specs/SPEC-OBSERVABILITY.md`
- `specs/SPEC-RENDERER-CRITIQUES.md`
