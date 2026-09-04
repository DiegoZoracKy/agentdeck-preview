"""Regression coverage for failures observed in the installed-package journey."""

import copy
import itertools
import inspect
import json
import threading
from dataclasses import asdict
from pathlib import Path

import pytest

from agentdeck import (
    ActionOnlyController,
    AgentDeck,
    AgentDeckConfig,
    AssemblyExecutionError,
    ConclusionPolicy,
    GameStatus,
    MockPlayer,
    PlayerFactory,
    RenderResult,
    StudyExecutionError,
    TurnBasedGame,
    execute_prepared_assembly,
    execute_prepared_study,
    inspect_provider_call_custody,
    load_study_execution,
    prepare_assembly,
    prepare_study,
    select_study,
)
from agentdeck.core.base import Game
from agentdeck.core.types import MatchAbortedError, ParseFailurePolicy
from agentdeck.monitors import Monitor
from agentdeck.players.llm_player import LLMPlayer
from agentdeck.research._canonical import sha256_json
from test_assembly import write_assembly
from test_study import ASSEMBLY_SOURCE, study_payload, write_study
from test_study_cli import run_cli


class SinglePlayerGame(TurnBasedGame):
    @property
    def default_handshake_template(self):
        return "{game_instructions}\n{handshake_controller_format}"

    @property
    def instructions(self):
        return "Choose WAIT to finish. An invalid action aborts this single-player match."

    @property
    def allowed_actions(self):
        return ["WAIT"]

    def setup(self, players, seed):
        return {"done": False, "player": players[0]}

    def get_view(self, game_state, player):
        return dict(game_state)

    def update(self, game_state, player, action, *, rng):
        return {**game_state, "done": True}

    def status(self, game_state):
        return GameStatus(is_over=game_state["done"], winner=None)

    def on_action_parse_failure(self, player_name, error, turn_context):
        return ParseFailurePolicy.ABORT_MATCH


class PaidFixture(LLMPlayer):
    PROVIDER = "fixture"
    default_model = "fixture"
    api_key_env_var = "UNUSED_TEST_CREDENTIAL"

    def _get_api_key_from_env(self):
        return "provider-free-fixture"

    def _initialize_client(self):
        self.client = None

    def _make_api_call(self, messages):
        self._capture_sdk_request("fixture.responses.create", {"messages": messages})
        response = "OK" if self._active_phase == "handshake" else "ACTION: WAIT"
        return response, {
            "tokens_used": 10,
            "prompt_tokens": 8,
            "completion_tokens": 2,
            "cost": 0.01,
            "response_complete": True,
        }


def config(path, concurrency):
    return AgentDeckConfig(
        run_dir=str(path),
        seed=31,
        concurrency=concurrency,
        monitors=[],
        max_turns=2,
        log_level=None,
        log_file_levels=[],
        provider_call_custody="durable",
        conclusion=ConclusionPolicy(enabled=False),
    )


def records(path):
    return [json.loads(p.read_text()) for p in Path(path).rglob("match_*.json")]


@pytest.mark.parametrize("concurrency", [1, 2])
def test_abort_persists_record_and_raises_in_both_schedulers(tmp_path, concurrency):
    class BatchCapture:
        completed = None

        def on_batch_end(self, event):
            self.completed = event.data["matches_completed"]

    capture = BatchCapture()
    with AgentDeck(
        game=SinglePlayerGame(), session=config(tmp_path, concurrency), spectators=[capture]
    ) as deck:
        with pytest.raises(MatchAbortedError):
            deck.play([MockPlayer("C", actions=["UNKNOWN"], conclusion_template=None)], matches=2)
    assert capture.completed == 0
    observed = records(tmp_path)
    assert observed
    assert all(r["metadata"]["match"]["outcome"] == "aborted" for r in observed)
    assert all(r["final_state"]["done"] is False for r in observed)
    assert all(
        any(e["type"] == "player_action_parse_failed" for e in r["events"]) for r in observed
    )


@pytest.mark.parametrize("concurrency", [1, 2])
def test_descriptor_failure_precedes_response_acquisition(tmp_path, concurrency):
    class BadDescriptor(SinglePlayerGame):
        def describe(self):
            raise ValueError("broken descriptor")

    class MustNotRun(MockPlayer):
        def get_response(self, prompt):
            raise AssertionError("response source must not run")

    with AgentDeck(game=BadDescriptor(), session=config(tmp_path, concurrency)) as deck:
        with pytest.raises(ValueError, match="Game descriptor.*broken descriptor"):
            deck.play([MustNotRun("C")])
    assert not records(tmp_path)


def test_inherited_single_player_forfeit_is_rejected_before_response(tmp_path):
    class InheritedForfeit(SinglePlayerGame):
        on_action_parse_failure = Game.on_action_parse_failure

    with AgentDeck(game=InheritedForfeit(), session=config(tmp_path, 1)) as deck:
        with pytest.raises(ValueError, match="single-player Game must override"):
            deck.play([MockPlayer("C")])
    assert not records(tmp_path)


@pytest.mark.parametrize("concurrency", [1, 2])
def test_unexpected_failure_records_only_observed_state(tmp_path, concurrency):
    class FailingGame(SinglePlayerGame):
        def update(self, game_state, player, action, *, rng):
            game_state["done"] = True
            raise ValueError("transition was never committed")

    with AgentDeck(game=FailingGame(), session=config(tmp_path, concurrency)) as deck:
        with pytest.raises(RuntimeError, match="FailingGame.update"):
            deck.play([MockPlayer("C", actions=["WAIT"])], matches=2)
        if concurrency == 1:
            assert deck.console.game is None
            assert deck.console.players == []
    observed = records(tmp_path)
    assert observed
    assert all(r["final_state"]["done"] is False for r in observed)
    assert all(r["metadata"]["match"]["outcome"] == "execution_error" for r in observed)
    assert all(not any(e["type"] == "gameplay" for e in r["events"]) for r in observed)


def test_parallel_failure_drains_started_workers_and_preserves_cost(tmp_path):
    barrier = threading.Barrier(2)
    failure_observed = threading.Event()
    slots = itertools.count()

    class FailingGame(SinglePlayerGame):
        def setup(self, players, seed):
            return {**super().setup(players, seed), "slot": next(slots)}

        def update(self, game_state, player, action, *, rng):
            barrier.wait(timeout=5)
            if game_state["slot"] == 0:
                raise ValueError("injected game transition failure")
            assert failure_observed.wait(timeout=5)
            return super().update(game_state, player, action, rng=rng)

    class FailureMonitor(Monitor):
        def on_console_worker_failed(self, event):
            failure_observed.set()

    player = PaidFixture("C", controller=ActionOnlyController(), conclusion_template=None)
    with AgentDeck(
        game=FailingGame(), session=config(tmp_path, 2), runtime_monitors=[FailureMonitor()]
    ) as deck:
        with pytest.raises(RuntimeError, match="FailingGame.update") as captured:
            deck.play([player], matches=2)
    assert isinstance(captured.value.__cause__, ValueError)
    assert str(captured.value.__cause__) == "injected game transition failure"
    observed = records(tmp_path)
    assert len(observed) == 2
    failed = next(r for r in observed if r["metadata"]["match"].get("outcome") == "execution_error")
    successful = next(r for r in observed if r is not failed)
    assert failed["final_state"]["done"] is False
    assert failed["winner"] is None
    assert failed["metadata"]["match"]["error_type"] == "RuntimeError"
    assert successful["final_state"]["done"] is True
    assert player.total_cost == pytest.approx(0.04)
    assert player.total_tokens == 40
    recovered = inspect_provider_call_custody(tmp_path)
    assert recovered["usage"]["cost_usd"] == pytest.approx(0.04)


@pytest.mark.parametrize("concurrency", [1, 2])
def test_player_usage_accumulates_across_matches_and_batches(tmp_path, concurrency):
    player = PaidFixture("C", controller=ActionOnlyController(), conclusion_template=None)
    with AgentDeck(game=SinglePlayerGame(), session=config(tmp_path, concurrency)) as deck:
        for _ in range(2):
            deck.play([player], matches=3)
    assert player.total_cost == pytest.approx(0.12)
    assert player.total_tokens == 120
    assert len(records(tmp_path)) == 6


@pytest.mark.parametrize("failure_kind", ["player", "monitor"])
def test_construction_failure_preserves_previous_assembly_run(tmp_path, monkeypatch, failure_kind):
    entrypoint = write_assembly(tmp_path)
    prepared = prepare_assembly(entrypoint)
    calls = 0
    original = PlayerFactory.create

    def create(factory):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise ValueError("second run constructor failed")
        return original(factory)

    def monitors(name):
        if name.startswith("variable"):
            raise ValueError("second run monitor failed")
        return []

    if failure_kind == "player":
        monkeypatch.setattr(PlayerFactory, "create", create)
    output = tmp_path / "output"
    with pytest.raises(AssemblyExecutionError, match="second run") as captured:
        execute_prepared_assembly(
            entrypoint,
            prepared,
            output_root=output,
            runtime_monitor_factory=monitors if failure_kind == "monitor" else None,
        )
    partial = captured.value.execution
    assert partial.complete is False
    assert len(partial.runs) == 2 and partial.runs[0].complete
    assert len(partial.records) == 1
    assert (output / "assembly-execution.json").is_file()
    assert isinstance(captured.value.__cause__, ValueError)


def test_renderer_metadata_snapshot_supports_json_and_deepcopy():
    metadata = {"sections": [{"name": "original"}]}
    rendered = RenderResult("view", metadata)
    metadata["sections"][0]["name"] = "changed"
    assert rendered.metadata["sections"][0]["name"] == "original"
    with pytest.raises(TypeError, match="immutable"):
        rendered.metadata["sections"][0]["name"] = "changed"
    with pytest.raises(TypeError, match="immutable"):
        rendered.metadata["sections"].append("extra")
    copied = copy.deepcopy(rendered)
    with pytest.raises(TypeError, match="immutable"):
        copied.metadata.clear()
    assert json.loads(json.dumps(asdict(rendered))) == {
        "text": "view",
        "metadata": {"sections": [{"name": "original"}]},
    }


def test_paid_handshake_subtotal_survives_unavailable_response_and_receipts(tmp_path):
    source = (
        """
from agentdeck import (AgentDeckConfig, Assembly, AssemblyRun, ConclusionPolicy,
                       FixedDamageGame, PlayerFactory, ActionOnlyController)
from agentdeck.players.llm_player import LLMPlayer
"""
        + inspect.getsource(PaidFixture)
        + """
class UnavailableFixture(PaidFixture):
    def _make_api_call(self, messages):
        self._capture_sdk_request("fixture.responses.create", {"messages": messages})
        raise RuntimeError("no response available")

def create_assembly():
    return Assembly((AssemblyRun(
        name="paid-then-unavailable", game=FixedDamageGame(), matches=1,
        players=tuple(PlayerFactory(kind, {"name": name, "max_retries": 0,
                      "controller": ActionOnlyController(), "conclusion_template": None})
                      for kind, name in ((PaidFixture, "Paid"), (UnavailableFixture, "Unavailable"))),
        session=AgentDeckConfig(first_player_policy="fixed", fixed_first_player_index=0,
                  log_level=None, log_file_levels=[], monitors=[],
                  provider_call_custody="durable", conclusion=ConclusionPolicy(enabled=False))
    ),))
"""
    )
    payload = study_payload()
    payload["cells"] = [copy.deepcopy(payload["cells"][0])]
    payload["cells"][0]["assembly_run"] = "paid-then-unavailable"
    manifest = write_study(tmp_path / "study", payload=payload, assembly=source)
    prepared = prepare_study(manifest)
    execution = execute_prepared_study(
        manifest, prepared, select_study(prepared, all_groups=True), output_root=tmp_path / "runs"
    )
    observed = records(tmp_path / "runs")
    assert len(observed) == 1
    match = observed[0]["metadata"]["match"]
    assert match["cost"] is None
    assert match["known_cost_usd"] == pytest.approx(0.01)
    assert execution.as_dict()["usage"]["cost_usd"] == pytest.approx(0.01)
    assert execution.groups[0].cost_usd == pytest.approx(0.01)
    assembly = json.loads(next((tmp_path / "runs").rglob("assembly-execution.json")).read_text())
    assert assembly["usage"]["cost_usd"] == pytest.approx(0.01)
    assert inspect_provider_call_custody(tmp_path / "runs")["usage"]["cost_usd"] == pytest.approx(
        0.01
    )


def test_load_partial_study_prefix_and_reject_dishonest_completion(tmp_path):
    payload = study_payload()
    payload["execution_groups"].append({"id": "later", "phase": "p1", "entrypoint": "assembly.py"})
    for cell in copy.deepcopy(payload["cells"]):
        cell["id"] += "-later"
        cell["execution_group"] = "later"
        payload["cells"].append(cell)
    source = ASSEMBLY_SOURCE.replace(
        'return {"done": False, "information_level": self.information_level, "seed": seed}',
        'raise RuntimeError("first group failed")',
    )
    manifest = write_study(tmp_path / "study", payload=payload, assembly=source)
    prepared = prepare_study(manifest)
    with pytest.raises(StudyExecutionError) as captured:
        execute_prepared_study(
            manifest,
            prepared,
            select_study(prepared, all_groups=True),
            output_root=tmp_path / "runs",
        )
    path = captured.value.receipt_path
    loaded = load_study_execution(path)
    assert loaded.complete is False
    assert loaded.execution_group_ids == ("main", "later")
    assert len(loaded.groups) == 1
    data = json.loads(path.read_text())
    data["complete"] = True
    identity = {k: v for k, v in data.items() if k != "execution_sha256"}
    data["execution_sha256"] = sha256_json(identity)
    alternate = path.parent / "dishonest.json"
    alternate.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="every selected group"):
        load_study_execution(alternate)


def test_json_cli_is_clean_with_noisy_preparation_and_default_parallel_monitor(tmp_path):
    source = ASSEMBLY_SOURCE.replace(
        "from agentdeck import (",
        'print("authored preparation output")\nfrom agentdeck import (\n    AgentDeckConfig,',
    )
    source = source.replace("matches=2,", "matches=2, session=AgentDeckConfig(concurrency=2),")
    manifest = write_study(tmp_path / "study", assembly=source)
    inspected = run_cli("study", "inspect", str(manifest), "--json")
    plan = json.loads(inspected.stdout)["plan_sha256"]
    assert "authored preparation output" in inspected.stderr
    result = run_cli(
        "study",
        "run",
        str(manifest),
        "--all",
        "--approve",
        plan,
        "--output-root",
        str(tmp_path / "runs"),
        "--json",
    )
    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["data"]["execution"]["record_count"] == 4
    assert "Executing matches" in result.stderr
    assert envelope["data"]["receipt_path"] == "execution.json"
