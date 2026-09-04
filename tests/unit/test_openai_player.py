"""Unit tests for OpenAI GPTPlayer Responses API integration."""

import types

import pytest

from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.core.types import PromptBundle
from agentdeck.players.openai_player import GPTPlayer


class _DummyUsage:
    def __init__(
        self,
        input_tokens=100,
        output_tokens=20,
        total_tokens=120,
        reasoning_tokens=None,
    ):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        if reasoning_tokens is not None:
            self.output_tokens_details = types.SimpleNamespace(reasoning_tokens=reasoning_tokens)


class _DummyResponsesAPI:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


class _DummyClient:
    def __init__(self, response):
        self.responses = _DummyResponsesAPI(response)


class _DummyResponse:
    def __init__(self, output_text="ATTACK", usage=None, model="gpt-4o-mini", output=None):
        self.output_text = output_text
        self.usage = usage or _DummyUsage()
        self.model = model
        self.output = output or []


def _install_dummy_client(monkeypatch, response):
    def _fake_init_client(self):
        self.client = _DummyClient(response)

    monkeypatch.setattr(GPTPlayer, "_initialize_client", _fake_init_client)


def _build_player(monkeypatch, response, **kwargs):
    _install_dummy_client(monkeypatch, response)
    return GPTPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
        model="gpt-4o-mini",
        **kwargs,
    )


def test_openai_player_uses_responses_api_and_system_to_instructions(monkeypatch):
    response = _DummyResponse(output_text="ATTACK")
    player = _build_player(monkeypatch, response, top_p=0.9)

    messages = [
        {"role": "system", "content": "Rule A"},
        {"role": "user", "content": "Turn: 1"},
    ]
    text, metadata = player._make_api_call(messages)

    assert text == "ATTACK"
    kwargs = player.client.responses.last_kwargs
    assert kwargs is not None
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["store"] is False
    assert kwargs["instructions"] == "Rule A"
    assert kwargs["input"] == [{"role": "user", "content": "Turn: 1"}]
    assert kwargs["top_p"] == 0.9
    assert metadata["prompt_tokens"] == 100
    assert metadata["completion_tokens"] == 20


def test_openai_player_joins_multiple_system_messages(monkeypatch):
    response = _DummyResponse(output_text="ATTACK")
    player = _build_player(monkeypatch, response)
    messages = [
        {"role": "system", "content": "System 1"},
        {"role": "system", "content": "System 2"},
        {"role": "assistant", "content": "Prev"},
        {"role": "user", "content": "Now"},
    ]

    player._make_api_call(messages)
    kwargs = player.client.responses.last_kwargs

    assert kwargs["instructions"] == "System 1\n\nSystem 2"
    assert kwargs["input"] == [
        {"role": "assistant", "content": "Prev"},
        {"role": "user", "content": "Now"},
    ]


def test_openai_player_prompt_is_system_instruction_not_sdk_config(monkeypatch):
    response = _DummyResponse(output_text="ATTACK", model="gpt-5")
    player = _build_player(
        monkeypatch,
        response,
        prompt="Classify the current case.",
    )

    player._invoke_model(PromptBundle(text="Case text", blocks=[]), None)

    kwargs = player.client.responses.last_kwargs
    assert kwargs["instructions"] == "Classify the current case."
    assert "prompt" not in kwargs
    assert "prompt" not in player.config


def test_openai_player_omits_unset_temperature_and_records_that_configuration(
    monkeypatch,
):
    response = _DummyResponse(output_text="ATTACK", model="gpt-5")
    player = _build_player(monkeypatch, response, temperature=None)

    player._make_api_call([{"role": "user", "content": "Turn"}])

    kwargs = player.client.responses.last_kwargs
    assert "temperature" not in kwargs
    assert "temperature" not in player._pending_sdk_request["arguments"]
    assert player.temperature is None
    assert player.describe()["temperature"] is None


def test_openai_player_preserves_explicit_numeric_temperature(monkeypatch):
    response = _DummyResponse(output_text="ATTACK")
    player = _build_player(monkeypatch, response, temperature=0.25)

    player._make_api_call([{"role": "user", "content": "Turn"}])

    assert player.client.responses.last_kwargs["temperature"] == 0.25


def test_openai_player_remaps_token_limit_aliases(monkeypatch):
    response = _DummyResponse(output_text="ATTACK")
    player = _build_player(monkeypatch, response, max_completion_tokens=321)

    player._make_api_call([{"role": "user", "content": "Turn"}])
    kwargs = player.client.responses.last_kwargs

    assert kwargs["max_output_tokens"] == 321
    assert "max_tokens" not in kwargs
    assert "max_completion_tokens" not in kwargs


def test_openai_player_sets_max_output_tokens_from_max_tokens_arg(monkeypatch):
    response = _DummyResponse(output_text="ATTACK")
    player = _build_player(monkeypatch, response, max_tokens=222)

    player._make_api_call([{"role": "user", "content": "Turn"}])
    kwargs = player.client.responses.last_kwargs
    assert kwargs["max_output_tokens"] == 222


def test_openai_player_rejects_unsupported_config_keys(monkeypatch):
    response = _DummyResponse(output_text="ATTACK")
    player = _build_player(monkeypatch, response, n=2)

    with pytest.raises(ValueError, match="Unsupported OpenAI Responses API config key"):
        player._make_api_call([{"role": "user", "content": "Turn"}])


def test_openai_player_rejects_conflicting_token_limits(monkeypatch):
    response = _DummyResponse(output_text="ATTACK")
    player = _build_player(
        monkeypatch,
        response,
        max_tokens=100,
        max_output_tokens=200,
    )

    with pytest.raises(ValueError, match="Conflicting max token settings"):
        player._make_api_call([{"role": "user", "content": "Turn"}])


def test_openai_player_maps_usage_input_output_tokens(monkeypatch):
    response = _DummyResponse(
        output_text="ATTACK",
        usage=_DummyUsage(input_tokens=123, output_tokens=45, total_tokens=168),
        model="gpt-4o-mini-2026-01-01",
    )
    player = _build_player(monkeypatch, response)

    _, metadata = player._make_api_call([{"role": "user", "content": "Turn"}])

    assert metadata["tokens_used"] == 168
    assert metadata["prompt_tokens"] == 123
    assert metadata["completion_tokens"] == 45
    assert metadata["input_tokens"] == 123
    assert metadata["output_tokens"] == 45
    assert metadata["provider_model"] == "gpt-4o-mini-2026-01-01"


def test_openai_player_preserves_provider_reported_reasoning_usage(monkeypatch):
    response = _DummyResponse(
        output_text="ATTACK",
        usage=_DummyUsage(
            input_tokens=123,
            output_tokens=45,
            total_tokens=168,
            reasoning_tokens=32,
        ),
    )
    player = _build_player(monkeypatch, response)

    _, metadata = player._make_api_call([{"role": "user", "content": "Turn"}])

    assert metadata["completion_tokens"] == 45
    assert metadata["reasoning_usage"] == {
        "tokens": 32,
        "kind": "reasoning",
        "source": "openai.responses.usage.output_tokens_details.reasoning_tokens",
    }


def test_openai_player_keeps_missing_reasoning_usage_absent(monkeypatch):
    player = _build_player(monkeypatch, _DummyResponse(output_text="ATTACK"))

    _, metadata = player._make_api_call([{"role": "user", "content": "Turn"}])

    assert "reasoning_usage" not in metadata


def test_openai_player_extracts_text_from_output_fallback(monkeypatch):
    output_chunk = types.SimpleNamespace(type="output_text", text="POTION")
    output_item = types.SimpleNamespace(type="message", content=[output_chunk])
    response = _DummyResponse(output_text=None, output=[output_item])
    player = _build_player(monkeypatch, response)

    text, _ = player._make_api_call([{"role": "user", "content": "Turn"}])
    assert text == "POTION"


def test_openai_player_raises_when_no_text_output(monkeypatch):
    response = _DummyResponse(output_text=None, output=[])
    player = _build_player(monkeypatch, response)

    with pytest.raises(RuntimeError, match="returned no text output"):
        player._make_api_call([{"role": "user", "content": "Turn"}])


def test_openai_player_reports_bounded_incomplete_response_diagnostic(monkeypatch):
    response = _DummyResponse(output_text=None, output=[])
    response.status = "incomplete"
    response.incomplete_details = types.SimpleNamespace(reason="max_output_tokens")
    response.max_output_tokens = 384
    response.usage.output_tokens = 384
    response.usage.output_tokens_details = types.SimpleNamespace(reasoning_tokens=384)
    player = _build_player(monkeypatch, response)

    with pytest.raises(RuntimeError) as captured:
        player._make_api_call([{"role": "user", "content": "Turn"}])

    diagnostic = str(captured.value)
    assert "status=incomplete" in diagnostic
    assert "incomplete_reason=max_output_tokens" in diagnostic
    assert "output_tokens=384" in diagnostic
    assert "reasoning_tokens=384" in diagnostic
    assert "max_output_tokens=384" in diagnostic
    assert "Raw response" not in diagnostic
