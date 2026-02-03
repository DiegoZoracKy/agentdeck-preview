"""
Generate a test match for viewer testing.
gpt-4o-mini (ReasoningController) vs gpt-4o (ActionOnlyController)
"""

import os
import sys

# Check for API key first
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not set")
    sys.exit(1)

from agentdeck import (
    AgentDeck,
    AgentDeckConfig,
    FixedDamageGame,
)
from agentdeck.players.openai_player import GPTPlayer
from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.controllers.reasoning import ReasoningController


def main():
    print("=" * 60)
    print("Viewer Test Match")
    print("gpt-4o-mini (Reasoning) vs gpt-4o (ActionOnly)")
    print("=" * 60)

    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=2,
        information_level="full",
    )

    config = AgentDeckConfig(seed=42)

    players = [
        GPTPlayer(
            name="Mini-Reasoner",
            model="gpt-4o-mini",
            temperature=0.7,
            controller=ReasoningController(),
        ),
        GPTPlayer(
            name="4o-Direct",
            model="gpt-4o",
            temperature=0.7,
            controller=ActionOnlyController(),
        ),
    ]

    with AgentDeck(game=game, session=config) as deck:
        results = deck.play(players=players, matches=1, seed=42)

        print(f"\nMatch complete!")
        print(f"Winner: {results[0].winner}")
        print(f"Session: {deck.session.session_id}")
        print(f"Records: {deck.session.record_directory}")

        # Return session path for easy access
        return deck.session.session_id, deck.session.record_directory


if __name__ == "__main__":
    session_id, record_dir = main()
    print(f"\n=== SESSION PATH ===")
    print(record_dir)
