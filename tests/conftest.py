"""
Pytest configuration and common fixtures for AgentDeck test suite.

Per TEST-PLAN-consensus.md, provides:
- Mock games (FixedDamageGame)
- Mock players (deterministic responses)
- Mock LLM APIs (OpenAI, Anthropic, Google)
- Event bus instances
- Temporary directories for recordings
"""

from unittest.mock import Mock

import pytest

# Import AgentDeck components
from agentdeck.core.base import Player
from agentdeck.core.event_bus import EventBus
from agentdeck.core.types import (
    HandshakeContext,
    TurnContext,
)
from agentdeck.games.examples import FixedDamageGame

# ============================================================================
# MOCK PLAYERS
# ============================================================================


class MockPlayer(Player):
    """
    Deterministic mock player for testing.

    Returns predictable responses based on phase:
    - Handshake: "OK"
    - Turn: "ATTACK"
    - Conclusion: "Good game!"
    """

    def __init__(self, name: str = "MockPlayer", **kwargs):
        """Initialize mock player with default controller."""
        from agentdeck.controllers import ActionOnlyController

        super().__init__(name=name, controller=ActionOnlyController(), **kwargs)

    def get_response(self, prompt: str) -> str:
        """Return deterministic response based on prompt content."""
        # Check for handshake phase (actual template says "ready to begin")
        if "ready to begin" in prompt.lower() or "respond 'ok'" in prompt.lower():
            return "OK"
        elif "conclude" in prompt.lower() or "game over" in prompt.lower():
            return "Good game!"
        else:
            return "ATTACK"

    def conclude(self, result, *, match_context):
        """Return deterministic conclusion and record prompt metadata."""
        response_text = "Good game!"
        prompt_text = match_context.conclusion_prompt or "Match concluded."
        controller_metadata = self.controller.parse_conclusion(response_text)
        self._record_exchange(
            prompt=prompt_text,
            response=response_text,
            phase="conclusion",
            turn_context=None,
            prompt_blocks=[
                {
                    "key": "outcome",
                    "content": self._format_outcome(result),
                    "metadata": {},
                }
            ],
            controller_format=self.controller.get_format_instructions(),
            controller_metadata=controller_metadata,
            renderer_output={},
            usage_info=None,
        )
        return response_text

    def _format_outcome(self, result) -> str:
        if result.winner is None:
            return "Draw"
        if result.winner == self.name:
            return f"You ({self.name}) won the match."
        return f"{result.winner} won the match."


@pytest.fixture
def mock_player():
    """Fresh MockPlayer instance for testing."""
    return MockPlayer(name="TestPlayer")


@pytest.fixture
def mock_player_pair():
    """Pair of mock players for two-player games."""
    return [MockPlayer(name="Alice"), MockPlayer(name="Bob")]


# ============================================================================
# MOCK GAMES
# ============================================================================


@pytest.fixture
def mock_game():
    """Fresh FixedDamageGame instance for testing."""
    return FixedDamageGame()


@pytest.fixture
def mock_game_state(mock_game):
    """Valid game state for FixedDamageGame."""
    return mock_game.setup(players=["Alice", "Bob"])


# ============================================================================
# EVENT BUS
# ============================================================================


@pytest.fixture
def event_bus():
    """Fresh EventBus instance."""
    return EventBus()


@pytest.fixture
def mock_spectator():
    """
    Mock spectator with modern Event signature.

    Tracks all received events in a list for easy verification.
    """

    class MockSpectator:
        def __init__(self):
            self.events = []
            self.on_match_start_calls = []
            self.on_event_calls = []
            self.on_dialogue_turn_calls = []

        def on_match_start(self, event):
            """Modern signature: receives Event object."""
            self.events.append(event)
            self.on_match_start_calls.append(event)

        def on_event(self, event):
            """Modern signature: fallback handler."""
            self.events.append(event)
            self.on_event_calls.append(event)

        def on_dialogue_turn(self, event):
            """Modern signature: for DIALOGUE_TURN events."""
            self.events.append(event)
            self.on_dialogue_turn_calls.append(event)

    return MockSpectator()


# ============================================================================
# TEMPORARY DIRECTORIES
# ============================================================================


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for recordings."""
    output_dir = tmp_path / "recordings"
    output_dir.mkdir()
    return output_dir


# ============================================================================
# MOCK LLM APIS
# ============================================================================


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI Responses API response structure."""
    mock_response = Mock()
    mock_response.output_text = "ATTACK"
    mock_response.output = []
    mock_response.model = "gpt-4o-mini"
    mock_response.usage = Mock(input_tokens=100, output_tokens=20, total_tokens=120)

    return mock_response


@pytest.fixture
def mock_openai_api(mocker, mock_openai_response):
    """Mocked OpenAI API client."""
    mocker.patch("openai.OpenAI.responses.create", return_value=mock_openai_response)
    return mock_openai_response


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response structure."""
    mock_response = Mock()
    mock_response.content = [Mock(text="ATTACK")]
    mock_response.usage = Mock(input_tokens=100, output_tokens=20)

    return mock_response


@pytest.fixture
def mock_anthropic_api(mocker, mock_anthropic_response):
    """Mocked Anthropic API client."""
    mocker.patch("anthropic.Anthropic.messages.create", return_value=mock_anthropic_response)
    return mock_anthropic_response


@pytest.fixture
def mock_gemini_response():
    """Mock Google Gemini API response structure."""
    mock_candidate = Mock()
    mock_candidate.content.parts = [Mock(text="ATTACK")]

    mock_response = Mock()
    mock_response.candidates = [mock_candidate]
    mock_response.usage_metadata = Mock(prompt_token_count=100, candidates_token_count=20)

    return mock_response


@pytest.fixture
def mock_gemini_api(mocker, mock_gemini_response):
    """Mocked Google Gemini API client."""
    mocker.patch(
        "google.generativeai.GenerativeModel.generate_content", return_value=mock_gemini_response
    )
    return mock_gemini_response


# ============================================================================
# CONTEXT OBJECTS
# ============================================================================


@pytest.fixture
def handshake_context():
    """Valid HandshakeContext for testing."""
    return HandshakeContext(
        match_id="test-match-001",
        player_name="Alice",
        opponent_names=["Bob"],
        game_name="FixedDamageGame",
        seed=42,
        handshake_template_id="default",
        metadata={},
    )


@pytest.fixture
def turn_context():
    """Valid TurnContext for testing."""
    return TurnContext(
        match_id="test-match-001", turn_number=1, current_player="Alice", metadata={}
    )


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests (manual)")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Auto-mark tests based on directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
