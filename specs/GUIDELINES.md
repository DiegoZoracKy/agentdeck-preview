# Specification Authoring Guidelines

> Status: Final v1.0.0  
> Last Updated: 2025-01-22  
> Purpose: Align specification writing with AgentDeck product & engineering philosophy  
> References: [`SPEC.md`](./SPEC.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`specs/_template.md`](./_template.md)

---

## 1. Design Philosophy Recap

| Principle | Source | Application in Specs |
|-----------|--------|----------------------|
| **Simplicity is sacred** | `SPEC.md` §3.1 | Specs should describe the simplest solution that meets the user need. Avoid enumerating optional bells & whistles unless they are product-backed requirements. |
| **Single responsibility** | `SPEC.md` §3.2 | Each spec must lock in *one* well-defined component responsibility. If the component does more, split the spec. |
| **Separation of concerns** | `SPEC.md` §3.2 | Capture clear contracts between components. Specs should highlight boundaries, not implementation tricks. |
| **Compose, don't integrate** | `SPEC.md` §3.2 | Document how components plug together (inputs/outputs). Specs are the wiring diagrams for modularity. |
| **Reproducibility & determinism** | `SPEC.md` §2.4 | Whenever randomness or stateful behavior appears, explicitly state determinism expectations & seed flow. |
| **Research-first framing** | `SPEC.md` §1 | Specs should speak in terms of researcher value and workflows. Start from the user story, then drill into engineering detail. |

### Research Platform Focus

AgentDeck is a research platform for studying AI behavior. Specs must support:

- **Rapid Experimentation**: Can researchers use this component in <5 lines of code? Are defaults sensible for 80% of use cases?
- **Reproducibility**: Does the component preserve deterministic behavior (seed propagation)? Are all decisions recorded for analysis?
- **Flexibility**: Can researchers customize the component? Does it support different input formats (text/image/JSON)?
- **Data Collection**: Does the component emit relevant events? Are decisions, timings, and reasoning captured?
- **Interoperability**: Does it plug into existing components without custom glue code?

**LLM Integration**: Specs covering the player pipeline (Player, LLM integrations, Controllers) must address:
- Model integration patterns (API calls, message formatting)
- Cost tracking (token usage, pricing calculations)
- Retry logic and error handling
- Response timing and metadata

---

## 2. Spec Writing Workflow

1. **Start with the user flow**
   - What is the researcher trying to accomplish when they touch this component?
   - Where are they coming from? Where do they go next?

2. **Align on scope**
   - Use single responsibility to confirm whether functionality belongs in this spec.
   - Call out explicit non-goals if helpful.

3. **Draft using the shared template** (`specs/_template.md`)
   - Fill sections in order; they build context progressively.
   - Keep language user-facing first, engineering second.
   - Populate the header metadata (Status, Version, Last Updated, Implementation, Review State, Audience).
   - Keep the spec header contract-only. Do not add rolling `Changes in v...` blocks inside specs; version history belongs in git/audit notes, not in the source-of-truth contract.
   - In §1 Purpose, name the primary audience (researcher, contributor, game author, etc.).
   - Use §4 Data Structures when the component exposes reusable schemas (contexts, payloads, results); omit if not applicable.

4. **Cross-reference philosophy**  
   - Add a short subsection in “Scope & Philosophy Alignment” mapping spec decisions to core principles.  

5. **List invariants before behavior**  
   - Promote explicit guarantees (e.g., “GameStatus is evaluated after every update”) so tests map cleanly.

6. **Define test strategy early**
   - Derive tests from invariants (spec → tests), not line coverage.
   - Keep guidance at the behavioral level unless tests already exist (e.g., “verify replay parity” vs “update test_replay_engine.py”).
   - Map tests directly to invariants and error conditions.

7. **Call out interactions clearly**  
   - In “Data Flow & Interaction”, reference other specs by name/section.  
   - If a component depends on another spec, state which invariants it relies on.

8. **Document error handling**  
   - Explain both the user-facing error (what they see) and internal logging/metrics implications.  
   - Tie back to “Fail noisily & early” as a guiding principle.

9. **Provide runnable examples**  
   - Examples should compile/run with the current codebase.  
   - Use minimal scaffolding; highlight the component’s contract.
 
10. **Review cadence**  
    - Treat specs like code: design review before marking “Final”.  
    - Keep spec + implementation in sync (spec-first workflow).  

## 2c. Lean Specification Writing

**Core principle**: capture every contract in the fewest lines. If a sentence does not clarify a guarantee, remove it.

### Lean techniques

- **Contract bullets**: Prefer concise bullet lists over paragraphs for parameters and guarantees.  
  `seed: Session seed (overrides session.seed)` beats multi-line prose explaining the same rule.
- **Arrow data flow**: Summarise interactions in one line (e.g., `Init: Facade → Console (config/seed) → SessionState + SESSION_START`).
- **Focused examples**: 3–4 snippets covering distinct workflows (minimal, common, replay/advanced). Delete overlapping examples.
- **Minimal rationale**: Record only non-obvious decisions (e.g., “Always-present seed”). Skip statements the API already implies (e.g., “Facade pattern”).

### Targets

- Orchestrator/facade specs ~250 lines.  
- Core component specs (Player, Recorder, etc.) ~200 lines.  
- Utility specs (LLM adapters, helpers) ~150 lines.  
- Expect a lean pass to trim 10–15% from the first draft without losing guarantees.

---

## 2a. Specification Abstraction Level

**Core Principle**: Specs define **WHAT** the system must guarantee, not **HOW** the code implements it.

Specifications document contracts, invariants, and observable behavior—not internal algorithms, call sequences, or implementation details. Think of specs as **interface contracts** that could have multiple valid implementations.

### Writing at Specification Level

**✅ DO Document (Contracts & Guarantees)**:

- **Behavioral guarantees**: "MUST emit SESSION_START before accepting operations"
- **Input/output contracts**: "MUST reject empty player lists with ValueError"
- **Invariants**: "Session spectators MUST receive events from all play() calls"
- **Determinism guarantees**: "Match i MUST use seed S+i for reproducibility"
- **Error contracts**: "MUST re-raise failures with enriched context (game, players, seed)"
- **Observable outcomes**: "Replay MUST emit identical events to live execution"

**❌ DON'T Document (Implementation Details)**:

- **Internal call sequences**: "Call `self.console.event_bus.emit(EventType.SESSION_START)`"
- **Loop mechanics**: "For i in range(matches): match_seed = base_seed + i"
- **Data structure choices**: "8-character UUID prefix", "timestamp + random suffix"
- **Internal method names**: "`_cleanup()` sets `_closed` flag to True"
- **Merging logic**: "Console combines session + execution spectator lists"
- **Algorithm steps**: "Increment self.total_matches by len(results)"

### Red Flags (You're Too Low-Level If...)

🚩 **Referencing line numbers**: `[agentdeck.py:231-237]` (means you're documenting existing code)
🚩 **Describing loops**: "For each match i in range(matches)..."
🚩 **Showing implementation code**: `session or AgentDeckConfig()`
🚩 **Naming private methods**: `self._cleanup()`, `self._prepare_batch()`
🚩 **Detailing internal state**: "Sets self._closed to True before emitting"
🚩 **Explaining algorithms**: "Create 8-char UUID by taking first 8 characters of uuid.uuid4()"

### Specification-Level Examples (from SPEC-OBSERVABILITY)

✅ **Good** (§5 Spectator Scopes):
> Semantics are **additive**: active spectators = session defaults + execution extras. No implicit override, no dedupe.

✅ **Good** (§3.1 Lifecycle Events):
> `SESSION_START` / `SESSION_END` | Fired when the deck context opens/closes.

✅ **Good** (§6 Emission Responsibilities):
> Console MUST emit lifecycle events, manage RNG orchestration, bind helpers, ensure cleanup.

❌ **Too Low-Level** (if it said):
> AgentDeck.__init__ line 66 calls `self.console.event_bus.emit(EventType.SESSION_START, deck=self)` after initializing the recorder on line 55.

### How to Elevate Implementation Notes to Contracts

| Implementation Detail | Specification Contract |
|----------------------|------------------------|
| "Loop through matches: `for i in range(matches)`" | "MUST execute exactly N matches where N = matches parameter" |
| "Call `self.console.run(game, players, seed)`" | "MUST delegate match execution to Console component" |
| "Create UUID: `str(uuid.uuid4())[:8]`" | "MUST assign unique batch identifier per play() invocation" |
| "`session or AgentDeckConfig()`" | "MUST use session config if provided, otherwise use defaults" |
| "Append to results list then wrap in MatchResults" | "MUST aggregate all match outcomes into MatchResults container" |

### When Implementation Details Are Appropriate

Implementation notes **MAY** appear in:

- **Design Rationale** (§11): Explaining **why** an approach was chosen ("UUID suffix ensures uniqueness across concurrent sessions")
- **Examples** (§9): Showing **how** to use the API in practice (`with AgentDeck(...) as deck:`)
- **Appendices** (optional): Low-level performance notes or migration guides

But even in rationale, focus on **tradeoffs** and **alternatives considered**, not line-by-line code walkthroughs.

---

## 2b. When NOT to Spec

Not every component needs a full specification. Skip the spec for:

- **Simple utilities**: Pure, single-purpose helpers documented by type hints and docstrings.
- **CRUD wrappers**: Straightforward data access without domain decisions.
- **Rapid prototypes**: Code still exploring requirements (capture intent in a design note instead).
- **Thin adapters**: Pass-through wrappers with no business logic.

Reserve specs for components with:

- Cross-cutting impact across modules.
- Non-trivial lifecycle/state machines.
- Public or stable APIs that external users depend on.
- Reproducibility or observability guarantees.
- Subtle invariants that tests must exercise.

---

## 3. Quality Checklist (Draft)

Before marking a spec "Final", ensure:

**Content & Completeness**:
- [ ] **Metadata**: Status, Review State, Audience fields populated.
- [ ] **Purpose**: Framed as researcher problem/goal, names primary audience.
- [ ] **Responsibilities**: Limited to one primary function.
- [ ] **Public API**: Documented with signatures and returned values.
- [ ] **Invariants**: Explicit guarantees enumerated (determinism, ordering, schema, etc.).
- [ ] **Data flow**: Diagrams or descriptions reference adjacent specs using standard notation (e.g., `SPEC-CONSOLE §4.2`).
- [ ] **Error handling**: Lists user-facing messages and internal logging.
- [ ] **Examples**: Demonstrate happy path + key edge case, runnable with current codebase.
- [ ] **Testing strategy**: Maps directly to invariants at behavioral level (not specific file names unless they exist).
- [ ] **Design rationale**: Records key decisions and alternatives.
- [ ] **Open questions**: Captured (if any) with TODOs or future spec references.
- [ ] **Cross-links**: References relevant philosophy sections (`SPEC.md`, `CONTRIBUTING.md`, other specs).
- [ ] **LLM coverage** (if applicable): Player pipeline specs address model integration, cost tracking, retries, metadata.

**Abstraction Level** (§2a):
- [ ] **Contracts over implementation**: Describes WHAT system guarantees, not HOW code implements.
- [ ] **No line numbers**: Avoids references to specific code lines (e.g., `[file.py:123]`).
- [ ] **No internal methods**: Avoids naming private methods (`_cleanup()`, `_prepare_batch()`).
- [ ] **No loop mechanics**: Describes iteration guarantees, not `for i in range(...)` patterns.
- [ ] **Behavioral focus**: Testing strategy describes observable behavior, not mock implementation details.

**Lean Writing** (§2c):
- [ ] Parameter descriptions are concise bullets (no duplicate prose).
- [ ] Data flow uses single-line arrow summaries where practical.
- [ ] Example count is focused (3–4 snippets, no redundant overlap).
- [ ] Design rationale lists only non-obvious decisions.
- [ ] Spec length aligns with targets (~250 lines for orchestrators, ~200 for components, ~150 for utilities).

---

## 4. Writing Conventions

### 4.1 Modal Verbs (RFC 2119 style)
- **MUST / REQUIRED**: Non-negotiable requirement
- **SHOULD / RECOMMENDED**: Strong preference, exceptions allowed with justification
- **MAY / OPTIONAL**: Truly optional feature
- **MUST NOT / SHALL NOT**: Prohibited behavior

### 4.2 Cross-Referencing Standard
- **Other specs**: `SPEC-CONSOLE §4.2` (spec name, section number)
- **Source files**: `[src/agentdeck/core/console.py:142](../src/agentdeck/core/console.py)` (markdown link)
- **Examples**: `[examples/games/auction.py](../examples/games/auction.py)` (markdown link)
- **Philosophy docs**: `` `SPEC.md` §2.4`` or `` `SPEC.md` §3.2`` (inline code with section)

### 4.3 Voice & Tense
- **Active voice**: "The Console emits events" (not "Events are emitted")
- **Present tense**: "The EventBus routes events" (not "will route")
- **User-facing first**: Start with researcher perspective, then implementation details
- **Concise**: Prefer bullets over prose and arrow summaries over nested explanations (see §2c).

### 4.4 Public API Documentation Format

**Standard**: All Public API methods MUST use the lean contract format for consistency and scannability.

**Format**:
```markdown
### method_name(param1: Type1, param2: Type2, *, kwarg: Type3 = default) -> ReturnType

Brief one-sentence description of method purpose.

**Contract**:
- Accept: High-level summary of inputs (when parameters need clarification beyond types)
- Perform: What the method does (core behavior)
- Return: What it returns (structure, semantics)
- Emit: Events emitted (if applicable)
- Raise: Exceptions raised (if applicable)
- MUST/MUST NOT: Critical invariants and guarantees
```

**Rationale**:
- **Lean**: Types in signature reduce need for verbose parameter descriptions
- **Contract-focused**: Accept/Perform/Return/Emit/Raise/MUST captures complete semantics
- **Consistent**: Same structure for all methods (simple and complex)
- **Scannable**: Readers can quickly find guarantees and error conditions

**Example (Console constructor)**:
```markdown
### Console(*, config: Optional[SessionConfig] = None, seed: Optional[int] = None, recorder: Optional[Recorder] = None) -> None

Create Console instance and initialize session lifecycle.

**Contract**:
- Accept: Session config (creates default if None), optional seed override (precedence: seed param > config.seed > entropy)
- Perform: Create SessionState, resolve seed precedence, ensure directories exist, subscribe recorder/spectators
- Emit: SESSION_START (synchronously during construction)
- Raise: ValueError if directories cannot be created
- MUST: Create and expose SessionState via console.session (immutable interface)
- MUST: Subscribe recorder/spectators before SESSION_START emission
```

**Not This** (verbose alternative):
```markdown
### Console(*, config=None, seed=None, recorder=None)

**Inputs**:
- `config` (SessionConfig, optional): Session configuration for paths, logging, defaults...
- `seed` (int, optional): Override for session seed. Precedence: seed parameter > config.seed...
- `recorder` (Recorder, optional): Recorder instance for match/event recording...
[etc - duplicates type information, harder to scan, bloats spec]
```

---

## 5. Good vs Bad Patterns (Examples)

| Section | ✅ Lean & Effective | ⚠️ Verbose Anti-pattern |
|---------|-------------------|-------------------------|
| Purpose | “AgentDeck facade ensures deterministic batch execution and spectator scoping for researchers running experiments.” | “This spec describes AgentDeck.” |
| Parameters | `seed: Session seed (overrides session.seed)` | Multi-line prose explaining the same rule in detail |
| Data Flow | `Init: Facade → Console (config/seed) → SessionState + SESSION_START` | Nested sub-bullets with lengthy prose |
| Examples | 3 focused snippets covering minimal, common, replay | 5+ examples with overlapping coverage |
| Testing Strategy | “Replay parity → verify recorded vs replayed streams match” | “Write tests for replay.” |

Use these patterns as litmus tests while drafting.

---

## 6. Open Questions for Discussion

- Should specs include explicit "Version Compatibility" / "Deprecations" sections?
- How strict should we be with example completeness (fully runnable vs illustrative pseudo-code)?
- What cadence should we set for spec audit cycles (quarterly, per release, per major change)?
- Do we want specs to double as user-facing docs (maybe trimmed versions for docs site)?
- Should we create a `specs/index.md` registry linking all specs?
- Do we need additional LLM-specific guidelines (e.g., minimum telemetry, retry budgets)?
- Should we standardise spec version numbers beyond git history (e.g., banner fields)?

---

## 7. Next Steps

1. Gather feedback from the people reviewing the change.
2. Iterate on checklist & template alignment.
3. Finalize this guideline doc (mark Status as "Final").
4. Reference it from the relevant spec or issue once agreed.
5. Begin drafting SPEC-AGENTDECK.md using these guidelines.

> _Please add comments, suggestions, or objections so we converge on a shared spec-writing discipline before diving into SPEC-AGENTDECK._  
