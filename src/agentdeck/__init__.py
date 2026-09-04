"""AgentDeck - Open execution and Research system for AI agents in game scenarios."""

__version__ = "0.4.0"

# Controller implementations
from .controllers import ActionOnlyController, ReasoningController

# Core imports
from .core.agentdeck import AgentDeck
from .core.console import BatchStoppedError
from .core.assembly import (
    Assembly,
    AssemblyArtifact,
    AssemblyExecution,
    AssemblyExecutionError,
    AssemblyRecordReceipt,
    AssemblyRun,
    AssemblyRunExecution,
    PlayerFactory,
    PreparedAssembly,
    execute_prepared_assembly,
    inspect_provider_call_custody,
    prepare_assembly,
)

# Base classes for extension
from .core.base import Controller, Game, Player, Renderer, Spectator
from .core.mechanics import TurnBasedGame

# Prompt composition
from .core.prompt_builder import PromptBuilder
from .core.provider_call_journal import (
    FilesystemProviderCallJournal,
    MemoryProviderCallJournal,
    ProviderCallCustodyError,
    ProviderCallJournal,
)

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
    PlayerResponseUnavailableError,
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
from .games.examples.hidden_signal import HiddenSignalGame
from .games.examples.variable_damage import VariableDamageGame

# Player implementations
from .players import ClaudePlayer, GeminiPlayer, GPTPlayer, HumanPlayer, MockPlayer

# Research contracts
from .research import (
    ConditionAssignment,
    ConditionTarget,
    CorpusRecord,
    Evidence,
    EvidenceCitation,
    EvidenceDiagnostic,
    Finding,
    FindingAuthor,
    FindingDeclaration,
    GameResearchProfile,
    Hypothesis,
    MeasureArtifact,
    MeasureDeclaration,
    MeasureDiagnostic,
    MeasureInput,
    MeasureOutput,
    MeasureReference,
    MeasureResult,
    PreparedGameResearchProfile,
    PreparedMeasure,
    PreparedExecutionGroup,
    PreparedStudy,
    RecordCorpus,
    ResearchOperationalization,
    ResearchOpportunity,
    SourceLocator,
    StudyCell,
    StudyAnalysis,
    StudyCondition,
    StudyDefinition,
    StudyDiagnostic,
    StudyExecutionGroup,
    StudyExecution,
    StudyExecutionError,
    StudyGroupExecution,
    StudyLineage,
    StudyPhase,
    StudyRecordReceipt,
    StudyRunExecution,
    StudySelection,
    StudyValidationError,
    load_study,
    execute_prepared_study,
    load_study_execution,
    analyze_study,
    build_record_corpus,
    derive_evidence,
    evaluate_measure,
    load_finding,
    load_evidence,
    load_game_research_profile,
    load_measure,
    prepare_study,
    prepare_finding,
    prepare_game_research_profile,
    prepare_measure,
    render_finding_markdown,
    write_finding_report,
    select_study,
)

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
    "BatchStoppedError",
    "Assembly",
    "AssemblyRun",
    "AssemblyArtifact",
    "AssemblyExecution",
    "AssemblyExecutionError",
    "AssemblyRecordReceipt",
    "PlayerFactory",
    "AssemblyRunExecution",
    "PreparedAssembly",
    "prepare_assembly",
    "execute_prepared_assembly",
    "inspect_provider_call_custody",
    "AgentDeckConfig",
    "ConclusionPolicy",
    "SessionContext",
    "SessionConfig",
    "ProviderCallJournal",
    "MemoryProviderCallJournal",
    "FilesystemProviderCallJournal",
    "ProviderCallCustodyError",
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
    "PlayerResponseUnavailableError",
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
    # Human-controlled Players
    "HumanPlayer",
    # Testing
    "MockPlayer",
    # Renderers
    "TextRenderer",
    # Controllers
    "ActionOnlyController",
    "ReasoningController",
    # Research
    "ConditionAssignment",
    "ConditionTarget",
    "CorpusRecord",
    "Evidence",
    "EvidenceCitation",
    "EvidenceDiagnostic",
    "Finding",
    "FindingAuthor",
    "FindingDeclaration",
    "GameResearchProfile",
    "Hypothesis",
    "MeasureArtifact",
    "MeasureDeclaration",
    "MeasureDiagnostic",
    "MeasureInput",
    "MeasureOutput",
    "MeasureReference",
    "MeasureResult",
    "PreparedGameResearchProfile",
    "PreparedMeasure",
    "PreparedExecutionGroup",
    "PreparedStudy",
    "RecordCorpus",
    "ResearchOperationalization",
    "ResearchOpportunity",
    "SourceLocator",
    "StudyCell",
    "StudyAnalysis",
    "StudyCondition",
    "StudyDefinition",
    "StudyDiagnostic",
    "StudyExecutionGroup",
    "StudyExecution",
    "StudyExecutionError",
    "StudyGroupExecution",
    "StudyLineage",
    "StudyPhase",
    "StudyRecordReceipt",
    "StudyRunExecution",
    "StudySelection",
    "StudyValidationError",
    "load_study",
    "prepare_study",
    "select_study",
    "execute_prepared_study",
    "load_study_execution",
    "analyze_study",
    "build_record_corpus",
    "derive_evidence",
    "evaluate_measure",
    "load_finding",
    "load_evidence",
    "load_game_research_profile",
    "load_measure",
    "prepare_finding",
    "prepare_game_research_profile",
    "prepare_measure",
    "render_finding_markdown",
    "write_finding_report",
    # Spectators
    "StatsTracker",
    "ProgressDisplay",
    "TokenUsageTracker",
    "MatchReporter",
    # Games
    "ArchivistChoiceGame",
    "FixedDamageGame",
    "HangmanGame",
    "HiddenSignalGame",
    "VariableDamageGame",
    # Prompt composition
    "PromptBuilder",
    # Recording
    "Recorder",
    "ReplayEngine",
    # Version
    "__version__",
]
