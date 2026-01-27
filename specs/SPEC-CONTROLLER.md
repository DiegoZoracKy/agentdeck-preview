# SPEC-CONTROLLER: Unified Controller Contract

> Status: Draft v1.3.0 (Pending Review)
> Version: 1.3.0
> Last Updated: 2025-11-17
> Implementation: ✅ Complete (src/agentdeck/core/base/controller.py)
> Authors: Diego ZoracKy, Codex, Claude
> Audience: Player authors, controller implementers, validation tooling
>
> **Changes in v1.3.0**: Unified single-controller architecture. Controllers now handle all lifecycle phases (handshake, turn, conclusion) via lifecycle methods instead of separate controller classes. See §14 Migration Guide for dual-controller → single-controller transition.

## 1. Purpose
- Define controller responsibilities for **all player-game interaction phases**: handshake validation, turn action parsing, and optional conclusion parsing.
- Guarantee deterministic parsing, validation, and metadata capture so console and recorder can rely on controller output.
- Provide extension patterns for JSON/regex/custom controllers without coupling them to LLM invocation.
- Support prompt metadata capture (prompt_text, prompt_blocks, renderer_output) for SPEC-RECORDER PM1-PM6 requirements.
- **Simplify mental model**: One controller per player handles all phases via lifecycle methods (parallel to Renderer pattern).

## 2. Scope & Philosophy Alignment
- Upholds `SPEC.md` §3.1 separation of concerns: controllers parse/validate strings; players manage prompts/LLM calls; console orchestrates outcomes.
- Supports `SPEC.md` §2.4 reproducibility by requiring deterministic parsing and comprehensive metadata (`ParseResult`, `HandshakeResult`).
- **Unified lifecycle**: Controllers implement lifecycle methods (validate_handshake, parse, parse_conclusion) instead of separate controller objects. Default implementations handle common cases; subclasses override for customization.
- **Fail-fast principle**: Controllers MUST error clearly if `bind_game()` wasn't called when validation requires allowed actions (catch configuration errors early).
- Non-goals: prompt composition (`SPEC-PROMPT-BUILDER.md`), LLM transport (`SPEC-LLM.md`), or console orchestration (`SPEC-CONSOLE.md`).

## 3. Responsibilities
- **Handshake validation**: Default implementation accepts OK/READY/YES. Override `validate_handshake()` for custom validation. Report acceptance/rejection with reasons.
- **Turn action parsing**: Abstract `parse()` method converts LLM responses into actions/reasoning. Validate against allowed sets. **Fail explicitly on parsing errors** (v1.2.0: no fallbacks).
- **Conclusion parsing** (optional): Default passthrough implementation. Override `parse_conclusion()` for structured reflection parsing.
- **Format instructions**: Provide instructions for all phases via `get_handshake_format_instructions()` and `get_format_instructions()`.
- **Metadata enrichment**: Attach candidates, reasoning, allowed sets, and validation context for recorder/spectators.
- **Determinism**: Ensure identical input/configuration produces identical output without side effects.

## 4. Public API

### 4.1 Controller Base Class

```python
class Controller(ABC):
    """
    Unified controller handling all player-game interaction phases (v1.3.0).

    Lifecycle phases:
    1. Handshake: validate_handshake() - Default accepts OK/READY/YES
    2. Turn: parse() - Abstract, must implement
    3. Conclusion: parse_conclusion() - Default passthrough
    """

    # ===== Handshake Phase =====

    def get_handshake_format_instructions(self) -> str:
        """
        Return handshake format instructions for PromptBuilder template injection.

        Template placeholders (backward compatibility):
        - {handshake_controller_format}: New placeholder (recommended)
        - {controller_format}: Legacy placeholder during handshake phase

        Player populates both placeholders with this method's output during handshake.

        Default: "Reply with 'OK' if you understand and are ready to begin."
        Override for custom instructions.
        """

    def validate_handshake(
        self,
        response: str,
        *,
        context: HandshakeContext | None = None
    ) -> HandshakeResult:
        """
        Validate handshake acknowledgement (HV1-HV4).

        Default implementation:
        - Accepts: "OK", "READY", "YES" (case-insensitive, ignores punctuation)
        - Normalizes: Uppercases and strips whitespace/punctuation
        - Returns: HandshakeResult(accepted, normalized_response, raw_response, reason?, metadata)

        Override for custom validation (e.g., require specific phrase, multi-language).

        Args:
            response: Raw LLM acknowledgement string
            context: Optional HandshakeContext (player_name, game_name, etc.)

        Returns:
            HandshakeResult with acceptance decision and metadata
        """

    # ===== Game Binding (before match starts) =====

    def bind_game(self, game: Game) -> None:
        """
        Bind controller to game (called once per batch by Console before handshake).

        Controllers that validate actions SHOULD extract game.allowed_actions
        and store for use in parse() and get_format_instructions().

        MUST be idempotent (safe to call multiple times with same game).

        Args:
            game: Game instance with allowed_actions list
        """

    # ===== Turn Phase =====

    def get_format_instructions(self) -> str:
        """
        Return turn action format instructions (injected via {controller_format} placeholder).

        SHOULD return game-specific instructions when bound (GB5):
        - "Respond with: ACTION: <action>\nAllowed: ATTACK, DEFEND, POTION"

        MUST return sensible defaults when unbound (GB4):
        - "Respond with: ACTION: <action>"

        Returns:
            Deterministic formatting guidance string
        """

    @abstractmethod
    def parse(self, response: str) -> ParseResult:
        """
        Parse turn action from LLM response (AP1-AP3, VF1-VF4).

        MUST return ParseResult with:
        - success=True + action + metadata (on success)
        - success=False + error + metadata (on failure, no fallbacks)

        Controllers with allowed actions MUST:
        - Validate against self._allowed_actions (if bind_game() called)
        - Raise RuntimeError if validation needed but bind_game() not called (GB6)

        Args:
            response: Raw LLM response string

        Returns:
            ParseResult(success, action, raw_response, error?, reasoning?, metadata)
        """

    # ===== Conclusion Phase (Optional) =====

    def parse_conclusion(self, response: str) -> dict:
        """
        Parse conclusion reflection (optional, default passthrough).

        Default implementation: {"reflection_text": response.strip()}
        Override for structured parsing (e.g., extract lessons_learned, strategy_adjustments).

        Args:
            response: Raw LLM conclusion string

        Returns:
            Dictionary with parsed conclusion metadata (e.g., reflection_text)
        """
```

### 4.2 Result Types

```python
@dataclass
class HandshakeResult:
    """Result from handshake validation."""
    accepted: bool                          # True if acknowledgement accepted
    normalized_response: str | None         # Uppercased, cleaned token (None if rejected)
    raw_response: str                       # Original response for observability
    reason: str | None = None              # Rejection reason if accepted=False
    metadata: dict | None = None           # Parsing context (allowed tokens, player, etc.)

@dataclass
class ParseResult:
    """Result from turn action parsing."""
    success: bool                           # True if parsing succeeded
    action: str | None                      # Normalized action (None if failed)
    raw_response: str                       # Original response for observability
    error: str | None = None               # Error message if success=False
    reasoning: str | None = None           # Extracted reasoning (if controller supports)
    normalized_action: str | None = None   # Canonical action form
    metadata: dict | None = None           # Parsing context (candidates, allowed, etc.)

    def to_action_result(self) -> ActionResult:
        """
        Convert to ActionResult (v1.2.0: raises ActionParseError on failure).

        Returns:
            ActionResult when success=True

        Raises:
            ActionParseError when success=False (carries this ParseResult)
        """

class ActionParseError(Exception):
    """
    Raised when turn action parsing fails (v1.2.0).

    Attributes:
        parse_result: Originating ParseResult with error details
    """
```

### 4.3 Built-in Controllers

```python
# ActionOnlyController - Parses "ACTION: <value>" format
class ActionOnlyController(Controller):
    """
    Parses simple ACTION: <value> format with action validation.
    Inherits default handshake validation (accepts OK/READY/YES).
    """

# ReasoningController - Parses "REASONING:\nACTION:" format
class ReasoningController(Controller):
    """
    Parses REASONING: <thinking>\nACTION: <value> format.
    Extracts reasoning text + action, validates action.
    Inherits default handshake validation.
    """
```

## 5. Invariants & Guarantees

### 5.1 Handshake Validation (HV)
1. **HV1**: `validate_handshake()` MUST be deterministic and side-effect free for a given response/context.
2. **HV2**: Controllers MUST normalise whitespace/punctuation, preserve raw response, and return upper-cased or canonical acknowledgement in `normalized_response` when `accepted=True`. When `accepted=False`, `normalized_response` MAY be `None` or a normalized form of the rejected token.
3. **HV3**: Rejection MUST set `accepted=False` and populate `reason` with a human-readable explanation.
4. **HV4**: Accepted acknowledgements SHOULD populate `metadata` (e.g., allowed tokens, player) for recorder.
5. **HV5**: Default implementation MUST accept {"OK", "READY", "YES"} (case-insensitive, punctuation-tolerant).

### 5.2 Format Instructions (FI)
6. **FI1**: `get_format_instructions()` MUST align with parsing expectations (e.g., mention `ACTION:` prefix if parser requires it).
7. **FI2**: Format instructions MUST be deterministic text (no randomness/state).
8. **FI3**: `get_handshake_format_instructions()` MUST return instructions matching `validate_handshake()` expectations.

### 5.3 Action Parsing (AP)
9. **AP1**: `parse()` MUST populate `ParseResult.raw_response` with trimmed input for observability.
10. **AP2**: On success, `ParseResult.success=True`, `ParseResult.action` contains normalised action; `error` MUST be `None`.
11. **AP3**: On failure, `ParseResult.success=False`, `ParseResult.error` SHOULD explain the failure, and `normalized_action` SHOULD be `None`.

### 5.4 Validation & Error Propagation (VF) — **v1.2.0 Semantics**
12. **VF1**: Controllers with allowed sets MUST honour `casefold` semantics and include the allowed set in metadata.
13. **VF2** (v1.2.0): `to_action_result()` MUST raise `ActionParseError` when `success=False`. The exception MUST expose the originating `ParseResult` via `error.parse_result`.
14. **VF3** (v1.2.0): Controllers MUST NOT return fallback actions. When parsing fails, `ParseResult.action` MUST be `None`, and the raised `ActionParseError` MUST be propagated to Console.
15. **VF4** (v1.2.0): `ParseResult.metadata` SHOULD contain diagnostic fields (candidates, reasoning flags, allowed actions, etc.) so downstream systems can analyse the failure.

**Rationale for v1.2.0 semantics**: Research evaluation requires observing when/how LLMs fail to follow instructions. Fallback mechanisms hide failures and prevent assessment of controller effectiveness and model instruction-following capability.

### 5.5 Metadata Integrity (MI)
16. **MI1**: `ParseResult.metadata` and `HandshakeResult.metadata` MUST be JSON-serialisable.
17. **MI2**: Controllers SHOULD include candidate lists, reasoning text, and other debug aids where available.

### 5.6 Determinism & Safety (DS)
18. **DS1**: Controllers MUST NOT mutate inputs or global state.
19. **DS2**: Repeat calls with identical input/configuration MUST yield identical outputs.

### 5.7 Game Binding (GB)
20. **GB1**: Console MUST call `controller.bind_game(game)` for all players **once per batch** before match starts (before handshake phase). Controllers remain bound across all matches in the batch.
21. **GB2**: `bind_game()` MUST be idempotent (safe to call multiple times with same game).
22. **GB3**: Controllers that validate actions SHOULD extract `game.allowed_actions` during binding and use it in both `parse()` and `get_format_instructions()`.
23. **GB4**: Controllers MUST NOT require `bind_game()` to be called before `get_format_instructions()` (must return sensible defaults when unbound).
24. **GB5**: Controllers SHOULD return game-specific format instructions when bound (e.g., "Respond with one of: ATTACK, POTION") and generic instructions when unbound (e.g., "Respond with your action").
25. **GB6**: Controllers that **require** `allowed_actions` for validation MUST raise `RuntimeError` during `parse()` if `bind_game()` was not called (fail-fast, catch configuration errors early). **Note**: Built-in controllers (`ActionOnlyController`, `ReasoningController`) are validation-optional—they accept any parsed action when unbound. Custom controllers requiring strict validation SHOULD implement this check.

### 5.8 Prompt Metadata Capture (PM)

Controllers support SPEC-RECORDER v1.0.0 §6.7 prompt metadata requirements by exposing metadata fields that Player/Console can include in ActionResult/HandshakeResult:

26. **PM1**: `ParseResult.metadata` MUST be available for Player to include in `ActionResult.metadata` alongside prompt_text, prompt_blocks, renderer_output (per SPEC-PLAYER DS2).
27. **PM2**: `HandshakeResult.metadata` MUST be available for Console to include in PLAYER_HANDSHAKE_COMPLETE/ABORT events (per SPEC-OBSERVABILITY §3.1.1).
28. **PM3**: Controllers SHOULD populate metadata with parsing-specific context (allowed_actions, candidates, reasoning, error details) to aid replay analysis.
29. **PM4**: All metadata fields MUST be JSON-serializable (aligns with MI1—no lambda functions, no non-serializable objects).

**Note**: Controllers do NOT capture prompt_text or prompt_blocks themselves (Player/PromptBuilder responsibility). Controllers provide **parsing metadata** (validation results, candidates, errors) that gets merged into the complete prompt metadata structure by Player.

## 6. Data Flow & Interaction

**Batch setup**: Console calls `player.controller.bind_game(game)` for all players **once per batch** before handshake phase (SPEC-CONSOLE §7 step 3). Controller extracts `game.allowed_actions` for validation. Controllers remain bound across all matches in batch.

**Handshake Phase**:
1. Console calls `controller.get_handshake_format_instructions()`
2. Player populates both `{handshake_controller_format}` and `{controller_format}` placeholders with instructions (backward compatibility)
3. Player invokes LLM → raw acknowledgement string
4. Console calls `controller.validate_handshake(raw, context)` → HandshakeResult
5. Console enforces policy: `accepted=True` → proceed, `accepted=False` → abort match

**Turn Phase**:
1. PromptBuilder injects `controller.get_format_instructions()` via `{controller_format}` placeholder
2. Player invokes LLM → raw response string
3. Player calls `controller.parse(raw)` → ParseResult
4. Player converts ParseResult → ActionResult via `to_action_result()` (raises ActionParseError on failure)
5. Console applies action via `game.update()` or handles parse failure per policy

**Conclusion Phase** (optional):
1. Player invokes LLM for post-match reflection → raw conclusion string
2. Player calls `controller.parse_conclusion(raw)` → metadata dict
3. Player emits reflection metadata for spectators/recorder

**Observability**: Recorder/spectators consume metadata from `HandshakeResult` (acknowledgement, reason) and `ParseResult` (candidates, reasoning, errors).

## 7. Error Handling & Edge Cases
- Controllers SHOULD trim whitespace and tolerate benign punctuation.
- When allowed actions provided, controllers MUST reject missing/invalid tokens with descriptive errors.
- JSON-based controllers SHOULD surface decode errors with detailed `json.JSONDecodeError` string.
- Controllers SHOULD guard against overly long responses (truncate or summarise metadata when necessary).
- Controllers MUST raise `RuntimeError` if `bind_game()` not called when validation requires allowed actions (GB6).

## 8. Examples

### Example 1: ActionOnlyController (Default Handshake)

```python
import re
from agentdeck import Controller, Game, ParseResult

class ActionOnlyController(Controller):
    """Parses ACTION: <value> format. Inherits default handshake (OK/READY/YES)."""

    def __init__(self) -> None:
        self._allowed_actions = None  # Bound by console via bind_game()

    # Handshake: Inherits default validate_handshake() - accepts OK/READY/YES
    # Handshake format: Inherits default get_handshake_format_instructions()

    def bind_game(self, game: Game) -> None:
        """Extract allowed actions for validation (GB1, GB3)."""
        self._allowed_actions = {action.upper() for action in game.allowed_actions}

    def get_format_instructions(self) -> str:
        """Game-specific instructions when bound, generic when unbound (GB4, GB5)."""
        if self._allowed_actions:
            actions_list = ", ".join(sorted(self._allowed_actions))
            return f"Respond in the format:\nACTION: <your_action>\n\nAllowed actions: {actions_list}"
        else:
            return "Respond in the format:\nACTION: <your_action>"

    def parse(self, response: str) -> ParseResult:
        """Parse ACTION: <value> from response (AP1-AP3, VF1-VF4)."""
        raw = response.strip()

        # Extract action from "ACTION: <action>" format
        action_match = re.search(r"ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)", raw, re.IGNORECASE)
        if not action_match:
            return ParseResult(
                success=False,
                action=None,
                raw_response=raw,
                error="No ACTION: field found",
                metadata={"allowed_actions": sorted(self._allowed_actions) if self._allowed_actions else None}
            )

        normalized = action_match.group("action").strip().upper()

        # Validate against allowed actions (if bound)
        if self._allowed_actions and normalized not in self._allowed_actions:
            return ParseResult(
                success=False,
                action=None,
                raw_response=raw,
                error=f"Invalid action '{normalized}'. Allowed: {sorted(self._allowed_actions)}",
                metadata={"allowed_actions": sorted(self._allowed_actions)}
            )

        return ParseResult(
            success=True,
            action=normalized,
            raw_response=raw,
            normalized_action=normalized,
            metadata={"allowed_actions": sorted(self._allowed_actions) if self._allowed_actions else None}
        )
```

### Example 2: Custom Handshake Validation

```python
from agentdeck import Controller, HandshakeResult, HandshakeContext

class StrictReasoningController(ReasoningController):
    """
    Extends ReasoningController with custom handshake validation.
    Requires explicit confirmation phrase instead of default OK/READY/YES.
    """

    def validate_handshake(
        self,
        response: str,
        *,
        context: HandshakeContext | None = None
    ) -> HandshakeResult:
        """Override: Require 'I understand and am ready' phrase."""
        raw = response.strip()

        required_phrase = "I understand and am ready"
        accepted = required_phrase.lower() in raw.lower()

        if accepted:
            return HandshakeResult(
                accepted=True,
                normalized_response=required_phrase.upper(),
                raw_response=raw,
                metadata={"validation_mode": "strict", "required_phrase": required_phrase}
            )
        else:
            return HandshakeResult(
                accepted=False,
                normalized_response="",
                raw_response=raw,
                reason=f"Must include phrase: '{required_phrase}'",
                metadata={"validation_mode": "strict", "required_phrase": required_phrase}
            )

    def get_handshake_format_instructions(self) -> str:
        """Override: Provide strict handshake instructions."""
        return "Reply with: 'I understand and am ready' to confirm you understand the rules."

    # Inherits all turn-phase logic from ReasoningController
```

### Example 3: ReasoningController (Full Implementation)

```python
import re
from agentdeck import Controller, Game, ParseResult

class ReasoningController(Controller):
    """
    Parses REASONING: <thinking>\nACTION: <value> format.
    Inherits default handshake validation.
    """

    def __init__(self) -> None:
        self._allowed_actions = None

    def bind_game(self, game: Game) -> None:
        self._allowed_actions = {action.upper() for action in game.allowed_actions}

    def get_format_instructions(self) -> str:
        actions_note = ""
        if self._allowed_actions:
            actions_list = ", ".join(sorted(self._allowed_actions))
            actions_note = f"\n\nAllowed actions: {actions_list}"

        return f"""Respond in the format:
REASONING: <your strategic thinking>
ACTION: <your_action>{actions_note}"""

    def parse(self, response: str) -> ParseResult:
        raw = response.strip()

        # Extract reasoning and action
        reasoning_match = re.search(r"REASONING:\s*(?P<reasoning>.*?)(?=ACTION:)", raw, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r"ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)", raw, re.IGNORECASE)

        reasoning = reasoning_match.group("reasoning").strip() if reasoning_match else None

        if not action_match:
            return ParseResult(
                success=False,
                action=None,
                raw_response=raw,
                reasoning=reasoning,
                error="No ACTION: field found",
                metadata={
                    "allowed_actions": sorted(self._allowed_actions) if self._allowed_actions else None,
                    "had_reasoning": reasoning is not None
                }
            )

        normalized = action_match.group("action").strip().upper()

        # Validate against allowed actions
        if self._allowed_actions and normalized not in self._allowed_actions:
            return ParseResult(
                success=False,
                action=None,
                raw_response=raw,
                reasoning=reasoning,
                error=f"Invalid action '{normalized}'. Allowed: {sorted(self._allowed_actions)}",
                metadata={
                    "allowed_actions": sorted(self._allowed_actions),
                    "had_reasoning": reasoning is not None
                }
            )

        return ParseResult(
            success=True,
            action=normalized,
            raw_response=raw,
            reasoning=reasoning,
            normalized_action=normalized,
            metadata={
                "allowed_actions": sorted(self._allowed_actions) if self._allowed_actions else None,
                "had_reasoning": reasoning is not None,
                "reasoning_length": len(reasoning) if reasoning else 0
            }
        )
```

## 9. Testing Strategy

| Focus | Invariants | Verification |
|-------|------------|--------------|
| Default handshake | HV1-HV5 | Feed OK/READY/YES/invalid; verify deterministic results, normalization, defaults. |
| Custom handshake | HV1-HV4 | Override validate_handshake(); test custom validation logic. |
| Action parsing | AP1-AP3 | Provide valid/invalid responses; inspect `ParseResult` success/error fields. |
| Validation & failure propagation | VF1-VF4 | Configure allowed set; trigger invalid action; assert `ParseResult` metadata populated and `ActionParseError` raised. |
| Metadata integrity | MI1-MI2 | Ensure metadata serialises to JSON; contains candidates/allowed sets. |
| Determinism | DS1-DS2 | Run parse twice with identical inputs; assert equality, no state mutation. |
| Game binding | GB1-GB6 | Test bind_game(), verify format instructions change, validation uses bound actions. |

### Concrete Test Examples

#### Test 1: Default handshake accepts OK/READY/YES (HV5)
```python
def test_default_handshake_accepts_standard_tokens():
    controller = ActionOnlyController()  # Inherits default validate_handshake()

    for token in ["OK", "ready", "YES!!!", "  ok  "]:
        result = controller.validate_handshake(token)
        assert result.accepted == True
        assert result.normalized_response in {"OK", "READY", "YES"}
```

#### Test 2: Default handshake rejects invalid tokens (HV3)
```python
def test_default_handshake_rejects_invalid():
    controller = ActionOnlyController()

    result = controller.validate_handshake("maybe")

    assert result.accepted == False
    assert "OK" in result.reason or "READY" in result.reason or "YES" in result.reason
```

#### Test 3: Custom handshake override works
```python
def test_custom_handshake_validation():
    controller = StrictReasoningController()

    # Valid
    result = controller.validate_handshake("I understand and am ready to play")
    assert result.accepted == True

    # Invalid
    result = controller.validate_handshake("OK")
    assert result.accepted == False
    assert "I understand and am ready" in result.reason
```

#### Test 4: ActionOnlyController parses valid action (AP2)
```python
def test_action_only_controller_success():
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK", "DEFEND"])
    controller.bind_game(game)

    result = controller.parse("ACTION: ATTACK")

    assert result.success == True
    assert result.action == "ATTACK"
    assert result.error is None
```

#### Test 5: ActionOnlyController raises on failure (VF2)
```python
def test_controller_raises_on_failure():
    controller = ActionOnlyController()
    game = MockGame(allowed_actions=["ATTACK"])
    controller.bind_game(game)

    result = controller.parse("ACTION: INVALID")

    # v1.2.0: to_action_result() raises ActionParseError
    with pytest.raises(ActionParseError) as excinfo:
        result.to_action_result()

    assert excinfo.value.parse_result is result
    assert "INVALID" in excinfo.value.parse_result.error
```

## 10. Open Questions / Future Work

### Multi-Step Handshake Validation
- Should controllers support **multi-step acknowledgement** (e.g., rules → acknowledge → quiz → acknowledge)?
- How would multi-round handshakes integrate with HandshakeResult (chain multiple results)?

### Contextual Allowed Actions
- Should controllers support **context-dependent action validation** (actions vary by game state)?
- How to pass current game state to `parse()` for dynamic validation?

### LLM-Based Controllers
- Should we support **LLM-powered validation** for natural language actions (e.g., "I attack the goblin" → "ATTACK")?
- How to handle LLM calls within controllers without violating separation of concerns?

## 11. Design Rationale

### Why Single-Controller Architecture (v1.3.0)?

**Problem with dual-controller pattern (v1.2.0 and earlier)**:
- ✅ Legacy dual objects: `handshake_controller=AcceptOKHandshakeController()` + turn-phase controller (e.g., `ReasoningController()`)
- ❌ Mental model complexity: "Why do I need two controllers for one player?"
- ❌ API verbosity: Two imports, two parameters for 99% of use cases
- ❌ Semantic confusion: Separate turn controllers sounded like they controlled actions rather than parsing responses
- ❌ Asymmetric importance: Handshake rarely customized (default OK/READY/YES), turn parsing is core

**Benefits of single-controller pattern**:
- ✅ Simpler mental model: One player, one controller (parallel to one player, one renderer)
- ✅ Cleaner API: One import, one parameter (`controller=ReasoningController()`)
- ✅ Semantic clarity: "Controller controls all player-game interactions"
- ✅ Default handshake "just works": Accepts OK/READY/YES without configuration
- ✅ Customization via standard OOP: Override `validate_handshake()` method when needed
- ✅ Parallel with Renderer pattern: Multiple methods, one object

**Migration path**: See §14 Migration Guide.

### Other Design Decisions

- **Default handshake implementation**: Accepts {"OK", "READY", "YES"} so 99% of cases work without customization.
- **Lifecycle methods** (validate_handshake, parse, parse_conclusion): Mirrors player lifecycle, makes controller behavior explicit.
- **Metadata-first design**: Gives recorder/spectators visibility into parsing decisions without re-running controllers.
- **Format instructions via placeholders**: `get_handshake_format_instructions()` and `get_format_instructions()` enable template injection, keeping prompts in sync with controller expectations.

## 12. Version History

### v1.3.0 (Draft - 2025-11-17): Unified Single-Controller Architecture

**Motivation**: Dual-controller pattern (separate handshake controller + turn controller) created unnecessary complexity. Single controller with lifecycle methods simplifies API and mental model.

**Breaking Changes**:
1. Removed `HandshakeController` abstract class. Handshake validation is now a lifecycle method on `Controller`.
2. Player constructor now accepts single `controller` parameter instead of `handshake_controller` plus a separate turn controller.
3. Default handshake implementation built into `Controller.validate_handshake()` (accepts OK/READY/YES).
4. Controllers override `validate_handshake()` for custom handshake logic instead of creating separate handshake controller.

**Migration Guide**: See §14.

**Research Benefits**:
- Simpler API reduces researcher onboarding friction
- Default handshake behavior matches 99% of use cases
- Clear override pattern for custom validation (standard OOP)
- Parallel structure with Renderer (one object, multiple methods)

### v1.2.0 (Final - 2025-11-03): Remove Fallback Semantics

**Changes**:
- Removed `fallback` parameter from `ParseResult.to_action_result()`
- `to_action_result()` now raises `ActionParseError` on failure
- Controllers must populate `ParseResult` metadata for failure analysis

**Rationale**: Research evaluation requires explicit visibility into parsing failures to assess controller effectiveness and model instruction-following capability.

## 13. References

### Specifications
- [SPEC.md](./SPEC.md) §2.4 (Reproducibility via deterministic parsing), §3.1 (Separation of concerns)
- [SPEC-PLAYER.md](./SPEC-PLAYER.md) v1.2.0 (Single controller parameter, lifecycle phases)
- [SPEC-CONSOLE.md](./SPEC-CONSOLE.md) (Handshake orchestration, bind_game() timing)
- [SPEC-OBSERVABILITY.md](./SPEC-OBSERVABILITY.md) §3.1.1 (Player lifecycle events)
- [SPEC-RECORDER.md](./SPEC-RECORDER.md) v1.0.0 §6.7 (PM1-PM6: Prompt metadata capture)
- [SPEC-PROMPT-BUILDER.md](./SPEC-PROMPT-BUILDER.md) (Template placeholders: {handshake_controller_format}, {controller_format})

### Implementation
- [src/agentdeck/core/base/controller.py](../src/agentdeck/core/base/controller.py) - Controller base class
- [src/agentdeck/controllers/action_only.py](../src/agentdeck/controllers/action_only.py) - ActionOnlyController
- [src/agentdeck/controllers/reasoning.py](../src/agentdeck/controllers/reasoning.py) - ReasoningController

## 14. Migration Guide: Dual-Controller → Single-Controller

### Code Changes

**Before (v1.2.0 - Dual Controller)**:
```python
from agentdeck import GPTPlayer
from agentdeck.controllers import AcceptOKHandshakeController, ReasoningController

player = GPTPlayer(
    name="Alice",
    handshake_controller=AcceptOKHandshakeController(),  # Legacy extra controller
    controller=ReasoningController(),                    # Turn/conclusion controller
    renderer=TextRenderer()
)
```

**After (v1.3.0 - Single Controller)**:
```python
from agentdeck import GPTPlayer, ReasoningController

player = GPTPlayer(
    name="Alice",
    controller=ReasoningController(),  # One controller handles all phases
    renderer=TextRenderer()
)
```

### Custom Handshake Migration

**Before (v1.2.0)**:
```python
class StrictHandshakeController(HandshakeController):
    def parse(self, response, *, context=None):
        if "I understand" not in response:
            return HandshakeResult(accepted=False, reason="Must say 'I understand'", ...)
        return HandshakeResult(accepted=True, ...)

player = GPTPlayer(
    name="Alice",
    handshake_controller=StrictHandshakeController(),
    controller=ReasoningController(),
    ...
)
```

**After (v1.3.0)**:
```python
class StrictReasoningController(ReasoningController):
    def validate_handshake(self, response, *, context=None):
        """Override handshake method on existing controller."""
        if "I understand" not in response:
            return HandshakeResult(accepted=False, reason="Must say 'I understand'", ...)
        return HandshakeResult(accepted=True, ...)

    # Inherits all turn-phase logic from ReasoningController

player = GPTPlayer(
    name="Alice",
    controller=StrictReasoningController(),  # One controller, custom handshake
    ...
)
```

### Default Handshake Behavior

**v1.3.0 Default**: All controllers inherit default `validate_handshake()` that accepts {"OK", "READY", "YES"}.

**No change needed** if you were using `AcceptOKHandshakeController()` - just remove it!

```python
# v1.2.0
player = GPTPlayer(
    handshake_controller=AcceptOKHandshakeController(),  # Explicit default
    controller=ActionOnlyController(),
    ...
)

# v1.3.0
player = GPTPlayer(
    controller=ActionOnlyController(),  # Inherits default handshake
    ...
)
```

### Deprecation Timeline

- **v1.3.0**: Single-controller architecture introduced, dual-controller deprecated but supported
- **v1.4.0** (planned): Remove dual-controller support entirely
- **Migration period**: 2 releases (v1.3.0, v1.3.1) to update codebases
