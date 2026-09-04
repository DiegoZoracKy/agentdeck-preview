"""Contract tests for synchronous human-controlled Players."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agentdeck import (
    ActionOnlyController,
    HumanPlayer,
    TurnContext,
    execute_prepared_assembly,
    prepare_assembly,
)
from agentdeck.games.examples.fixed_damage import FixedDamageGame


def test_human_player_is_public_and_returns_the_exact_reader_response() -> None:
    prompts: list[str] = []
    supplied = "  ACTION: POTION  \n"

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return supplied

    player = HumanPlayer(
        "Diego",
        controller=ActionOnlyController(),
        response_reader=read,
    )

    assert player.get_response("Choose now") == supplied
    assert prompts == ["Choose now"]


def test_default_terminal_adapter_presents_prompt_and_reads_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[str] = []

    def read(prompt: str = "") -> str:
        calls.append(prompt)
        return "ACTION: ATTACK"

    monkeypatch.setattr(
        "builtins.input",
        read,
    )
    player = HumanPlayer("Diego", controller=ActionOnlyController())

    assert player.get_response("Choose now") == "ACTION: ATTACK"
    assert calls == ["> "]
    assert capsys.readouterr().out == "Choose now\n"


def test_human_player_rejects_invalid_reader_contracts() -> None:
    with pytest.raises(TypeError, match="callable or None"):
        HumanPlayer(
            "Diego",
            controller=ActionOnlyController(),
            response_reader="stdin",  # type: ignore[arg-type]
        )

    def invalid_reader(_prompt: str) -> Any:
        return 7

    player = HumanPlayer(
        "Diego",
        controller=ActionOnlyController(),
        response_reader=invalid_reader,
    )
    with pytest.raises(TypeError, match="must return a string"):
        player.get_response("Choose now")


def test_human_player_uses_the_normal_controller_pipeline_without_provider_metadata() -> None:
    game = FixedDamageGame()
    controller = ActionOnlyController()
    controller.bind_game(game)
    player = HumanPlayer(
        "Diego",
        controller=controller,
        response_reader=lambda _prompt: "ACTION: POTION",
    )

    result = player.decide(
        game.setup(["Diego", "Mock"], seed=11),
        turn_context=TurnContext(
            match_id="match-human",
            turn_number=1,
            turn_index=0,
            player="Diego",
            started_at=1.0,
            duration=0.0,
            rng_seed=11,
        ),
    )

    assert result.action == "POTION"
    assert result.metadata is not None
    assert result.metadata["raw_response"] == "ACTION: POTION"
    for key in (
        "usage_info",
        "provider_call",
        "retries",
        "retry_durations",
        "attempt_durations",
    ):
        assert key not in result.metadata

    description = player.describe()
    summary = player.get_summary()
    assert description["interaction"] == {"authority": "human", "mode": "callable"}
    assert summary["interaction"] == {"authority": "human", "mode": "callable"}
    for payload in (description, summary):
        assert "model" not in payload
        assert "provider" not in payload


def test_human_player_rejects_parallel_cloning() -> None:
    player = HumanPlayer("Diego", controller=ActionOnlyController())

    with pytest.raises(RuntimeError, match="concurrency=1"):
        player.clone()


def test_human_assembly_requests_input_only_during_authorized_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entrypoint = tmp_path / "assembly.py"
    entrypoint.write_text(
        """
from agentdeck import (
    ActionOnlyController,
    AgentDeckConfig,
    Assembly,
    AssemblyRun,
    ConclusionPolicy,
    FixedDamageGame,
    HumanPlayer,
    MockPlayer,
    PlayerFactory,
)


def create_assembly():
    session = AgentDeckConfig(
        concurrency=1,
        conclusion=ConclusionPolicy(enabled=False),
        first_player_policy="fixed",
        fixed_first_player_index=0,
        log_level=None,
        log_file_levels=[],
        max_turns=2,
    )
    return Assembly(runs=(AssemblyRun(
        name="human-fixed-damage",
        game=FixedDamageGame(max_health=20, attack_damage=20),
        players=(
            PlayerFactory(HumanPlayer, {
                "name": "Human",
                "controller": ActionOnlyController(),
                "conclusion_template": None,
            }),
            PlayerFactory(MockPlayer, {
                "name": "Mock",
                "actions": ["ATTACK"],
                "controller": ActionOnlyController(),
                "conclusion_template": None,
            }),
        ),
        matches=1,
        seed=5,
        session=session,
    ),))
""".strip() + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": pytest.fail("Assembly preparation requested human input"),
    )

    prepared = prepare_assembly(entrypoint)

    human = prepared.assembly["runs"][0]["players"][0]
    assert human["player_type"]["name"] == "HumanPlayer"
    assert "provider" not in human
    assert "model" not in human
    assert prepared.provider_requirements == ()

    responses = iter(["OK", "ACTION: ATTACK"])
    input_prompts: list[str] = []

    def read(prompt: str = "") -> str:
        input_prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr("builtins.input", read)
    execution = execute_prepared_assembly(
        entrypoint,
        prepared,
        output_root=tmp_path / "execution",
    )

    assert execution.complete is True
    assert input_prompts == ["> ", "> "]
