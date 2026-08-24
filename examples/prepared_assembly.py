"""Prepare and execute one complete, asymmetric AgentDeck assembly."""

from pathlib import Path

from agentdeck import (
    ActionOnlyController,
    AgentDeckConfig,
    Assembly,
    AssemblyRun,
    ConclusionPolicy,
    FixedDamageGame,
    GPTPlayer,
    GeminiPlayer,
    PlayerFactory,
    ReasoningController,
    TextRenderer,
    execute_prepared_assembly,
    prepare_assembly,
)

HANDSHAKE_TEMPLATE = (
    "{game_instructions}\n\n"
    "When gameplay begins, use this response format:\n"
    "{controller_format}\n\n"
    "{handshake_controller_format}"
)
TURN_TEMPLATE = "{game_view}\n\n{controller_format}"


def create_assembly() -> Assembly:
    session = AgentDeckConfig(
        seed=42,
        max_turns=100,
        pairing_policy="none",
        first_player_policy="fixed",
        fixed_first_player_index=0,
        conclusion=ConclusionPolicy(enabled=False),
    )
    return Assembly(
        runs=(
            AssemblyRun(
                name="reasoning-versus-action",
                game=FixedDamageGame(),
                players=(
                    PlayerFactory(
                        GPTPlayer,
                        {
                            "name": "Reasoning participant",
                            "model": "gpt-5",
                            "controller": ReasoningController(),
                            "temperature": None,
                            "max_tokens": 2_048,
                            "max_retries": 3,
                            "retry_delay": 1.0,
                            "context_policy": "full_history",
                            "renderer": TextRenderer(),
                            "handshake_template": HANDSHAKE_TEMPLATE,
                            "turn_template": TURN_TEMPLATE,
                            "conclusion_template": None,
                        },
                    ),
                    PlayerFactory(
                        GeminiPlayer,
                        {
                            "name": "Action participant",
                            "model": "gemini-2.5-flash-lite",
                            "controller": ActionOnlyController(),
                            "temperature": 0.0,
                            "max_tokens": 512,
                            "max_retries": 3,
                            "retry_delay": 1.0,
                            "context_policy": "full_history",
                            "renderer": TextRenderer(),
                            "handshake_template": HANDSHAKE_TEMPLATE,
                            "turn_template": TURN_TEMPLATE,
                            "generation_config": {"thinking_config": {"thinking_budget": 0}},
                            "conclusion_template": None,
                        },
                    ),
                ),
                matches=1,
                seed=42,
                session=session,
            ),
        )
    )


if __name__ == "__main__":
    entrypoint = Path(__file__).resolve()
    prepared = prepare_assembly(entrypoint)
    result = execute_prepared_assembly(
        entrypoint,
        prepared,
        output_root=entrypoint.parent / "runs",
    )
    print(prepared.plan_sha256)
    print(*(str(path) for path in result.records), sep="\n")
