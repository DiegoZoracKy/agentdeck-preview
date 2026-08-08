# AgentDeck Implementation Specification

**Version**: 2.4 (Instrument Package Contract)
**Status**: Active
**Last Updated**: 2026-08-07
**Purpose**: Navigation hub for AgentDeck architecture and component specifications

> This document provides high-level orientation for AgentDeck's design philosophy, architecture, and navigation to detailed component specifications. For implementation details, consult the component specs linked below.

---

## 1. Purpose & Vision

AgentDeck is a **research platform for studying AI behavior through game scenarios**. It enables researchers to run controlled experiments where AI agents interact in well-defined environments, providing comprehensive data collection for analysis of prompting strategies, decision-making patterns, and model capabilities.

### 1.1 Why Games?

Most LLM benchmarks measure **knowledge** (answering static questions). But real-world utility requires **agency**: maintaining state, forming strategies, and adapting over time.

Games are the perfect "behavioral wind tunnel" for testing these capabilities:

- **Constrained environments** – Isolate specific variables (e.g., "Does the model understand resource scarcity?")
- **Iterative decision making** – Agents live with consequences, testing long-term planning
- **Social dynamics** – Multiplayer games reveal cooperation, betrayal, and negotiation patterns
- **Measurable outcomes** – Win/lose provides clear signal for cost/quality trade-offs

### 1.2 The Console Metaphor

AgentDeck is architected like a video game console to keep experiments modular and clean:

- 🎮 **Console (AgentDeck)** – The engine that orchestrates sessions, manages seeding, and enforces rules
- 💾 **Game (Cartridge)** – Pure logic defining rules and state transitions; swap games without changing agents
- 🤖 **Player** – The AI agent (GPT-4, Claude, Gemini) that "holds the controller"
- 🕹️ **Controller** – Translates the AI's text response into valid game actions
- 📺 **Renderer** – "Draws" the game state into text the AI can understand
- 👁️ **Spectator** – The audience watching the live stream (stats, narration, cost tracking)
- 📹 **Recorder** – The "DVR" capturing every event for perfect replay and analysis

By separating these concerns, AgentDeck ensures your research is **reproducible, observable, and easy to modify**.

### 1.3 Core Capabilities
- Rapid experimentation (games in ~15 lines, experiments in ~3 lines)
- Comprehensive data collection (every decision, timing, reasoning captured)
- Flexible observation (spectators can analyze live or replay)
- Reproducible research (deterministic experiments via seeded randomness)

**Success Criteria:**
1. Researchers can create a working game in <20 lines of code
2. Running 100 matches takes <5 lines of code
3. All match data is automatically persisted
4. Experiments are fully reproducible via seed parameter

---

## 2. Architecture Overview

### 2.1 System Design

```
┌─────────────────────────────────────────────────────────┐
│                    AgentDeck (Facade)                    │
│  - Stable public API                                     │
│  - Engine selection & configuration                      │
│  - Result aggregation                                    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│             Console (Execution Engine)                  │
│  - Session lifecycle                                    │
│  - Match execution                                      │
│  - Event bus management                                 │
│  - Player coordination & logging                        │
└──────┬───────────────────────────────────────┬──────────┘
       │                                       │
┌──────▼──────┐                         ┌─────▼──────┐
│    Game     │                         │  EventBus  │
│ - Rules     │                         │ - Events   │
│ - Flow      │                         │ - Routing  │
└──────┬──────┘                         └─────┬──────┘
       │                                       │
┌──────▼──────────────────────┐         ┌─────▼──────────┐
│         Players              │         │   Spectators   │
│ - Renderer (state→view)      │         │ - Observation  │
│ - Controller (response→action)│         │ - Recording    │
└──────────────────────────────┘         └────────────────┘
```

### 2.2 Event-Driven Architecture

The system uses an event-driven architecture where:
- **Console** owns session lifecycle, orchestrates match execution, and emits events
- **EventBus** distributes events to all registered spectators
- **Spectators** observe without affecting game flow
- **Games** focus only on game logic, not infrastructure

**Event hierarchy:**
```
session_start
  └── batch_start
      ├── player_handshake_start         # per player, before gameplay (mandatory)
      ├── player_handshake_complete      # per player, on acceptance
      ├── player_handshake_abort         # per player, on rejection
      └── match_start
          ├── gameplay                   # canonical GameplayEventData payload
          ├── player_action_parse_failed # optional, emitted before policy handling
          ├── <custom domain events>     # snake_case strings from games
          ├── player_conclusion          # optional per-player reflection
          └── match_end
      └── batch_end
  └── session_end
```

**Critical ordering** (per [SPEC-CONSOLE](SPEC-CONSOLE.md) §6.6 E1): Handshake events MUST precede MATCH_START. Conclusion events occur after final gameplay turn but before MATCH_END.

### 2.3 Three-Phase Player Lifecycle

Per [SPEC-PLAYER](SPEC-PLAYER.md) v1.3.2:

1. **Handshake Phase** (Mandatory, before gameplay):
   - Console → Player.build_handshake_bundle() → PromptBundle
   - Console emits PLAYER_HANDSHAKE_START (with prompt_text + prompt_blocks)
   - Console → Player.execute_handshake() → HandshakeResponse
   - Console → Controller.validate_handshake() → HandshakeResult
   - Console emits PLAYER_HANDSHAKE_COMPLETE/ABORT

2. **Turn Phase** (Gameplay loop):
   - Game.get_view() → player_view (includes narrative)
   - PromptBuilder.compose() → Prompt
   - Player.decide() → ActionResult
   - Game.update() → New State
   - Console emits GAMEPLAY (with prompt payload)

3. **Conclusion Phase** (Policy-driven, post-match reflection):
   - Console applies conclusion policy → Player.conclude()
   - Console emits PLAYER_CONCLUSION before MATCH_END

### 2.4 Reproducibility Architecture

**Critical for Research**: AgentDeck ensures full reproducibility through deterministic seeding:

1. **AgentDeck configuration seed**: Provided by researchers via facade and passed to the console to control session randomness
2. **Match-level seed**: Optional override for specific match control
3. **Random state management**: Deterministic `RandomGenerator` helper cascades per match/turn
4. **LLM determinism**: When supported by models (e.g., temperature=0)

**Seed propagation (canonical API):**
```
config = AgentDeckConfig(seed=42)
deck = AgentDeck(game=MyGame(), session=config)
  └── Console(seed=42)
      ├── Match 1 (seed=42 + match_index)
      ├── Match 2 (seed=43)
      └── Match N (seed=42 + N-1)
```

---

## 3. Core Design Principles

### 3.1 Simplicity First
- Games center on 4 core methods: `setup()`, `get_view()`, `update()`, `status()`, plus descriptive properties such as `instructions`, `allowed_actions`, and `default_handshake_template`
- State is just Python dictionaries, not complex objects
- Direct instantiation, no registration or string IDs required

### 3.2 Clean Separation of Concerns
- **Games** only handle game logic
- **Console** handles all orchestration
- **Renderers** only format state (no instructions)
- **Controllers** provide format instructions AND parsing
- **Spectators** observe without interfering

### 3.3 Research Flexibility
- Each player can have different renderer/controller
- Spectators work identically for live and replay
- All data automatically recorded for analysis

### 3.4 Event-Driven Observation
- Spectators subscribe to events via EventBus
- Games don't know about spectators
- Multiple spectators can run simultaneously

---

## 4. Component Specifications

All component specifications follow the lean spec format with numbered invariants, examples, and testing strategies. For implementation details, consult the individual specs.

### 4.1 Core Components

| Component | Version | Status | Description |
|-----------|---------|--------|-------------|
| [AgentDeck](SPEC-AGENTDECK.md) | 0.3.1 | Final | Public API facade for the framework |
| [Console](SPEC-CONSOLE.md) | 0.7.2 | Final | Execution engine for session/match lifecycle |
| [Observability / EventBus](SPEC-OBSERVABILITY.md) | 2.0.0 | Final | Event distribution, emission responsibilities, and spectator routing |
| [Gameplay Event Data](SPEC-GAMEPLAY-EVENT-DATA.md) | 2.0.0 | Final | Canonical `GAMEPLAY` payload shared by live play, recording, and replay |
| [Game](SPEC-GAME.md) | 0.8.0 | Final | Game author contract (rules, state, narrative, lifecycle hooks, effective config) |
| [Instrument Package](SPEC-INSTRUMENT-PACKAGE.md) | 0.1.0 | Final | External manifest, inspection, certification, and capability tiers |
| [Player](SPEC-PLAYER.md) | 1.3.2 | Final | Three-phase player lifecycle (handshake/turn/conclusion) |
| [Controller](SPEC-CONTROLLER.md) | 1.3.1 | Final | Handshake, gameplay parsing, and conclusion parsing contract |
| [Renderer](SPEC-RENDERER.md) | 0.3.0 | Final | State formatting for AI consumption |
| [Spectator](SPEC-SPECTATOR.md) | 2.0.0 | Final | Observation and analysis interface |

### 4.2 Infrastructure Components

| Component | Version | Status | Description |
|-----------|---------|--------|-------------|
| [Recorder](SPEC-RECORDER.md) | 2.1.0 | Final | Strict match persistence with complete effective configuration snapshots |
| [ReplayEngine](SPEC-REPLAY.md) | 2.0.0 | Final | Exact replay of canonical event payloads |
| [PromptBuilder](SPEC-PROMPT-BUILDER.md) | 0.4.0 | Final | Template-driven prompt composition |
| [Turn-Based Mechanic](SPEC-GAME-MECHANIC-TURN-BASED.md) | 2.0.0 | Final | TurnBasedGame + TurnLoop helper using MatchRuntime |
| [MatchRuntime](SPEC-MATCH-RUNTIME.md) | 1.2.0 | Final | Per-match infrastructure context with strict state/view validation |
| [Pricing](SPEC-PRICING.md) | 1.0.1 | Final | Cost tracking system for LLM usage |
| [LLM](SPEC-LLM.md) | 1.1.4 | Final | LLM provider integration contract |
| [Parallel](SPEC-PARALLEL.md) | 1.0.0 | Final | Worker-based concurrent match execution |
| [Monitor](SPEC-MONITOR.md) | 1.0.0 | Final | Console-level observation and progress reporting |

### 4.3 Research Tools

| Component | Version | Status | Description |
|-----------|---------|--------|-------------|
| [Research](SPEC-RESEARCH.md) | 1.1.0 | Final | Statistical analysis, model comparison, and post-hoc analysis from recordings |
| [Intervention Comparison](SPEC-RESEARCH-INTERVENTION-COMPARISON.md) | 0.1.0 | Final | Exact cross-run difference artifact for a declared baseline and intervention |
| [Research Behavioral](SPEC-RESEARCH-BEHAVIORAL.md) | 0.2.0 | Final | Global behavioral scorer contract and extension interface for game-specific profiles |
| [Archivist Choice Behavioral](SPEC-BEHAVIORAL-ARCHIVIST-CHOICE-v0.1.0.md) | 0.1.0 | Final | Deterministic Archivist Choice score, completion, and post-hoc action-fit profile |
| [Research Experiment](SPEC-RESEARCH-EXPERIMENT.md) | 1.6.0 | Final | Experiment package, manifest/results/index contracts |
| [Research Packager](SPEC-RESEARCH-PACKAGER.md) | 0.4.0 | Final | Contained session-to-experiment package helper |
| [Research Packager Context](SPEC-RESEARCH-PACKAGER-CONTEXT-v0.1.0.md) | 0.1.0 | Final | Optional confirmed world configuration for package behavioral export |

### 4.4 Viewer Surface

| Component | Version | Status | Description |
|-----------|---------|--------|-------------|
| [Match Surface Projection](SPEC-MATCH-SURFACE-PROJECTION.md) | 0.4.0 | Final | Core spectator projection and contained static artifact sinks |
| [Artifact Safety](SPEC-ARTIFACT-SAFETY.md) | 0.1.0 | Final | Portable identity, output containment, strict JSON, and executable trust boundary |
| [Viewer](SPEC-VIEWER.md) | 0.6.0 | Legacy / Frozen | Offline browser replay viewer for Recorder v1.3 artifacts; not kept compatible with Recorder v2.0 |

---

## 5. Quick Start Example

```python
from agentdeck import AgentDeck, FixedDamageGame, MockPlayer

game = FixedDamageGame(
    max_health=100,
    attack_damage=20,
    potion_heal=30,
    starting_potions=2,
    information_level="partial",
)

players = [
    MockPlayer("Alice", actions=["ATTACK"]),
    MockPlayer("Bob", actions=["POTION", "ATTACK"]),
]

with AgentDeck(game=game) as deck:
    results = deck.play(players=players, matches=3)

print(results.summary)
print(results.win_rates)
```

---

## 6. File Structure

```
agentdeck/
├── pyproject.toml
├── README.md
├── src/
│   └── agentdeck/
│       ├── core/
│       │   ├── agentdeck.py           # Public API facade
│       │   ├── console.py             # Match orchestrator
│       │   ├── event_bus.py           # Event distribution
│       │   ├── event_factory.py       # Standardised gameplay payloads
│       │   ├── game_event_emitter.py  # Domain event helper
│       │   ├── prompt_builder.py      # Prompt composition
│       │   ├── recorder.py            # Match recorder spectator
│       │   ├── replay.py              # Replay engine
│       │   ├── turn_loop.py           # Turn-based execution helper
│       │   ├── types.py               # Shared dataclasses & enums
│       │   └── base/…                 # Game/player/controller/spectator bases
│       ├── games/
│       │   ├── __init__.py
│       │   └── examples/              # Sample games with bundled viewers
│       │       └── fixed_damage/      # Game package (game.py + viewers/)
│       ├── players/                   # Mock player, LLM integrations
│       ├── controllers/               # ActionOnly, Reasoning controllers
│       ├── renderers/                 # Text renderer, helpers
│       ├── spectators/                # Stats tracker, logger
│       └── research/                  # Analysis utilities
├── tests/                             # Pytest suite
└── specs/                             # Component specifications
    ├── SPEC.md                        # This file (navigation hub)
    ├── SPEC-AGENTDECK.md
    ├── SPEC-CONSOLE.md
    ├── SPEC-GAME.md
    ├── SPEC-PLAYER.md
    ├── SPEC-CONTROLLER.md
    ├── SPEC-RENDERER.md
    ├── SPEC-SPECTATOR.md
    ├── SPEC-RECORDER.md
    ├── SPEC-REPLAY.md
    ├── SPEC-PROMPT-BUILDER.md
    ├── SPEC-GAME-MECHANIC-TURN-BASED.md
    ├── SPEC-PRICING.md
    ├── SPEC-OBSERVABILITY.md
    ├── SPEC-LLM.md
    ├── SPEC-RESEARCH.md
    ├── SPEC-RESEARCH-BEHAVIORAL.md
    └── SPEC-RESEARCH-EXPERIMENT.md
```

---

## 7. Design Philosophy & Guidelines

For detailed authoring guidelines, design patterns, and architectural decisions, see:
- [GUIDELINES.md](GUIDELINES.md) - Spec authoring best practices
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guide, design principles, and workflow
- [research/README.md](../research/README.md) - Research experiment patterns

---

## 8. Public API

```python
# Everything users need is in the top-level import
from agentdeck import (
    # Main
    AgentDeck,

    # Base classes for extension
    Game, TurnBasedGame,
    Player, Renderer, Controller, Spectator,

    # Types
    ActionResult, GameStatus, MatchResult, MatchResults,
    Event, LogLevel,

    # LLM Players (CORE COMPONENTS!)
    GPTPlayer,           # OpenAI integration (MANDATORY)
    ClaudePlayer,        # Anthropic integration (CORE)
    GeminiPlayer,        # Google integration (CORE)

    # Built-in implementations
    MockPlayer, TextRenderer, ActionOnlyController
)

# Research module for statistical rigor (Kaggle-inspired)
from agentdeck.research import (
    compare_models,          # The 80% use case - rigorous model comparison
    progressive_comparison,  # Early stopping to save API costs
    parameter_sweep,         # Hyperparameter optimization
    EloLeague,              # ELO rating system for ongoing competitions
    Benchmark,              # Standardized benchmarks with exact reproducibility
    statistical_significance # P-values, confidence intervals, effect sizes
)
```

---

## 9. Version History

### v2.0 (2025-01-27) - Lean Navigation
- **Breaking Change**: Restructured as navigation hub to component specs
- Archived detailed content outside this repo
- Added component specification table with versions and status
- Added quick start example and file structure
- Reduced from 1360 lines to ~250 lines (navigation-only)
- **Rationale**: Component specs ([SPEC-GAME.md](SPEC-GAME.md), [SPEC-PLAYER.md](SPEC-PLAYER.md), etc.) are source of truth. This document now provides high-level orientation and navigation, preventing sync issues.

### v1.0 (2025-01-24) - Full Specification
- Comprehensive implementation specification (archived outside this repo)
- Detailed component contracts, data flows, and examples

---

## 10. References

### External Documentation
- [README.md](../README.md) - Project overview and getting started
- [Contributing Guide](../CONTRIBUTING.md) - Development workflow
- API Reference (planned)

### Related Specifications
- All component specs linked in Section 4
- [GUIDELINES.md](GUIDELINES.md) - Spec authoring patterns
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development workflow and design philosophy

---

**Note**: This is the lean navigation version (v2.0). The v1.0 full specification is archived outside this repo.
