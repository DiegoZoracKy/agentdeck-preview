"""Unit tests for GeminiPlayer credential resolution and request wiring."""

from __future__ import annotations

import base64
import json

import pytest
from google.oauth2 import service_account

from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.players.google_player import GeminiPlayer


def _service_account_payload() -> dict:
    return {
        "type": "service_account",
        "project_id": "agentdeck-gcp-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
        "client_email": "agentdeck@test-project.iam.gserviceaccount.com",
        "client_id": "1234567890",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def _encoded_service_account(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def test_gemini_player_infers_project_id_from_b64_credentials(monkeypatch):
    payload = _service_account_payload()
    monkeypatch.delenv("VERTEX_PROJECT_ID", raising=False)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS_B64", _encoded_service_account(payload))
    monkeypatch.setattr(
        GeminiPlayer,
        "_initialize_client",
        lambda self: setattr(self, "client", object()),
    )

    player = GeminiPlayer(
        name="Gemini",
        model="gemini-2.5-flash",
        location="us-central1",
        controller=ActionOnlyController(),
    )

    assert player._project_id == payload["project_id"]
    assert player._service_account_info == payload


def test_gemini_player_passes_b64_credentials_to_vertex_init(monkeypatch):
    payload = _service_account_payload()
    monkeypatch.delenv("VERTEX_PROJECT_ID", raising=False)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS_B64", _encoded_service_account(payload))

    captured = {}

    fake_credentials = object()

    def fake_from_service_account_info(info, scopes=None):
        captured["service_account_info"] = info
        captured["scopes"] = scopes
        return fake_credentials

    monkeypatch.setattr(
        service_account.Credentials,
        "from_service_account_info",
        staticmethod(fake_from_service_account_info),
    )
    import google.genai

    class DummyClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

    monkeypatch.setattr(google.genai, "Client", DummyClient)

    GeminiPlayer(
        name="Gemini",
        model="gemini-2.5-flash",
        location="us-central1",
        controller=ActionOnlyController(),
    )

    assert captured["service_account_info"] == payload
    assert captured["scopes"] == [GeminiPlayer._VERTEX_SCOPE]
    assert captured["client_kwargs"]["vertexai"] is True
    assert captured["client_kwargs"]["project"] == payload["project_id"]
    assert captured["client_kwargs"]["location"] == "us-central1"
    assert captured["client_kwargs"]["credentials"] is fake_credentials


def test_gemini_player_rejects_invalid_b64_credentials(monkeypatch):
    monkeypatch.delenv("VERTEX_PROJECT_ID", raising=False)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS_B64", "not-valid-base64")

    with pytest.raises(
        ValueError,
        match="GOOGLE_APPLICATION_CREDENTIALS_B64 must be valid base64-encoded JSON",
    ):
        GeminiPlayer(
            name="Gemini",
            model="gemini-2.5-flash",
            location="us-central1",
            controller=ActionOnlyController(),
        )


def test_gemini_player_passes_generation_config_to_google_sdk(monkeypatch):
    monkeypatch.setenv("VERTEX_PROJECT_ID", "agentdeck-gcp-project")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS_B64", raising=False)

    captured = {}

    class DummyUsage:
        prompt_token_count = 12
        candidates_token_count = 4
        total_token_count = 16

    class DummyResponse:
        text = "ACTION: ATTACK"
        usage_metadata = DummyUsage()

    class DummyModels:
        def generate_content(self, **kwargs):
            captured["generate_kwargs"] = kwargs
            return DummyResponse()

    def fake_init_client(self):
        self.client = type("DummyClient", (), {"models": DummyModels()})()

    monkeypatch.setattr(GeminiPlayer, "_initialize_client", fake_init_client)

    player = GeminiPlayer(
        name="Gemini",
        model="gemini-2.5-flash",
        location="us-central1",
        controller=ActionOnlyController(),
        generation_config={"thinking_config": {"thinking_budget": 0}},
    )

    response_text, metadata = player._make_api_call(
        [
            {"role": "system", "content": "Follow the format exactly."},
            {"role": "user", "content": "Reply with ACTION: ATTACK"},
            {"role": "assistant", "content": "ACTION: ATTACK"},
            {"role": "user", "content": "Reply with ACTION: POTION"},
        ]
    )

    assert response_text == "ACTION: ATTACK"
    assert captured["generate_kwargs"]["model"] == "gemini-2.5-flash"
    contents = captured["generate_kwargs"]["contents"]
    assert [content.role for content in contents] == ["user", "model", "user"]
    assert contents[0].parts[0].text == "Reply with ACTION: ATTACK"
    assert contents[1].parts[0].text == "ACTION: ATTACK"
    assert contents[2].parts[0].text == "Reply with ACTION: POTION"
    config = captured["generate_kwargs"]["config"]
    assert config.temperature == 1.0
    assert config.thinking_config.thinking_budget == 0
    assert config.system_instruction == "Follow the format exactly."
    assert player._pending_sdk_request["method"] == "google.genai.models.generate_content"
    assert player._pending_sdk_request["assurance"] == "sent_to_official_sdk"
    assert player._pending_sdk_request["arguments"]["model"] == "gemini-2.5-flash"
    assert metadata["prompt_tokens"] == 12
    assert metadata["completion_tokens"] == 4
    assert metadata["tokens_used"] == 16


def test_gemini_player_prices_candidates_and_thoughts_as_output(monkeypatch):
    monkeypatch.setenv("VERTEX_PROJECT_ID", "agentdeck-gcp-project")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS_B64", raising=False)

    captured = {}

    class DummyUsage:
        prompt_token_count = 12
        candidates_token_count = 4
        thoughts_token_count = 6
        total_token_count = 22

    class DummyResponse:
        text = "ACTION: ATTACK"
        usage_metadata = DummyUsage()

    class DummyModels:
        def generate_content(self, **kwargs):
            return DummyResponse()

    def fake_init_client(self):
        self.client = type("DummyClient", (), {"models": DummyModels()})()

    def fake_calculate_cost(**kwargs):
        captured["pricing"] = kwargs
        return 0.123

    monkeypatch.setattr(GeminiPlayer, "_initialize_client", fake_init_client)
    monkeypatch.setattr("agentdeck.players.google_player.calculate_cost", fake_calculate_cost)
    player = GeminiPlayer(
        name="Gemini",
        model="gemini-2.5-flash",
        controller=ActionOnlyController(),
    )

    _, metadata = player._make_api_call([{"role": "user", "content": "Turn"}])

    assert captured["pricing"]["prompt_tokens"] == 12
    assert captured["pricing"]["completion_tokens"] == 10
    assert metadata["completion_tokens"] == 10
    assert metadata["tokens_used"] == 22
    assert metadata["reasoning_usage"] == {
        "tokens": 6,
        "kind": "thinking",
        "source": "google.generate_content.usage_metadata.thoughts_token_count",
    }
