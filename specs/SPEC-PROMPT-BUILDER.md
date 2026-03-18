# SPEC-PROMPT-BUILDER: Template-Driven Prompt Composition

> Status: Final
> Version: 0.4.1
> Last Updated: 2026-03-17
> Implementation: ✅ Complete (Phase 6-8 compliance verified)
> Authors: Diego ZoracKy, Codex, Claude
> Audience: Researchers, player implementers, prompt engineers

## 1. Purpose
- Provide a deterministic, template-driven prompt builder that supports handshake, turn, and conclusion phases.
- Allow researchers to control prompt content through explicit template strings—what you write is what you get.
- Capture prompt metadata (template identifiers, rendered prompts) for recorder, observers, and debugging.

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC-PLAYER.md` lifecycle hooks; PromptBuilder is the glue between templates and controllers.
- Respects `SPEC.md` §2.4 reproducibility: same phase + turn number + inputs → identical prompt string.
- Embraces simplicity: Templates are the single source of truth for what appears in prompts.
- Non-goals: LLM invocation, controller parsing, or renderer implementation.

## 3. Responsibilities
- Resolve templates (`handshake_template`, `turn_template`, `conclusion_template`) for each lifecycle phase.
- Substitute placeholders with provided data (renderer output, controller format, extras).
- Produce rendered prompt strings for LLM invocation.
- Support optional custom block providers (`builder.bind(name, provider)`) for dynamic content.
- Emit metadata (template_id, phase, turn_number) for observability.

## 4. Public API

### PromptBuilder(*, handshake_template=None, turn_template=None, conclusion_template=None)

Create PromptBuilder instance with phase-specific templates.

**Contract**:
- Accept: Optional template strings OR Path objects for each phase
- Perform: Store templates (loading from files if Path provided), prepare placeholder bindings
- Templates use Python `str.format()` syntax: `"{placeholder_name}"`
- Template parameters accept:
  - **Literal strings**: Inline template content (e.g., `"{game_view}\n{controller_format}"`)
  - **Path objects**: File path to load (e.g., `Path("prompts/turn.txt")`)
  - When `Path` provided, builder loads file contents (UTF-8) during initialization
  - Raises `FileNotFoundError` if path doesn't exist, `UnicodeDecodeError` if not valid UTF-8
- Missing template for a phase → use minimal default (when template not provided):
  - handshake: `"You are playing {game_name}.\n\n{game_instructions}\n\n{player_instructions}\n\n{controller_format}\n\n{handshake_controller_format}"`
  - turn: `"{game_view}"`
  - conclusion: `"=== Match Concluded ===\n\n{outcome}\n\nFinal state:\n{game_view}"`
- If `conclusion_template=None` is provided explicitly, PromptBuilder stores `None` for the conclusion template and callers SHOULD skip prompt composition for conclusion (use minimal prompt metadata instead).
  - Calling `compose(phase=CONCLUSION, ...)` when the conclusion template is disabled MUST raise a `ValueError`.

**Example**:
```python
# Inline templates
builder = PromptBuilder(
    handshake_template="{game_instructions}\n{strategy}\n\nRespond with 'OK' if ready.",
    turn_template="{game_view}\n\n{controller_format}",
    conclusion_template="{outcome}\n\nReflect on your performance:",
)

# Load from files (recommended for teams iterating on wording)
from pathlib import Path
builder = PromptBuilder(
    handshake_template=Path("prompts/handshake.txt"),
    turn_template=Path("prompts/turn.txt"),
    conclusion_template=Path("prompts/conclusion.txt"),
)
```

### from_template(template: str) -> PromptBuilder

Convenience factory for single-template builders (typically turn-only).

**Contract**:
- Accept: Template string
- Return: PromptBuilder with template set for turn phase
- Use case: Simple games that don't need handshake/conclusion

**Example**:
```python
builder = PromptBuilder.from_template("{game_view}\n{controller_format}")
```

### from_file(path: Union[str, Path]) -> PromptBuilder

Load template from file (UTF-8 encoded).

**Contract**:
- Accept: File path to template
- Return: PromptBuilder with template loaded for turn phase
- Raise: `FileNotFoundError` if path doesn't exist, `UnicodeDecodeError` if not valid UTF-8

**Example**:
```python
builder = PromptBuilder.from_file("prompts/tic_tac_toe/turn.txt")
```

### bind(name: str, provider: Callable[[PromptContext], str]) -> PromptBuilder

Register custom placeholder provider for dynamic content.

**Contract**:
- Accept: Placeholder name, callable that receives PromptContext and returns string
- Return: Self (for chaining)
- Provider called during `compose()` to generate placeholder content
- Provider receives immutable context (render_result, controller_format, handshake_controller_format, turn_context, extras)

**Example**:
```python
builder.bind("timestamp", lambda ctx: datetime.now().isoformat())
builder.bind("strategy", lambda ctx: ctx.extras.get("strategy", ""))
```

### compose(*, phase: LifecyclePhase, render_result: RenderResult, controller_format: str, handshake_controller_format: Optional[str] = None, turn_context: Optional[TurnContext] = None, extras: Optional[Dict[str, Any]] = None) -> PromptBundle

Render prompt for given phase by substituting template placeholders and capturing metadata.

**Contract**:
- Accept: Lifecycle phase (HANDSHAKE/TURN/CONCLUSION), renderer output, action controller format instructions, optional handshake controller format instructions, optional turn context, optional extras dict
- Perform: Select template for phase, evaluate custom providers, substitute all placeholders, capture metadata, return PromptBundle
- Raise: `TemplateError` if a custom provider fails, `ValueError` if unsupported phase or conclusion composition is disabled
- Return: PromptBundle containing rendered prompt text, block metadata, and template info

**Available placeholders** (automatically bound unless overridden):
- `{game_view}`: Renderer output (RenderResult.text)
- `{controller_format}`: Action controller format instructions
- `{handshake_controller_format}`: Handshake controller format instructions (for handshake templates)
- Any key from `extras` dict (including values like `game_name`, `game_instructions`, or `player_instructions`)
- Any custom provider registered via `bind()`

**Note**: Placeholders from `extras` render as empty string when key not provided, allowing optional content without template changes.

**Example**:
```python
# TURN phase example
bundle = builder.compose(
    phase=LifecyclePhase.TURN,
    render_result=text_renderer.render(view, player),
    controller_format=controller.get_format_instructions(),
    turn_context=turn_ctx,
    extras={"strategy": "Prioritize corners"},
)

# Access prompt text and metadata
prompt_text = bundle.text
template_used = bundle.metadata["template_id"]
blocks_included = bundle.metadata["blocks_rendered"]
```

### from_function(compose_fn: Callable[[PromptContext], str]) -> PromptBuilder

Escape hatch for advanced composition logic.

**Contract**:
- Accept: Function that receives PromptContext and returns prompt string
- Return: PromptBuilder that delegates to custom function
- Use case: Complex dynamic prompts that can't be expressed with templates

**Example**:
```python
def custom_compose(ctx):
    if ctx.turn_number == 1:
        return f"{ctx.extras['strategy']}\n{ctx.render_result.text}"
    return ctx.render_result.text

builder = PromptBuilder.from_function(custom_compose)
```

## 5. Invariants & Guarantees

### 5.1 Template Control (TC)
1. **TC1**: Templates are the ONLY source of truth for prompt content. If a placeholder is in the template, it MUST be rendered. If absent, it MUST NOT appear in the prompt.
2. **TC2**: Researchers control what appears in each phase by choosing which placeholders to include in each template.
3. **TC3**: No hidden filtering or automatic block suppression. What you write in the template is what gets sent to the LLM.

### 5.2 Composition Determinism (CD)
4. **CD1**: Given identical phase, templates, `render_result`, `controller_format`, and `extras`, `compose()` MUST produce identical PromptBundle (same text, same blocks, same metadata).
5. **CD2**: Renderer output MUST be inserted without alteration (verbatim substitution).
6. **CD3**: Template selection based on phase MUST be deterministic (handshake_template for HANDSHAKE phase, turn_template for TURN phase, conclusion_template for CONCLUSION phase).

### 5.3 Metadata Capture (MC)
7. **MC1**: PromptBundle.metadata MUST be a non-null dict containing required keys: `template_id` (str), `phase` (str), `turn_number` (int), and `blocks_rendered` (List[str]). Implementation MAY use dataclass field factory to ensure dict is always initialized.
8. **MC2**: PromptBundle.blocks MUST contain ordered PromptBlock entries for each placeholder rendered (in order of appearance in template).
9. **MC3**: When renderer returns RenderResult with metadata, that metadata MUST be preserved in the corresponding PromptBlock.

### 5.4 Provider Safety (PS)
10. **PS1**: Custom providers MUST receive immutable `PromptContext` (render result, controller format, handshake controller format, turn context, extras).
11. **PS2**: Builder MUST memoize provider output per composition call to avoid double evaluation of the same provider.
12. **PS3**: Provider exceptions MUST surface as `TemplateError` with block name and phase context for debugging.

### 5.5 Error Handling (EH)
13. **EH1**: Missing placeholders MUST render as empty strings. PromptBuilder MUST NOT maintain a separate required/optional placeholder policy layer.
14. **EH2**: Missing template for active phase MUST fall back to minimal default template (never fail silently).
15. **EH3**: Providers raising exceptions MUST be wrapped in `TemplateError` with provider name and phase context.

## 6. Data Structures

### LifecyclePhase (Enum)
```python
class LifecyclePhase(Enum):
    HANDSHAKE = "handshake"
    TURN = "turn"
    CONCLUSION = "conclusion"
```

### PromptContext (Data Class)
```python
@dataclass
class PromptContext:
    phase: LifecyclePhase
    turn_number: int
    render_result: RenderResult
    controller_format: str
    handshake_controller_format: Optional[str]
    turn_context: Optional[TurnContext]
    extras: Dict[str, Any]
```

Immutable context passed to custom providers during composition.

### PromptBlock (Data Class)
```python
@dataclass
class PromptBlock:
    key: str              # Placeholder name (e.g., "game_view", "strategy")
    content: str          # Rendered content for this block
    metadata: Optional[Dict[str, Any]] = None  # Optional block-specific metadata
```

Represents a single content block that was rendered into the prompt. Used for observability and debugging.

### PromptBundle (Data Class)
```python
@dataclass
class PromptBundle:
    text: str                              # Final rendered prompt string
    blocks: List[PromptBlock]              # Ordered list of blocks rendered
    metadata: Dict[str, Any]               # Bundle metadata (template_id, phase, etc.)
```

**Metadata keys** (MUST be present per MC1):
- `template_id`: Identifier for the template used (string)
- `phase`: Lifecycle phase (HANDSHAKE/TURN/CONCLUSION as string)
- `turn_number`: Turn number (int, 0 for handshake/conclusion)
- `blocks_rendered`: List of block keys that were rendered (e.g., `["game_view", "controller_format"]`)

**Purpose**: Captures both the prompt text (for LLM invocation) and metadata (for recorder, debugging, and observability).

### TemplateError (Exception)
```python
class TemplateError(Exception):
    """Raised when provider-backed template rendering fails."""
    def __init__(self, message: str, placeholder: str = None, template_id: str = None, phase: str = None):
        self.placeholder = placeholder
        self.template_id = template_id
        self.phase = phase
        super().__init__(message)
```

## 7. Data Flow & Interaction

**Initialization**:
1. Researcher creates `PromptBuilder` with templates for handshake/turn/conclusion phases
2. Optionally binds custom providers for dynamic content
3. Passes builder to `GPTPlayer` (or other Player implementation)

**Composition Flow**:
1. Player calls `builder.compose(phase=..., render_result=..., controller_format=..., handshake_controller_format=..., extras=...)`
2. Builder selects template based on phase
3. Builder evaluates custom providers (if any)
4. Builder substitutes all placeholders with provided data (including `{handshake_controller_format}` for handshake phase)
5. Builder captures metadata (template_id, blocks_rendered, phase, turn_number)
6. Builder returns PromptBundle containing text + blocks + metadata
7. Player sends `bundle.text` to LLM
8. Player attaches `bundle.metadata` to ActionResult for recorder

**Observability**:
- PromptBundle.metadata contains template_id, phase, blocks_rendered list
- PromptBundle.blocks contains ordered PromptBlock entries for each placeholder
- Recorder can capture full bundle for replay and debugging
- Researchers can inspect which blocks were included without reading template

## 8. Error Handling & Edge Cases

### Undefined Placeholder

**Missing extras key (renders as empty string)**:
```python
# Template references {player_instructions} but it's not in extras
handshake_template = "{game_instructions}\n\n{player_instructions}\n\n{handshake_controller_format}"
builder.compose(
    phase=HANDSHAKE,
    render_result=...,
    controller_format=...,
    handshake_controller_format=...,
    extras={"game_instructions": "..."}  # player_instructions not provided
)
# Result: player_instructions placeholder renders as empty string (no error)
# Final prompt: "{game_instructions}\n\n\n\n{handshake_controller_format}"
```

**Missing placeholder (renders as empty string)**:
```python
# Template references {unknown_block} that's not in any source
turn_template = "{game_view}\n{unknown_block}\n{controller_format}"
builder.compose(phase=TURN, render_result=..., controller_format=..., extras={})
# Result: unknown_block renders as ""
```

**Solution**: If a block is semantically required, enforce that in the caller or a provider. PromptBuilder itself stays permissive and template-driven.

### Missing Template for Phase
```python
# Builder only has turn_template, but handshake phase requested
builder = PromptBuilder(turn_template="{game_view}")
builder.compose(phase=HANDSHAKE, ...)
# Falls back to the built-in handshake default
```

**Solution**: Provide templates for all phases you intend to use, or rely on defaults.

### Provider Exception
```python
# Custom provider raises exception
builder.bind("timestamp", lambda ctx: 1 / 0)  # ZeroDivisionError
builder.compose(...)
# Raises: TemplateError("Provider 'timestamp' failed: division by zero", placeholder="timestamp", ...)
```

**Solution**: Ensure providers handle errors gracefully or raise meaningful exceptions.

## 9. Examples

### Basic Three-Phase Setup
```python
builder = PromptBuilder(
    handshake_template="""
You are playing FixedDamageGame.

{game_instructions}

{strategy}

{handshake_controller_format}
""",
    turn_template="{game_view}\n\n{controller_format}",
    conclusion_template="{outcome}\n\nReflect on your performance:",
)

# Handshake phase (coaching included)
handshake_bundle = builder.compose(
    phase=LifecyclePhase.HANDSHAKE,
    render_result=RenderResult(text=""),  # No game state yet
    controller_format=controller.get_format_instructions(),
    handshake_controller_format=controller.get_handshake_format_instructions(),
    extras={
        "game_instructions": game.instructions,
        "strategy": "Attack relentlessly...",
    }
)
# Access prompt text and metadata
handshake_prompt = handshake_bundle.text
print(f"Template: {handshake_bundle.metadata['template_id']}")
print(f"Blocks: {handshake_bundle.metadata['blocks_rendered']}")

# Turn phase (coaching NOT included - not in template)
turn_bundle = builder.compose(
    phase=LifecyclePhase.TURN,
    render_result=text_renderer.render(view, player),
    controller_format=controller.get_format_instructions(),
    extras={
        "game_instructions": game.instructions,  # Provided but not used (not in template)
        "strategy": "Attack relentlessly...",     # Provided but not used (not in template)
    }
)
# Access prompt text - strategy NOT included (not in turn_template)
turn_prompt = turn_bundle.text
assert "strategy" not in turn_bundle.metadata["blocks_rendered"]  # Verify exclusion
```

### A/B Testing Coaching Delivery

**Variant A: Coaching in handshake only**
```python
builder_A = PromptBuilder(
    handshake_template="{game_instructions}\n{strategy}\nRespond OK",
    turn_template="{game_view}\n{controller_format}",
)
```

**Variant B: Coaching every turn**
```python
builder_B = PromptBuilder(
    handshake_template="{game_instructions}\n{strategy}\nRespond OK",
    turn_template="{strategy}\n{game_view}\n{controller_format}",  # Strategy included
)
```

**Comparison**: Templates explicitly show the difference. No hidden configuration.

### Dynamic Content with Providers
```python
builder = PromptBuilder(turn_template="{game_view}\n{hint}\n{controller_format}")

# Provide hints only when player is losing
builder.bind("hint", lambda ctx:
    "Consider using a potion!" if ctx.turn_context.player_hp < 30 else ""
)
```

### Loading from Files (Recommended Practice)
```python
# Project structure:
# prompts/
#   handshake.txt    - "You are playing {game_name}...\n{handshake_controller_format}"
#   turn.txt         - "{game_view}\n\n{controller_format}"
#   conclusion.txt   - "=== Match Concluded ===\n{outcome}\n{game_view}"

from pathlib import Path

# Pass Path objects directly (builder loads contents automatically)
builder = PromptBuilder(
    handshake_template=Path("prompts/handshake.txt"),
    turn_template=Path("prompts/turn.txt"),
    conclusion_template=Path("prompts/conclusion.txt"),
)

# Benefits:
# - Version control: Git tracks template changes separately
# - Iteration: Copy/paste/tweak workflow without code changes
# - Review: Easier to review prompt wording in plain text files
# - Reuse: Share templates across experiments
```

## 10. Testing Strategy

| Focus | Invariants | Verification |
|-------|------------|--------------|
| Template control | TC1-TC3 | Compose prompts with different templates; assert only referenced placeholders appear. |
| Determinism | CD1-CD3 | Compose twice with identical inputs; assert identical PromptBundle (text, blocks, metadata). |
| Metadata capture | MC1-MC3 | Compose prompts; assert metadata includes template_id, phase, blocks_rendered; verify PromptBlock ordering. |
| Provider safety | PS1-PS3 | Register provider raising exception; confirm TemplateError surfaces with context. |
| Error handling | EH1-EH3 | Verify missing placeholders render empty strings, missing templates fall back to defaults, and provider exceptions surface as `TemplateError`. |
| Phase selection | CD3 | Compose for each phase; assert correct template selected. |

## 11. Design Rationale

### Templates as Single Source of Truth
- **Simplicity**: Researchers see exactly what will be sent to the LLM by reading the template.
- **Explicitness**: No hidden filtering, policies, or magic. What you write is what you get.
- **Debuggability**: Print the template to understand prompt structure. No need to mentally simulate policy interactions.
- **Traceability**: Git diffs show template changes directly. No separate configuration to track.

### No DeliveryPolicy / Block Filtering
- **YAGNI**: No proven use case that templates can't handle.
- **Flexibility**: Researchers can use Python (conditionals, functions) or templating engines (Jinja2) for complex logic when needed.
- **One Way to Do It**: Avoid "should I edit template or change policy?" confusion.
- **Future-Proof**: Can add richer templating (Jinja2, conditionals) without breaking existing API.

### Metadata for Observability
- **PromptBundle Structure**: Returns both text (for LLM) and metadata (for recorder/debugging).
- **Blocks List**: Captures which placeholders were rendered and in what order.
- **Template Transparency**: Researchers can inspect `blocks_rendered` without parsing template strings.
- **Deterministic Metadata**: Same inputs → same metadata, enabling replay and debugging.

### Provider Pattern for Dynamic Content
- **Escape Hatch**: Researchers needing dynamic logic can use providers without forking PromptBuilder.
- **Immutable Context**: Providers can't mutate state, ensuring determinism.
- **Lazy Evaluation**: Providers evaluated during composition, enabling turn-specific logic.

## 12. Migration from v0.3.0 (DeliveryPolicy)

**For researchers using previous spec**:

**Old approach (v0.3.0 with DeliveryPolicy)**:
```python
builder = PromptBuilder(
    handshake_template="{game_instructions}\n{strategy}\nRespond OK",
    turn_template="{game_view}\n{controller_format}",
    block_policies={
        "game_instructions": DeliveryPolicy.HANDSHAKE,
        "strategy": DeliveryPolicy.HANDSHAKE,
        "game_view": DeliveryPolicy.EVERY_TURN,
        "controller_format": DeliveryPolicy.EVERY_TURN,
    }
)
```

**New approach (v0.4.0 template-only)**:
```python
# Same templates, no block_policies needed!
# Templates already control what appears in each phase
builder = PromptBuilder(
    handshake_template="{game_instructions}\n{strategy}\nRespond OK",
    turn_template="{game_view}\n{controller_format}",
)

# Compose returns PromptBundle (text + metadata)
bundle = builder.compose(phase=TURN, ...)
prompt_text = bundle.text  # Send to LLM
blocks_rendered = bundle.metadata["blocks_rendered"]  # ["game_view", "controller_format"]
```

**Key changes**:
1. No `block_policies` parameter (templates control what appears)
2. `compose()` returns `PromptBundle` instead of just string (metadata preserved)
3. Metadata automatically captures which blocks were rendered

## 13. References
- `specs/SPEC-PLAYER.md` (Three-phase lifecycle)
- `specs/SPEC-CONSOLE.md` (Match orchestration)
- `specs/SPEC-CONTROLLER.md` (Format instructions)
- `specs/SPEC-LLM.md` (LLM invocation)
- `specs/SPEC.md` §2.4 (Reproducibility)
- `docs/AGENTS.md` §2.1 (Separation of concerns)
- `docs/GUIDELINES.md` §2c (Lean writing, simplicity)
