"""Canonical incomplete Match coverage for rejected handshakes."""

import json
from pathlib import Path

import pytest

from agentdeck import AgentDeck, AgentDeckConfig, BatchStoppedError, TextRenderer
from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.core.types import EventType
from agentdeck.games.examples.fixed_damage import FixedDamageGame
from agentdeck.players.llm_player import LLMPlayer
from agentdeck.players.mock import MockPlayer


class RejectingHandshakePlayer(MockPlayer):
    def get_response(self, prompt: str) -> str:
        if getattr(self, "_active_phase", None) == "handshake":
            return '```json\n{"acao":"COOPERAR","justificativa":"teste"}\n```'
        return super().get_response(prompt)


class HandshakeOnlyGame(FixedDamageGame):
    def run(self, runtime, players):  # pragma: no cover - rejection must prevent this path
        raise AssertionError("game.run must not execute after a rejected handshake")


class UnavailableLLMPlayer(LLMPlayer):
    PROVIDER = "fixture"
    default_model = "fixture-unavailable"
    api_key_env_var = "UNUSED_FIXTURE_API_KEY"

    def _initialize_client(self) -> None:
        self.client = None

    def _make_api_call(self, messages):
        self._capture_sdk_request("fixture.responses.create", {"messages": messages})
        raise RuntimeError("technical failure without response")


class LifecycleCapture:
    def __init__(self) -> None:
        self.types: list[str] = []

    def _append(self, event) -> None:
        self.types.append(
            event.type.value if isinstance(event.type, EventType) else str(event.type)
        )

    def on_match_start(self, event) -> None:
        self._append(event)

    def on_player_handshake_start(self, event) -> None:
        self._append(event)

    def on_player_handshake_abort(self, event) -> None:
        self._append(event)

    def on_match_end(self, event) -> None:
        self._append(event)


def test_rejected_handshake_is_a_canonical_incomplete_match_and_batch_continues(tmp_path):
    capture = LifecycleCapture()
    config = AgentDeckConfig(
        seed=42,
        run_dir=tmp_path,
        concurrency=1,
        first_player_policy="fixed",
        fixed_first_player_index=0,
    )

    with AgentDeck(game=HandshakeOnlyGame(), session=config, spectators=[capture]) as deck:
        results = deck.play(
            [RejectingHandshakePlayer("Claude"), MockPlayer("Other")],
            matches=2,
        )
        records_dir = Path(deck.session.record_directory)

    assert len(results) == 2
    for result in results:
        assert result.winner is None
        assert result.metadata["outcome"] == "aborted"
        assert result.metadata["abort_reason"] == "handshake_rejected"
        assert result.metadata["failing_player"] == "Claude"
        assert result.metadata["handshake_completed"] is False
        assert result.metadata["turns"] == 0
        assert result.metadata["cost"] == 0.0
        assert result.final_state["health"] == {"Claude": 100, "Other": 100}

        event_types = [
            event.type.value if isinstance(event.type, EventType) else event.type
            for event in result.events
        ]
        assert event_types == [
            EventType.MATCH_START.value,
            EventType.PLAYER_HANDSHAKE_START.value,
            EventType.PLAYER_HANDSHAKE_ABORT.value,
            EventType.MATCH_END.value,
        ]
        abort_event = result.events[2]
        assert abort_event.data["response_text"].startswith("```json")
        assert abort_event.data["prompt_text"]
        assert abort_event.data["accepted"] is False

    assert (
        capture.types
        == [
            EventType.MATCH_START.value,
            EventType.PLAYER_HANDSHAKE_START.value,
            EventType.PLAYER_HANDSHAKE_ABORT.value,
            EventType.MATCH_END.value,
        ]
        * 2
    )

    record_paths = sorted(records_dir.glob("match_*.json"))
    assert len(record_paths) == 2
    for record_path in record_paths:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        assert record["metadata"]["match"]["outcome"] == "aborted"
        assert record["metadata"]["match"]["abort_reason"] == "handshake_rejected"
        assert record["metadata"]["match"]["turns"] == 0
        assert [event["type"] for event in record["events"]] == [
            EventType.PLAYER_HANDSHAKE_START.value,
            EventType.PLAYER_HANDSHAKE_ABORT.value,
        ]
        assert record["events"][1]["data"]["response_text"].startswith("```json")


def test_exhausted_handshake_attempts_are_canonical_unavailable_matches(tmp_path):
    capture = LifecycleCapture()
    config = AgentDeckConfig(
        seed=91,
        run_dir=tmp_path,
        concurrency=1,
        first_player_policy="fixed",
        fixed_first_player_index=0,
    )
    unavailable = UnavailableLLMPlayer(
        "Claude",
        api_key="provider-free",
        controller=ActionOnlyController(),
        renderer=TextRenderer(),
        max_retries=1,
        retry_delay=0.0,
    )

    with AgentDeck(game=HandshakeOnlyGame(), session=config, spectators=[capture]) as deck:
        results = deck.play([unavailable, MockPlayer("Other")], matches=2)
        records_dir = Path(deck.session.record_directory)

    assert len(results) == 2
    for result in results:
        assert result.winner is None
        assert result.metadata["outcome"] == "unavailable"
        assert result.metadata["abort_reason"] == "provider_response_unavailable"
        assert result.metadata["failing_player"] == "Claude"
        assert result.metadata["handshake_completed"] is False
        assert result.metadata["response_available"] is False
        assert result.metadata["turns"] == 0
        assert result.metadata["cost"] is None
        assert result.metadata["cost_status"] == "unavailable"

        event_types = [
            event.type.value if isinstance(event.type, EventType) else event.type
            for event in result.events
        ]
        assert event_types == [
            EventType.MATCH_START.value,
            EventType.PLAYER_HANDSHAKE_START.value,
            EventType.PLAYER_HANDSHAKE_ABORT.value,
            EventType.MATCH_END.value,
        ]
        abort = result.events[2].data
        assert abort["response_text"] is None
        assert abort["usage_info"] is None
        assert abort["controller_metadata"]["response_available"] is False
        assert abort["retries"] == 1
        assert len(abort["attempt_durations"]) == 2
        assert abort["provider_call"]["sdk_response"] is None
        assert abort["provider_call"]["custody"]["mode"] == "volatile"
        assert [attempt["outcome"] for attempt in abort["provider_call"]["attempts"]] == [
            "failed",
            "failed",
        ]

    assert (
        capture.types
        == [
            EventType.MATCH_START.value,
            EventType.PLAYER_HANDSHAKE_START.value,
            EventType.PLAYER_HANDSHAKE_ABORT.value,
            EventType.MATCH_END.value,
        ]
        * 2
    )

    record_paths = sorted(records_dir.glob("match_*.json"))
    assert len(record_paths) == 2
    for record_path in record_paths:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        metadata = record["metadata"]["match"]
        assert metadata["outcome"] == "unavailable"
        assert metadata["cost"] is None
        abort = next(
            event for event in record["events"] if event["type"] == "player_handshake_abort"
        )
        assert abort["data"]["response_text"] is None
        assert len(abort["data"]["provider_call"]["attempts"]) == 2


def test_unavailable_handshake_can_stop_batch_after_canonical_record(tmp_path):
    capture = LifecycleCapture()
    config = AgentDeckConfig(
        seed=91,
        run_dir=tmp_path,
        concurrency=1,
        unavailable_match_policy="stop_batch",
        first_player_policy="fixed",
        fixed_first_player_index=0,
    )
    unavailable = UnavailableLLMPlayer(
        "Claude",
        api_key="provider-free",
        controller=ActionOnlyController(),
        renderer=TextRenderer(),
        max_retries=0,
        retry_delay=0.0,
    )

    with AgentDeck(game=HandshakeOnlyGame(), session=config, spectators=[capture]) as deck:
        with pytest.raises(BatchStoppedError) as stopped:
            deck.play([unavailable, MockPlayer("Other")], matches=3)
        records_dir = Path(deck.session.record_directory)

    assert stopped.value.outcome == "unavailable"
    assert stopped.value.completed_matches == 1
    assert stopped.value.planned_matches == 3
    record_paths = sorted(records_dir.glob("match_*.json"))
    assert len(record_paths) == 1
    record = json.loads(record_paths[0].read_text(encoding="utf-8"))
    assert record["match_id"] == stopped.value.match_id
    assert record["metadata"]["match"]["outcome"] == "unavailable"
    assert capture.types == [
        EventType.MATCH_START.value,
        EventType.PLAYER_HANDSHAKE_START.value,
        EventType.PLAYER_HANDSHAKE_ABORT.value,
        EventType.MATCH_END.value,
    ]


def test_stop_batch_unavailable_policy_requires_serial_execution():
    with pytest.raises(ValueError, match="requires concurrency=1"):
        AgentDeckConfig(concurrency=2, unavailable_match_policy="stop_batch")
