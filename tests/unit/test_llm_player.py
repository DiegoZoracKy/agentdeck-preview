"""
Unit tests for LLMPlayer lifecycle phases.

Ensures handshake, decide (turn), conclude, and clone work correctly
per SPEC-PLAYER v1.2.0.
"""

from dataclasses import dataclass

import pytest

from agentdeck.players.llm_player import LLMPlayer
from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.renderers.text_renderer import TextRenderer
from agentdeck.core.types import (
    MatchResult,
    MatchContext,
    HandshakeContext,
    RenderResult,
    TurnContext,
)
from agentdeck.players import GPTPlayer, ClaudePlayer, GeminiPlayer


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
