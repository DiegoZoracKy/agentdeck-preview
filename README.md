# AgentDeck 🎮

**The game console for AI agents.**

A research platform for analyzing AI agent behavior through game scenarios.

[Why Games?](#-why-games) · [Quick Start](#-quick-start) · [AI-First](#spec-driven-and-ai-first-by-design) · [Docs](docs/README.md) · [Examples](examples/README.md) · [Research](research/README.md) · [Specs](specs/SPEC.md)

---

## 🎯 Purpose & Vision

AgentDeck helps you turn a behavioral question into a concrete study: define a game or reuse an existing one, run seeded matches across models and controllers, replay every decision, and export artifacts you can validate and compare.

It is useful when static prompt-response evaluation is not enough. By putting agents inside structured games, AgentDeck makes state, incentives, and resource tradeoffs explicit so behavior is easier to observe, compare, replay, and explain.

![AgentDeck Overview](docs/images/agentdeck-whiteboard-overview.png)

---

## 🚦 Current Capabilities

AgentDeck currently supports:
- Core match execution through the `AgentDeck` facade
- Provider-backed and mock-player experiments
- Recording, replay, and event-driven observability
- Native fairness controls for paired side-swap and explicit first-player policies
- Matrix-based research packages
- Research export, artifact validation, behavioral profiles, and post-hoc analysis workflows
- Curated replay/viewer workflows for selected studies

---

## Spec-Driven and AI-First by Design

AgentDeck is human-led and AI-written: a codebase built with AI agents, designed for humans and AI agents, and validated through tests, replayable experiments, research artifacts, and blind QA rounds performed by autonomous agents.

Specs are the source of truth. They define intent, contracts, boundaries, and expected behavior. Code, tests, docs, examples, and research workflows derive from that specification layer and are validated through execution.

AgentDeck is therefore designed to be legible to both humans and AI agents, treating AI agents as first-class users, contributors, evaluators, and research operators.

---

## 🎮 Why Games?

Most LLM benchmarks measure **knowledge** through static questions. AgentDeck focuses on **behavior**: maintaining state, adapting over time, and making tradeoffs inside explicit rules.

Game scenarios work well because they make the important variables legible:
- **Constrained environments** – Isolate specific variables (for example, resource scarcity or turn order)
- **Iterative decision making** – Agents live with consequences, testing longer-horizon behavior
- **Social dynamics** – Multiplayer games reveal cooperation, betrayal, and negotiation patterns
- **Measurable outcomes** – Win/lose provides a clean signal for cost/quality trade-offs

---

## 🔎 Flagship Evidence

The [Agentic Edge study](research/2026-04-27-agentic-edge-strategy-stack/README.md) uses AgentDeck to test whether agent design can overcome model-tier gaps in sequential decision games.

In FixedDamage, the same lower-tier model moves from failure to a tier inversion as the agent wrapper changes:

| Agent configuration | Opponent | Result |
| --- | --- | --- |
| FlashLite S0 action-only | GPT-4o-mini S0 action-only | 0/48 wins (0.0%) |
| FlashLite S1 reasoning controller | GPT-4o-mini S0 action-only | 34/48 wins (70.8%) |
| FlashLite S3 reasoning + HP grounding | GPT-4o-mini S0 action-only | 38/48 wins (79.2%) |

The VariableDamage transfer result is more cautious: the adapted risk-grounded stack wins its same-model mechanism test, but the cross-tier result is seat-sensitive and not statistically strong. That caveat is the point: AgentDeck is built to expose behavior, not hide messy evidence.

---

## 🚀 Quick Start

> **Install**: `pip install agentdeck-ai` (import as `agentdeck`)
>
> **AI-first prompt**: Ask Claude, Codex, or your coding agent:
> “Learn AgentDeck from the README, create a tiny tic-tac-toe game, run a few matches, then analyze the recorded behavior.”

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
git clone https://github.com/agentdeck/agentdeck.git
cd agentdeck
pip install -e ".[dev]"
```

### Your First Experiment
```python
from agentdeck import (
    ActionOnlyController,
    AgentDeck,
    FixedDamageGame,
    GPTPlayer,
    ReasoningController,
)

# 1. Create a game
game = FixedDamageGame(
    max_health=100,
    attack_damage=20,
    potion_heal=30,
    starting_potions=3,
    information_level="full",  # use "partial" to hide opponent HP/potions
)

# 2. Create AI players: same model, different behavioral interface
players = [
    GPTPlayer(
        name="SameModel-AO",
        model="gpt-4o-mini",
        temperature=0.7,
        controller=ActionOnlyController(),
    ),
    GPTPlayer(
        name="SameModel-RC",
        model="gpt-4o-mini",
        temperature=0.7,
        controller=ReasoningController(),
    ),
]

# Models must be provided explicitly for every provider-backed player.

# 3. Run experiment
with AgentDeck(game=game) as deck:
    results = deck.play(
        players=players,
        matches=1,
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
> In `bash`/`zsh`, a simple local setup is:
> `set -a; source .env; set +a`

> ✅ **First real provider-backed run**
> Start with `matches=1` so you can confirm credentials, recordings, and replay before scaling up.

> 🎮 **FixedDamageGame information level**
> `information_level="full"` shows both players' HP and potion counts.
> `information_level="partial"` hides the opponent's HP and potions while still showing last actions.

### Try AgentDeck Without API Keys
- Run `python examples/mock_demo.py`
- Uses `MockPlayer` (deterministic) so no LLM providers are needed
- Shows live reporting + progress + stats, and saves recordings under `agentdeck_runs/mock_demo/<session>/records/`

### Recommended Learning Path
1. `examples/mock_demo.py` — verify the install with a zero-provider run
2. `examples/first_game_walkthrough.py` — build a tiny game and replay it
3. `examples/minimal_experiment.py` — run the smallest real provider-backed experiment
4. `examples/spectator_example.py` and `examples/replay_minimal.py` — add monitoring and replay workflows

For the full ladder, see [examples/README.md](examples/README.md).

### Walkthroughs & Docs
- Build your first game + replay tour: `examples/first_game_walkthrough.py`
- Examples index: [examples/README.md](examples/README.md)
- End-to-end study workflow: [docs/how-to-run-a-study.md](docs/how-to-run-a-study.md)
- Package-owned behavioral scoring: keep `scripts/behavioral_scorer.py` in
  your research package and run `agentdeck-research-score` after export to
  populate the targeted `results.json.behavioral_profile` (`artifacts/<cell>/results.json`
  for matrix studies, top-level `results.json` for direct packages)

### Artifacts (Recordings + Logs)

After you run a batch, AgentDeck writes artifacts under `agentdeck_runs/<session_id>/` (or your
configured `run_dir`):

- `records/` contains a `batch_<batch_id>.json` summary plus one `match_*.json` per match
- `logs/` contains `info.log` and `debug.log` by default

Tip: open `batch_<batch_id>.json` first for the high-level batch summary, then open `match_*.json`
for the full audit trail, replay source, prompts, raw responses, parsed actions, costs, and event
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

## 🔬 Research Program

This repo ships release-facing benchmark packages, arc summaries, and a cross-game synthesis layer alongside the engine.

Start here:
- **[The Agentic Edge](research/2026-04-27-agentic-edge-strategy-stack/README.md)** - Flagship study: strategy-stack effects, FixedDamage tier inversion, VariableDamage caveats, and public replay artifacts
- **[How To Run A Study](docs/how-to-run-a-study.md)** - Supported end-to-end workflow for creating, running, exporting, and validating a study

Supporting arcs:
- **[FixedDamage Arc 1](research/2026-03-23-fixed-damage-arc-1/README.md)** - Deterministic flagship arc: diagnosis, intervention ladder, and final carry-forward stack
- **[VariableDamage Arc 1](research/2026-03-26-variable-damage-arc-1/README.md)** - Uncertainty arc: risk-band metrics, transfer failures, and premium ceiling check
- **[Cross-Game Comparison 1](research/2026-03-26-cross-game-comparison-1/README.md)** - What transferred, what broke, and why the metrics had to evolve

Deeper references:
- **[Research Guide](research/README.md)** - How experiment packages are organized
- **[Research Index](research/INDEX.md)** - Registry of experiments and status
- **[Research Schema](research/SCHEMA.md)** - Contract for manifests, results, and validation
- **[Research Templates](research/_templates/)** - Boilerplate for new experiment packages

## ⚙️ Architecture

### The Console Metaphor

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
- Examples: [FixedDamageGame](src/agentdeck/games/examples/fixed_damage/) and
  [ArchivistChoiceGame](src/agentdeck/games/examples/archivist_choice.py)

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
- `MatchReporter` - turn-by-turn reporting
- `MatchCurator` - sidecar metadata for replay viewer curation
- `ProgressDisplay` - real-time progress with ETA
- `TokenUsageTracker` - cost tracking per player/model
- `StatsTracker` - win rates and performance metrics

**Recording & Replay**
- `Recorder` - captures complete match data to JSON
- `ReplayEngine` - reconstructs matches with event parity guarantee

---

## 💡 Key Features

### 1. Event-Driven Observation
Everything is observable through events - no modifications needed to games:

```python
from agentdeck import AgentDeck
from agentdeck.spectators import MatchReporter, TokenUsageTracker

# Add spectators for observation
with AgentDeck(game=game, spectators=[
    MatchReporter(),      # Turn-by-turn reporting
    TokenUsageTracker()   # Cost tracking
]) as deck:
    results = deck.play(players, matches=1)
```

### 2. Complete Recording & Replay
Every match is automatically recorded with full metadata:

```python
from pathlib import Path

from agentdeck import AgentDeck, MatchReporter

with AgentDeck(game=game) as deck:
    results = deck.play(players, matches=3, seed=7)

    # Replay from memory (no file I/O)
    deck.replay(match=results[0], spectators=[MatchReporter()], speed=0.0)

    # Or replay from disk (recorded under records/)
    record_dir = Path(deck.session.record_directory)
    match_path = sorted(record_dir.glob("match_*.json"))[0]
    deck.replay(path=match_path, spectators=[MatchReporter()], speed=0.0)
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

- **[Documentation Index](docs/README.md)** - Main docs entry point
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Workflow, local setup, tests
- **[Specs](specs/SPEC.md)** - Specification index (source of truth)
- **[Examples](examples/README.md)** - Runnable examples and tutorials
- **[Security Policy](SECURITY.md)** - Vulnerability reporting process

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
