"""
Unit tests for LLMPlayer lifecycle phases.

Ensures handshake, decide (turn), conclude, and clone work correctly
per SPEC-PLAYER v1.2.0.
"""

import copy
import json

import pytest

from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.core.conversation import ConversationManager
from agentdeck.core.types import (
    HandshakeContext,
    MatchContext,
    MatchResult,
    TurnContext,
)
from agentdeck.games.examples.fixed_damage.game import FixedDamageGame
from agentdeck.players import ClaudePlayer, GeminiPlayer, GPTPlayer
from agentdeck.players.llm_player import LLMPlayer
from agentdeck.renderers.text_renderer import TextRenderer


class DummyLLMPlayer(LLMPlayer):
    """Minimal concrete LLM player for testing conclude()."""

    default_model = "dummy-model"
    api_key_env_var = "DUMMY_API_KEY"

    def _get_api_key_from_env(self):
        return "dummy"

    def _initialize_client(self):
        """Skip client initialisation for tests."""
        self.last_bundle = None

    def _make_api_call(self, messages):
        raise NotImplementedError("Not used in tests")

    def _invoke_model(self, bundle, turn_context):
        self.last_bundle = bundle
        return "Well played!", {}


class AuditedDummyLLMPlayer(LLMPlayer):
    """Provider-shaped fake that exercises canonical call provenance."""

    PROVIDER = "audited-dummy"
    default_model = "dummy-model"
    api_key_env_var = "DUMMY_API_KEY"

    def _get_api_key_from_env(self):
        return "dummy"

    def _initialize_client(self):
        self.responses = []
        self.requests = []

    def _make_api_call(self, messages):
        arguments = {
            "model": self.model,
            "messages": copy.deepcopy(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        self.requests.append(arguments)
        self._capture_sdk_request("dummy.responses.create", arguments)
        outcome = self.responses.pop(0) if self.responses else "ACTION: ATTACK"
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, {
            "tokens_used": 12,
            "prompt_tokens": 9,
            "completion_tokens": 3,
            "cost": 0.001,
            "model": self.model,
            "provider_model": "dummy-model-2026-08-12",
            "provider_response_id": "response-123",
            "stop_reason": "completed",
        }


def _make_match_result(winner: str = "Alice"):
    return MatchResult(
        winner=winner,
        final_state={"health": {"Alice": 20, "Bob": 0}},
        events=[],
        seed=123,
        metadata={"game": "FixedDamageGame"},
    )


def _make_match_context():
    return MatchContext(
        match_id="match-1",
        players=["Alice", "Bob"],
        game_name="FixedDamageGame",
        seed=123,
        handshake_completed=True,
        rng_info={},
    )


def test_llmplayer_conclude_uses_default_template():
    """LLMPlayer.conclude should render default template and return reflection."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
    )

    reflection = player.conclude(_make_match_result("Alice"), match_context=_make_match_context())

    # Reflection text returned
    assert reflection == "Well played!"

    # Ensure prompt bundle captured and includes default template content
    bundle = player.last_bundle
    assert bundle is not None
    assert bundle.metadata["phase"] == "conclusion"
    assert "=== Match Concluded ===" in bundle.text
    assert "You ( Alice ) won the match." in bundle.text


def test_llmplayer_conclude_formats_outcome_for_loss():
    """Outcome string should reflect opponent victory when player loses."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
    )

    player.conclude(_make_match_result("Bob"), match_context=_make_match_context())
    bundle = player.last_bundle
    assert "Bob won the match." in bundle.text


def test_llmplayer_conclude_handles_draw():
    """Outcome string should indicate draw when no winner."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
    )

    match_result = _make_match_result(winner=None)
    player.conclude(match_result, match_context=_make_match_context())
    bundle = player.last_bundle
    assert "Draw" in bundle.text


def test_llmplayer_conclude_hides_engine_internal_state_keys():
    """Conclusion prompt must not expose engine bookkeeping fields."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
    )

    match_result = MatchResult(
        winner="Bob",
        final_state={
            "health": {"Alice": 0, "Bob": 20},
            "potions": {"Alice": 0, "Bob": 0},
            "_turn_count": 39,
            "_first_player_idx": 1,
        },
        events=[],
        seed=123,
        metadata={"game": "FixedDamageGame"},
    )

    player.conclude(match_result, match_context=_make_match_context())
    bundle = player.last_bundle
    assert "_turn_count" not in bundle.text
    assert "_first_player_idx" not in bundle.text
    assert "Turn Count" not in bundle.text
    assert "First Player Idx" not in bundle.text


# Test handshake and decide phases are covered by integration tests
# Handshake is covered by integration tests; keep a focused decide() regression here


def test_llmplayer_decide_preserves_usage_info_in_action_metadata():
    """Turn actions should carry per-call usage_info into downstream observers."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
    )
    usage_info = {
        "tokens": 42,
        "prompt_tokens": 30,
        "completion_tokens": 12,
        "cost": 0.0002,
        "model": "dummy-model",
        "call_id": "call-123",
    }

    def _fake_get_response(prompt):
        player.last_usage_info = usage_info
        return "ACTION: ATTACK"

    player.get_response = _fake_get_response  # type: ignore[method-assign]

    action = player.decide(
        game_state={"health": {"Alice": 100, "Bob": 100}},
        turn_context=TurnContext(
            match_id="match-1",
            turn_number=1,
            turn_index=0,
            player="Alice",
            started_at=0.0,
            duration=0.0,
        ),
    )

    assert action.action == "ATTACK"
    assert action.metadata["usage_info"] == usage_info
    assert action.metadata["raw_prompt"]


def test_llmplayer_handshake_uses_game_default_template_and_frontloads_action_format():
    controller = ActionOnlyController()
    controller.bind_game(FixedDamageGame())
    player = DummyLLMPlayer(
        name="Alice",
        controller=controller,
        api_key="dummy",
    )
    context = HandshakeContext(
        match_id="match-1",
        player_name="Alice",
        opponent_names=["Bob"],
        game_name="FixedDamageGame",
        seed=123,
        metadata={
            "game_instructions": "Rules here",
            "default_handshake_template": (
                "{game_instructions}\n\n"
                "Gameplay format:\n{controller_format}\n\n"
                "{handshake_controller_format}"
            ),
        },
    )

    bundle = player.build_handshake_bundle(context)

    assert bundle.metadata["phase"] == "handshake"
    assert bundle.metadata["template_id"] == "game_default_handshake"
    assert "Rules here" in bundle.text
    assert "Gameplay format:" in bundle.text
    assert "Respond with: ACTION: <action>" in bundle.text
    assert "Allowed actions: ATTACK, POTION" in bundle.text
    assert (
        "Reply with exactly 'OK' and nothing else if you understand and are ready to begin."
        in bundle.text
    )


# Test clone()


def test_llmplayer_clone():
    """Test clone() creates independent copy."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        renderer=TextRenderer(),
        api_key="dummy",
        temperature=0.5,
    )

    # Clone
    cloned = player.clone()

    # Should be independent instance
    assert cloned is not player
    assert cloned.name == player.name
    assert cloned.temperature == player.temperature

    # Controller should be deep-copied
    assert cloned.controller is not player.controller

    # Renderer should be deep-copied
    assert cloned.renderer is not player.renderer


def test_llmplayer_describe():
    """Test describe() returns metadata dict."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
        temperature=0.7,
    )

    desc = player.describe()

    assert desc["name"] == "Alice"
    assert desc["model"] == "dummy-model"
    assert desc["temperature"] == 0.7
    assert "controller" in desc
    assert "renderer" in desc
    assert "templates" in desc  # prompt_builder is rendered as templates


def test_llmplayer_describe_with_disabled_conclusion_template():
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
        conclusion_template=None,
    )

    desc = player.describe()

    assert "templates" in desc
    assert desc["templates"]["conclusion"] is None


def test_provider_players_require_explicit_model():
    """Provider-backed players must be constructed with an explicit model name."""
    with pytest.raises(ValueError):
        GPTPlayer(name="Alice", controller=ActionOnlyController(), api_key="dummy")

    with pytest.raises(ValueError):
        ClaudePlayer(name="Bob", controller=ActionOnlyController(), api_key="dummy")

    with pytest.raises(ValueError):
        GeminiPlayer(
            name="Charlie",
            controller=ActionOnlyController(),
            project_id="proj",
            location="us-central1",
        )


def test_provider_players_define_provider_constants():
    """SPEC-LLM PI1 / SPEC-PLAYER LP1: shipped provider players declare PROVIDER constants."""
    assert GPTPlayer.PROVIDER == "openai"
    assert ClaudePlayer.PROVIDER == "anthropic"
    assert GeminiPlayer.PROVIDER == "google"


def test_PCA1_PCA2_claude_player_captures_effective_sdk_arguments(monkeypatch):
    """Claude API calls should include a high max_tokens fallback when unset."""

    class _DummyUsage:
        input_tokens = 10
        output_tokens = 20

    class _DummyContent:
        text = "ACTION: ATTACK"

    class _DummyResponse:
        content = [_DummyContent()]
        usage = _DummyUsage()

    class _DummyMessagesAPI:
        def __init__(self):
            self.last_kwargs = None

        def create(self, **kwargs):
            self.last_kwargs = kwargs
            return _DummyResponse()

    class _DummyClient:
        def __init__(self):
            self.messages = _DummyMessagesAPI()

    def _fake_init_client(self):
        self.client = _DummyClient()

    monkeypatch.setattr(ClaudePlayer, "_initialize_client", _fake_init_client)

    player = ClaudePlayer(
        name="Bob",
        controller=ActionOnlyController(),
        api_key="dummy",
        model="claude-haiku-4.5-latest",
    )

    player._make_api_call([{"role": "user", "content": "test"}])
    assert (
        player.client.messages.last_kwargs["max_tokens"]
        == ClaudePlayer.REQUIRED_MAX_TOKENS_FALLBACK
    )
    assert player._pending_sdk_request["method"] == "anthropic.messages.create"
    assert player._pending_sdk_request["arguments"] == player.client.messages.last_kwargs
    assert player._effective_max_tokens_for_request() == ClaudePlayer.REQUIRED_MAX_TOKENS_FALLBACK


def test_claude_player_preserves_explicit_max_tokens(monkeypatch):
    """Claude API call should honor explicit max_tokens when provided."""

    class _DummyUsage:
        input_tokens = 10
        output_tokens = 20

    class _DummyContent:
        text = "ACTION: ATTACK"

    class _DummyResponse:
        content = [_DummyContent()]
        usage = _DummyUsage()

    class _DummyMessagesAPI:
        def __init__(self):
            self.last_kwargs = None

        def create(self, **kwargs):
            self.last_kwargs = kwargs
            return _DummyResponse()

    class _DummyClient:
        def __init__(self):
            self.messages = _DummyMessagesAPI()

    def _fake_init_client(self):
        self.client = _DummyClient()

    monkeypatch.setattr(ClaudePlayer, "_initialize_client", _fake_init_client)

    player = ClaudePlayer(
        name="Bob",
        controller=ActionOnlyController(),
        api_key="dummy",
        model="claude-haiku-4.5-latest",
        max_tokens=1234,
    )

    player._make_api_call([{"role": "user", "content": "test"}])
    assert player.client.messages.last_kwargs["max_tokens"] == 1234
    assert player._effective_max_tokens_for_request() == 1234


def test_reset_conversation_clears_conversation_manager():
    """reset_conversation should clear both local and bound conversation history."""
    player = DummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
    )

    player._local_history.append({"role": "user", "content": "hi"})
    manager = ConversationManager(player_name=player.name)
    manager.append("user", "Hello")
    manager.append("assistant", "World")
    player.bind_conversation_manager(manager)

    player.reset_conversation()

    assert player._local_history == []
    assert manager.history() == []


def _manager_with_two_exchanges(player_name="Alice"):
    manager = ConversationManager(player_name=player_name)
    manager.append("user", "Handshake rules", phase="handshake", exchange_id="handshake-0")
    manager.append("assistant", "READY", phase="handshake", exchange_id="handshake-0")
    manager.append("user", "Turn one view", phase="turn", exchange_id="turn-1")
    manager.append("assistant", "ACTION: ATTACK", phase="turn", exchange_id="turn-1")
    return manager


def test_CTA2_PCA4_PCA5_provider_call_records_exact_context_and_sdk_arguments():
    player = AuditedDummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
        temperature=0.25,
        max_tokens=128,
        prompt="System rules",
    )
    manager = _manager_with_two_exchanges()
    player.bind_conversation_manager(manager)

    assert player.get_response("Turn two view") == "ACTION: ATTACK"

    call = player.last_provider_call
    assert call["context_selection"]["policy"]["id"] == "full_history"
    assert call["context_selection"]["selected_history_messages"] == 4
    assert call["context_selection"]["omitted_message_ids"] == []
    assert call["composed_input"]["messages"] == [
        {"role": "system", "content": "System rules"},
        {"role": "user", "content": "Handshake rules"},
        {"role": "assistant", "content": "READY"},
        {"role": "user", "content": "Turn one view"},
        {"role": "assistant", "content": "ACTION: ATTACK"},
        {"role": "user", "content": "Turn two view"},
    ]
    assert call["sdk_request"]["assurance"] == "sent_to_official_sdk"
    assert call["sdk_request"]["arguments"] == player.requests[0]
    assert call["sdk_response"]["provider_model"] == "dummy-model-2026-08-12"
    assert call["sdk_response"]["response_id"] == "response-123"
    json.dumps(call, allow_nan=False)
    assert call["attempts"] == [
        {
            "attempt": 1,
            "started_at_unix_ns": call["attempts"][0]["started_at_unix_ns"],
            "duration_ms": call["attempts"][0]["duration_ms"],
            "outcome": "completed",
            "sdk_request": call["sdk_request"],
        }
    ]


def test_CTA1_handshake_plus_recent_policy_declares_selected_and_omitted_history():
    player = AuditedDummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
        context_policy={"id": "handshake_plus_recent", "parameters": {"recent_count": 2}},
    )
    manager = _manager_with_two_exchanges()
    manager.append("user", "Turn two view", phase="turn", exchange_id="turn-2")
    manager.append("assistant", "ACTION: POTION", phase="turn", exchange_id="turn-2")
    player.bind_conversation_manager(manager)

    player.get_response("Turn three view")
    selection = player.last_provider_call["context_selection"]

    assert player.describe()["context_policy"] == {
        "id": "handshake_plus_recent",
        "version": "1",
        "parameters": {"recent_count": 2},
    }
    assert selection["selected_message_ids"] == [
        "handshake-0-user",
        "handshake-0-assistant",
        "turn-2-user",
        "turn-2-assistant",
    ]
    assert selection["omitted_message_ids"] == ["turn-1-user", "turn-1-assistant"]
    assert [
        message["content"] for message in player.last_provider_call["composed_input"]["messages"]
    ] == [
        "Handshake rules",
        "READY",
        "Turn two view",
        "ACTION: POTION",
        "Turn three view",
    ]


def test_CTA3_player_contexts_do_not_cross_leak():
    alice = AuditedDummyLLMPlayer(name="Alice", controller=ActionOnlyController(), api_key="dummy")
    bob = AuditedDummyLLMPlayer(name="Bob", controller=ActionOnlyController(), api_key="dummy")
    alice_manager = ConversationManager(player_name="Alice")
    alice_manager.append("user", "Alice private value: 7", phase="turn")
    bob_manager = ConversationManager(player_name="Bob")
    bob_manager.append("user", "Bob private value: 3", phase="turn")
    alice.bind_conversation_manager(alice_manager)
    bob.bind_conversation_manager(bob_manager)

    alice.get_response("Alice current turn")
    bob.get_response("Bob current turn")

    alice_payload = str(alice.last_provider_call["sdk_request"]["arguments"])
    bob_payload = str(bob.last_provider_call["sdk_request"]["arguments"])
    assert "Bob private value" not in alice_payload
    assert "Alice private value" not in bob_payload


def test_PCA3_retry_history_records_every_attempt_without_hiding_failed_request(monkeypatch):
    monkeypatch.setattr("agentdeck.players.llm_player.time.sleep", lambda _seconds: None)
    player = AuditedDummyLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        api_key="dummy",
        max_retries=2,
        retry_delay=0.01,
    )
    player.responses = [RuntimeError("temporary provider failure"), "ACTION: ATTACK"]

    player.get_response("Current turn")

    attempts = player.last_provider_call["attempts"]
    assert [attempt["outcome"] for attempt in attempts] == ["failed", "completed"]
    assert attempts[0]["error"]["type"] == "RuntimeError"
    assert attempts[0]["sdk_request"]["arguments"] == attempts[1]["sdk_request"]["arguments"]
    assert player.last_retries == 1


def test_reset_removes_prior_match_context_from_next_provider_call():
    player = AuditedDummyLLMPlayer(name="Alice", controller=ActionOnlyController(), api_key="dummy")
    manager = ConversationManager(player_name="Alice")
    manager.append("user", "Secret from prior match", phase="turn")
    player.bind_conversation_manager(manager)
    player.reset_conversation()

    player.get_response("Fresh match")

    assert player.last_provider_call["context_selection"]["available_history_messages"] == 0
    assert "Secret from prior match" not in str(player.last_provider_call["sdk_request"])
