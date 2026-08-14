"""
Unit tests for LLMPlayer lifecycle phases.

Ensures handshake, decide (turn), conclude, and clone work correctly
per SPEC-PLAYER v1.2.0.
"""

import pytest

from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.core.conversation import ConversationManager
from agentdeck.core.types import (
    ActionParseError,
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


class AuditLLMPlayer(LLMPlayer):
    """Provider double that exercises the real LLMPlayer audit path."""

    PROVIDER = "audit"
    default_model = "audit-model"
    api_key_env_var = "AUDIT_API_KEY"

    def _get_api_key_from_env(self):
        return "dummy"

    def _initialize_client(self):
        self.test_response = "ACTION: ATTACK"
        self.test_stop_reason = "completed"
        self.test_response_complete = True

    def _make_api_call(self, messages):
        arguments = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        self._capture_sdk_request("audit.responses.create", arguments)
        return self.test_response, {
            "tokens_used": 12,
            "prompt_tokens": 10,
            "completion_tokens": 2,
            "cost": 0.001,
            "model": self.model,
            "provider_model": "audit-model-2026-08-14",
            "provider_response_id": "response-1",
            "stop_reason": self.test_stop_reason,
            "response_complete": self.test_response_complete,
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
    assert "Respond with: ACTION: <your_action>" in action.metadata["raw_prompt"]
    assert action.metadata["controller_format"] == "Respond with: ACTION: <your_action>"


def test_no_history_policy_keeps_current_decision_protocol_explicit():
    player = AuditLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        context_policy="no_history",
    )
    manager = ConversationManager(player_name="Alice")
    manager.record_turn(
        user_message="handshake prompt",
        assistant_message="OK",
        turn_context=None,
        prompt_metadata=[],
        response_metadata={},
        phase="handshake",
    )
    player.bind_conversation_manager(manager)

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

    provider_call = action.metadata["provider_call"]
    assert provider_call["context_selection"]["selected_history_messages"] == 0
    assert len(provider_call["composed_input"]["messages"]) == 1
    assert (
        "Respond with: ACTION: <your_action>"
        in provider_call["composed_input"]["messages"][0]["content"]
    )


def test_provider_call_retains_exact_context_selection_sdk_arguments_and_response():
    player = AuditLLMPlayer(
        name="Alice",
        controller=ActionOnlyController(),
        context_policy={"id": "last_n_messages", "parameters": {"recent_count": 2}},
    )
    manager = ConversationManager(player_name="Alice")
    manager.record_turn(
        user_message="handshake prompt",
        assistant_message="OK",
        turn_context=None,
        prompt_metadata=[],
        response_metadata={},
        phase="handshake",
    )
    manager.record_turn(
        user_message="earlier turn",
        assistant_message="ACTION: DEFEND",
        turn_context=None,
        prompt_metadata=[],
        response_metadata={},
        phase="turn",
    )
    player.bind_conversation_manager(manager)

    action = player.decide(
        game_state={"health": {"Alice": 100, "Bob": 100}},
        turn_context=TurnContext(
            match_id="match-1",
            turn_number=2,
            turn_index=1,
            player="Alice",
            started_at=0.0,
            duration=0.0,
        ),
    )

    provider_call = action.metadata["provider_call"]
    selection = provider_call["context_selection"]
    assert selection["available_history_messages"] == 4
    assert selection["selected_history_messages"] == 2
    assert selection["omitted_message_ids"] == [
        "handshake-0-user",
        "handshake-0-assistant",
    ]
    assert provider_call["composed_input"]["messages"][-1]["role"] == "user"
    assert (
        provider_call["sdk_request"]["arguments"]["messages"]
        == provider_call["composed_input"]["messages"]
    )
    assert provider_call["sdk_response"]["provider_model"] == "audit-model-2026-08-14"
    assert provider_call["sdk_response"]["response_complete"] is True
    assert provider_call["attempts"][0]["outcome"] == "completed"


def test_parse_failure_retains_prompt_provider_call_and_truncation_truth():
    controller = ActionOnlyController()
    controller.bind_game(FixedDamageGame())
    player = AuditLLMPlayer(name="Alice", controller=controller)
    player.test_response = "I considered ATTACK but need to check"
    player.test_stop_reason = "max_tokens"
    player.test_response_complete = False

    with pytest.raises(ActionParseError) as captured:
        player.decide(
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

    parse_result = captured.value.parse_result
    assert parse_result.action is None
    assert parse_result.metadata["contract_satisfied"] is False
    assert parse_result.prompt_text
    assert parse_result.provider_call["sdk_response"]["stop_reason"] == "max_tokens"
    assert parse_result.provider_call["sdk_response"]["response_complete"] is False


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


def test_claude_player_uses_high_fallback_max_tokens(monkeypatch):
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
