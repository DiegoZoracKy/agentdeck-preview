"""Exercise real SDK transports: hidden retries must not bypass attempt custody."""

import httpx
import pytest

from agentdeck import ActionOnlyController, ClaudePlayer, GeminiPlayer, GPTPlayer
from agentdeck.core.types import PlayerResponseUnavailableError


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
@pytest.mark.parametrize("retries", [0, 2])
def test_each_http_attempt_matches_the_declared_retry_budget(monkeypatch, provider, retries):
    dispatched = []
    http = httpx

    def unavailable(request):
        dispatched.append(request)
        return http.Response(
            503,
            json={
                "error": {
                    "message": "injected unavailable transport",
                    "status": "UNAVAILABLE",
                    "code": 503,
                }
            },
        )

    transport = httpx.MockTransport(unavailable)
    kwargs = {
        "name": "Probe",
        "model": "fixture-model",
        "controller": ActionOnlyController(),
        "max_retries": retries,
        "retry_delay": 0,
        "max_tokens": 10,
    }
    if provider == "openai":
        import openai

        original = openai.OpenAI

        def client(**options):
            return original(**options, http_client=httpx.Client(transport=transport))

        monkeypatch.setattr(openai, "OpenAI", client)
        player = GPTPlayer(api_key="provider-free-fixture", **kwargs)
    elif provider == "anthropic":
        import anthropic
        from anthropic import _base_client

        original = anthropic.Anthropic
        http = getattr(_base_client, "httpx2", httpx)
        transport = http.MockTransport(unavailable)

        def client(**options):
            return original(**options, http_client=http.Client(transport=transport))

        monkeypatch.setattr(anthropic, "Anthropic", client)
        player = ClaudePlayer(api_key="provider-free-fixture", **kwargs)
    else:
        from google import genai
        from google.auth.credentials import AnonymousCredentials

        original = genai.Client
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS_B64", raising=False)

        def client(**options):
            options["credentials"] = AnonymousCredentials()
            options["credentials"].token = "provider-free-fixture"
            options["http_options"] = {
                **options.get("http_options", {}),
                "client_args": {"transport": transport},
            }
            return original(**options)

        monkeypatch.setattr(genai, "Client", client)
        player = GeminiPlayer(
            project_id="provider-free-fixture",
            generation_config={"automatic_function_calling": {"disable": True}},
            **kwargs,
        )
    try:
        with pytest.raises(PlayerResponseUnavailableError) as captured:
            player.get_response("Reply OK.")
        assert len(dispatched) == retries + 1, str(captured.value.__cause__)
        entries = player.provider_call_journal.entries()
        assert len(entries) == retries + 1
        assert [entry["attempt_index"] for entry in entries] == list(range(1, retries + 2))
        assert len({entry["call_id"] for entry in entries}) == 1
        assert all(entry["state"] == "attempt_failed" for entry in entries)
    finally:
        player.client.close()
