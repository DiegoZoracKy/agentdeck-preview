"""Play FixedDamage against an existing deterministic Player."""

from agentdeck import (
    ActionOnlyController,
    AgentDeck,
    AgentDeckConfig,
    ConclusionPolicy,
    FixedDamageGame,
    HumanPlayer,
    MockPlayer,
)


def main() -> None:
    game = FixedDamageGame()
    human = HumanPlayer(
        name="Human",
        controller=ActionOnlyController(),
    )
    opponent = MockPlayer(
        name="Mock",
        actions=["ATTACK", "POTION"],
        controller=ActionOnlyController(),
    )
    session = AgentDeckConfig(
        concurrency=1,
        conclusion=ConclusionPolicy(enabled=False),
        run_dir="agentdeck_runs/human_fixed_damage",
    )

    print("Respond with OK during the handshake and ACTION: ATTACK or ACTION: POTION.\n")
    with AgentDeck(game=game, session=session) as deck:
        results = deck.play(players=[human, opponent], matches=1)

    print(f"\nWinner: {results.matches[0].winner or 'draw'}")


if __name__ == "__main__":
    main()
