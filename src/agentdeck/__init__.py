"""AgentDeck - Research platform for studying AI behavior through game scenarios."""

__version__ = "0.1.0rc1"

# Core imports
from .core.agentdeck import AgentDeck
from .core.session import AgentDeckConfig, SessionContext, SessionConfig
from .core.types import (
    ActionResult,
    GameStatus,
    Event,
    MatchResult,
    MatchResults,
    LogLevel,
    LifecyclePhase,
    PromptBundle,
    PromptBlock,
    PromptContext,
    TemplateError,
    HandshakeContext,
    HandshakeResult,
    MatchContext,
    TurnContext,
)

# Base classes for extension
from .core.base import Game, Player, Renderer, Controller, Spectator

# Player implementations
from .players import MockPlayer, GPTPlayer, ClaudePlayer, GeminiPlayer

# Renderer implementations
from .renderers import TextRenderer

# Controller implementations
from .controllers import ActionOnlyController, ReasoningController

# Spectator implementations
from .spectators import StatsTracker, ProgressDisplay, TokenUsageTracker, MatchNarrator

# Game examples
from .games.examples.fixed_damage import FixedDamageGame
from .games.examples.hangman import HangmanGame

# Prompt composition
from .core.prompt_builder import PromptBuilder

# Recorder and Replay
from .core.recorder import Recorder
from .core.replay import ReplayEngine

__all__ = [
    # Main
    "AgentDeck",
    "AgentDeckConfig",
    "SessionContext",
    "SessionConfig",
    # Base classes
    "Game",
    "Player",
    "Renderer",
    "Controller",
    "Spectator",
    # Types
    "ActionResult",
    "GameStatus",
    "Event",
    "MatchResult",
    "MatchResults",
    "LogLevel",
    "LifecyclePhase",
    "PromptBundle",
    "PromptBlock",
    "PromptContext",
    "TemplateError",
    "HandshakeContext",
    "HandshakeResult",
    "MatchContext",
    "TurnContext",
    # LLM Players
    "GPTPlayer",
    "ClaudePlayer",
    "GeminiPlayer",
    # Testing
    "MockPlayer",
    # Renderers
    "TextRenderer",
    # Controllers
    "ActionOnlyController",
    "ReasoningController",
    # Spectators
    "StatsTracker",
    "ProgressDisplay",
    "TokenUsageTracker",
    "MatchNarrator",
    # Games
    "FixedDamageGame",
    "HangmanGame",
    # Prompt composition
    "PromptBuilder",
    # Recording
    "Recorder",
    "ReplayEngine",
    # Version
    "__version__",
]
