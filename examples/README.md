# AgentDeck Examples

This directory contains practical examples demonstrating AgentDeck usage patterns.

## Recommended Learning Path

If you are new to the repo, run these in order:

1. `mock_demo.py`
2. `first_game_walkthrough.py`
3. `archivist_choice_demo.py`
4. `minimal_experiment.py`
5. `spectator_example.py`
6. `replay_minimal.py`
7. `test_parallel_execution.py`
8. `replay_curate_match.py`

These examples form the intended onboarding ladder: no-provider install check,
custom game authoring, a non-combat benchmark-style game, minimal LLM experiment,
spectators, replay, parallel execution, then replay-driven viewer curation.

## Quick Start Examples

### 1. Zero-Dependency Mock Demo (`mock_demo.py`)

**Purpose**: Verify your install without any API keys or SDKs.

**What You'll Learn**:
- Deterministic MockPlayer gameplay (no network calls)
- Where recordings/logs are stored (`agentdeck_runs/mock_demo/...`)
- Live reporting and stats via spectators

**Usage**:
```bash
python examples/mock_demo.py
```

---

### 2. Build Your First Game (`first_game_walkthrough.py`)

**Purpose**: Author a tiny turn-based game, run it with deterministic mock players, and replay the recording.

**What You'll Learn**:
- How to subclass `TurnBasedGame` and define `setup()`, `get_view()`, `update()`, `status()`
- Running without API keys using `MockPlayer`
- Recording and replaying with `Recorder` + `ReplayEngine`

**Usage**:
```bash
python examples/first_game_walkthrough.py
```

---

### 3. Non-Combat Benchmark (`archivist_choice_demo.py`)

**Purpose**: Show a maintained non-combat game where agents triage manuscripts instead of fighting.

**What You'll Learn**:
- Independent per-player decision queues that avoid first-player advantage
- Deterministic mock policies for policy comparison
- Viewer-compatible recordings for a non-combat game

**Usage**:
```bash
python examples/archivist_choice_demo.py
```

---

### 4. Minimal Configuration (`minimal_experiment.py`)

**Purpose**: Demonstrate the simplest possible setup for running LLM agent experiments.

**What You'll Learn**:
- Minimal player configuration (only `name`, `model`, `controller` required)
- Smart defaults for templates, renderers, and controllers
- Real-time progress monitoring with spectators
- Token usage and cost tracking
- The shortest real-provider path: one match, one recording, one replayable artifact

**Usage**:
```bash
export OPENAI_API_KEY="sk-..."
python examples/minimal_experiment.py
```

Runs a single match by default so you can validate credentials, recordings, and replay before scaling up.

**Smart Defaults Used**:
- `renderer`: TextRenderer()
- `prompt_builder`: PromptBuilder() with default templates
- Handshake template: game instructions + gameplay format + handshake acknowledgement format
- Turn template: `{game_view}`
- Conclusion template: omitted unless explicitly provided

---

### 5. Spectator Monitoring (`spectator_example.py`)

**Purpose**: Show how to use spectators for experiment monitoring and analysis.

**What You'll Learn**:
- Multiple spectators working together
- Real-time progress display with ETA
- Token usage tracking (for LLM players)
- Match statistics collection

**Usage**:
```bash
python examples/spectator_example.py
```

**Spectators Demonstrated**:
- `ProgressDisplay`: Real-time match progress with ETA
- `TokenUsageTracker`: API cost tracking per player/model
- `StatsTracker`: Win rates, actions, timing statistics

---

### 6. Parallel Execution (`test_parallel_execution.py`)

**Purpose**: Demonstrate parallel match execution with configurable concurrency.

**What You'll Learn**:
- Worker-based parallel execution (SPEC-PARALLEL v1.0.0)
- Deterministic seeding for reproducible results
- Event replay in match_index order
- Automatic progress monitoring with ProgressMonitor
- How concurrency changes throughput on a provider-limited workload

**Usage**:
```bash
export OPENAI_API_KEY="sk-..."
python examples/test_parallel_execution.py
```

**Key Features**:
- `concurrency=10`: Run up to 10 matches in parallel
- Auto-attached ProgressMonitor for real-time tracking
- Perfect spectator/recorder parity
- Deterministic replay guarantee

---

### 7. Replay Engine (`replay_minimal.py`)

**Purpose**: Replay a previously recorded match with full lifecycle observation.

**What You'll Learn**:
- Loading and replaying match recordings
- Spectators observe replay identically to live execution
- Event parity guarantee (R1) from SPEC-REPLAY v1.0.0
- Token usage reconstruction from metadata

**Usage**:
```bash
# Replay most recent recording
python examples/replay_minimal.py

# Replay specific recording
python examples/replay_minimal.py --recording agentdeck_runs/session_XXX/records/match_YYY.json --speed 1.0
```

**Replay Features**:
- Automatic discovery of latest recording
- Configurable replay speed (0.0 = instant, 1.0 = real-time)
- Full three-phase lifecycle (handshake → gameplay → conclusion)
- Identical spectator experience to live matches

---

### 8. Match Curation (`replay_curate_match.py`)

**Purpose**: Generate viewer-ready sidecar metadata from an existing match
record.

**What You'll Learn**:
- Replay-driven post-analysis with `MatchCurator`
- Writing `*.meta.json` next to a match file
- How viewer subtitles, synopses, highlight markers, and optional highlight
  kinds can be derived from the same replay artifact

**Usage**:
```bash
python examples/replay_curate_match.py viewer/matches/fixed-damage-01-flashlite-ao-collapse-vs-flash-ao.json
```

---

## Research-Oriented Examples

These are useful once you already know the basics:

- `hangman_demo.py`
- `hangman_benchmark.py`
- `hangman_gpt4o_reasoning.py`
- `hangman_llm_test.py`
- `hangman_llm_test_reasoning.py`

These are more scenario-specific than the onboarding ladder above.

---

## Internal / Diagnostic Examples

These are maintained as repo utilities or smoke checks rather than first-touch
examples:

- `test_minimal_setup.py`
- `test_prompt_builder_ux_full.py`
- `test_prompt_builder_ux_minimal.py`
- `test_research_compare_models.py`
- `test_research_gpt_compare.py`
- `run_auction_replay.py`

---

## Example Patterns

### Running with Different LLM Providers

#### OpenAI (GPT)
```python
from agentdeck.players.openai_player import GPTPlayer

player = GPTPlayer(
    name="Alice",
    model="gpt-4o-mini",  # or "gpt-4", "gpt-3.5-turbo"
    temperature=0.7,
    controller=ActionOnlyController(),
)
```

#### Anthropic (Claude)
```python
from agentdeck.players.anthropic_player import ClaudePlayer

player = ClaudePlayer(
    name="Bob",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    controller=ActionOnlyController(),
)
```

#### Google (Gemini)
```python
from agentdeck.players.google_player import GeminiPlayer

player = GeminiPlayer(
    name="Charlie",
    model="gemini-2.5-flash-lite",
    project_id="your-gcp-project-id",
    location="us-central1",
    temperature=0.7,
    controller=ActionOnlyController(),
)
```

Gemini uses the Google Gen AI SDK in Vertex mode. You can provide credentials
through standard ADC or through `GOOGLE_APPLICATION_CREDENTIALS_B64` when your
environment injects secrets as base64.

### Using Context Manager (Recommended)

```python
with AgentDeck(game=game, session=config) as deck:
    results = deck.play(players, matches=1)
    # Session automatically closes on exit
```

### Adding Spectators

```python
from agentdeck import ProgressDisplay, TokenUsageTracker, StatsTracker

deck = AgentDeck(
    game=game,
    spectators=[
        ProgressDisplay(show_eta=True),
        TokenUsageTracker(),
        StatsTracker(),
    ],
    session=config,
)
```

### Accessing Results

```python
results = deck.play(players, matches=10)

for result in results:
    print(f"Winner: {result.winner}")
    print(f"Turns: {result.metadata['turns']}")
    print(f"Duration: {result.metadata['duration']:.2f}s")
    print(f"Seed: {result.seed}")
```

---

## Configuration Options

### Session Configuration

```python
from agentdeck import AgentDeckConfig
from agentdeck.core.types import LogLevel

config = AgentDeckConfig(
    seed=42,                      # Deterministic RNG
    concurrency=1,                # Parallel workers (default: 1 = sequential)
    run_dir="./agentdeck_runs",   # Session root; logs/ and records/ live under it
    log_level=LogLevel.INFO,      # Log verbosity
    max_turns=100,                # Turn limit per match
)
```

### Parallel Execution Configuration

```python
from agentdeck import AgentDeckConfig
from agentdeck.monitors import ProgressMonitor

# Default: Auto-attached ProgressMonitor (mode="normal")
config = AgentDeckConfig(
    seed=42,
    concurrency=10,              # Run 10 matches in parallel
)

# Verbose: Show worker-level details
config = AgentDeckConfig(
    seed=42,
    concurrency=10,
    monitors=[ProgressMonitor(mode="verbose")]
)

# Silent: No progress monitoring
config = AgentDeckConfig(
    seed=42,
    concurrency=10,
    monitors=[]                  # Explicit opt-out
)
```

### Game Configuration

```python
from agentdeck import FixedDamageGame

game = FixedDamageGame(
    max_health=100,
    attack_damage=20,
    starting_potions=3,
    potion_heal=30,
)
```

---

## Common Use Cases

### 1. Quick Baseline Test (3-5 matches)
```python
deck.play(players, matches=3, seed=42)
```

### 2. Statistical Analysis (50-100 matches)
```python
stats = StatsTracker()
deck = AgentDeck(game=game, spectators=[stats])
deck.play(players, matches=100)

summary = stats.get_stats()
print(f"Player1 win rate: {summary['players']['Player1']['win_rate']:.1%}")
```

### 3. Cost Estimation
```python
tokens = TokenUsageTracker()
deck = AgentDeck(game=game, spectators=[tokens])
deck.play(players, matches=10)

cost_per_match = tokens.get_average_cost_per_match(10)
print(f"Estimated cost for 100 matches: ${cost_per_match * 100:.2f}")
```

### 4. Batch Execution (Multiple Runs)
```python
deck = AgentDeck(game=game, spectators=[ProgressDisplay()])

# Run multiple batches
deck.play(players, matches=50, seed=1)
deck.play(players, matches=50, seed=2)
deck.play(players, matches=50, seed=3)
```

---

## Environment Variables

Required for LLM players:

```bash
# Copy `.env.example` to `.env`, then source it or load it with `python-dotenv`

# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Vertex AI (Gemini)
export VERTEX_PROJECT_ID="your-gcp-project-id"
export VERTEX_LOCATION="us-central1"

# Optional: base64-encoded service-account JSON for ADC-free secret injection
export GOOGLE_APPLICATION_CREDENTIALS_B64="$(base64 < /path/to/service-account.json | tr -d '\n')"
```

If `GOOGLE_APPLICATION_CREDENTIALS_B64` is set and the decoded service-account
JSON includes `project_id`, AgentDeck can infer the Vertex project automatically.

---

## Next Steps

- Check `docs/SPEC-*.md` for detailed specifications
- See `tests/` for more usage patterns
- Build custom games by extending `Game` base class
- Create custom spectators by extending `Spectator` base class

---

## Questions?

- GitHub Issues: https://github.com/agentdeck/agentdeck/issues
- Documentation: See `docs/` directory
- Examples: This directory (`examples/`)
