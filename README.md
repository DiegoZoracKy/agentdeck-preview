# AgentDeck 🎮

**Turn an AI behavior question into a runnable, replayable, analyzable experiment.**

> **Install**: `pip install agentdeck-ai` (import as `agentdeck`)
> **Quality**: 75% coverage gate · Python 3.9+

---

## 🎯 Purpose & Vision

![AgentDeck Overview](docs/images/agentdeck-whiteboard-overview.png)

AgentDeck is a **research platform for studying AI behavior through game scenarios**. It enables researchers to run controlled experiments where AI agents interact in well-defined environments, providing comprehensive data collection for analysis of prompting strategies, decision-making patterns, and model capabilities.

Want to try it immediately? Jump to [Quick Start](#-quick-start).

### The Core Promise

Bring a behavioral question, then use AgentDeck to:

1. define a constrained game or reuse an existing one
2. run seeded matches across models, prompts, and controllers
3. replay and inspect what happened turn by turn
4. export objective artifacts for validation and comparison

### Why Games?

Most LLM benchmarks measure **knowledge** (answering static questions). But real-world utility requires **agency**: maintaining state, forming strategies, and adapting over time.

Games are the perfect "behavioral wind tunnel" for testing these capabilities:

- **Constrained environments** – Isolate specific variables (e.g., "Does the model understand resource scarcity?")
- **Iterative decision making** – Agents live with consequences, testing long-term planning
- **Social dynamics** – Multiplayer games reveal cooperation, betrayal, and negotiation patterns
- **Measurable outcomes** – Win/lose provides clear signal for cost/quality trade-offs

### The Console Metaphor

AgentDeck is architected like a video game console to keep experiments modular and clean:

- 🎮 **Console (AgentDeck)** – The engine that orchestrates sessions, manages seeding, and enforces rules
- 💾 **Game (Cartridge)** – Pure logic defining rules and state transitions; swap games without changing agents
- 🤖 **Player** – The AI agent (GPT-4, Claude, Gemini) that "holds the controller"
- 🕹️ **Controller** – Translates the AI's text response into valid game actions
- 📺 **Renderer** – "Draws" the game state into text the AI can understand
- 👁️ **Spectator** – The audience watching the live stream (stats, narration, cost tracking)
- 📹 **Recorder** – The "DVR" capturing every event for perfect replay and analysis

By separating these concerns, AgentDeck ensures your research is **reproducible, observable, and easy to modify**.

**Core Capabilities:**
- Run experiments with GPT/Claude/Gemini in ~10 lines of code
- Deterministic seeding + recordings + replay parity
- Parallel execution for scaling
- Event-driven observability via spectators
- Research export, validation, and package-friendly analysis workflows

## 🚦 Release Status

AgentDeck is currently published as a **public beta / preview**.

Today, the project is ready for:
- Core match execution through the `AgentDeck` facade
- Provider-backed and mock-player experiments
- Recording, replay, and event-driven observability
- Native fairness controls for paired side-swap and diagnostic first-player policies
- Research export, packaging, invariant validation, and post-hoc analysis workflows

It is **not** presented as a `1.0` stable platform yet. The main remaining gaps are:
- A methodologically stronger default benchmark regime for behavioral claims
- A sharper public narrative connecting the engine, the shipped FixedDamage and VariableDamage arcs, and the viewer
- Curated replay/viewer surfaces for the strongest release-facing examples

Viewer and replay UI work should currently be treated as a **beta offline surface**. The core product is still the engine, record contract, and research workflow.

---

## 🔬 Research Program

This README focuses on the **core AgentDeck platform** (architecture, APIs, and usage).
Experiment-specific findings, result narratives, and benchmark grids live under [`research/`](research/).

This preview repo now ships committed release-facing benchmark packages, arc
summaries, and a cross-game synthesis layer alongside the research tooling.

### Explore Research
- **[FixedDamage Arc 1](research/2026-03-23-fixed-damage-arc-1/README.md)** - Deterministic reference arc: diagnosis, intervention ladder, and final carry-forward stack
- **[VariableDamage Arc 1](research/2026-03-26-variable-damage-arc-1/README.md)** - Uncertainty arc: risk-band metrics, transfer failures, and final premium ceiling check
- **[Cross-Game Comparison 1](research/2026-03-26-cross-game-comparison-1/README.md)** - What transferred, what broke, and why the metrics had to evolve
- **[How To Run A Study](docs/how-to-run-a-study.md)** - Supported end-to-end workflow for creating, running, exporting, and validating a study
- **[Research Guide](research/README.md)** - How experiment packages are organized
- **[Research Index](research/INDEX.md)** - Registry of experiments and status
- **[Research Schema](research/SCHEMA.md)** - Contract for manifests, results, and validation
- **[Research Templates](research/_templates/)** - Boilerplate for new experiment packages

---

## ⚙️ Architecture

AgentDeck follows a **gaming console metaphor** with clean separation of concerns:

```
┌─────────────────────────────────────┐
│         AgentDeck (Facade)          │  ← You interact here
├─────────────────────────────────────┤
│         Console (Orchestrator)       │  ← Manages lifecycle
├─────────────┬───────────────────────┤
│    Game     │     EventBus          │  ← Game logic + Events
├─────────────┼───────────────────────┤
│   Players   │     Spectators        │  ← AI agents + Observers
└─────────────┴───────────────────────┘
```

### Single Turn Flow

![Single Turn Flow](docs/images/agentdeck-whiteboard-single-turn-flow.png)

### Core Components

**Games** define rules and state
- Required properties: `instructions`, `allowed_actions`, `default_handshake_template`
- Core methods: `setup()`, `get_view()`, `update()`, `status()`
- State is JSON-serializable dicts (no complex objects)
- Example: [FixedDamageGame](src/agentdeck/games/examples/fixed_damage/)

**Players** are AI agents making decisions
- Three-phase lifecycle: Handshake → Turn → Conclusion
- Built-in: `GPTPlayer`, `ClaudePlayer`, `GeminiPlayer`, `MockPlayer`
- Composable prompt templates via `PromptBuilder`

**Controllers** parse AI responses into actions
- `ActionOnlyController` - extracts single action token
- `ReasoningController` - extracts reasoning + action
- Handshake validation is built into the base `Controller` (default accepts exactly `OK`)

**Renderers** format game state for AI consumption
- `TextRenderer` - human-readable text format
- Custom renderers can provide JSON, images, etc.

**Spectators** observe and analyze matches
- `MatchNarrator` - turn-by-turn commentary
- `ProgressDisplay` - real-time progress with ETA
- `TokenUsageTracker` - cost tracking per player/model
- `StatsTracker` - win rates and performance metrics

**Recording & Replay**
- `Recorder` - captures complete match data to JSON
- `ReplayEngine` - reconstructs matches with event parity guarantee

---

## 🚀 Quick Start

> Requires Python 3.9+ (CI covers 3.9–3.11).

### Installation

**PyPI install (recommended):**
```bash
# Latest release on PyPI
pip install agentdeck-ai

# With provider SDKs
pip install agentdeck-ai[openai]      # OpenAI SDK
pip install agentdeck-ai[anthropic]   # Anthropic SDK
pip install agentdeck-ai[google]      # Google Gen AI SDK (Vertex mode)
pip install agentdeck-ai[providers]   # All provider SDKs

# With research stack (statistics/plotting)
pip install agentdeck-ai[research]

# Development install
pip install agentdeck-ai[dev]
```

**Source install (for contributors):**
```bash
git clone https://github.com/DiegoZoracKy/agentdeck-preview.git
cd agentdeck-preview
pip install -e ".[dev]"
```

### Your First Experiment
```python
from agentdeck import AgentDeck, GPTPlayer, FixedDamageGame, ActionOnlyController

# 1. Create a game
game = FixedDamageGame(
    max_health=100,
    attack_damage=20,
    potion_heal=30,
    starting_potions=1,
)

# 2. Create AI players
players = [
    GPTPlayer(
        name="Player-1",
        model="gpt-4o-mini",
        temperature=0.7,
        controller=ActionOnlyController(),
    ),
    GPTPlayer(
        name="Player-2",
        model="gpt-4o-mini",
        temperature=0.7,
        controller=ActionOnlyController(),
    ),
]

# Models must be provided explicitly for every provider-backed player.

# 3. Run experiment
with AgentDeck(game=game) as deck:
    results = deck.play(
        players=players,
        matches=10,
        seed=42,  # Reproducible!
    )

# 4. Analyze results
print(f"Win rates: {results.win_rates}")
```

> 🔒 **Models are explicit**  
> Provider-backed players never fall back to defaults; pass `model=` for every GPT/Claude/Gemini player.
>
> ℹ️ **Provider credentials**  
> Set the provider-specific environment variables before running examples (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `VERTEX_PROJECT_ID`/`VERTEX_LOCATION` for Gemini). For Gemini on Vertex, AgentDeck also supports `GOOGLE_APPLICATION_CREDENTIALS_B64` for base64-encoded service-account JSON. Start from [`.env.example`](./.env.example) for local setup.

> 📝 **`.env` loading policy**  
> AgentDeck does not auto-load `.env` at the library level. Source it in your shell or load it in your entry script.

### Try AgentDeck Without API Keys
- Run `python examples/mock_demo.py`
- Uses `MockPlayer` (deterministic) so no LLM providers are needed
- Shows live commentary + progress + stats, and saves recordings under `agentdeck_runs/mock_demo/<session>/records/`

### Walkthroughs & Docs
- Build your first game + replay tour: `examples/first_game_walkthrough.py`
- Examples index: `examples/README.md`
- End-to-end study workflow: `docs/how-to-run-a-study.md`

### Artifacts (Recordings + Logs)

After you run a batch, AgentDeck writes artifacts under `agentdeck_runs/<session_id>/` (or your
configured `run_dir`):

- `records/` contains a `batch_<batch_id>.json` summary plus one `match_*.json` per match
- `logs/` contains `info.log` and `debug.log` by default

Tip: open a match JSON to see prompts, raw responses, parsed actions, costs, and the full event
timeline.

### Parallel Execution (Workload-Dependent Speedups)
```python
from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck import LogLevel

# Configure parallel execution with real-time monitoring
config = AgentDeckConfig(
    seed=42,
    concurrency=10,      # Run 10 matches in parallel
    log_level=LogLevel.INFO
)

# Run 100 matches with automatic progress tracking
with AgentDeck(game=game, session=config) as deck:
    results = deck.play(players=players, matches=100)

# ProgressMonitor is auto-attached when concurrency > 1 (unless monitors=[] is provided)
```
> Performance depends on provider rate limits and workload. For a determinism + concurrency comparison,
> see [`examples/test_parallel_execution.py`](examples/test_parallel_execution.py).

---

## 💡 Key Features

### 1. Event-Driven Observation
Everything is observable through events - no modifications needed to games:

```python
from agentdeck import AgentDeck
from agentdeck.spectators import MatchNarrator, TokenUsageTracker

# Add spectators for observation
with AgentDeck(game=game, spectators=[
    MatchNarrator(),      # Turn-by-turn commentary
    TokenUsageTracker()   # Cost tracking
]) as deck:
    results = deck.play(players, matches=10)
```

### 2. Complete Recording & Replay
Every match is automatically recorded with full metadata:

```python
from pathlib import Path

from agentdeck import AgentDeck, MatchNarrator

with AgentDeck(game=game) as deck:
    results = deck.play(players, matches=3, seed=7)

    # Replay from memory (no file I/O)
    deck.replay(match=results[0], spectators=[MatchNarrator()], speed=0.0)

    # Or replay from disk (recorded under records/)
    record_dir = Path(deck.session.record_directory)
    match_path = sorted(record_dir.glob("match_*.json"))[0]
    deck.replay(path=match_path, spectators=[MatchNarrator()], speed=0.0)
```

**Replay Parity Guarantee**: Replay emits identical event stream as live execution, including complete three-phase lifecycle (handshake → gameplay → conclusion).

### 3. Reproducible Experiments
Seeding makes **game-level randomness** reproducible (player ordering, RNG) and guarantees recording/replay parity.
However, **LLM outputs are not guaranteed to be deterministic across runs**, even with a fixed seed.

```python
from agentdeck import AgentDeck, AgentDeckConfig, MockPlayer

config = AgentDeckConfig(seed=42)
players = [
    MockPlayer(name="Alice", actions=["ATTACK", "POTION"]),
    MockPlayer(name="Bob", actions=["POTION", "ATTACK"]),
]

with AgentDeck(game=game, session=config) as deck:
    results = deck.play(players=players, matches=10)
```

### 4. Three-Phase Player Lifecycle
Players go through structured interaction phases:

1. **Handshake** (Mandatory): Player acknowledges rules and format
2. **Turn** (Gameplay): Player makes decisions each turn
3. **Conclusion** (Optional): Player reflects on match outcome

This provides rich data for analyzing AI behavior patterns.

---

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Workflow, local setup, tests
- **[Specs](specs/SPEC.md)** - Specification index (source of truth)
- **[ROADMAP.md](ROADMAP.md)** - Implementation progress and future plans
- **[Examples](examples/README.md)** - Runnable examples and tutorials

### AI Assistants

Project assistants for exploration, development, and research:

[![GPT Assistant](https://img.shields.io/badge/GPT-AgentDeck-74aa9c?logo=openai&logoColor=white)](https://chatgpt.com/g/g-6923cdbde5648191a202c3f9a8a8796c-agentdeck)
[![Gemini Gem](https://img.shields.io/badge/Gem-AgentDeck-4285F4?logo=google&logoColor=white)](https://gemini.google.com/gem/1i6xn0HwFMaCNNeo392WCw1yQQzEsUxix?usp=sharing)

---

## 🎯 Design Principles

1. **Spec-Driven**: Every component has a rigorous specification
2. **Observable**: Every decision is captured and analyzable
3. **Reproducible**: Everything we control is reproducible (seeding + recordings + replay parity)
4. **Composable**: Mix and match components freely
5. **Research-First**: Built by researchers, for researchers

---

## 📝 License

MIT License (see [LICENSE](LICENSE)).

---

**Built with ❤️ for AI researchers**

*Spec-Driven Architecture for AI Behavioral Research*
