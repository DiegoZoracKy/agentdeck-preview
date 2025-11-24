"""
AgentDeck UX Research: Full Configuration Example

Purpose:
    Demonstrate all available customization options for researchers who need
    fine-grained control over templates, controllers, and player behavior.

Usage:
    export OPENAI_API_KEY="sk-..."
    python examples/test_prompt_builder_ux_full.py

What This Demonstrates:
    ✓ Custom handshake/turn/conclusion templates (inline strings)
    ✓ Template loading from files (Path objects) - see commented alternative
    ✓ Custom player instructions (coaching, cognitive styles)
    ✓ Custom controllers (ActionOnlyController vs ReasoningController)
    ✓ A/B testing setup (different strategies per player)
    ✓ Full observability (MatchNarrator, metadata, stats, token tracking)

Comparison with Minimal Example:
    - Minimal: Just controller (uses all smart defaults)
    - Full: Every parameter customized (demonstrates flexibility)

Controllers (SPEC-CONTROLLER v1.1.0):
    - Controllers return ParseResult (stateless parsing)
    - No fallback_action in constructor (handled by Player.decide())
    - AcceptOKHandshakeController uses fixed token set (OK/READY/YES)
"""

from pathlib import Path

from agentdeck import AgentDeck
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players.openai_player import GPTPlayer
from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.controllers.reasoning import ReasoningController
from agentdeck.renderers.text_renderer import TextRenderer
from agentdeck.spectators import MatchNarrator


def main():
    """
    Run FixedDamageGame with full custom configuration.

    This example shows how researchers can customize every aspect of the
    three-phase lifecycle for A/B testing and experimentation.
    """

    # =========================================================================
    # STEP 1: Create game instance
    # =========================================================================

    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        information_level="full"
    )

    # =========================================================================
    # STEP 2: Define custom templates for each phase
    # =========================================================================

    # OPTION A: Inline template strings (used in this example)
    # Custom handshake template (front-loads all instructions)
    custom_handshake_template = """You are playing {game_name}.

{game_instructions}

{player_instructions}

{controller_format}

{handshake_controller_format}"""

    # Custom turn template (minimal - leverages conversation history)
    custom_turn_template = """{game_view}

{controller_format}"""

    # Custom conclusion template (post-game reflection)
    custom_conclusion_template = """Match concluded.

Result: {outcome}
Your final HP: {your_health}
Opponent's final HP: {opponent_health}
Total turns: {turns}

Provide a brief reflection on your performance and what you learned (2-3 sentences)."""

    # OPTION B: Load templates from files (alternative approach)
    # Uncomment to use file-based templates instead of inline strings:
    #
    # custom_handshake_template = Path("prompts/handshake.txt")
    # custom_turn_template = Path("prompts/turn.md")
    # custom_conclusion_template = Path("prompts/conclusion.txt")
    #
    # Player automatically loads file contents (UTF-8) during initialization.
    # Raises FileNotFoundError if path doesn't exist.
    # Explicit Path objects (no magic string detection) for clarity.

    # =========================================================================
    # STEP 3: Define player-specific instructions (A/B testing)
    # =========================================================================

    aggressive_instructions = """Your Strategy: AGGRESSIVE
- Attack relentlessly to maintain pressure
- Only use potions when HP drops below 30
- Force opponent to waste potions early
- Prioritize damage output over defense"""

    defensive_instructions = """Your Strategy: DEFENSIVE
- Conserve health with timely potion usage
- Use potions when HP drops below 50
- Outlast opponent through careful resource management
- Prioritize survival over damage output"""

    # =========================================================================
    # STEP 4: Create players with full custom configuration
    # =========================================================================

    # Player 1: Aggressive strategy with reasoning controller
    player_1 = GPTPlayer(
        name="Aggressive-Bot",
        model="gpt-4o-mini",
        temperature=0.7,

        # Custom templates
        handshake_template=custom_handshake_template,
        turn_template=custom_turn_template,
        conclusion_template=custom_conclusion_template,

        # Custom controllers (SPEC-CONTROLLER v1.1.0)
        controller=ReasoningController(
            # allowed_actions bound automatically by console!
            # No fallback_action - handled by Player.decide() via to_action_result()
        ),

        # Custom renderer (explicit, though this is the default)
        renderer=TextRenderer(),

        # Player-specific content via extras
        extras={
            "player_instructions": aggressive_instructions,
        }
    )

    # Player 2: Defensive strategy with action-only controller
    player_2 = GPTPlayer(
        name="Defensive-Bot",
        model="gpt-4o-mini",
        temperature=0.7,

        # Same custom templates (consistent experiment setup)
        handshake_template=custom_handshake_template,
        turn_template=custom_turn_template,
        conclusion_template=custom_conclusion_template,

        # Same handshake controller (SPEC-CONTROLLER v1.1.0)

        # Different action controller (A/B testing controller types)
        controller=ActionOnlyController(
            # No fallback_action - handled by Player.decide() via to_action_result()
        ),

        # Same renderer
        renderer=TextRenderer(),

        # Different player instructions (A/B testing strategies)
        extras={
            "player_instructions": defensive_instructions,
        }
    )

    # =========================================================================
    # STEP 5: Run match with full observability
    # =========================================================================

    # Use MatchNarrator for turn-by-turn commentary
    # Logger is auto-injected per SPEC-SPECTATOR v1.2.0
    with AgentDeck(game=game, spectators=[MatchNarrator()]) as deck:
        results = deck.play(
            players=[player_1, player_2],
            matches=1,
            seed=42
        )


if __name__ == "__main__":
    main()
