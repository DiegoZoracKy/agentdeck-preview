"""AgentDeck - Execution and evidence engine for AI agents in game scenarios."""

__version__ = "0.4.0"

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
from .core.session import AgentDeckConfig, ConclusionPolicy, SessionConfig, SessionContext
from .core.types import (
    ActionResult,
    Event,
    GameStatus,
    HandshakeContext,
    HandshakeResponse,
    HandshakeResult,
    LifecyclePhase,
    LogLevel,
    MatchContext,
    MatchResult,
    MatchResults,
    PromptBlock,
    PromptBundle,
    PromptContext,
    RenderResult,
    TemplateError,
    TurnContext,
)

# Game examples
from .games.examples.archivist_choice import ArchivistChoiceGame
from .games.examples.fixed_damage import FixedDamageGame
from .games.examples.hangman import HangmanGame
from .games.examples.variable_damage import VariableDamageGame

# Player implementations
from .players import ClaudePlayer, GeminiPlayer, GPTPlayer, MockPlayer

# Renderer implementations
from .renderers import TextRenderer

# Spectator implementations
from .spectators import (
    MatchReporter,
    ProgressDisplay,
    StatsTracker,
    TokenUsageTracker,
)

__all__ = [
    # Main
    "AgentDeck",
    "AgentDeckConfig",
    "ConclusionPolicy",
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
    "RenderResult",
    "TemplateError",
    "HandshakeContext",
    "HandshakeResponse",
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
    "MatchReporter",
    # Games
    "ArchivistChoiceGame",
    "FixedDamageGame",
    "HangmanGame",
    "VariableDamageGame",
    # Prompt composition
    "PromptBuilder",
    # Recording
    "Recorder",
    "ReplayEngine",
    # Version
    "__version__",
]
