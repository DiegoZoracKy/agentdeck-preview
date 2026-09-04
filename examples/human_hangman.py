"""Play a one-person Hangman match through the normal AgentDeck lifecycle."""

from agentdeck import (
    ActionOnlyController,
    AgentDeck,
    AgentDeckConfig,
    ConclusionPolicy,
    HangmanGame,
    HumanPlayer,
)


def main() -> None:
    game = HangmanGame()
    human = HumanPlayer(
        name="Human",
        controller=ActionOnlyController(),
    )
    session = AgentDeckConfig(
        concurrency=1,
        conclusion=ConclusionPolicy(enabled=False),
        run_dir="agentdeck_runs/human_hangman",
    )

    print("Respond with OK during the handshake and ACTION: <letter> on each turn.\n")
    with AgentDeck(game=game, session=session) as deck:
        results = deck.play(players=[human], matches=1)

    print(f"\nWinner: {results.matches[0].winner or 'none'}")


if __name__ == "__main__":
    main()
