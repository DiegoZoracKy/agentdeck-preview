# Contributing to AgentDeck

> **First Time?** Start with [SPEC.md](specs/SPEC.md) §3 Core Design Principles, then read this guide.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Core Philosophy](#core-philosophy)
3. [Contribution Workflow](#contribution-workflow)
4. [Writing Specifications](#writing-specifications)
5. [Writing Code](#writing-code)
6. [Testing Requirements](#testing-requirements)
7. [Code Review Checklist](#code-review-checklist)

---

## Project Overview

AgentDeck is an **execution and evidence engine for AI agents in game scenarios**. Think of it as a "game console" where:

- **Games** define rules and environments
- **Players** are AI agents making decisions
- **Controllers** parse AI responses into game actions
- **Renderers** format game state for AI consumption
- **Spectators** observe matches without interfering

**Target Audience**: AI-agent developers, game authors, and systems that need inspectable execution Records

AgentDeck owns execution truth. Research questions, corpus selection, measurements,
statistical inference, and claims belong to downstream systems.

**For complete architectural principles**, see [SPEC.md](specs/SPEC.md) §3.

### Repository Layout

```
src/agentdeck/      # Library code
tests/              # Unit + integration tests
examples/           # Runnable examples
specs/              # Specifications (source of truth)
docs/               # Documentation + diagrams
research/           # Frozen historical study artifacts
scripts/            # CI/dev utilities
```

Runtime artifacts (recordings/logs) are written under `agentdeck_runs/` by default and are ignored by git.

Game file location convention:
- Put reusable game implementations under `src/agentdeck/games/` so tests and downstream users can import them from the package.
- Keep runnable demos, walkthroughs, and one-off harnesses in `examples/`.
- Add coverage under `tests/`.
- Only place a game directly under `examples/` when it is intentionally example-only and not meant to ship as part of the importable library surface.
- For repo-local example games that should remain importable but not become core built-ins, prefer `src/agentdeck/games/examples/<slug>/`.

---

## Core Philosophy

AgentDeck marries modern software engineering best practices with the timeless Unix philosophy:

### Architecture: Modularity & Composition

- **Do One Thing Well**: Each component must have a single, well-defined responsibility
  > *Unix Rule of Modularity*: Write simple parts connected by clean interfaces

- **Compose, Don't Integrate**: Components must be pluggable and interchangeable
  > *Unix Rule of Composition*: Design programs to be connected to other programs

- **Separate Policy from Mechanism**: Core logic must be independent of presentation layer
  > *Unix Rule of Separation*: Separate policy from mechanism; separate interfaces from engines

### Code Quality: Simplicity & Clarity

- **Simplicity is Sacred**: Design for simplicity; add complexity only where you must
  > *Unix Rule of Simplicity*

- **Clarity Over Cleverness**: Write code for humans first
  > *Unix Rule of Clarity*: Clarity is better than cleverness

- **Don't Repeat Yourself (DRY)**: Eliminate duplication

### Robustness & Data Flow

- **Data is King**: Fold knowledge into data structures so program logic can be simple and robust
  > *Unix Rule of Representation*

- **Fail Fast & Noisily**: When a component must fail, do so as early and loudly as possible
  > *Unix Rule of Repair*: When you must fail, fail noisily and as soon as possible

### Execution Substrate Focus

AgentDeck supports:

- **Rapid Execution**: Can callers run a Game in <5 lines of code?
- **Controlled Reproducibility**: Deterministic framework behavior via seeded RNG
- **Flexibility**: Support different input formats (text/image/JSON)
- **Execution Truth**: Comprehensive event emission and canonical recording
- **Interoperability**: Components plug together without glue code

---

## Contribution Workflow

AgentDeck follows a **strict spec-first approach**: **No implementation without approved specifications.**

### Why Spec-Driven?

**Benefits:**
1. **Prevents Drift** - Specs keep us aligned on requirements before coding
2. **Enables AI Collaboration** - AI assistants can implement from clear specs
3. **Reduces Rework** - Catch design issues in specs, not in code
4. **Team Alignment** - Everyone agrees on "what" before debating "how"
5. **Living Documentation** - Specs stay current with implementation
6. **Quality** - Specs define success criteria upfront

**Without specs:**
- ❌ Implementation drift (wrong approach)
- ❌ Rework (build wrong thing, then rebuild)
- ❌ Team misalignment (different mental models)
- ❌ Missing edge cases
- ❌ Incomplete testing

---

### The Three-Phase Process

Every feature/task follows this workflow:

```
Phase A: Specification → Phase B: Implementation → Phase C: Testing & Validation
```

#### Phase A: Specification Work

**Goal**: Define **what** we're building with consensus

**Process**:
1. **Draft specs** following [Writing Specifications](#writing-specifications) guidelines
   - Create draft in `specs/drafts/SPEC-<component>-v<version>.md`
   - Drafts stay in `drafts/` until approval
2. **Review** - Relevant contributors review the spec
   - Check product/user perspective
   - Check technical feasibility
   - Check pragmatic implementability and edge cases
3. **Incorporate feedback** - Refine specs based on reviews
   - Update draft in `specs/drafts/`
4. **Maintainer gate** - **A maintainer must approve before Phase B**
   - AgentDeck is currently maintainer-led while the contributor model evolves
   - Once approved, move spec from `drafts/` to `specs/`
   - Update version in main spec file (or create new file for major versions)

**Deliverables**:
- Approved SPEC-*.md files in `specs/` (moved from `drafts/`)
- Updated related specs for consistency
- Approval state documented (in commit message)

**Exit Criteria**:
- [ ] Specs follow `specs/GUIDELINES.md`
- [ ] All invariants documented (e.g., GB1-GB6)
- [ ] All success criteria defined
- [ ] All edge cases addressed
- [ ] A maintainer confirms requirements are met
- [ ] Technical soundness confirmed
- [ ] Implementability confirmed

---

#### Phase B: Implementation Work

**Goal**: Build exactly what the specs define

**Process**:
1. **Implement** - Write code matching specs exactly
   - Follow method signatures exactly (parameter names matter)
   - Enforce all invariants (GB1-GB6, EI1-EI3, etc.)
   - Match behavior precisely (no creative interpretation)
2. **Code review** - Reviewers check implementation
   - Verify spec compliance
   - Catch implementation bugs
   - Suggest improvements
3. **Iterate** - Fix issues found in review
4. **Approval** - Review is completed

**Deliverables**:
- Working implementation (code files)
- Updated tests (verify spec compliance)
- Updated imports/exports (package integrity)

**Exit Criteria**:
- [ ] Code matches spec exactly
- [ ] All invariants enforced
- [ ] Tests pass
- [ ] No regressions (existing tests still pass)
- [ ] Review completed

**⚠️ BLOCKED until Phase A complete** (approved specs required)

---

#### Phase C: Testing & Validation

**Goal**: Verify implementation meets all success criteria

**Process**:
1. **Unit testing** - Test individual components
2. **Integration testing** - Test component interactions
3. **Live API testing** - Test with real LLM providers (if applicable)
4. **Success criteria verification** - Check all Phase A criteria met
5. **Edge case testing** - Verify defensive behavior

**Deliverables**:
- Passing test suite
- Live validation results (if applicable)
- Success criteria confirmation

**Exit Criteria**:
- [ ] All tests pass (unit + integration)
- [ ] All success criteria met
- [ ] Live validation successful (if applicable)
- [ ] No regressions introduced
- [ ] Results validated

---

## Writing Specifications

Specifications define contracts that both humans and AI agents implement. They are the source of truth for AgentDeck components.

### When to Write a Spec

**Write a full spec for:**
- Components with cross-cutting impact
- Non-trivial lifecycle or state machines
- Public or stable APIs
- Components requiring reproducibility/observability guarantees
- Anything with subtle invariants that tests must verify

**Skip full specs for:**
- Simple utilities documented by type hints
- CRUD wrappers with no business logic
- Rapid prototypes (use design notes instead)
- Thin pass-through adapters

### Specification Template

Use this structure (see `specs/_template.md`):

```markdown
# SPEC-COMPONENT v1.0.0

## 1. Purpose
[What problem? Who uses it? Why does it exist?]

## 2. Terminology
[Key terms, abbreviations, domain concepts]

## 3. Architecture
[How this fits in the system, dependencies, data flow]

## 4. Data Structures
[Schemas, types, payload formats - omit if not applicable]

## 5. Invariants
[Rules that MUST hold - enumerate as GB1, GB2, etc.]

## 6. Error Handling
[What fails, when, error messages, logging]

## 7. Testing Strategy
[How to validate invariants, test scenarios]

## 8. Examples
[Runnable code demonstrating usage]

## 9. Design Rationale
[Why these decisions? Alternatives considered?]
```

### Writing Principles

#### Abstraction Level: Contracts, Not Implementation

**Core Principle**: Specs define **WHAT** the system must guarantee, not **HOW** the code implements it.

**✅ DO document (behavioral guarantees):**
- "MUST emit SESSION_START before accepting operations"
- "MUST reject empty player lists with ValueError"
- "Match i MUST use seed S+i for reproducibility"
- "MUST NOT mutate input state"
- "Session spectators MUST receive events from all play() calls"

**❌ DON'T document (implementation details):**
- "Call `self.console.event_bus.emit(...)`"
- "For i in range(matches): seed = base_seed + i"
- "Sets self._closed to True before emitting"
- Line-by-line code walkthroughs
- Internal method names (`_cleanup()`, `_prepare()`)

**Red flags you're too low-level:**
- 🚩 Referencing line numbers (`[file.py:123]`)
- 🚩 Describing loop mechanics ("For each match i in range...")
- 🚩 Naming private methods (`self._cleanup()`, `self._prepare()`)
- 🚩 Showing implementation code verbatim
- 🚩 Detailing internal state management

#### Lean Writing

**Core principle**: Capture every contract in the fewest lines.

**Techniques:**
- **Contract bullets**: `seed: Session seed (overrides session.seed)`
- **Arrow data flow**: `Init: Facade → Console (config/seed) → SessionState + SESSION_START`
- **Focused examples**: 3-4 snippets covering distinct workflows, no overlap
- **Minimal rationale**: Record only non-obvious decisions

**Length targets:**
- Orchestrator/facade specs: ~250 lines
- Core component specs: ~200 lines
- Utility specs: ~150 lines

Expect to trim 10-15% from first draft without losing guarantees.

#### Modal Verbs (RFC 2119 Style)

- **MUST / REQUIRED** - Non-negotiable requirement
- **SHOULD / RECOMMENDED** - Strong preference, exceptions allowed with justification
- **MAY / OPTIONAL** - Truly optional feature
- **MUST NOT / SHALL NOT** - Prohibited behavior

#### Cross-Referencing Standard

- **Other specs**: `SPEC-CONSOLE §4.2`
- **Source files**: `[src/agentdeck/core/console.py](src/agentdeck/core/console.py)`
- **Examples**: `[examples/games/auction.py](examples/games/auction.py)`
- **Philosophy**: `` `SPEC.md` §3.1`` or `` `AGENTS.md` §2.1``

#### Voice & Tense

- **Active voice**: "The Console emits events" (not "Events are emitted")
- **Present tense**: "The EventBus routes events" (not "will route")
- **User-facing first**: Start with caller perspective, then implementation
- **Concise**: Prefer bullets over prose, arrows over nested explanations

### Clean Spec Principle

Specs MUST NOT contain review meta-commentary:
- ❌ "Reviewer feedback:", "Product suggested:", "After discussion:"
- ✅ Specs are clean technical documentation, not change logs

Review history belongs in:
- Git commit messages ("Add packaging requirements per review feedback")
- WORKFLOW.md example sections
- PR descriptions / GitHub discussions

### Quality Checklist

Before marking a spec "Final":

**Content & Completeness:**
- [ ] Purpose framed as a caller problem/goal, names primary audience
- [ ] Responsibilities limited to one primary function
- [ ] Public API documented with signatures and return values
- [ ] Invariants explicitly enumerated (GB1-GB6 style)
- [ ] Data flow diagrams/descriptions reference adjacent specs
- [ ] Error handling lists user-facing messages and internal logging
- [ ] Examples demonstrate happy path + edge case, runnable with current codebase
- [ ] Testing strategy maps directly to invariants at behavioral level
- [ ] Design rationale records key decisions and alternatives
- [ ] Cross-links reference SPEC.md §3 principles and related specs

**Abstraction Level:**
- [ ] Describes WHAT system guarantees, not HOW code implements
- [ ] No line numbers, private methods, or loop mechanics
- [ ] Behavioral focus (not mock implementation details)

**Lean Writing:**
- [ ] Parameter descriptions are concise bullets
- [ ] Data flow uses single-line arrow summaries where practical
- [ ] Example count is focused (3-4 snippets, no redundancy)
- [ ] Design rationale lists only non-obvious decisions
- [ ] Spec length aligns with targets

**Philosophy Alignment:**
- [ ] Maps to SPEC.md §3 principles explicitly
- [ ] Execution-truth boundary is explicit
- [ ] Supports determinism/reproducibility requirements

**For complete specification guidelines**, see [specs/GUIDELINES.md](specs/GUIDELINES.md).

---

## Writing Code

### General Guidelines

1. **Follow the spec exactly** - No creative interpretation
2. **Reference SPEC.md §3** - Ensure code aligns with architectural principles
3. **Test as you go** - Write tests alongside implementation
4. **Document your code** - Clear docstrings, type hints
5. **Keep it simple** - Simplest solution that meets requirements

### Adding a Game

Games define rules and win conditions for matches.

**Requirements:**
- Extend an existing game mechanic or create new one
- Implement only 4 required methods: `instructions`, `setup`, `update`, `status`
- Use simple dictionary state (no complex objects)
- Follow **SPEC-GAME v1.0.0** contract
- Test with `MockPlayer` before LLM players

**Example structure:**
```python
from agentdeck import Game, GameStatus

class MyGame(Game):
    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        """Initialize game state."""
        return {"score": {p: 0 for p in players}}

    def get_view(self, state: Dict[str, Any], player: str) -> Dict[str, Any]:
        """Generate player-specific view (includes narrative)."""
        return {
            "instructions": "Choose your action...",
            "state": state,
            "player": player
        }

    def update(self, state: Dict[str, Any], player: str,
               action: ActionResult) -> Dict[str, Any]:
        """Apply action to state."""
        # Modify state here (framework handles immutability)
        return state

    def status(self, state: Dict[str, Any]) -> GameStatus:
        """Check if game is over."""
        return GameStatus(is_over=False)
```

### Adding a Player Type

Players represent AI agents making decisions.

**Requirements:**
- Extend `LLMPlayer` for API-based models
- Use `src/agentdeck/config/pricing.yaml` for cost tracking
- Include retry logic with exponential backoff
- Follow **SPEC-PLAYER v1.0.0** three-phase lifecycle
- Support handshake, turn, and conclusion phases

**Key methods:**
- `handshake()` - Pre-match acknowledgment
- `decide()` - Turn-by-turn decisions
- `conclude()` - Post-match reflection

### Adding a Controller

Controllers parse AI responses into structured results.

**Requirements:**
- Extend `HandshakeController` or `ActionController`
- Provide format instructions via `get_format_instructions()`
- Parse robustly (handle malformed responses)
- Follow **SPEC-CONTROLLER v1.0.0** or later

**Two types:**
- **HandshakeController**: Parses handshake acknowledgments → `HandshakeResult`
- **ActionController**: Parses turn actions → `ActionResult`

### Adding a Spectator

Spectators observe matches without interfering.

**Requirements:**
- Implement only needed event handlers (duck typing)
- Never affect gameplay (read-only)
- Handle errors gracefully
- Follow **SPEC-SPECTATOR v1.0.0**

**Common handlers:**
- `on_match_start()`, `on_match_end()`
- `on_gameplay()` - Unified gameplay events
- `on_player_handshake_complete()`, `on_player_conclusion()`

### Adding a Renderer

Renderers format game state for AI consumption.

**Requirements:**
- Transform state into view for LLM
- Support different modalities (text/JSON/image)
- NO format instructions (that's Controller's job)
- Follow renderer contract in SPEC.md

### Common Pitfalls to Avoid

1. ❌ **Don't mutate state directly** - Use `copy.deepcopy()`
2. ❌ **Don't add game logic to Players** - Keep them separate
3. ❌ **Don't make Spectators affect gameplay** - They are read-only
4. ❌ **Don't skip event emissions** - Replays depend on them
5. ❌ **Don't skip specs** - No "let's just try this" implementation

---

## Testing Requirements

### Test Strategy

**Invariants as Tests:**
All spec invariants (GB1-GB6, etc.) MUST have corresponding unit tests.

**Test naming convention:**
```python
def test_gb1_setup_returns_dict():
    """GB1: setup() MUST return dict"""
    game = FixedDamageGame()
    state = game.setup(["Alice", "Bob"], seed=42)
    assert isinstance(state, dict)
```

### Required Tests

Run this command before any commit:

```bash
pytest tests/
```

All tests MUST pass without warnings.

### Local Development Setup

```bash
pip install -e ".[dev]"
```

### Coverage Requirements

Each component should have tests for:
- **Happy path** - Normal operation
- **Error conditions** - How it fails
- **Edge cases** - Boundary conditions
- **Interface contracts** - Signature compliance
- **Invariants** - All spec invariants verified

### Running Tests

```bash
# Run all tests
pytest tests/

# Mirror GitHub Actions locally (format + tests)
./scripts/ci.sh

# Run specific test file
pytest tests/unit/test_game.py

# Run with coverage
pytest --cov=agentdeck tests/
```

### Running Examples

```bash
# Zero-dependency sanity check (no API keys required)
python examples/mock_demo.py

# Provider-backed examples (set provider env vars first)
export OPENAI_API_KEY="sk-..."
python examples/minimal_experiment.py
```

See [examples/README.md](examples/README.md) for a curated list of example scripts and what they demonstrate.

### Test Organization

```
tests/
├── unit/           # Component tests
│   ├── test_game.py
│   ├── test_player.py
│   └── ...
├── integration/    # System tests
│   ├── test_match_lifecycle.py
│   └── ...
└── conftest.py     # Shared fixtures
```

---

## Code Review Checklist

Before submitting a PR, verify:

### Architecture & Design
- [ ] Follows **SPEC.md §3** design principles
- [ ] Single responsibility maintained
- [ ] Separation of concerns enforced
- [ ] Code matches spec exactly (no creative interpretation)

### Implementation Quality
- [ ] State changes use deep copy (immutability)
- [ ] Events properly emitted (observability)
- [ ] Deterministic RNG used where needed (reproducibility)
- [ ] Error handling follows spec error contracts
- [ ] No unnecessary complexity added

### Testing
- [ ] All tests pass (unit + integration)
- [ ] All spec invariants tested
- [ ] No regressions introduced
- [ ] New tests added for new functionality

### Documentation
- [ ] Specs updated if behavior changed
- [ ] Docstrings added/updated with type hints
- [ ] Examples work and are up-to-date
- [ ] Public docs updated if needed

### Process
- [ ] Phase A complete (specs approved) before implementation
- [ ] Code review completed and approved
- [ ] All exit criteria met for current phase

---

## Anti-Patterns (What NOT to Do)

### ❌ Anti-Pattern 1: "Let's just try this"

**Wrong:**
```
Contributor: "I'll port pricing.py and we can adjust the spec later"
```

**Right:**
```
Contributor: "Let me write SPEC-PRICING first, get review, then implement"
```

### ❌ Anti-Pattern 2: "Specs are bureaucracy"

**Wrong:**
```
Attitude: "Specs slow us down, let's just code and document later"
```

**Right:**
```
Attitude: "Specs save time by catching issues before coding"
```

### ❌ Anti-Pattern 3: Implementation drift

**Wrong:**
```
Contributor changes behavior from the spec
Contributor: "I thought this was better"
```

**Right:**
```
Contributor: "Spec says X, but I think Y is better. Let me update the spec
and get review first"
```

### ❌ Anti-Pattern 4: Skip review

**Wrong:**
```
Contributor: "This spec looks good to me, moving to implementation"
(Without review)
```

**Right:**
```
Contributor: "SPEC-PRICING draft ready for review."
```

---

## Quick Reference: Component Checklist

### For Games:
- [ ] Implements `instructions`, `setup`, `update`, `status`
- [ ] Uses dictionary state
- [ ] Follows SPEC-GAME v1.0.0
- [ ] Tested with MockPlayer

### For Players:
- [ ] Extends `LLMPlayer` or `Player`
- [ ] Implements three phases (handshake, decide, conclude)
- [ ] Includes retry logic
- [ ] Follows SPEC-PLAYER v1.0.0

### For Controllers:
- [ ] Extends `HandshakeController` or `ActionController`
- [ ] Provides format instructions
- [ ] Parses responses robustly
- [ ] Follows SPEC-CONTROLLER v1.0.0+

### For Spectators:
- [ ] Implements needed event handlers only
- [ ] Read-only (no gameplay interference)
- [ ] Error handling included
- [ ] Follows SPEC-SPECTATOR v1.0.0

---

## Getting Help

- **Documentation**: Read [SPEC.md](specs/SPEC.md) and component specs in `specs/`
- **Examples**: Check `examples/` directory for working code
- **Questions**: Ask in GitHub issues or Discussions when enabled

---

## References

- **[SPEC.md](specs/SPEC.md)** - Master specification and architectural principles
- **[specs/GUIDELINES.md](specs/GUIDELINES.md)** - Complete specification authoring guidelines
- **[specs/](specs/)** - Component specifications
- **[examples/](examples/)** - Working examples and tutorials

---

## ⚠️ About Planning Documents (`docs/planning/`)

**IMPORTANT for Humans and AI:** Planning documents in `docs/planning/` are **TEMPORARY working notes**, NOT authoritative specifications.

### What Planning Docs Are:
- ✅ Design discussions for **active work**
- ✅ Decision logs for **ongoing features**
- ✅ Implementation strategies **being executed**

### What Planning Docs Are NOT:
- ❌ Current system specifications (use `specs/` instead)
- ❌ Reference documentation (use SPEC.md)
- ❌ Permanent contracts (specs are permanent)

### Lifecycle:
1. **Active**: Planning doc guides current work (lives in `docs/planning/`)
2. **Archived**: Work completes → moved to `docs/planning/archive/` (historical reference)
3. **Deleted**: After 6-12 months → deleted from repo (git history preserves)

### For Current Work, Use:
- ✅ **`specs/`** - Component contracts and requirements
- ✅ **`CONTRIBUTING.md`** - Workflow and standards (this file!)

### Why This Matters:
Planning docs are **temporal artifacts** that become outdated. Relying on them for current work leads to:
- Implementing against old/superseded designs
- Confusion about what's actually implemented
- LLM/AI context pollution from stale information

**See [README.md](README.md) for the user-facing overview and Quick Start.**

---

**Remember**: Specs first, code second. No exceptions.

The spec-driven approach ensures quality, enables AI collaboration, and prevents costly rework. Following this process makes AgentDeck a better execution substrate for everyone.
