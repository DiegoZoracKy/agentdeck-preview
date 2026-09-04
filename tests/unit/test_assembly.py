import json
from pathlib import Path

import pytest

from agentdeck import (
    AssemblyExecutionError,
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


def test_provider_call_custody_is_part_of_prepared_identity(tmp_path):
    volatile_entrypoint = write_assembly(tmp_path)
    volatile = prepare_assembly(volatile_entrypoint)
    durable_source = ASSEMBLY_SOURCE.replace(
        "seed=41,\n        max_turns=20,",
        'seed=41,\n        provider_call_custody="durable",\n        max_turns=20,',
    )
    durable_entrypoint = tmp_path / "durable_assembly.py"
    durable_entrypoint.write_text(durable_source, encoding="utf-8")

    durable = prepare_assembly(durable_entrypoint)

    assert volatile.plan_sha256 != durable.plan_sha256
    assert durable.assembly["runs"][0]["session"]["provider_call_custody"] == "durable"


def test_default_unavailable_policy_preserves_identity_but_stop_policy_is_bound(tmp_path):
    default_entrypoint = write_assembly(tmp_path)
    default = prepare_assembly(default_entrypoint)
    assert "unavailable_match_policy" not in default.assembly["runs"][0]["session"]

    stopping_source = ASSEMBLY_SOURCE.replace(
        "seed=41,\n        max_turns=20,",
        'seed=41,\n        unavailable_match_policy="stop_batch",\n        max_turns=20,',
    )
    stopping_entrypoint = tmp_path / "stopping_assembly.py"
    stopping_entrypoint.write_text(stopping_source, encoding="utf-8")
    stopping = prepare_assembly(stopping_entrypoint)

    assert stopping.plan_sha256 != default.plan_sha256
    assert stopping.assembly["runs"][0]["session"]["unavailable_match_policy"] == "stop_batch"


def test_prepared_assembly_identity_is_deeply_immutable(tmp_path):
    prepared = prepare_assembly(write_assembly(tmp_path))
    original = prepared.as_dict()
    run = prepared.assembly["runs"][0]

    with pytest.raises(TypeError):
        run["matches"] = 999
    with pytest.raises(AttributeError):
        prepared.assembly["runs"].append({"name": "injected"})

    detached = prepared.as_dict()
    detached["assembly"]["runs"][0]["matches"] = 999
    assert prepared.as_dict() == original
    assert prepared.plan_sha256 == original["plan_sha256"]


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


def test_entrypoint_defined_game_keeps_prepared_identity_in_records(tmp_path):
    source = ASSEMBLY_SOURCE.replace(
        "def player(name, controller):",
        "class LocalFixedDamageGame(FixedDamageGame):\n"
        "    pass\n\n\n"
        "def player(name, controller):",
    ).replace(
        "game=FixedDamageGame(",
        "game=LocalFixedDamageGame(",
        1,
    )
    entrypoint = write_assembly(tmp_path, source)
    prepared = prepare_assembly(entrypoint)
    prepared_version = prepared.as_dict()["assembly"]["runs"][0]["game"]["version"]

    execution = execute_prepared_assembly(
        entrypoint,
        prepared,
        output_root=tmp_path / "local-game-runs",
    )

    payload = json.loads(execution.records[0].read_text(encoding="utf-8"))
    recorded_version = payload["metadata"]["game_version"]
    assert prepared_version["assurance"] == "class_source_only"
    assert prepared_version["implementation_sha256"]
    assert recorded_version == prepared_version


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
    assert execution.complete is True
    assert [run.run_name for run in execution.runs] == [
        "fixed-action-v-reasoning",
        "variable-action-v-reasoning",
    ]
    assert all(run.complete for run in execution.runs)
    assert all(run.records[0].match_index == 0 for run in execution.runs)
    assert all(len(run.records[0].record_sha256) == 64 for run in execution.runs)
    assert all(not run.records[0].relative_path.startswith("/") for run in execution.runs)
    assert execution.cost_usd == 0
    persisted = json.loads((tmp_path / "runs" / "assembly-execution.json").read_text())
    assert persisted == execution.as_dict()
    for record in execution.records:
        payload = json.loads(record.read_text(encoding="utf-8"))
        configs = payload["metadata"]["player_configs"]
        assert configs["Action"]["controller"]["type"] == "ActionOnlyController"
        assert configs["Reasoning"]["controller"]["type"] == "ReasoningController"


def test_execution_preserves_partial_receipt_before_raising(tmp_path, monkeypatch):
    entrypoint = write_assembly(tmp_path)
    prepared = prepare_assembly(entrypoint)
    original_play = __import__("agentdeck.core.assembly", fromlist=["AgentDeck"]).AgentDeck.play
    calls = 0

    def fail_second_run(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("second run failed")
        return original_play(self, *args, **kwargs)

    monkeypatch.setattr("agentdeck.core.assembly.AgentDeck.play", fail_second_run)
    output_root = tmp_path / "partial-runs"

    with pytest.raises(AssemblyExecutionError, match="second run failed") as raised:
        execute_prepared_assembly(entrypoint, prepared, output_root=output_root)

    persisted = json.loads((output_root / "assembly-execution.json").read_text())
    assert persisted == raised.value.execution.as_dict()
    assert persisted["complete"] is False
    assert persisted["runs"][0]["complete"] is True
    assert persisted["runs"][1]["complete"] is False


def test_execution_rejects_output_root_with_existing_receipt_before_player_creation(
    tmp_path, monkeypatch
):
    entrypoint = write_assembly(tmp_path)
    prepared = prepare_assembly(entrypoint)
    output_root = tmp_path / "runs"
    execute_prepared_assembly(entrypoint, prepared, output_root=output_root)

    def forbidden_create(_self):
        raise AssertionError("Player construction happened before receipt collision check")

    monkeypatch.setattr("agentdeck.core.assembly.PlayerFactory.create", forbidden_create)
    with pytest.raises(ValueError, match="already contains an execution receipt"):
        execute_prepared_assembly(entrypoint, prepared, output_root=output_root)


def test_runtime_monitor_factory_observes_sequential_turns_without_changing_plan(tmp_path):
    entrypoint = write_assembly(tmp_path)
    prepared = prepare_assembly(entrypoint)
    observed = []

    class CaptureMonitor:
        logger = None

        def __init__(self, run_name):
            self.run_name = run_name

        def on_console_worker_turn(self, event):
            observed.append((self.run_name, event.type, event.data))

    execution = execute_prepared_assembly(
        entrypoint,
        prepared,
        output_root=tmp_path / "observed-sequential-runs",
        runtime_monitor_factory=lambda run_name: [CaptureMonitor(run_name)],
    )

    assert execution.plan_sha256 == prepared.plan_sha256
    assert len(execution.records) == prepared.total_matches
    turns = [item for item in observed if item[1] == "console_worker_turn"]
    assert turns
    assert {item[0] for item in turns} == {
        "fixed-action-v-reasoning",
        "variable-action-v-reasoning",
    }
    assert {item[2]["match_index"] for item in turns} == {0}


def test_runtime_monitor_factory_observes_parallel_turns_without_changing_plan(tmp_path):
    source = ASSEMBLY_SOURCE.replace(
        "max_turns=20,",
        "max_turns=20,\n        concurrency=2,",
    ).replace("matches=1,", "matches=2,", 1)
    entrypoint = write_assembly(tmp_path, source)
    prepared = prepare_assembly(entrypoint)
    observed = []

    class CaptureMonitor:
        logger = None

        def __init__(self, run_name):
            self.run_name = run_name

        def on_console_batch_start(self, event):
            observed.append((self.run_name, event.type, event.data))

        def on_console_worker_start(self, event):
            observed.append((self.run_name, event.type, event.data))

        def on_console_worker_turn(self, event):
            observed.append((self.run_name, event.type, event.data))

        def on_console_batch_progress(self, event):
            observed.append((self.run_name, event.type, event.data))

    execution = execute_prepared_assembly(
        entrypoint,
        prepared,
        output_root=tmp_path / "observed-runs",
        runtime_monitor_factory=lambda run_name: [CaptureMonitor(run_name)],
    )

    assert execution.plan_sha256 == prepared.plan_sha256
    assert len(execution.records) == prepared.total_matches
    turns = [item for item in observed if item[1] == "console_worker_turn"]
    assert turns
    assert {item[0] for item in turns} == {
        "fixed-action-v-reasoning",
        "variable-action-v-reasoning",
    }
    assert {item[2]["match_index"] for item in turns if item[0] == "fixed-action-v-reasoning"} == {
        0,
        1,
    }
    for _, _, data in turns:
        assert set(data) == {
            "worker_id",
            "match_index",
            "match_id",
            "seed",
            "turn_number",
            "phase_index",
            "player",
            "action",
            "state_before",
            "state_after",
        }
