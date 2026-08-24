import json
from pathlib import Path

import pytest

from agentdeck import (
    PreparedAssembly,
    execute_prepared_assembly,
    prepare_assembly,
)

ASSEMBLY_SOURCE = """
from agentdeck import (
    ActionOnlyController,
    AgentDeckConfig,
    Assembly,
    AssemblyRun,
    ConclusionPolicy,
    FixedDamageGame,
    MockPlayer,
    PlayerFactory,
    ReasoningController,
    VariableDamageGame,
)


def player(name, controller):
    return PlayerFactory(
        MockPlayer,
        {
            "name": name,
            "model": "mock-behavior",
            "actions": ["ATTACK"],
            "controller": controller,
            "conclusion_template": None,
        },
    )


def create_assembly():
    session = AgentDeckConfig(
        seed=41,
        max_turns=20,
        log_level=None,
        log_file_levels=[],
        pairing_policy="none",
        first_player_policy="fixed",
        fixed_first_player_index=0,
        conclusion=ConclusionPolicy(enabled=False),
    )
    return Assembly(
        runs=(
            AssemblyRun(
                name="fixed-action-v-reasoning",
                game=FixedDamageGame(
                    max_health=40,
                    attack_damage=20,
                    potion_heal=30,
                    starting_potions=3,
                    information_level="partial",
                ),
                players=(
                    player("Action", ActionOnlyController()),
                    player("Reasoning", ReasoningController()),
                ),
                matches=1,
                seed=41,
                session=session,
            ),
            AssemblyRun(
                name="variable-action-v-reasoning",
                game=VariableDamageGame(
                    max_health=30,
                    min_attack_damage=15,
                    max_attack_damage=25,
                    potion_heal=30,
                    starting_potions=3,
                    information_level="partial",
                ),
                players=(
                    player("Action", ActionOnlyController()),
                    player("Reasoning", ReasoningController()),
                ),
                matches=1,
                seed=42,
                session=session,
            ),
        )
    )
"""


def write_assembly(tmp_path: Path, source: str = ASSEMBLY_SOURCE) -> Path:
    path = tmp_path / "assembly.py"
    path.write_text(source, encoding="utf-8")
    return path


def test_preparation_is_deterministic_and_preserves_asymmetric_components(tmp_path):
    entrypoint = write_assembly(tmp_path)

    first = prepare_assembly(entrypoint)
    second = prepare_assembly(entrypoint)

    assert first.plan_sha256 == second.plan_sha256
    assert first.entrypoint == "assembly.py"
    assert [artifact.path for artifact in first.artifacts] == ["assembly.py"]
    assert first.total_matches == 2
    assert first.provider_requirements == ()
    players = first.assembly["runs"][0]["players"]
    assert players[0]["kwargs"]["controller"]["type"]["name"] == "ActionOnlyController"
    assert players[1]["kwargs"]["controller"]["configuration"]["type"] == ("ReasoningController")
    assert PreparedAssembly.from_dict(first.as_dict()) == first


def test_preparation_rejects_artifacts_outside_the_source_directory(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    entrypoint = write_assembly(source_root)
    outside = tmp_path / "outside.csv"
    outside.write_text("private", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the entrypoint directory"):
        prepare_assembly(entrypoint, artifacts=[outside])


def test_preparation_does_not_create_players(tmp_path, monkeypatch):
    entrypoint = write_assembly(tmp_path)

    def forbidden_create(_self):
        raise AssertionError("Player construction happened during preparation")

    monkeypatch.setattr("agentdeck.core.assembly.PlayerFactory.create", forbidden_create)
    prepare_assembly(entrypoint)


def test_entrypoint_defined_components_have_stable_identity_and_execute(tmp_path):
    source = ASSEMBLY_SOURCE.replace(
        "def player(name, controller):",
        "class LocalActionController(ActionOnlyController):\n"
        "    pass\n\n\n"
        "def player(name, controller):",
    ).replace(
        'player("Action", ActionOnlyController())', 'player("Action", LocalActionController())'
    )
    entrypoint = write_assembly(tmp_path, source)

    first = prepare_assembly(entrypoint)
    second = prepare_assembly(entrypoint)
    execution = execute_prepared_assembly(
        entrypoint,
        first,
        output_root=tmp_path / "local-component-runs",
    )

    assert first.plan_sha256 == second.plan_sha256
    assert len(execution.records) == 2
    local_controller = first.assembly["runs"][0]["players"][0]["kwargs"]["controller"]
    assert local_controller["type"]["module"].startswith("agentdeck_assembly_")


def test_execution_rejects_changed_source_before_player_construction(tmp_path, monkeypatch):
    entrypoint = write_assembly(tmp_path)
    prepared = prepare_assembly(entrypoint)
    entrypoint.write_text(ASSEMBLY_SOURCE + "\nMARKER = True\n", encoding="utf-8")

    def forbidden_create(_self):
        raise AssertionError("Player construction happened before identity validation")

    monkeypatch.setattr("agentdeck.core.assembly.PlayerFactory.create", forbidden_create)
    with pytest.raises(ValueError, match="changed before execution"):
        execute_prepared_assembly(entrypoint, prepared, output_root=tmp_path / "runs")


def test_player_factory_rejects_credentials(tmp_path):
    source = ASSEMBLY_SOURCE.replace(
        '"name": name,', '"name": name,\n            "api_key": "not-allowed",'
    )
    entrypoint = write_assembly(tmp_path, source)

    with pytest.raises(ValueError, match="credentials are execution-host capabilities"):
        prepare_assembly(entrypoint)


def test_player_factory_rejects_nested_credentials(tmp_path):
    source = ASSEMBLY_SOURCE.replace(
        '"actions": ["ATTACK"],',
        '"actions": ["ATTACK"],\n            "config": {"credentials": "not-allowed"},',
    )
    entrypoint = write_assembly(tmp_path, source)

    with pytest.raises(ValueError, match="player.kwargs.config.credentials"):
        prepare_assembly(entrypoint)


def test_execution_runs_every_prepared_composition_and_preserves_records(tmp_path):
    entrypoint = write_assembly(tmp_path)
    prepared = prepare_assembly(entrypoint)

    execution = execute_prepared_assembly(
        entrypoint,
        prepared,
        output_root=tmp_path / "runs",
    )

    assert execution.plan_sha256 == prepared.plan_sha256
    assert len(execution.records) == 2
    assert execution.cost_usd == 0
    for record in execution.records:
        payload = json.loads(record.read_text(encoding="utf-8"))
        configs = payload["metadata"]["player_configs"]
        assert configs["Action"]["controller"]["type"] == "ActionOnlyController"
        assert configs["Reasoning"]["controller"]["type"] == "ReasoningController"
