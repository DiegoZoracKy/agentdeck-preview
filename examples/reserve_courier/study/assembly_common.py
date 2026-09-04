"""Explicit execution choices, separate from the Study's semantic assignments."""

from agentdeck import (
    ActionOnlyController,
    AgentDeckConfig,
    AssemblyRun,
    ConclusionPolicy,
    GPTPlayer,
    PlayerFactory,
    ReasoningController,
    TextRenderer,
)
from courier_game import ReserveCourierGame
from components import CalibrationPlayer, DecisionTrail, JsonActionController, JsonViewRenderer

MODELS = {"nano": "gpt-4.1-nano", "mini": "gpt-4o-mini"}


def make_run(
    name,
    *,
    model=None,
    advice="none",
    treatment="action",
    matches=4,
    policy="optimal",
    extension=False,
):
    controller = (
        JsonActionController()
        if treatment == "json"
        else ReasoningController() if treatment == "rationale" else ActionOnlyController()
    )
    kwargs = {
        "name": "Courier",
        "controller": controller,
        "renderer": JsonViewRenderer() if extension else TextRenderer(),
        "turn_template": "{game_view}\n\n{controller_format}",
        "conclusion_template": (
            "REFLECT_ON_DELIVERIES: Briefly describe your strategy." if extension else None
        ),
    }
    if model is None:
        kind = CalibrationPlayer
        kwargs["policy"] = policy
    else:
        kind = GPTPlayer
        kwargs.update(
            model=model,
            temperature=0.0,
            max_tokens=384,
            max_retries=0,
            retry_delay=0,
            context_policy="full_history",
        )
    session = AgentDeckConfig(
        seed=20260904,
        concurrency=1 if extension else 2,
        max_turns=3,
        log_level=None,
        log_file_levels=[],
        monitors=[],
        provider_call_custody="durable",
        conclusion=ConclusionPolicy(enabled=extension),
    )
    return AssemblyRun(
        name=name,
        game=ReserveCourierGame(advice=advice),
        players=(PlayerFactory(kind, kwargs),),
        matches=matches,
        seed=20260904,
        session=session,
        spectators=(DecisionTrail(),),
    )
