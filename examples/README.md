# AgentDeck Examples

This directory contains practical examples demonstrating AgentDeck usage patterns.

## Quick Start Examples

### 0. Zero-Dependency Mock Demo (`mock_demo.py`)

**Purpose**: Verify your install without any API keys or SDKs.

**What You'll Learn**:
- Deterministic MockPlayer gameplay (no network calls)
- Where recordings/logs are stored (`agentdeck_runs/mock_demo/...`)
- Live commentary and stats via spectators

**Usage**:
```bash
python examples/mock_demo.py
```

---

### 1. Minimal Configuration (`minimal_experiment.py`)

**Purpose**: Demonstrate the simplest possible setup for running LLM agent experiments.

**What You'll Learn**:
- Minimal player configuration (only `name`, `model`, `action_controller` required)
- Smart defaults for templates, renderers, and controllers
- Real-time progress monitoring with spectators
- Token usage and cost tracking

**Usage**:
```bash
export OPENAI_API_KEY="sk-..."
python examples/minimal_experiment.py
```

**Smart Defaults Used**:
- `handshake_controller`: HandshakeController()
- `renderer`: TextRenderer()
- `prompt_builder`: PromptBuilder() with default templates
- Templates: System-provided defaults for handshake, turn, conclusion

---

### 2. Spectator Monitoring (`spectator_example.py`)

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

### 3. Parallel Execution (`test_parallel_execution.py`)

**Purpose**: Demonstrate parallel match execution with configurable concurrency.

**What You'll Learn**:
- Worker-based parallel execution (SPEC-PARALLEL v1.0.0)
- Deterministic seeding for reproducible results
- Event replay in match_index order
- Automatic progress monitoring with ProgressMonitor
- 10× speedup with concurrency=10

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

### 4. Replay Engine (`replay_minimal.py`)

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
python examples/replay_minimal.py --recording agentdeck_records/session_XXX/match_YYY.json --speed 1.0
```

**Replay Features**:
- Automatic discovery of latest recording
- Configurable replay speed (0.0 = instant, 1.0 = real-time)
- Full three-phase lifecycle (handshake → gameplay → conclusion)
- Identical spectator experience to live matches

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
    action_controller=ActionOnlyController(),
)
```

#### Anthropic (Claude)
```python
from agentdeck.players.anthropic_player import ClaudePlayer

player = ClaudePlayer(
    name="Bob",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    action_controller=ActionOnlyController(),
)
```

#### Google (Gemini)
```python
from agentdeck.players.google_player import GeminiPlayer

player = GeminiPlayer(
    name="Charlie",
    model="gemini-1.5-flash",
    temperature=0.7,
    action_controller=ActionOnlyController(),
)
```

### Using Context Manager (Recommended)

```python
with AgentDeck(game=game, session=config) as deck:
    results = deck.play(players, matches=10)
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
    log_dir="./logs",             # Log directory
    record_dir="./recordings",    # Recording directory
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
    initial_potions=3,
    potion_healing=30,
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
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google
export GOOGLE_API_KEY="..."
```

---

## Next Steps

- Check `docs/SPEC-*.md` for detailed specifications
- See `tests/` for more usage patterns
- Build custom games by extending `Game` base class
- Create custom spectators by extending `Spectator` base class

---

## Questions?

- GitHub Issues: https://github.com/anthropics/agentdeck-wip/issues
- Documentation: See `docs/` directory
- Examples: This directory (`examples/`)
