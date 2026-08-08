"""AgentDeck - Research platform for studying AI behavior through game scenarios."""

__version__ = "0.2.0"

# Controller implementations
from .controllers import ActionOnlyController, ReasoningController

# Core imports
from .core.agentdeck import AgentDeck
from .core.conversation import ConversationManager

# Base classes for extension
from .core.base import Controller, Game, Player, Renderer, Spectator
from .core.match_runtime import MatchRuntime
from .core.mechanics import TurnBasedGame, TurnResult

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
    ParseResult,
    PromptBlock,
    PromptBundle,
    PromptContext,
    RandomGenerator,
    RenderResult,
    TemplateError,
    TurnContext,
)
from .instruments import (
    InstrumentCheck,
    InstrumentReport,
    certify_instrument,
    inspect_instrument,
    validate_instrument,
)

# Game examples
from .games.examples.archivist_choice import ArchivistChoiceGame
from .games.examples.fixed_damage import FixedDamageGame
from .games.examples.hangman import HangmanGame
from .games.examples.variable_damage import VariableDamageGame

# Player implementations
from .players import ClaudePlayer, GeminiPlayer, GPTPlayer, LLMPlayer, MockPlayer

# Renderer implementations
from .renderers import TextRenderer
from .research.behavioral import BehavioralScorer

# Spectator implementations
from .spectators import (
    MatchCurator,
    MatchReporter,
    ProgressDisplay,
    StatsTracker,
    TokenUsageTracker,
    curate_match_file,
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
    "TurnResult",
    "MatchRuntime",
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
    "RandomGenerator",
    "ParseResult",
    "ConversationManager",
    # LLM Players
    "LLMPlayer",
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
    "BehavioralScorer",
    # Spectators
    "StatsTracker",
    "ProgressDisplay",
    "TokenUsageTracker",
    "MatchCurator",
    "MatchReporter",
    "curate_match_file",
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
    "InstrumentCheck",
    "InstrumentReport",
    "inspect_instrument",
    "validate_instrument",
    "certify_instrument",
    # Version
    "__version__",
]
