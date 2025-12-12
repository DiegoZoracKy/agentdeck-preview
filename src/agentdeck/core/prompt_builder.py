"""
Template-driven prompt composition for AgentDeck v1.0.0.

This module implements the PromptBuilder class per SPEC-PROMPT-BUILDER v0.4.0,
providing deterministic, template-driven prompt composition for handshake, turn,
and conclusion phases.

Key features:
- Template-based composition with Python str.format() syntax
- Support for Path objects (load templates from files)
- Custom provider pattern for dynamic content
- Metadata capture for observability and replay
- Deterministic rendering (same inputs → same output)

Example:
    builder = PromptBuilder(
        handshake_template="{game_instructions}\\n{handshake_controller_format}",
        turn_template="{game_view}\\n{controller_format}",
    )

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=renderer.render(view, player),
        controller_format=controller.get_format_instructions(),
        turn_context=turn_ctx,
    )

    prompt_text = bundle.text  # Send to LLM
"""

from __future__ import annotations

from pathlib import Path
from string import Formatter
from types import MappingProxyType
from typing import Any, Callable, Dict, Optional

from .types import (
    LifecyclePhase,
    PromptBlock,
    PromptBundle,
    PromptContext,
    RenderResult,
    TemplateError,
    TurnContext,
)


class PromptBuilder:
    """
    Template-driven prompt builder for three-phase player lifecycle.

    Per SPEC-PROMPT-BUILDER v0.4.0, this class provides deterministic prompt
    composition using Python str.format() templates for handshake, turn, and
    conclusion phases.

    Key invariants (SPEC-PROMPT-BUILDER §5):
    - TC1-TC3: Templates control what appears (no hidden filtering)
    - CD1-CD3: Deterministic composition (same inputs → same output)
    - MC1-MC3: Metadata capture (template_id, blocks_rendered, phase, turn_number)
    - PS1-PS3: Provider safety (immutable context, memoization, exception wrapping)
    - EH1-EH3: Error handling (undefined placeholders, missing templates, provider errors)

    Example:
        # Inline templates
        builder = PromptBuilder(
            handshake_template="{game_instructions}\\n{handshake_controller_format}",
            turn_template="{game_view}\\n{controller_format}",
        )

        # Load from files
        builder = PromptBuilder(
            handshake_template=Path("prompts/handshake.txt"),
            turn_template=Path("prompts/turn.txt"),
        )

        # Compose prompt for turn phase
        bundle = builder.compose(
            phase=LifecyclePhase.TURN,
            render_result=renderer.render(view, player),
            controller_format=controller.get_format_instructions(),
            turn_context=turn_ctx,
        )
    """

    # Default templates per SPEC-PROMPT-BUILDER §4
    DEFAULT_HANDSHAKE = (
        "You are playing {game_name}.\\n\\n"
        "{game_instructions}\\n\\n"
        "{player_instructions}\\n\\n"
        "{controller_format}\\n\\n"
        "{handshake_controller_format}"
    )
    DEFAULT_TURN = "{game_view}\\n\\n{controller_format}"
    DEFAULT_CONCLUSION = (
        "=== Match Concluded ===\\n\\n" "{outcome}\\n\\n" "Final state:\\n{game_view}"
    )

    def __init__(
        self,
        *,
        handshake_template: Optional[str | Path] = None,
        turn_template: Optional[str | Path] = None,
        conclusion_template: Optional[str | Path] = None,
    ):
        """
        Initialize PromptBuilder with phase-specific templates.

        Args:
            handshake_template: Template for handshake phase (string or Path)
            turn_template: Template for turn phase (string or Path)
            conclusion_template: Template for conclusion phase (string or Path)

        Raises:
            FileNotFoundError: If Path provided but file doesn't exist
            UnicodeDecodeError: If file not valid UTF-8

        Example:
            # Inline templates
            builder = PromptBuilder(
                turn_template="{game_view}\\n{controller_format}"
            )

            # Load from files
            builder = PromptBuilder(
                turn_template=Path("prompts/turn.txt")
            )
        """
        # Load templates (from files if Path, otherwise use string directly)
        self._handshake_template = self._load_template(handshake_template, self.DEFAULT_HANDSHAKE)
        self._turn_template = self._load_template(turn_template, self.DEFAULT_TURN)
        self._conclusion_template = self._load_template(
            conclusion_template, self.DEFAULT_CONCLUSION
        )

        # Custom providers: Dict[str, Callable[[PromptContext], str]]
        self._providers: Dict[str, Callable[[PromptContext], str]] = {}

    def _load_template(self, template: Optional[str | Path], default: str) -> str:
        """
        Load template from Path or use string directly.

        Args:
            template: Template string or Path to load
            default: Default template if template is None

        Returns:
            Template string

        Raises:
            FileNotFoundError: If Path provided but doesn't exist
            UnicodeDecodeError: If file not valid UTF-8
        """
        if template is None:
            return default
        if isinstance(template, Path):
            # Load from file (UTF-8)
            return template.read_text(encoding="utf-8")
        return template

    @classmethod
    def from_template(cls, template: str) -> PromptBuilder:
        """
        Convenience factory for single-template builders (turn-only).

        Args:
            template: Template string for turn phase

        Returns:
            PromptBuilder with turn_template set

        Example:
            builder = PromptBuilder.from_template("{game_view}\\n{controller_format}")
        """
        return cls(turn_template=template)

    @classmethod
    def from_file(cls, path: str | Path) -> PromptBuilder:
        """
        Load template from file (turn-only).

        Args:
            path: File path to template

        Returns:
            PromptBuilder with turn_template loaded from file

        Raises:
            FileNotFoundError: If path doesn't exist
            UnicodeDecodeError: If not valid UTF-8

        Example:
            builder = PromptBuilder.from_file("prompts/turn.txt")
        """
        path_obj = Path(path) if isinstance(path, str) else path
        return cls(turn_template=path_obj)

    @classmethod
    def from_function(cls, compose_fn: Callable[[PromptContext], str]) -> PromptBuilder:
        """
        Escape hatch for advanced composition logic.

        Args:
            compose_fn: Function that receives PromptContext and returns prompt string

        Returns:
            PromptBuilder that delegates to custom function

        Example:
            def custom_compose(ctx):
                if ctx.turn_number == 1:
                    return f"{ctx.extras['strategy']}\\n{ctx.render_result.text}"
                return ctx.render_result.text

            builder = PromptBuilder.from_function(custom_compose)
        """
        # Create builder with no-op templates
        builder = cls()
        # Replace compose() method with custom function
        builder._custom_compose_fn = compose_fn  # type: ignore
        return builder

    def bind(self, name: str, provider: Callable[[PromptContext], str]) -> PromptBuilder:
        """
        Register custom placeholder provider for dynamic content.

        Args:
            name: Placeholder name (without braces)
            provider: Callable that receives PromptContext and returns string

        Returns:
            Self (for chaining)

        Example:
            builder.bind("timestamp", lambda ctx: datetime.now().isoformat())
            builder.bind("strategy", lambda ctx: ctx.extras.get("strategy", ""))
        """
        self._providers[name] = provider
        return self

    def compose(
        self,
        *,
        phase: LifecyclePhase,
        render_result: RenderResult,
        controller_format: str,
        handshake_controller_format: Optional[str] = None,
        turn_context: Optional[TurnContext] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> PromptBundle:
        """
        Render prompt for given phase with metadata capture.

        Per SPEC-PROMPT-BUILDER v0.4.0 §4, this method:
        1. Selects template based on phase
        2. Evaluates custom providers (if any)
        3. Substitutes all placeholders
        4. Captures metadata (template_id, blocks_rendered, phase, turn_number)
        5. Returns PromptBundle with text + metadata

        Args:
            phase: Lifecycle phase (HANDSHAKE/TURN/CONCLUSION)
            render_result: Renderer output (game view text + metadata)
            controller_format: Action controller format instructions
            handshake_controller_format: Handshake controller format instructions
            turn_context: Optional turn execution metadata
            extras: Additional researcher-provided data (optional placeholders)

        Returns:
            PromptBundle with rendered text, blocks, and metadata

        Raises:
            TemplateError: If placeholder undefined or provider fails
            ValueError: If unsupported phase

        Available auto-bound placeholders:
            - {game_view}: render_result.text
            - {controller_format}: controller_format
            - {handshake_controller_format}: handshake_controller_format (handshake only)
            - Any key from extras dict (renders as empty string if not provided)
            - Any custom provider registered via bind()

        Example:
            bundle = builder.compose(
                phase=LifecyclePhase.TURN,
                render_result=text_renderer.render(view, player),
                controller_format=controller.get_format_instructions(),
                turn_context=turn_ctx,
                extras={"strategy": "Prioritize corners"},
            )

            prompt_text = bundle.text
            blocks_included = bundle.metadata["blocks_rendered"]
        """
        # Check for custom compose function (from from_function)
        if hasattr(self, "_custom_compose_fn"):
            ctx = self._build_context(
                phase=phase,
                render_result=render_result,
                controller_format=controller_format,
                handshake_controller_format=handshake_controller_format,
                turn_context=turn_context,
                extras=extras or {},
            )
            text = self._custom_compose_fn(ctx)  # type: ignore
            return PromptBundle(
                text=text,
                blocks=[],
                metadata={
                    "template_id": "custom_function",
                    "phase": phase.value,
                    "turn_number": ctx.turn_number,
                    "blocks_rendered": [],
                },
            )

        # Select template based on phase (CD3)
        template, template_id = self._select_template(phase)

        # Build context for provider evaluation
        turn_number = turn_context.turn_number if turn_context else 0
        ctx = self._build_context(
            phase=phase,
            render_result=render_result,
            controller_format=controller_format,
            handshake_controller_format=handshake_controller_format,
            turn_context=turn_context,
            extras=extras or {},
        )

        # Build substitution dict (auto-bound + extras + providers)
        substitutions, provider_cache = self._build_substitutions(ctx)

        # Extract placeholder names from template
        placeholder_names = self._extract_placeholders(template)

        # Render template with substitutions (EH1)
        # Use a default dict that returns empty string for missing keys (per SPEC §4 EH1)
        # This allows extras keys and optional placeholders to render as empty when not provided
        class DefaultEmptyDict(dict):
            """Dict that returns empty string for missing keys."""

            def __missing__(self, key):
                return ""

        format_dict = DefaultEmptyDict(substitutions)

        try:
            text = template.format_map(format_dict)
        except KeyError as e:
            # Should never happen with DefaultEmptyDict, but kept for safety
            placeholder = e.args[0] if e.args else "unknown"
            raise TemplateError(
                f"Undefined placeholder: '{placeholder}'",
                placeholder=placeholder,
                template_id=template_id,
                phase=phase.value,
            ) from e

        # Build blocks list (ordered by appearance in template)
        # Pass format_dict (which includes defaults) instead of substitutions
        # to ensure all placeholders get blocks per MC2
        blocks = self._build_blocks(placeholder_names, format_dict, render_result)

        # Build metadata (MC1)
        metadata = {
            "template_id": template_id,
            "phase": phase.value,
            "turn_number": turn_number,
            "blocks_rendered": [block.key for block in blocks],
        }

        return PromptBundle(text=text, blocks=blocks, metadata=metadata)

    def _select_template(self, phase: LifecyclePhase) -> tuple[str, str]:
        """
        Select template and identifier for given phase.

        Args:
            phase: Lifecycle phase

        Returns:
            Tuple of (template string, template_id)

        Raises:
            ValueError: If unsupported phase
        """
        if phase == LifecyclePhase.HANDSHAKE:
            return self._handshake_template, "handshake"
        elif phase == LifecyclePhase.TURN:
            return self._turn_template, "turn"
        elif phase == LifecyclePhase.CONCLUSION:
            return self._conclusion_template, "conclusion"
        else:
            raise ValueError(f"Unsupported phase: {phase}")

    def _build_context(
        self,
        *,
        phase: LifecyclePhase,
        render_result: RenderResult,
        controller_format: str,
        handshake_controller_format: Optional[str],
        turn_context: Optional[TurnContext],
        extras: Dict[str, Any],
    ) -> PromptContext:
        """
        Build immutable PromptContext for provider evaluation (PS1).

        Wraps extras in MappingProxyType to ensure true immutability - providers
        cannot mutate ctx.extras after context construction.
        """
        turn_number = turn_context.turn_number if turn_context else 0
        # Wrap extras in MappingProxyType for true immutability (PS1)
        # This prevents providers from doing ctx.extras[key] = value
        immutable_extras = MappingProxyType(extras)
        return PromptContext(
            phase=phase,
            turn_number=turn_number,
            render_result=render_result,
            controller_format=controller_format,
            handshake_controller_format=handshake_controller_format,
            turn_context=turn_context,
            extras=immutable_extras,  # type: ignore[arg-type]
        )

    def _build_substitutions(self, ctx: PromptContext) -> tuple[Dict[str, str], Dict[str, str]]:
        """
        Build substitution dict from auto-bound sources, extras, and providers.

        Per SPEC-PROMPT-BUILDER §4:
        - Auto-bound: game_view, controller_format, handshake_controller_format
        - Extras: Any key from ctx.extras (renders as empty string if not provided)
        - Providers: Custom providers registered via bind()

        Args:
            ctx: Immutable prompt context

        Returns:
            Tuple of (substitutions dict, provider cache)

        Raises:
            TemplateError: If provider raises exception (PS3)
        """
        substitutions: Dict[str, str] = {}
        provider_cache: Dict[str, str] = {}

        # Auto-bound placeholders (always available)
        substitutions["game_view"] = ctx.render_result.text
        substitutions["controller_format"] = ctx.controller_format
        if ctx.handshake_controller_format is not None:
            substitutions["handshake_controller_format"] = ctx.handshake_controller_format

        # Extras (optional placeholders, render as empty if not provided)
        for key, value in ctx.extras.items():
            substitutions[key] = str(value) if value is not None else ""

        # Custom providers (PS2: memoize per composition call)
        for name, provider in self._providers.items():
            if name not in provider_cache:
                try:
                    result = provider(ctx)
                    provider_cache[name] = result
                except Exception as e:
                    # PS3: Wrap provider exceptions in TemplateError
                    raise TemplateError(
                        f"Provider '{name}' failed: {e}",
                        placeholder=name,
                        template_id=ctx.phase.value,
                        phase=ctx.phase.value,
                    ) from e
            substitutions[name] = provider_cache[name]

        return substitutions, provider_cache

    def _extract_placeholders(self, template: str) -> list[str]:
        """
        Extract placeholder names from template in order of appearance.

        Uses string.Formatter to parse template and extract field names.

        Args:
            template: Template string

        Returns:
            List of placeholder names (ordered)
        """
        formatter = Formatter()
        placeholders: list[str] = []

        for _, field_name, _, _ in formatter.parse(template):
            if field_name is not None and field_name not in placeholders:
                placeholders.append(field_name)

        return placeholders

    def _build_blocks(
        self,
        placeholder_names: list[str],
        format_dict: Dict[str, str],
        render_result: RenderResult,
    ) -> list[PromptBlock]:
        """
        Build ordered list of PromptBlock entries (MC2).

        Per SPEC-PROMPT-BUILDER §5.3 MC2, "PromptBundle.blocks MUST contain ordered
        PromptBlock entries for each placeholder rendered (in order of appearance
        in template)." This includes placeholders that resolve to empty string.

        Args:
            placeholder_names: Ordered list of placeholder names
            format_dict: Format dict (includes DefaultEmptyDict behavior)
            render_result: Renderer output (for metadata preservation per MC3)

        Returns:
            Ordered list of PromptBlock entries (one per placeholder)
        """
        blocks: list[PromptBlock] = []

        for name in placeholder_names:
            # Get content from format_dict (will return "" for missing keys via __missing__)
            content = format_dict.get(name, "")

            # MC3: Preserve renderer metadata in game_view block
            metadata = None
            if name == "game_view" and render_result.metadata:
                metadata = render_result.metadata

            # MC2: Create block for every placeholder, even if content is empty
            blocks.append(PromptBlock(key=name, content=content, metadata=metadata))

        return blocks
