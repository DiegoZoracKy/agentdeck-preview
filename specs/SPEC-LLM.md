# SPEC-LLM: Provider Integration Contract

> Status: Final
> Version: 1.3.0
> Last Updated: 2026-08-24
> Implementation: ✅ Complete (Phase 6-8 compliance verified)
> Audience: LLM integration authors, pricing/ops maintainers, execution operators

## 1. Purpose
- Standardise how AgentDeck players invoke external LLM providers across handshake, turn, and conclusion phases.
- Guarantee retry/backoff semantics, metadata capture (usage, cost, retries), and conversation history management.
- Provide extension hooks for new providers while keeping player/prompt/controller contracts consistent.

## 2. Scope & Philosophy Alignment
- Upholds `SPEC.md` §3.2 separation: LLM players handle API transport; console governs lifecycle; controllers/renderer stay provider-agnostic.
- Reinforces `SPEC.md` §2.4 reproducibility by capturing tokens, costs, latency, retries, and provider identifiers.
- **Clean slate design**: v1.0.0 assumes modern three-phase lifecycle (handshake → turn → conclusion) with prompt metadata capture—no legacy handshake policy system, no backward compatibility shims.
- **Provider transparency**: All LLM calls (handshake, turn, conclusion) MUST capture complete metadata for cost accounting, fairness analysis, and reproducibility studies.
- Non-goals: prompt composition (see `SPEC-PROMPT-BUILDER.md`), controller parsing (`SPEC-CONTROLLER.md`), or game orchestration (`SPEC-CONSOLE.md`).

## 3. Responsibilities
- **Credential & client setup**: Resolve API keys (constructor arg > env var) and initialise provider SDK clients in `_initialize_client`.
- **Request execution**: Build provider-specific payloads, invoke models with retry/backoff, and surface errors after exhausting retries for handshake, turn, and conclusion calls.
- **Usage & cost tracking**: Aggregate per-call metadata (tokens, cost, latency) and maintain running totals for reporting.
- **Metadata injection**: Supply `usage_info`, retry metrics, and provider extras to `HandshakeResult` / `ActionResult` metadata.
- **Conversation management**: Maintain local history when no `ConversationManager` is bound and preserve handshake exchanges in history.
- **Prompt hygiene**: For template-driven conclusion prompts, sanitize engine bookkeeping keys from rendered final-state views before LLM invocation.

## 4. Public API
- `LLMPlayer(name, *, api_key=None, model=None, temperature=1.0, max_tokens=None, controller, renderer=None, handshake_template=None, turn_template=None, conclusion_template=None, max_retries=3, retry_delay=1.0, **kwargs)`
  - **Note**: Single `controller` parameter per SPEC-PLAYER v1.2.0 / SPEC-CONTROLLER v1.3.0.
  - `conclusion_template=None` disables conclusion prompt composition; player SHOULD still record minimal conclusion prompt metadata for observability.
  - `kwargs` forwarded to provider (top_p, penalties, optional `prompt`, etc.).
  - `temperature=None` explicitly leaves temperature unset. Provider adapters
    that support this option MUST omit the native request field rather than
    send JSON `null`; Player configuration and Records preserve the observed
    `None` value. OR6 currently requires this behavior for OpenAI.
  - `max_retries` is the number of retries after the initial provider attempt.
    It MUST be a non-negative integer. `max_retries=0` therefore makes exactly
    one provider attempt and performs no retry.
  - Defaults: PromptBuilder handshake/turn defaults and `TextRenderer`. Controller parameter is required.
- Subclass responsibilities:
  - `_initialize_client() -> None`: Setup provider SDK; raise informative errors if missing.
  - `_make_api_call(messages: List[Dict[str, str]]) -> Tuple[str, Dict]`: Perform single API call, returning response text and metadata (tokens, cost, provider model, etc.).
- `clone() -> LLMPlayer`
  - MUST construct a fresh instance recreating provider clients instead of copying them.
  - SHOULD preserve configuration (model, temperature, templates, controllers/renderer) and aggregate metrics (total tokens, cost, latency samples) so researchers observe consolidated statistics after parallel execution (SPEC-PARALLEL §5).
  - Example:
    ```python
    def clone(self) -> "GPTPlayer":
        return self.__class__(
            name=self.name,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            controller=copy.deepcopy(self.controller),  # v1.2.0: single controller
            renderer=copy.deepcopy(self.renderer) if self.renderer else None,
            handshake_template=getattr(self.prompt_builder, "_handshake_template", None),
            turn_template=getattr(self.prompt_builder, "_turn_template", None),
            conclusion_template=getattr(self.prompt_builder, "_conclusion_template", None),
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            **copy.deepcopy(self.config),
        )
    ```
- Provided helpers:
  - `_invoke_model(bundle, turn_context)` handles retry/backoff, logging, and metadata packaging. Phase context is derived from the active lifecycle call.
  - `reset_conversation()`, `_history_source()`, `_append_history()` manage conversation state when no manager bound.
  - `get_stats()`, `get_summary()` expose cumulative usage metrics.

## 5. Invariants & Guarantees
### 5.1 Credentials & Configuration (CC)
1. **CC1**: MUST resolve credentials via constructor argument > env var > provider-specific defaults (e.g., Google ADC). Providers supporting Application Default Credentials (ADC) or similar implicit auth MAY skip explicit `api_key` requirement. Env-based credential material MAY include encoded payloads such as `GOOGLE_APPLICATION_CREDENTIALS_B64` when the provider SDK supports direct credential injection. Raise `ValueError` only when no valid credential path exists.
2. **CC2**: MUST ensure `model` set (constructor override or class-level `default_model`); raise `ValueError` otherwise.
3. **CC3**: MUST call `_initialize_client` during construction; failures MUST raise actionable `ImportError`/`ValueError`.

### 5.2 Request Execution (RE)
4. **RE1**: `_invoke_model` MUST make one initial provider attempt and then up to `max_retries` additional attempts, applying exponential backoff (`retry_delay * 2**attempt`) before each retry. `max_retries=0` MUST still make the initial attempt.
5. **RE2**: MUST log request/response metadata via logger when attached (phase included).
6. **RE3**: MUST propagate final failure as `RuntimeError` with provider/model context and the total number of attempts (`1 + max_retries`) when retries are exhausted.

### 5.3 Metadata & Accounting (MA)
7. **MA1**: MUST populate `usage_info` with tokens, prompt/completion tokens (when available), cost, latency_ms, model, provider identifiers.
8. **MA2**: MUST accumulate `total_tokens`, `total_cost`, and latency samples across calls. `get_stats()` MUST expose `total_tokens`, `total_cost`, `avg_response_time`, and `model`.
9. **MA3**: MUST attach retry counters (`retries`, `retry_durations`, `attempt_durations`) to metadata for recorder.
10. **MA4**: SHOULD flag estimated metrics (`estimated=True`) when providers return approximations.

### 5.4 Conversation & History (CH)
11. **CH1**: When `ConversationManager` is bound, MUST delegate history logging (handshake, turns, conclusion) to the manager.
12. **CH2**: When manager absent, player lifecycle recording MUST append to `_local_history` (user/assistant pairs) and include handshake exchanges.
13. **CH3**: `reset_conversation()` MUST clear local history between matches regardless of handshake policy.
14. **CH4**: For template-driven conclusion composition (no explicit `match_context.conclusion_prompt` override), LLM players MUST sanitize engine bookkeeping keys from final-state prompt views before invoking the model. At minimum `_turn_count` and `_first_player_idx` MUST be removed.

### 5.5 Pricing Integration (PI)
15. **PI1**: Every LLMPlayer subclass MUST define a class-level `PROVIDER` constant identifying the provider (e.g., `"openai"`, `"anthropic"`, `"google"`) for cost calculation (SPEC-PRICING § 7.2 P1).
16. **PI2**: MUST use `calculate_cost(provider, model, prompt_tokens, completion_tokens)` to derive USD cost.
17. **PI3**: MUST log warning and default cost to `$0.00` when pricing info unavailable.

### 5.6 Prompt Metadata Capture (PM)
18. **PM1**: `_invoke_model` MUST return metadata dict containing `usage_info` (tokens, cost, latency_ms, model, provider) for Player to include in `ActionResult.metadata` / `HandshakeResult.metadata`.
19. **PM2**: Metadata MUST include `response_text` (raw LLM output before controller parsing) so Recorder can preserve it in lifecycle payloads or gameplay `interaction` payloads (SPEC-RECORDER v2.0 §6.7).
20. **PM3**: MUST capture phase context (`phase: LifecyclePhase`) in metadata to distinguish handshake/turn/conclusion calls in recorder events.
21. **PM4**: All metadata values MUST be JSON-serializable (no lambda functions, no non-serializable SDK objects).

### 5.7 Cloning & Parallel Execution (CL)
22. **CL1**: LLM players MUST override `clone()` to recreate provider SDK clients (new HTTP session, fresh locks) instead of copying them. Clone implementations MUST preserve configuration and aggregate metrics while leaving runtime bindings (conversation manager, logger) unset so the console can rebind them (see SPEC-PARALLEL §5). Failure to provide a working clone MUST raise a clear error directing researchers to run with `concurrency=1` or implement cloning.
23. **CL2**: LLM players MUST pass correlation metadata (`call_id`, `match_id`, `turn_number`, `phase`) to `api_request`, `api_response`, and `api_call` logger hooks so debug logs can be deterministically joined per call in concurrent runs.

### 5.8 OpenAI Responses API Contract (OR)
24. **OR1**: OpenAI-backed players MUST invoke `client.responses.create(...)` for model calls and MUST extract reply text from `response.output_text`; when `output_text` is empty, implementations MUST fallback to parsing text blocks under `response.output` and fail noisily if no text exists.
25. **OR2**: OpenAI-backed players MUST map prompt arrays to Responses API shape as follows: all `system` messages are joined into top-level `instructions`, while non-system messages are sent in top-level `input`.
26. **OR3**: OpenAI-backed players MUST normalize token-limit aliases (`max_tokens`, `max_completion_tokens`, `max_output_tokens`) to `max_output_tokens` before request dispatch, and MUST reject conflicting alias values with a clear `ValueError`.
27. **OR4**: OpenAI-backed players MUST map usage fields `usage.input_tokens` / `usage.output_tokens` into internal metadata keys `prompt_tokens` / `completion_tokens` to keep pricing and spectator contracts stable.
28. **OR5**: Until explicit server-history mode is introduced, OpenAI-backed players MUST send `store=False` on Responses API calls so match reproducibility remains grounded in local conversation history.
29. **OR6**: When an OpenAI-backed Player has `temperature=None`, the adapter MUST omit `temperature` from the Responses API request. This represents a provider-default, not a measured zero. Explicit numeric temperatures remain unchanged.
30. **AR1**: Anthropic-backed players MUST supply `max_tokens` on every request. When callers leave `max_tokens` unset, implementations MUST apply a documented fallback.
31. **GR1**: Gemini-backed players MAY authenticate via Vertex ADC or `GOOGLE_APPLICATION_CREDENTIALS_B64`. When base64 credentials are supplied, implementations MUST decode the JSON payload, create scoped Google credentials suitable for Vertex (`cloud-platform`), construct the provider client in Vertex mode, and infer `project_id` from the payload when possible.
32. **GR2**: Gemini-backed players MUST preserve multi-turn role structure using the provider's native content model rather than flattening history into a labeled transcript. User messages MUST be sent as user-role content, assistant messages MUST be sent as model-role content, and system instructions SHOULD use the provider-native system-instruction field when available.

### 5.9 Provider Call Audit (PCA)

33. **PCA1 Adapter Boundary**: Immediately before invoking an official provider SDK, an adapter MUST retain a strict-JSON snapshot of the effective method and arguments. This proves what AgentDeck handed to the SDK; it does not claim to intercept HTTP traffic.
34. **PCA2 Request Transformation**: Provider-neutral composed messages and provider-native SDK arguments MUST remain separate so adapter transformations are inspectable.
35. **PCA3 Attempt History**: Every attempted call MUST retain attempt order, start time, duration, outcome, and SDK request. A successful retry MUST NOT erase failed attempts.
36. **PCA4 Provider Response**: Successful calls MUST retain exact response text plus provider-returned model, response ID, stop reason, completion status, service tier, and token usage when exposed by the SDK. Missing values remain absent, never inferred.
37. **PCA5 JSON Safety**: Persisted call provenance MUST contain no credentials, SDK clients, live response objects, or other non-JSON values.

## 6. Data Flow & Interaction
- Player lifecycle calls `_invoke_model` for each phase:
  1. **Handshake**: Build handshake messages → `_invoke_model(...)` → provider metadata stored in handshake extras.
  2. **Turn**: Build turn messages → `_invoke_model(...)` → action controller parse.
  3. **Conclusion**: Optional reflection messages → `_invoke_model(...)`.
- `_invoke_model` collects metadata, updates totals, and returns `(response_text, metadata)` to the player lifecycle method. Prompt/response history is then recorded by `Player._record_exchange()`.
- Recorder/spectators consume usage metadata from `HandshakeResult` / `ActionResult` extras.

## 7. Error Handling & Edge Cases
- MUST raise informative `ImportError` if provider SDK missing.
- MUST raise `ValueError` for missing API key/model.
- MUST catch provider exceptions inside retry loop, log retry attempt, and backoff before retrying.
- MUST ensure handshake failures propagate so console can enforce policy.
- SHOULD support provider-specific quirks (e.g., OpenAI Responses API instructions/input mapping and max_output_tokens, Anthropic role mapping, Gemini token estimates and structured role mapping) while keeping metadata shape consistent.

## 8. Examples
```python
from agentdeck.players.openai_player import GPTPlayer

player = GPTPlayer(
    name="AggressiveBot",
    model="gpt-4o-mini",
    max_tokens=200,
    temperature=0.2,
    handshake_template="prompts/handshake.txt",
    turn_template="prompts/turn.txt",
)
```

```python
class CustomAPIPlayer(LLMPlayer):
    """Custom provider integration example."""
    PROVIDER = "custom"  # PI1: Required for pricing integration
    default_model = "research-model"
    api_key_env_var = "CUSTOM_API_KEY"

    def _initialize_client(self):
        self.client = CustomSDK(api_key=self.api_key)

    def _make_api_call(self, messages):
        response = self.client.generate(messages, temperature=self.temperature, **self.config)
        metadata = {
            "tokens_used": response.tokens,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "cost": response.cost,
            "model": response.model_name,
        }
        return response.text, metadata
```

### Extended Example: Multi-Provider Tournament

```python
from agentdeck.players.openai_player import GPTPlayer
from agentdeck.players.anthropic_player import ClaudePlayer
from agentdeck.players.google_player import GeminiPlayer

# Each provider class defines PROVIDER constant for pricing (PI1):
# GPTPlayer.PROVIDER = "openai"
# ClaudePlayer.PROVIDER = "anthropic"
# GeminiPlayer.PROVIDER = "google"

# Create players from different providers
players = [
    GPTPlayer(
        name="GPT-4o",
        model="gpt-4o-mini",
        temperature=0.7,
        handshake_template="prompts/handshake.txt",
        turn_template="prompts/turn.txt",
    ),
    ClaudePlayer(
        name="Claude-3.5-Sonnet",
        model="claude-3-5-sonnet-20241022",
        temperature=0.8,
        handshake_template="prompts/handshake.txt",
        turn_template="prompts/turn.txt",
    ),
    GeminiPlayer(
        name="Gemini-2.0-Flash",
        model="gemini-2.0-flash-exp",
        temperature=0.7,
        handshake_template="prompts/handshake.txt",
        turn_template="prompts/turn.txt",
    ),
]

# Run tournament across providers
console.run(game, players, matches=10)

# Compare provider costs and performance
for player in players:
    stats = player.get_stats()
    print(f"{player.name}:")
    print(f"  Total cost: ${stats['total_cost']:.4f}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Avg latency: {stats['avg_response_time'] * 1000:.0f}ms")
```

### Extended Example: Conversation Manager Integration

```python
from agentdeck.conversation import ConversationManager

# Create conversation manager for multi-turn reasoning
conv_manager = ConversationManager(max_history_turns=10)

player = GPTPlayer(
    name="ReasoningBot",
    model="gpt-4o",
    temperature=0.9,
    handshake_template="prompts/handshake.txt",
    turn_template="prompts/turn_with_history.txt",
)

# Bind conversation manager (player delegates history to manager)
player.bind_conversation_manager(conv_manager)

# Run match - player automatically logs all LLM exchanges (handshake, turns, conclusion)
console.run(game, [player], matches=1)

# Access conversation history via manager
history = conv_manager.get_history()
print(f"Conversation had {len(history)} exchanges")
for i, msg in enumerate(history):
    print(f"{i+1}. {msg['role']}: {msg['content'][:50]}...")
```

## 9. Testing Strategy
| Focus | Invariants | Verification |
|-------|------------|--------------|
| Credential resolution | CC1-CC3 | Instantiate with/without API key; assert env fallback and `_initialize_client` errors.
| Retry logic | RE1-RE3 | Inject failing `_make_api_call`; assert exponential backoff, logger retries, final RuntimeError.
| Metadata completeness | MA1-MA4 | Stub provider response; ensure usage info/ cost / retries update correctly (handshake + turns).
| Conversation handling | CH1-CH3 | Bind mock conversation manager vs none; ensure history recorded/reset, handshake preserved.
| Pricing integration | PI1-PI3 | Verify PROVIDER constant defined; mock `calculate_cost` success/failure; verify cost recorded and warnings emitted.
| Prompt metadata | PM1-PM4 | Verify response_text, usage_info, phase captured in metadata; assert JSON-serializable.
| Optional OpenAI temperature | OR6 | Set `temperature=None`; assert the SDK request and provider-call audit omit the field while Player introspection preserves `None`.

### Concrete Test Examples

#### Test 1: Credential resolution with fallback (CC1)
```python
import os
import pytest

def test_api_key_resolution():
    # Case 1: API key from constructor
    player = GPTPlayer(name="Test", api_key="explicit-key", model="gpt-4o-mini")
    assert player.api_key == "explicit-key"

    # Case 2: API key from environment variable
    os.environ["OPENAI_API_KEY"] = "env-key"
    player = GPTPlayer(name="Test", model="gpt-4o-mini")
    assert player.api_key == "env-key"
    del os.environ["OPENAI_API_KEY"]

    # Case 3: Missing API key raises ValueError
    with pytest.raises(ValueError, match="API key.*required"):
        GPTPlayer(name="Test", model="gpt-4o-mini")
```

#### Test 2: Exponential backoff on retries (RE1)
```python
from unittest.mock import patch, MagicMock
import time

def test_retry_exponential_backoff():
    player = GPTPlayer(name="Test", api_key="test", model="gpt-4o-mini", max_retries=3, retry_delay=0.1)

    call_times = []

    def failing_api_call(messages):
        call_times.append(time.time())
        raise Exception("Transient error")

    with patch.object(player, '_make_api_call', side_effect=failing_api_call):
        with pytest.raises(RuntimeError, match="retries exhausted"):
            player._invoke_model(
                bundle=MagicMock(messages=[{"role": "user", "content": "test"}]),
                turn_context=None,
            )

    # Verify exponential backoff: delays should be ~0.1s, ~0.2s, ~0.4s
    assert len(call_times) == 4  # Initial + 3 retries
    delays = [call_times[i+1] - call_times[i] for i in range(3)]
    assert delays[0] < 0.15  # ~0.1s
    assert 0.15 < delays[1] < 0.3  # ~0.2s
    assert 0.3 < delays[2] < 0.5  # ~0.4s
```

#### Test 3: Usage metadata accumulation (MA1, MA2)
```python
def test_usage_metadata_accumulation():
    player = GPTPlayer(name="Test", api_key="test", model="gpt-4o-mini")

    # Mock successful API calls with different token counts
    def mock_api_call(messages):
        return "response", {
            "tokens_used": 100,
            "prompt_tokens": 60,
            "completion_tokens": 40,
            "cost": 0.002,
            "model": "gpt-4o-mini",
        }

    with patch.object(player, '_make_api_call', side_effect=mock_api_call):
        # Call 1: Handshake
        player._active_phase = "handshake"
        response1, meta1 = player._invoke_model(
            bundle=MagicMock(messages=[{"role": "user", "content": "handshake"}]),
            turn_context=None,
        )
        assert meta1["usage_info"]["tokens_used"] == 100
        assert meta1["usage_info"]["cost"] == 0.002

        # Call 2: Turn
        response2, meta2 = player._invoke_model(
            bundle=MagicMock(messages=[{"role": "user", "content": "turn"}]),
            turn_context=TurnContext(turn_number=1),
        )

    # Verify cumulative stats
    stats = player.get_stats()
    assert stats["total_tokens"] == 200  # 100 + 100
    assert stats["total_cost"] == 0.004  # 0.002 + 0.002
    assert stats["avg_response_time"] >= 0
```

#### Test 4: Conversation history management with manager (CH1)
```python
def test_conversation_manager_delegation():
    player = GPTPlayer(name="Test", api_key="test", model="gpt-4o-mini")
    mock_manager = MagicMock()
    player.bind_conversation_manager(mock_manager)

    def mock_api_call(messages):
        return "OK", {"tokens_used": 10, "cost": 0.0}

    with patch.object(player, '_make_api_call', side_effect=mock_api_call):
        context = MagicMock()
        bundle = player.build_handshake_bundle(context)
        player.execute_handshake(bundle, context)

    # Verify history delegated to manager
    mock_manager.append_history.assert_called()
    assert player._local_history == []  # Local history not used when manager bound
```

#### Test 5: Conversation reset between matches (CH3)
```python
def test_conversation_reset():
    player = GPTPlayer(name="Test", api_key="test", model="gpt-4o-mini")

    # Manually populate local history
    player._local_history = [
        {"role": "user", "content": "turn 1"},
        {"role": "assistant", "content": "action 1"}
    ]

    # Reset conversation
    player.reset_conversation()

    assert player._local_history == []
```

#### Test 6: Prompt metadata capture (PM1-PM4)
```python
def test_prompt_metadata_capture():
    player = GPTPlayer(name="Test", api_key="test", model="gpt-4o-mini")

    def mock_api_call(messages):
        return "ACTION: ATTACK", {
            "tokens_used": 50,
            "prompt_tokens": 30,
            "completion_tokens": 20,
            "cost": 0.001,
            "model": "gpt-4o-mini",
        }

    with patch.object(player, '_make_api_call', side_effect=mock_api_call):
        response, metadata = player._invoke_model(
            bundle=MagicMock(messages=[{"role": "user", "content": "Your turn"}]),
            turn_context=TurnContext(turn_number=1),
        )

    # Verify PM requirements
    assert metadata["response_text"] == "ACTION: ATTACK"  # PM2: raw LLM output
    assert "usage_info" in metadata  # PM1: usage info present
    assert metadata["phase"] == LifecyclePhase.TURN  # PM3: phase captured

    # PM4: Verify JSON-serializable
    import json
    json_str = json.dumps(metadata)  # Should not raise
    assert json_str is not None
```

#### Test 7: PROVIDER constant required (PI1)
```python
def test_provider_constant_defined():
    """Verify all LLM player classes define PROVIDER constant."""
    from agentdeck.players.openai_player import GPTPlayer
    from agentdeck.players.anthropic_player import ClaudePlayer
    from agentdeck.players.google_player import GeminiPlayer

    # PI1: PROVIDER constant must be defined
    assert hasattr(GPTPlayer, "PROVIDER")
    assert GPTPlayer.PROVIDER == "openai"

    assert hasattr(ClaudePlayer, "PROVIDER")
    assert ClaudePlayer.PROVIDER == "anthropic"

    assert hasattr(GeminiPlayer, "PROVIDER")
    assert GeminiPlayer.PROVIDER == "google"

    # Verify TokenUsageTracker can access PROVIDER
    player = GPTPlayer(name="Test", api_key="test", model="gpt-4o-mini")
    assert player.PROVIDER == "openai"  # Accessible via instance
```

## 10. Open Questions / Future Work

### Streaming Response Support
- Should LLM players support **streaming responses** for long-form generation (e.g., conclusion reflections)?
- How to capture metadata (tokens, cost) for partial stream chunks while maintaining determinism?

### Batch API Integration
- How should players integrate with **batch APIs** (e.g., OpenAI Batch API) for cost savings on large tournaments?
- Should console orchestrate batch submission, or should players handle batching internally?

### Multi-Modal Input Support
- Should `_make_api_call` support **images, audio, or video** in messages for multi-modal models?
- How to extend metadata capture for non-text input tokens and costs?

### Provider-Specific Optimizations
- Should players expose **provider-specific features** (e.g., Anthropic's prompt caching, OpenAI's reasoning tokens)?
- How to balance standardization vs provider-specific performance gains?

### Cost Budget Enforcement
- Should players enforce **per-match or per-tournament cost budgets** to prevent runaway expenses?
- How to gracefully abort matches when budget exhausted?

### Model Fallback Chains
- Should players support **automatic model fallback** (e.g., GPT-4o → GPT-4o-mini on rate limit)?
- How to track which model was actually used for each call in metadata?

### Async LLM Calls
- Should `_invoke_model` support **async/await** for concurrent handshake processing?
- How to maintain conversation ordering with parallel turn execution?

### Provider Authentication Beyond API Keys
- Should players support **OAuth, IAM roles, or service accounts** for enterprise deployments?
- How to handle credential refresh and rotation during long-running tournaments?

## 11. Design Rationale
- Unified `_invoke_model` ensures handshake, turns, and conclusion share identical retry/metadata semantics.
- Defaults (Null templates, AcceptOK handshake) let researchers spin up players quickly while enabling deeper customisation.
- Usage metadata is critical for budgeting and fairness studies; spec enforces consistent capture across phases.

## 12. References

### Specifications
- [SPEC.md](./SPEC.md) §2.4 (Reproducibility via token/cost/retry metadata capture)
- [SPEC.md](./SPEC.md) §3.2 (Separation of concerns: LLM transport vs prompt composition vs parsing)
- [SPEC-PLAYER.md](./SPEC-PLAYER.md) v1.0.0 (Three-phase lifecycle: handshake → turn → conclusion)
- [SPEC-CONTROLLER.md](./SPEC-CONTROLLER.md) v1.0.0 (Controller parsing post-LLM, provider-agnostic validation)
- [SPEC-CONSOLE.md](./SPEC-CONSOLE.md) v0.3.0 (Console orchestration, handshake enforcement)
- [SPEC-PROMPT-BUILDER.md](./SPEC-PROMPT-BUILDER.md) (Template-driven prompt composition, message array construction)
- [SPEC-OBSERVABILITY.md](./SPEC-OBSERVABILITY.md) §3.1.1 (Player lifecycle events with metadata)
- [SPEC-RECORDER.md](./SPEC-RECORDER.md) v1.0.0 §6.7 (Prompt metadata capture: response_text, usage_info, phase)
- [SPEC-REPLAY.md](./SPEC-REPLAY.md) v1.0.0 (Dialogue array replay with LLM metadata preservation)
- [SPEC-PRICING.md](./SPEC-PRICING.md) v1.0.0 (PROVIDER constant requirement § 7.2, cost calculation integration)
