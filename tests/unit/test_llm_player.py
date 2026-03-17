"""
Unit tests for LLMPlayer lifecycle phases.

Ensures handshake, decide (turn), conclude, and clone work correctly
per SPEC-PLAYER v1.2.0.
"""

import pytest

from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.core.conversation import ConversationManager
from agentdeck.core.types import (
    MatchContext,
    MatchResult,
)
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
# Skipped here due to complexity of HandshakeContext/decide() setup


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
