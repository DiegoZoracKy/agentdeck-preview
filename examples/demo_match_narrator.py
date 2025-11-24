"""
Demo of MatchNarrator spectator (auto-attached by default).

This script demonstrates that MatchNarrator is automatically attached to provide
turn-by-turn commentary for researchers to "watch" matches unfold, showing:
- Match start banner
- Turn-by-turn: player, action, state changes
- Match completion summary

Per SPEC-CONSOLE §5, MatchNarrator is auto-attached when no spectators are
specified, giving researchers an out-of-the-box narrative experience.

Output flows to both console (INFO level) and info.log file.
"""

from agentdeck import AgentDeck
from agentdeck.core.session import AgentDeckConfig
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players.mock import MockPlayer


def main():
    """Run a demo match with auto-attached MatchNarrator."""

    # Create simple deterministic players for demo
    # FixedDamageGame has two actions: ATTACK (deals 20 damage) and POTION (heals 30 HP)
    alice = MockPlayer(name="Alice", actions=["ATTACK"] * 20)  # Aggressive strategy
    bob = MockPlayer(name="Bob", actions=["POTION", "POTION", "POTION"] + ["ATTACK"] * 20)  # Heal then attack

    print("=" * 70)
    print("MatchNarrator Auto-Attachment Demo")
    print("=" * 70)
    print()
    print("Running a match between Alice and Bob.")
    print("MatchNarrator is automatically attached (no import needed!).")
    print("Turn-by-turn commentary appears in console and info.log.")
    print()
    print("To silence the narrator, pass spectators=[] explicitly.")
    print("=" * 70)
    print()

    # Create deck WITHOUT specifying spectators
    # MatchNarrator will be auto-attached per SPEC-CONSOLE §5
    # Logger will be auto-injected per SPEC-SPECTATOR v1.2.0 LI1-LI5
    config = AgentDeckConfig(seed=42)

    with AgentDeck(
        game=FixedDamageGame(),
        # No spectators parameter - MatchNarrator auto-attached!
        session=config
    ) as deck:
        # Run a single match
        results = deck.play(
            players=[alice, bob],
            matches=1
        )

    print()
    print("=" * 70)
    print("Match complete!")
    print(f"Winner: {results.matches[0].winner}")
    print(f"Check the logs directory for complete narrative: {deck.session.log_directory}")
    print("=" * 70)


if __name__ == "__main__":
    main()
