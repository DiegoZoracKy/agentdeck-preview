"""AgentDeck - Research platform for studying AI behavior through game scenarios."""

__version__ = "0.1.0rc2"

# Controller implementations
from .controllers import ActionOnlyController, ReasoningController

# Core imports
from .core.agentdeck import AgentDeck

# Base classes for extension
from .core.base import Controller, Game, Player, Renderer, Spectator
from .core.mechanics import TurnBasedGame

# Prompt composition
from .core.prompt_builder import PromptBuilder

# Recorder and Replay
from .core.recorder import Recorder
from .core.replay import ReplayEngine
from .core.session import AgentDeckConfig, SessionConfig, SessionContext
from .core.types import (
    ActionResult,
    Event,
    GameStatus,
    HandshakeContext,
    HandshakeResult,
    LifecyclePhase,
    LogLevel,
    MatchContext,
    MatchResult,
    MatchResults,
    PromptBlock,
    PromptBundle,
    PromptContext,
    TemplateError,
    TurnContext,
)

# Game examples
from .games.examples.fixed_damage import FixedDamageGame
from .games.examples.hangman import HangmanGame

# Player implementations
from .players import ClaudePlayer, GeminiPlayer, GPTPlayer, MockPlayer

# Renderer implementations
from .renderers import TextRenderer

# Spectator implementations
from .spectators import MatchNarrator, ProgressDisplay, StatsTracker, TokenUsageTracker

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
    "TurnBasedGame",
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
