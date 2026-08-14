# SPEC-PLAYER: Three-Phase Player Contract

> Status: Final
> Version: 1.4.0
> Last Updated: 2026-08-14
> Implementation: ✅ Implemented
> Audience: Game authors, LLM player implementers, execution operators

## 1. Purpose
- Define the contract every player must satisfy across the three lifecycle phases: **handshake**, **turn decisions**, and **conclusion**.
- Guarantee deterministic prompt assembly, controller parsing, and metadata capture for reproducible experiments.
- Provide a configurable structure so researchers can swap templates, controllers, and renderers without touching console flow.

## 2. Scope & Philosophy Alignment
- Upholds `SPEC.md` §3.2 separation: console orchestrates, games own rules, players own LLM conversations.
- Supports `SPEC.md` §2.4 reproducibility by capturing prompt blocks, responses, usage info, and lifecycle events.
- Lifecycle follows the consensus handshake-first design; handshake is always mandatory (no policy configuration).
- **Clean slate design**: v1.0.0 contract assumes modern three-phase lifecycle with prompt metadata capture—no legacy handshake policy system, no backward compatibility shims.
- Non-goals: provider transport details (`SPEC-LLM.md`), renderer internals (`SPEC-RENDERER.md`), or console orchestration (`SPEC-CONSOLE.md`).

## 3. Responsibilities
- **Handshake phase (two-step)**: Build a deterministic handshake prompt bundle without invoking the LLM, then execute the LLM call using that bundle and return the raw acknowledgement string for console validation while preserving the exchange in history.
- **Turn phase**: Compose deterministic prompts via `PromptBuilder`, invoke the LLM, parse actions with the bound controller, and return `ActionResult` with metadata.
- **Conclusion phase** *(policy-driven)*: Base `Player` implementations MUST record conclusion prompt metadata and MAY return `None`; provider-backed subclasses MAY additionally invoke an LLM and return reflection text while keeping the same metadata contract. Template-driven conclusion prompts MUST hide engine-only bookkeeping keys from default LLM-facing views.
- **Component management**: Provide controller, renderer, prompt builder, and (optionally) conversation manager. Controller handles all lifecycle phases (handshake, turn, conclusion) per SPEC-CONTROLLER.
- **Metadata capture**: Attach prompt blocks, usage info (tokens, cost, latency), retry metrics, lifecycle phase, and controller metadata to the returned results.

## 4. Public API
- `Player(name, *, controller, renderer=None, handshake_template=None, turn_template=None, conclusion_template=None, model="unspecified", **config)`
  - **v1.3.0 change**: Handshake is split into build + execute steps so Console can emit `PLAYER_HANDSHAKE_START` before the LLM call.
  - **v1.2.0 change**: Single `controller` parameter (required) replaces `handshake_controller` plus a separate turn controller. Controller handles all lifecycle phases per SPEC-CONTROLLER.
  - Defaults: `renderer` defaults to `TextRenderer()`.
  - Default templates:
    - `handshake_template`: `"You are playing {game_name}.\n\n{game_instructions}\n\n{player_instructions}\n\n{controller_format}\n\n{handshake_controller_format}"` (front-loads all instructions)
    - `turn_template`: `"{game_view}\n\n{controller_format}"` (current state plus the decision protocol)
    - `conclusion_template`: `"=== Match Concluded ===\n\n{outcome}\n\nFinal state:\n{game_view}"` (shows outcome and final view)
  - Template parameters accept:
    - **Literal strings**: Inline template content (e.g., `"You are playing {game_name}..."`)
    - **Path objects**: File path to load (e.g., `Path("prompts/handshake.txt")`)
    - When `Path` provided, player loads file contents (UTF-8) before use
    - Raises `FileNotFoundError` if path doesn't exist, `UnicodeDecodeError` if not valid UTF-8
  - Note: `{player_instructions}` renders empty string when not provided in handshake metadata, so the default template works with or without it.
  - `controller` is required. Controller provides handshake validation (default accepts only `OK`), turn parsing, and optional conclusion parsing.
  - Templates control what appears in each phase—researchers choose which placeholders to include.
- `build_handshake_bundle(context: HandshakeContext) -> PromptBundle`
  - MUST render the handshake template (player override > game default > minimal built-in) and return the exact `PromptBundle` that will be sent to the LLM.
  - MUST NOT invoke the LLM or mutate conversation history.
  - MUST populate `{controller_format}` using `controller.get_format_instructions()` and `{handshake_controller_format}` using `controller.get_handshake_format_instructions()`.
- `execute_handshake(bundle: PromptBundle, context: HandshakeContext) -> HandshakeResponse`
  - MUST invoke the LLM using `bundle.text`, return raw acknowledgement text, and preserve the exchange in history.
  - MUST NOT validate; console calls `controller.validate_handshake(raw_response, context)` per SPEC-CONTROLLER.
- `decide(game_state: dict, *, turn_context: TurnContext) -> ActionResult`
  - MUST keep `game_state` immutable, build prompt via `PromptBuilder`, invoke LLM, parse response via `controller.parse()`, and return `ActionResult` with metadata.
- `conclude(result: MatchResult, *, match_context: MatchContext) -> Optional[str]`
  - OPTIONAL; default implementation records conclusion prompt metadata (using `match_context.conclusion_prompt` when present, otherwise the default conclusion template) and returns `None`.
  - When using template-driven conclusion composition (`match_context.conclusion_prompt` is absent), players MUST sanitize engine bookkeeping fields from the state rendered into `{game_view}` (at minimum `_turn_count` and `_first_player_idx`).
  - When `match_context.conclusion_prompt` is present, that prompt is treated as explicit caller-owned text and is sent verbatim.
  - When overridden, MUST return a reflection string or `None` and MUST record prompt metadata for conclusion events.
  - Console policy determines whether this method is invoked for a given match.
- `clone() -> Player`
  - Default implementation uses `copy.deepcopy` and clears runtime bindings (`conversation_manager`, `logger`) so the console can rebind them.
  - Players with non-serialisable state (e.g., LLM SDK clients, sockets, thread locks) MUST override this to construct a fresh instance that preserves configuration and aggregate metrics while recreating external resources (see SPEC-PARALLEL §5).
- `get_response(prompt: str) -> str`
  - Abstract hook used by all lifecycle methods; subclasses MUST implement provider transport.
- `bind_conversation_manager(manager)` / `reset_conversation()`
  - Integrate with console-injected `ConversationManager` and ensure history resets per match.
- Introspection helpers: base `Player` exposes `describe()` and `get_summary()`. Provider-backed subclasses such as `LLMPlayer` MAY additionally expose `get_stats()` for cumulative usage metrics.

## 5. Invariants & Guarantees
### 5.1 Handshake (HS)
1. **HS1**: Console MUST invoke `build_handshake_bundle` exactly once per match before turn `1`. Handshake is always mandatory.
2. **HS2**: `build_handshake_bundle` MUST be deterministic for identical inputs (same `HandshakeContext` → same `PromptBundle`).
3. **HS3**: Console MUST call `execute_handshake` with the exact `PromptBundle` returned by `build_handshake_bundle` (no re-rendering).
4. **HS4**: Players MUST preserve handshake prompts/responses in conversation history unless researcher explicitly opts out.
5. **HS5**: Players MUST return raw handshake responses in `HandshakeResponse.response_text`; console performs validation via `controller.validate_handshake()` per SPEC-CONTROLLER.
6. **HS6**: Players SHOULD use the default handshake template; controller's default validation accepts only `OK`.

### 5.2 Prompt Pipeline (PP)
6. **PP1**: PromptBuilder MUST substitute placeholders deterministically based on template and provided data (same inputs → same prompt).
7. **PP2**: Renderer output MUST remain unmodified other than joining; when renderer returns `RenderResult`, metadata MUST be stored under `renderer_output`.
8. **PP3**: Templates control which content appears in each phase; if a placeholder is in the template, it MUST be rendered; if absent, it MUST NOT appear.

### 5.3 Decision Semantics (DS)
9. **DS1**: Turn controller `parse` MUST be called exactly once per decision; parse failures MUST surface via `ActionParseError` rather than fallback actions.
10. **DS2**: Returned `ActionResult.metadata` MUST include raw prompt, prompt blocks, raw response, retries, attempt durations, usage info (if available), and controller metadata.
11. **DS3**: Players MUST log controller failures via bound logger (if present) and propagate parsing failures without mutating state.
12. **DS4**: LLM players MUST capture `usage_info` in `ActionResult.metadata` with `prompt_tokens` and `completion_tokens` fields for cost calculation (SPEC-PRICING § 7.1 M1-M2).

### 5.4 Conversation & State (CS)
13. **CS1**: Players MUST treat `game_state` arguments as read-only. Copies happen inside PromptBuilder/renderer when required.
14. **CS2**: When `ConversationManager` is bound, players MUST delegate history logging to it for all lifecycle phases; otherwise `_local_history` MUST track alternating user/assistant messages.
15. **CS3**: `reset_conversation()` MUST prepare the player for the next match by clearing local history (while leaving handshake templates intact).
16. **CS4**: Template-driven conclusion prompts MUST NOT expose engine bookkeeping keys in LLM-facing text. Implementations MUST sanitize at least `_turn_count` and `_first_player_idx` before rendering `{game_view}`.
17. **CS5**: Replay/research reproducibility MUST remain based on locally recorded conversation history (ConversationManager or `_local_history`). Provider-managed history features MAY be added, but MUST be explicit opt-in and MUST NOT replace local prompt/response recording required by recorder/replay contracts.

### 5.5 Component Integrity (CI)
18. **CI1** (v1.2.0): Controller MUST be pluggable; MUST be deterministic and stateless. Controller handles all lifecycle phases (handshake, turn, conclusion) per SPEC-CONTROLLER.
19. **CI2**: Players MUST expose `describe()` / `get_summary()` including controller name, renderer, model, temperature, and prompt strategy (with truncation for large strings).
20. **CI3**: Players intended for parallel execution MUST supply a `clone()` implementation when default `copy.deepcopy` is insufficient (e.g., presence of LLM clients, sockets, thread locks). Implementations MUST recreate external resources while preserving configuration and aggregate metrics so worker clones behave identically to the original instance (see SPEC-PARALLEL §5).

### 5.6 LLM Provider Integration (LP)
21. **LP1**: Every LLMPlayer subclass MUST define a class-level `PROVIDER` constant identifying the provider (e.g., `"openai"`, `"anthropic"`, `"google"`) for cost calculation (SPEC-PRICING § 7.2 P1).
22. **LP2**: The model identifier MUST be accessible via the `model` attribute (already provided by `Player.__init__`) for pricing lookups.

### 5.7 Context Selection Audit (CTA)

23. **CTA1 Declared Policy**: Every provider-backed Player MUST expose one versioned context policy in `describe()`. The default is `full_history`; bounded and empty-history policies are explicit configuration.
24. **CTA2 Exact Selection**: Before each provider call, the Player MUST retain the ordered provider-neutral messages, a content hash, and identifiers for available, selected, and omitted history. The current turn remains distinguishable from retained history.
25. **CTA3 Isolation**: Selection uses only the current Player's current-match conversation. `reset_conversation()` clears content and provenance identifiers.
26. **CTA4 Additive Compatibility**: Consumers MUST label history reconstructed from older Records as reconstructed, never exact provider input.

## 6. Data Structures
- **HandshakeContext**: `match_id`, `player_name`, `opponent_names`, `game_name`, `seed`, `handshake_template_id`, optional metadata. Provided by console so players can tailor handshake prompts.
- **HandshakeResponse** *(returned by `execute_handshake`)*:
  - `response_text` *(str, required)*: Raw LLM acknowledgement (unvalidated).
  - `usage_info` *(dict, optional)*: Tokens/cost metadata (same schema as ActionResult metadata).
  - `retries` *(int, optional)*: Retry count used by provider.
  - `retry_durations` *(list, optional)*: Backoff delays applied between retries.
  - `attempt_durations` *(list, optional)*: Durations for each attempt.
  - `provider_call` *(dict, optional)*: Exact context selection and provider-adapter call provenance for provider-backed Players.
- **PromptBundle** *(from SPEC-PROMPT-BUILDER)*:
  - `text` *(str)*: Fully rendered prompt string sent to the LLM.
  - `blocks` *(list)*: Rendered blocks with placeholder metadata for reproducibility.
- **HandshakeResult** *(returned by controller validate)*: `accepted`, `normalized_response`, `raw_response`, optional `reason`, optional `metadata`.
- **MatchContext**: Console-managed structure extended with `handshake_completed: bool` plus RNG info.
- **TurnContext**: Unchanged from previous spec; guarantee that gameplay begins at `turn_number=1`.
- **ActionResult.metadata** *(required fields for pricing integration - SPEC-PRICING § 7)*:
  - `usage_info` *(dict, required for LLM players)*: Token usage information
    - `prompt_tokens` *(int)*: Number of input tokens (prompt, context, system message)
    - `completion_tokens` *(int)*: Number of output tokens (response)
    - `total_tokens` *(int, optional)*: Sum of prompt + completion tokens
  - `decision_duration` *(float, recommended)*: Time spent on decision in seconds
  - `prompt_blocks` *(list, recommended)*: Structured prompt components for replay/analysis
  - `raw_prompt` / `prompt_text` *(str, required)*: The complete prompt sent to LLM
  - `raw_response` / `response_text` *(str, required)*: The complete response from LLM
  - `controller_metadata` *(dict, required)*: Metadata from action controller parsing
  - `renderer_output` *(dict, optional)*: Metadata from renderer when RenderResult returned
  - `retries` *(int, recommended)*: Number of retry attempts made
  - `attempt_durations` *(list, recommended)*: Duration of each attempt in seconds

## 7. Data Flow & Interaction
- **Handshake** (mandatory - v1.3.0): Console → `player.build_handshake_bundle(handshake_context)` → emit `PLAYER_HANDSHAKE_START` with prompt text → `player.execute_handshake(bundle, context)` → console calls `player.controller.validate_handshake(raw, context)` → emits `PLAYER_HANDSHAKE_COMPLETE|ABORT` → recorder stores acknowledgement.
- **Turn execution** (v1.2.0): Console → `player.decide(game_state, turn_context)` → PromptBuilder substitutes template placeholders → LLM invocation (`get_response`) → `controller.parse()` parses → `ActionResult` returned → console emits gameplay events.
- **Conclusion** (policy-driven): Console → `player.conclude(result, match_context)` → optional reflection recorded.
- **Conversation logging**: When conversation manager exists, handshake/turn/conclusion prompts/responses MUST be recorded via manager API; otherwise player stores them locally.

## 8. Error Handling & Edge Cases
- MUST raise `NotImplementedError` if `get_response` not overridden.
- MUST surface handshake/controller errors through metadata and logger warnings; do not swallow exceptions.
- MUST propagate provider errors (after retries) as `RuntimeError` allowing console to abort.
- MUST reset local history between matches (handshake always runs first in each match).
- SHOULD support "virtual handshake" experiments by overriding `execute_handshake()` to return canned responses.

## 9. Examples
```python
# Example 1: Custom player with coaching
class AggressiveBot(Player):
    def __init__(self, name: str, *, coaching: str):
        super().__init__(
            name=name,
            controller=ActionOnlyController(),
            # Handshake includes instructions and coaching
            handshake_template="{game_instructions}\n{coaching}\n\nRespond 'OK' if ready.",
            # Turns only include game state and format (coaching remembered from handshake)
            turn_template="{game_view}\n\n{controller_format}",
            conclusion_template="{outcome}\n\nReflect on your performance:",
        )
        self.coaching = coaching

    def conclude(self, result, *, match_context):
        return f"GG! Winner: {result.winner or 'draw'}"
```

```python
# Example 1b: LLMPlayer with PROVIDER constant (for pricing integration)
from agentdeck.players import LLMPlayer

class GPTPlayer(LLMPlayer):
    """OpenAI GPT player with cost tracking."""
    PROVIDER = "openai"  # Required for pricing lookups (LP1)

    def __init__(self, name: str, *, model: str = "gpt-4o-mini", **kwargs):
        super().__init__(name=name, model=model, **kwargs)

    def get_response(self, prompt: str) -> str:
        # OpenAI Responses API call
        response = self.client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": prompt}],
            store=False,
        )

        # Capture usage_info for cost calculation (DS4)
        usage = getattr(response, "usage", None)
        self._last_usage_info = {
            "prompt_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "completion_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
            "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
        }

        return response.output_text

    def decide(self, game_state: dict, *, turn_context: TurnContext) -> ActionResult:
        result = super().decide(game_state, turn_context=turn_context)

        # Include usage_info in metadata (DS4, M2)
        result.metadata["usage_info"] = self._last_usage_info

        return result
```

```python
# Example 2: Spectator tracking lifecycle events
class PlayerLifecycleTracker:
    """Track player interactions across all three phases."""

    def on_player_handshake_complete(self, event: Event) -> None:
        data = event.data
        print(f"[HANDSHAKE] {data['player']} acknowledged: {data['normalized_response']}")
        print(f"  Accepted: {data['accepted']}")
        print(f"  Prompt length: {len(data['prompt_text'])} chars")

    def on_player_handshake_abort(self, event: Event) -> None:
        data = event.data
        print(f"[HANDSHAKE ABORT] {data['player']} rejected!")
        print(f"  Reason: {data.get('reason', 'Unknown')}")

    def on_gameplay(self, event: Event) -> None:
        if event.data.get('mechanic') == 'turn_based':
            action = event.data.get('action')
            if action:
                print(f"[TURN {event.context['phase_index']}] {event.data['player']} → {action.action}")

    def on_player_conclusion(self, event: Event) -> None:
        data = event.data
        print(f"[CONCLUSION] {data['player']}'s reflection:")
        print(f"  {data['reflection_text']}")

# Use with AgentDeck
deck = AgentDeck(game=MyGame(), spectators=[PlayerLifecycleTracker()])
deck.play(players=[alice, bob])
```

```python
# Load templates from files (explicit Path objects)
from pathlib import Path

player = GPTPlayer(
    name="FileBot",
    controller=ActionOnlyController(),  # v1.2.0: single controller
    handshake_template=Path("prompts/handshake.txt"),
    turn_template=Path("prompts/turn.md"),
    conclusion_template=Path("prompts/conclusion.txt")
)
# Player loads file contents (UTF-8) during initialization
# Raises FileNotFoundError if path doesn't exist
```

## 10. Testing Strategy

| Focus | Invariants | Verification |
|-------|------------|--------------|
| Handshake validation | HS1-HS6 | Ensure build+execute runs before turn 1, raw responses returned, defaults acknowledged, history preserved. |
| Prompt composition | PP1-PP3 | Run multi-turn match with different templates; assert correct placeholders rendered and renderer metadata preserved. |
| Parse failure propagation | DS1-DS3 | Mock controller parsing failure; ensure `ActionParseError` surfaces, metadata is preserved, and logger warnings remain informative. |
| Conversation logging | CS2-CS3 | Bind mock manager, run handshake + turns, ensure history entries recorded/reset. |
| Component defaults | CI1-CI2 | Instantiate without components; assert defaults and describe/get_summary content. |

### Concrete Test Examples

**Test 1: Handshake build+execute runs exactly once before first turn (HS1-HS3)**
```python
def test_handshake_runs_once_before_turn_one():
    player = MockPlayer("Alice")
    build_call_count = 0
    exec_call_count = 0

    original_build = player.build_handshake_bundle
    original_execute = player.execute_handshake
    def tracked_build(context):
        nonlocal build_call_count
        build_call_count += 1
        return original_build(context)
    def tracked_execute(bundle, context):
        nonlocal exec_call_count
        exec_call_count += 1
        return original_execute(bundle, context)

    player.build_handshake_bundle = tracked_build
    player.execute_handshake = tracked_execute

    # Run match
    console.run(game, [player], matches=1)

    assert build_call_count == 1, "Handshake build must be called exactly once"
    assert exec_call_count == 1, "Handshake execute must be called exactly once"
    # Verify handshake happened before first turn (check event log ordering)
```

**Test 2: Prompt metadata fields appear in ActionResult.metadata (DS2)**
```python
def test_prompt_metadata_captured():
    player = GPTPlayer("Bob", controller=ActionOnlyController())  # v1.2.0

    result = player.decide(game_state, turn_context=TurnContext(turn_number=1))

    # DS2: MUST include prompt metadata
    assert "raw_prompt" in result.metadata or "prompt_text" in result.metadata
    assert "prompt_blocks" in result.metadata
    assert "raw_response" in result.metadata or "response_text" in result.metadata
    assert "controller_metadata" in result.metadata

    # When renderer returns RenderResult, metadata must be stored
    if "renderer_output" in result.metadata:
        assert isinstance(result.metadata["renderer_output"], dict)
```

**Test 3: Conclusion hook returns reflections when implemented**
```python
def test_conclusion_returns_reflection():
    class ReflectivePlayer(Player):
        def conclude(self, result, *, match_context):
            return f"I {'won' if result.winner == self.name else 'lost'}. GG!"

    player = ReflectivePlayer("Carol")
    match_result = MatchResult(winner="Carol", final_state={}, seed=42)

    reflection = player.conclude(match_result, match_context=MatchContext(...))

    assert reflection is not None
    assert "won" in reflection or "lost" in reflection
```

**Test 4: Default handshake validation accepts "OK" (HS6)**
```python
def test_default_handshake_validation():
    player = Player("Dave", controller=ActionOnlyController())

    # Controller has default validate_handshake() that accepts only OK
    assert player.controller is not None

    # Mock handshake returns "OK"
    context = HandshakeContext(match_id="test", player_name="Dave", game_name="TestGame")
    raw_response = "OK"

    result = player.controller.validate_handshake(raw_response, context=context)
    assert result.accepted == True
```

**Test 5: PromptBuilder deterministic substitution (PP1)**
```python
def test_prompt_builder_deterministic():
    builder = PromptBuilder(
        handshake_template="Hello {game_name}!",
        turn_template="{game_view}",
    )

    # Same inputs → same prompt
    prompt1 = builder.compose(phase="handshake", data={"game_name": "Chess"})
    prompt2 = builder.compose(phase="handshake", data={"game_name": "Chess"})

    assert prompt1 == prompt2
    assert prompt1 == "Hello Chess!"
```

**Test 6: Conversation reset prepares for next match (CS3)**
```python
def test_conversation_reset():
    player = GPTPlayer("Eve", controller=ActionOnlyController())  # v1.2.0

    # Run first match (populate history)
    context = HandshakeContext(...)
    bundle = player.build_handshake_bundle(context)
    player.execute_handshake(bundle, context)
    player.decide(game_state, turn_context=TurnContext(turn_number=1))

    assert len(player._local_history) > 0  # History populated

    # Reset for next match
    player.reset_conversation()

    assert len(player._local_history) == 0  # History cleared
    # Templates remain intact
    assert player.handshake_template is not None
```

## 11. Design Rationale
- Explicit lifecycle hooks ensure handshake/onboarding is visible, testable, and always-on.
- Template-driven prompt composition keeps researchers in control—what you write is what gets sent to the LLM.
- Two-step handshake preserves separation of concerns: Console emits lifecycle events before/after the LLM call; Player owns LLM interactions; Controller validates.
- **Smart defaults (v1.2.0)**:
  - `controller` parameter is required. Controller provides default handshake validation (accepts only `OK`) per SPEC-CONTROLLER.
  - Default `handshake_template` front-loads ALL instructions (game name, rules, player coaching, gameplay format, acknowledgement format).
    - Includes: `{game_name}`, `{game_instructions}`, `{player_instructions}` (optional), `{controller_format}`, `{handshake_controller_format}`.
    - Researchers can pass `player_instructions` via handshake metadata without reconfiguring templates.
    - When `player_instructions` not provided, placeholder renders as empty string (no template change needed).
  - Default `turn_template` includes `{game_view}` plus `{controller_format}`.
    - Game rules remain front-loaded in the handshake for token efficiency.
    - The decision protocol is repeated so memory-policy experiments do not silently
      alter the response contract.
  - Default `conclusion_template` provides closure: shows outcome and final state.
    - Gives players context for post-match reflection (if implemented).
    - Researchers can customize to prompt for specific analysis (e.g., "Reflect on your strategy:", "What would you change?").
    - Can be set to `None` to suppress prompt composition; `conclude()` may still run under policy but return `None`.
- **Template storage**: Templates can be inline strings OR `Path` objects pointing to files.
  - **Recommended practice**: Store templates as files for teams iterating on wording.
  - Files enable version control, copy/paste/tweak workflow, easier review, and reuse across experiments.
  - Example: `handshake_template=Path("prompts/handshake.txt")` loads UTF-8 content during player initialization.
- When `conclusion_template=None` is provided, `describe()` SHOULD report `"conclusion": None` under templates to signal composition is disabled.
- **Format placeholders**: `{handshake_controller_format}` and `{controller_format}` keep templates in sync with controller expectations (both placeholders populated during handshake for backward compatibility).
- Simplicity over configuration: Templates are the single source of truth; no parallel policy system to maintain.

## 12. Open Questions / Future Work

### Multi-Round Handshakes
- Should players support **multi-step handshakes** for complex onboarding (e.g., game rules → acknowledge → quiz → acknowledge)?
- How would multi-round handshakes integrate with conversation history and template system?

### Per-Match Player Overrides
- Should console support **per-match player configuration overrides** (e.g., different temperature or template for match N)?
- How to balance flexibility with reproducibility (overrides must be recorded)?

### Pause/Resume Support
- Should players support **pause/resume** during handshake or turns for interactive debugging?
- How would paused state be serialized for later resumption?

### Richer Conclusion Workflows
- Should `conclude()` support **multiple conclusion prompts** (e.g., strategy reflection → opponent analysis → lessons learned)?
- Could conclusion phase include **LLM-to-LLM dialogue** (players discuss the match)?

### Template Composition
- Should templates support **includes/imports** (e.g., `{include:common_rules.txt}`) for reusable fragments?
- How to handle template dependencies and version control?

### Prompt Metadata Validation
- Should Player enforce **metadata schema validation** before returning ActionResult (catch missing fields early)?
- What's the right balance between defensive validation and trust in PromptBuilder/Controller contracts?

### Conversation Manager Evolution
- Should `ConversationManager` support **branching histories** for A/B testing different prompts mid-match?
- How to support advanced conversation features (system messages, few-shot examples, token budgets)?

## 13. References

### Specifications
- [SPEC.md](./SPEC.md) §2.4 (Reproducibility requirements)
- [SPEC.md](./SPEC.md) §3.2 (Composition and separation of concerns)
- [SPEC-CONSOLE.md](./SPEC-CONSOLE.md) v0.3.0 (Handshake orchestration H1-H5)
- [SPEC-OBSERVABILITY.md](./SPEC-OBSERVABILITY.md) §3.1.1 (Player lifecycle events)
- [SPEC-RECORDER.md](./SPEC-RECORDER.md) v2.0.0 §6.7 (Prompt / interaction metadata capture)
- [SPEC-REPLAY.md](./SPEC-REPLAY.md) v2.0.0 (Event parity using canonical payloads)
- [SPEC-PROMPT-BUILDER.md](./SPEC-PROMPT-BUILDER.md) (Template-driven prompt composition)
- [SPEC-CONTROLLER.md](./SPEC-CONTROLLER.md) (Action and handshake controller contracts)
- [SPEC-RENDERER.md](./SPEC-RENDERER.md) v0.3.0 (Game view rendering)
- [SPEC-LLM.md](./SPEC-LLM.md) (Provider transport and API contracts)
- [SPEC-PRICING.md](./SPEC-PRICING.md) v1.0.0 (Pricing system integration and metadata requirements)
- [SPEC-GAME.md](./SPEC-GAME.md) v0.3.0 (Game rules and state management)
