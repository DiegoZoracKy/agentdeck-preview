"""Unit tests for GeminiPlayer credential resolution."""

from __future__ import annotations

import base64
import json
import sys
import types

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

    vertexai_module = types.ModuleType("vertexai")

    def fake_init(**kwargs):
        captured["init_kwargs"] = kwargs

    vertexai_module.init = fake_init

    generative_models_module = types.ModuleType("vertexai.generative_models")

    class DummyGenerativeModel:
        def __init__(self, model):
            captured["model"] = model

    generative_models_module.GenerativeModel = DummyGenerativeModel

    monkeypatch.setitem(sys.modules, "vertexai", vertexai_module)
    monkeypatch.setitem(sys.modules, "vertexai.generative_models", generative_models_module)

    fake_credentials = object()

    def fake_from_service_account_info(info):
        captured["service_account_info"] = info
        return fake_credentials

    monkeypatch.setattr(
        service_account.Credentials,
        "from_service_account_info",
        staticmethod(fake_from_service_account_info),
    )

    GeminiPlayer(
        name="Gemini",
        model="gemini-2.5-flash",
        location="us-central1",
        controller=ActionOnlyController(),
    )

    assert captured["service_account_info"] == payload
    assert captured["init_kwargs"]["project"] == payload["project_id"]
    assert captured["init_kwargs"]["location"] == "us-central1"
    assert captured["init_kwargs"]["credentials"] is fake_credentials
    assert captured["model"] == "gemini-2.5-flash"


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
