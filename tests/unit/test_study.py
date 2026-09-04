import json
import shutil
from pathlib import Path

import pytest
import yaml

from agentdeck import (
    PlayerFactory,
    StudyValidationError,
    execute_prepared_assembly,
    execute_prepared_study,
    load_study,
    prepare_study,
    select_study,
)

ASSEMBLY_SOURCE = """
from agentdeck.core.types import ParseFailurePolicy
from agentdeck import (
    Assembly,
    AssemblyRun,
    GameStatus,
    MockPlayer,
    PlayerFactory,
    TurnBasedGame,
)


class ObservationGame(TurnBasedGame):
    def on_action_parse_failure(self, player_name, error, turn_context):
        return ParseFailurePolicy.ABORT_MATCH

    def __init__(self, information_level):
        super().__init__()
        self.information_level = information_level

    @property
    def instructions(self):
        return "Observe the available information and record one decision. There is no winner."

    @property
    def allowed_actions(self):
        return ["OBSERVE"]

    @property
    def default_handshake_template(self):
        return "{game_instructions}\\n\\n{controller_format}\\n\\n{handshake_controller_format}"

    def setup(self, players, seed):
        if len(players) != 1:
            raise ValueError("ObservationGame requires exactly one Player")
        return {"done": False, "information_level": self.information_level, "seed": seed}

    def get_view(self, game_state, player):
        return {
            "player": player,
            "information": game_state["information_level"],
            "allowed_actions": self.allowed_actions,
        }

    def update(self, game_state, player, action, *, rng):
        return {
            **game_state,
            "done": True,
            "observed_by": player,
            "action": action.action,
        }

    def status(self, game_state):
        return GameStatus(is_over=game_state["done"], winner=None)


def player(name):
    return PlayerFactory(
        MockPlayer,
        {"name": name, "model": "mock-study", "actions": ["OBSERVE"]},
    )


def create_assembly():
    return Assembly(
        runs=(
            AssemblyRun(
                name="partial",
                game=ObservationGame(information_level="partial"),
                players=(player("candidate"),),
                matches=2,
                seed=11,
            ),
            AssemblyRun(
                name="full",
                game=ObservationGame(information_level="full"),
                players=(player("candidate"),),
                matches=2,
                seed=11,
            ),
        )
    )
"""

COMPETITIVE_ASSEMBLY_SOURCE = """
from agentdeck import Assembly, AssemblyRun, FixedDamageGame, MockPlayer, PlayerFactory


def player(name, action):
    return PlayerFactory(
        MockPlayer,
        {"name": name, "model": "mock-study", "actions": [action]},
    )


def create_assembly():
    return Assembly(
        runs=(
            AssemblyRun(
                name="matchup",
                game=FixedDamageGame(information_level="partial"),
                players=(player("action-policy", "ATTACK"), player("healing-policy", "POTION")),
                matches=4,
                seed=21,
            ),
        )
    )
"""


def study_payload() -> dict:
    return {
        "schema_version": 1,
        "study": {
            "id": "information-grounding",
            "title": "Information Grounding",
            "question": "Does additional state information change the agent's action?",
            "intent": "confirmatory",
            "hypotheses": [{"id": "h1", "statement": "Full information changes action rate."}],
        },
        "execution_groups": [{"id": "main", "phase": "p1", "entrypoint": "assembly.py"}],
        "phases": [{"id": "p1", "kind": "study"}],
        "conditions": [
            {"id": "partial_information", "description": "Partial Game information."},
            {"id": "full_information", "description": "Full Game information."},
        ],
        "cells": [
            {
                "id": "partial",
                "execution_group": "main",
                "assembly_run": "partial",
                "assignments": [{"condition": "partial_information", "target": {"scope": "run"}}],
            },
            {
                "id": "full",
                "execution_group": "main",
                "assembly_run": "full",
                "assignments": [
                    {
                        "condition": "full_information",
                        "target": {"scope": "player", "name": "candidate"},
                    }
                ],
            },
        ],
    }


def write_study(root: Path, *, payload: dict | None = None, assembly: str = ASSEMBLY_SOURCE):
    root.mkdir(parents=True, exist_ok=True)
    (root / "study.yaml").write_text(
        yaml.safe_dump(payload or study_payload(), sort_keys=False), encoding="utf-8"
    )
    (root / "assembly.py").write_text(assembly, encoding="utf-8")
    return root / "study.yaml"


def diagnostic_codes(error: StudyValidationError) -> set[str]:
    return {item.code for item in error.diagnostics}


def competitive_payload() -> dict:
    payload = study_payload()
    payload["study"] = {
        "id": "policy-comparison",
        "title": "Policy Comparison",
        "question": "Do two declared policies behave differently in the same Game?",
        "intent": "exploratory",
    }
    payload["conditions"] = [
        {"id": "action_policy", "description": "Action policy Player role."},
        {"id": "healing_policy", "description": "Healing policy Player role."},
    ]
    payload["cells"] = [
        {
            "id": "matchup",
            "execution_group": "main",
            "assembly_run": "matchup",
            "assignments": [
                {
                    "condition": "action_policy",
                    "target": {"scope": "player", "name": "action-policy"},
                },
                {
                    "condition": "healing_policy",
                    "target": {"scope": "player", "name": "healing-policy"},
                },
            ],
        }
    ]
    return payload


def test_load_study_is_structural_and_does_not_import_assembly(tmp_path):
    manifest = write_study(tmp_path / "study", assembly="raise RuntimeError('imported')\n")

    definition = load_study(manifest)

    assert definition.id == "information-grounding"
    assert definition.execution_groups[0].entrypoint == "assembly.py"
    with pytest.raises(StudyValidationError, match="Assembly preparation failed"):
        prepare_study(manifest)


def test_prepare_study_is_portable_stable_and_creates_no_players_or_cache(tmp_path, monkeypatch):
    first_root = tmp_path / "first"
    manifest = write_study(first_root)

    def forbidden_create(_self):
        raise AssertionError("Player construction happened during Study preparation")

    monkeypatch.setattr(PlayerFactory, "create", forbidden_create)
    first = prepare_study(manifest)
    repeated = prepare_study(first_root)

    second_root = tmp_path / "relocated"
    shutil.copytree(first_root, second_root)
    relocated = prepare_study(second_root)

    assert first.plan_sha256 == repeated.plan_sha256 == relocated.plan_sha256
    assert first.definition_sha256 == relocated.definition_sha256
    assert first.total_matches == 4
    assert first.provider_requirements == ()
    assert first.as_dict() == relocated.as_dict()
    serialized = json.dumps(first.as_dict(), sort_keys=True)
    assert str(first_root) not in serialized
    assert str(second_root) not in serialized
    assert not list(first_root.rglob("__pycache__"))
    assert not list(first_root.rglob("*.pyc"))


def test_prepared_study_identity_is_deeply_immutable(tmp_path):
    provider_source = ASSEMBLY_SOURCE.replace("MockPlayer", "GPTPlayer")
    prepared = prepare_study(write_study(tmp_path / "study", assembly=provider_source))
    original = prepared.as_dict()
    assembly = prepared.execution_groups[0].prepared_assembly.assembly

    with pytest.raises(TypeError):
        assembly["runs"][0]["matches"] = 999
    with pytest.raises(AttributeError):
        assembly["runs"].append({"name": "injected"})
    with pytest.raises(TypeError):
        prepared.provider_requirements[0]["model"] = "changed-model"

    detached = prepared.as_dict()
    detached["execution_groups"][0]["prepared_assembly"]["assembly"]["runs"][0]["matches"] = 999
    detached["provider_requirements"][0]["model"] = "changed-model"
    assert prepared.as_dict() == original
    assert prepared.plan_sha256 == original["plan_sha256"]


def test_same_study_contract_prepares_competitive_and_single_player_topologies(tmp_path):
    single_manifest = write_study(tmp_path / "single")
    single_player = prepare_study(single_manifest)
    competitive = prepare_study(
        write_study(
            tmp_path / "competitive",
            payload=competitive_payload(),
            assembly=COMPETITIVE_ASSEMBLY_SOURCE,
        )
    )

    assert type(single_player) is type(competitive)
    assert type(single_player.definition.cells[0]) is type(competitive.definition.cells[0])
    assert single_player.total_matches == competitive.total_matches == 4
    assert [
        assignment.target.scope for assignment in competitive.definition.cells[0].assignments
    ] == [
        "player",
        "player",
    ]
    single_runs = single_player.execution_groups[0].prepared_assembly.assembly["runs"]
    assert all(run["game"]["configuration"]["name"] == "ObservationGame" for run in single_runs)
    assert all(len(run["players"]) == 1 for run in single_runs)

    execution = execute_prepared_assembly(
        single_manifest.parent / "assembly.py",
        single_player.execution_groups[0].prepared_assembly,
        output_root=tmp_path / "single-player-runs",
    )
    assert len(execution.records) == 4
    for record in execution.records:
        payload = json.loads(record.read_text(encoding="utf-8"))
        assert payload["winner"] is None
        assert payload["final_state"]["done"] is True


def test_select_and_execute_study_preserves_exact_record_slots(tmp_path):
    root = tmp_path / "study"
    manifest = write_study(root)
    prepared = prepare_study(manifest)
    selection = select_study(prepared, phase_ids=["p1"])

    execution = execute_prepared_study(
        manifest,
        prepared,
        selection,
        output_root=tmp_path / "runs",
    )

    assert execution.complete is True
    assert execution.execution_group_ids == ("main",)
    assert len(execution.records) == 4
    assert execution.receipt_path.is_file()
    assert (execution.execution_root / "prepared-study.json").is_file()
    assert (execution.execution_root / "selection.json").is_file()
    group = execution.groups[0]
    assert group.complete is True
    assert [run.cell_id for run in group.runs] == ["partial", "full"]
    for run in group.runs:
        assert [record.match_index for record in run.records] == [0, 1]
        assert all(isinstance(record.effective_seed, int) for record in run.records)
        assert all(len(record.record_sha256) == 64 for record in run.records)
        assert all(record.path.is_file() for record in run.records)
        assert all(not record.relative_path.startswith("/") for record in run.records)

    receipt = json.loads(execution.receipt_path.read_text(encoding="utf-8"))
    assert receipt["execution_sha256"] == execution.execution_sha256
    assert receipt["record_count"] == 4
    assert receipt["groups"][0]["runs"][0]["records"][0]["cell_id"] == "partial"


def test_study_selection_is_explicit_and_bound_to_plan(tmp_path):
    manifest = write_study(tmp_path / "study")
    prepared = prepare_study(manifest)

    with pytest.raises(ValueError, match="exactly one"):
        select_study(prepared)
    with pytest.raises(ValueError, match="exactly one"):
        select_study(prepared, phase_ids=["p1"], all_groups=True)

    selection = select_study(prepared, all_groups=True)
    changed_payload = study_payload()
    changed_payload["study"]["question"] = "Changed after approval?"
    manifest.write_text(yaml.safe_dump(changed_payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="changed before execution"):
        execute_prepared_study(
            manifest,
            prepared,
            selection,
            output_root=tmp_path / "runs",
        )


def test_study_and_assembly_changes_change_plan_identity(tmp_path):
    root = tmp_path / "study"
    manifest = write_study(root)
    initial = prepare_study(manifest)

    changed_payload = study_payload()
    changed_payload["study"]["title"] = "Changed title"
    manifest.write_text(yaml.safe_dump(changed_payload, sort_keys=False), encoding="utf-8")
    changed_study = prepare_study(manifest)

    manifest.write_text(yaml.safe_dump(study_payload(), sort_keys=False), encoding="utf-8")
    (root / "assembly.py").write_text(ASSEMBLY_SOURCE + "\nMARKER = True\n", encoding="utf-8")
    changed_assembly = prepare_study(manifest)

    assert initial.definition_sha256 != changed_study.definition_sha256
    assert initial.plan_sha256 != changed_study.plan_sha256
    assert initial.definition_sha256 == changed_assembly.definition_sha256
    assert initial.plan_sha256 != changed_assembly.plan_sha256


def test_lineage_changes_study_identity(tmp_path):
    first = prepare_study(write_study(tmp_path / "first"))
    payload = study_payload()
    payload["lineage"] = {"parent": first.plan_sha256, "relation": "replication"}
    child = prepare_study(write_study(tmp_path / "child", payload=payload))

    assert first.definition_sha256 != child.definition_sha256
    assert first.plan_sha256 != child.plan_sha256


def test_load_reports_multiple_structural_and_reference_diagnostics(tmp_path):
    payload = study_payload()
    payload["model"] = "forbidden-duplicate-authority"
    payload["study"]["unexpected"] = True
    payload["execution_groups"][0]["phase"] = "missing-phase"
    payload["cells"][0]["assignments"][0]["condition"] = "missing-condition"
    manifest = write_study(tmp_path / "study", payload=payload)

    with pytest.raises(StudyValidationError) as captured:
        load_study(manifest)

    codes = diagnostic_codes(captured.value)
    assert "study.unknown_field" in codes
    assert "study.unknown_phase" in codes
    assert "study.unknown_condition" in codes
    assert len(captured.value.diagnostics) >= 4


def test_load_rejects_non_string_field_names_without_internal_failure(tmp_path):
    payload = study_payload()
    payload["study"][42] = "invalid-field-name"
    manifest = write_study(tmp_path / "study", payload=payload)

    with pytest.raises(StudyValidationError) as captured:
        load_study(manifest)

    assert "study.field_name" in diagnostic_codes(captured.value)


def test_prepare_reports_missing_duplicate_and_unmapped_runs(tmp_path):
    payload = study_payload()
    payload["cells"] = [
        {
            "id": "one",
            "execution_group": "main",
            "assembly_run": "partial",
        },
        {
            "id": "two",
            "execution_group": "main",
            "assembly_run": "partial",
        },
        {
            "id": "missing",
            "execution_group": "main",
            "assembly_run": "not-a-run",
        },
    ]
    manifest = write_study(tmp_path / "study", payload=payload)

    with pytest.raises(StudyValidationError) as captured:
        prepare_study(manifest)

    codes = diagnostic_codes(captured.value)
    assert "study.duplicate_run_mapping" in codes
    assert "study.unmapped_assembly_run" in codes
    assert "study.unknown_assembly_run" in codes


def test_prepare_rejects_unknown_player_target(tmp_path):
    payload = study_payload()
    payload["cells"][1]["assignments"][0]["target"]["name"] = "unknown"
    manifest = write_study(tmp_path / "study", payload=payload)

    with pytest.raises(StudyValidationError) as captured:
        prepare_study(manifest)

    assert "study.unknown_player" in diagnostic_codes(captured.value)


def test_prepare_detects_authored_source_mutation(tmp_path):
    source = (
        "from pathlib import Path\n"
        "Path(__file__).with_name('mutation.txt').write_text('changed')\n" + ASSEMBLY_SOURCE
    )
    manifest = write_study(tmp_path / "study", assembly=source)

    with pytest.raises(StudyValidationError) as captured:
        prepare_study(manifest)

    assert "study.source_mutation" in diagnostic_codes(captured.value)


def test_prepare_rejects_existing_interpreter_cache(tmp_path):
    root = tmp_path / "study"
    manifest = write_study(root)
    cache = root / "__pycache__"
    cache.mkdir()
    (cache / "assembly.pyc").write_bytes(b"not-bytecode")

    with pytest.raises(StudyValidationError) as captured:
        prepare_study(manifest)

    assert "study.generated_source" in diagnostic_codes(captured.value)


def test_package_hygiene_fails_before_trusted_assembly_import(tmp_path):
    root = tmp_path / "study"
    source = (
        "from pathlib import Path\nPath(__file__).with_name('imported.txt').write_text('yes')\n"
    )
    manifest = write_study(root, assembly=source)
    (root / "__pycache__").mkdir()

    with pytest.raises(StudyValidationError) as captured:
        prepare_study(manifest)

    assert "study.generated_source" in diagnostic_codes(captured.value)
    assert not (root / "imported.txt").exists()


def test_prepare_rejects_entrypoint_symlink_that_resolves_outside_package(tmp_path):
    root = tmp_path / "study"
    payload = study_payload()
    payload["execution_groups"][0]["entrypoint"] = "assembly-link.py"
    manifest = write_study(root, payload=payload)
    outside = tmp_path / "outside.py"
    outside.write_text(ASSEMBLY_SOURCE, encoding="utf-8")
    (root / "assembly-link.py").symlink_to(outside)

    with pytest.raises(StudyValidationError) as captured:
        prepare_study(manifest)

    assert "study.entrypoint" in diagnostic_codes(captured.value)


@pytest.mark.parametrize(
    "bad_path",
    ["../assembly.py", "/tmp/assembly.py", "assemblies\\main.py"],
)
def test_load_rejects_nonportable_entrypoint_paths(tmp_path, bad_path):
    payload = study_payload()
    payload["execution_groups"][0]["entrypoint"] = bad_path
    manifest = write_study(tmp_path / "study", payload=payload)

    with pytest.raises(StudyValidationError) as captured:
        load_study(manifest)

    assert "study.path" in diagnostic_codes(captured.value)
