"""
Player abstract base class for AgentDeck v1.3.0.

Implements the three-phase player lifecycle per SPEC-PLAYER v1.3.0:
- Handshake: Build prompt + execute LLM acknowledgement (mandatory)
- Turn: Repeated decision phase (action selection)
- Conclusion: Optional post-match reflection phase

Key features:
- Single unified controller architecture (per SPEC-CONTROLLER v1.3.0)
- PromptBuilder integration with phase-specific templates
- Conversation history management
- Metadata capture for reproducibility
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..prompt_builder import PromptBuilder, _DEFAULT_TEMPLATE
from ..types import (
    ActionResult,
    HandshakeContext,
    HandshakeResponse,
    LifecyclePhase,
    MatchContext,
    MatchResult,
    PromptBundle,
    RenderResult,
    TurnContext,
)

if TYPE_CHECKING:
    from ..conversation import ConversationManager
    from ..logging import AgentDeckLogger
    from .controller import Controller
    from .renderer import Renderer


class Player(ABC):
    """
    Abstract base for AI players with three-phase lifecycle.

    Per SPEC-PLAYER v1.3.0, players execute three lifecycle phases:
    1. Handshake: Acknowledge match conditions (mandatory, called once)
    2. Turn: Make decisions each turn (repeated until match ends)
    3. Conclusion: Optional reflection after match completes

    Key invariants (SPEC-PLAYER §5):
    - HS1-HS4: Handshake semantics (mandatory, preserved in history)
    - PP1-PP3: Prompt pipeline (deterministic, metadata capture)
    - DS1-DS3: Decision semantics (controller binding, fallback)
    - CS1-CS3: Conversation & state (immutable game_state, history)
    - CI1-CI2: Component integrity (pluggable controllers, introspection)

    Subclasses must implement:
        get_response(prompt: str) -> str: LLM provider transport

    Example:
        class GPTPlayer(Player):
            def get_response(self, prompt: str) -> str:
                response = openai.ChatCompletion.create(...)
                return response.choices[0].message.content
    """

    def __init__(
        self,
        name: str,
        *,
        controller: Controller,
        renderer: Optional[Renderer] = None,
        handshake_template: Optional[str | Path] = None,
        turn_template: Optional[str | Path] = None,
        conclusion_template: Optional[str | Path] | object = _DEFAULT_TEMPLATE,
        model: str = "unspecified",
        **config,
    ):
        """
        Initialize Player with three-phase lifecycle components.

        Args:
            name: Player identifier
            controller: Unified controller for all phases (required, game-specific)
            renderer: State formatter (defaults to TextRenderer)
            handshake_template: Template for handshake phase (string or Path)
            turn_template: Template for turn phase (string or Path)
            conclusion_template: Template for conclusion phase (string or Path).
                Use None to disable conclusion composition explicitly.
            model: Runtime model identifier. Provider-backed Players require an
                explicit model; local/custom Players default to "unspecified".
            **config: Model parameters (temperature, max_tokens, etc.)

        Template parameters accept:
            - Literal strings: Inline template content
            - Path objects: File path to load (UTF-8 encoding)
            - None: Use PromptBuilder defaults

        Example:
            player = GPTPlayer(
                "Alice",
                controller=ActionOnlyController(),
                handshake_template=Path("prompts/handshake.txt"),
                turn_template="{game_view}\\n{controller_format}",
                model="gpt-4",
                temperature=0.7
            )
        """
        self.name = name
        self.model = model
        self.config = config

        # Set controller (required)
        self.controller = controller

        # Set default renderer if not provided (CI1)
        if renderer is None:
            from ...renderers.text_renderer import TextRenderer

            self.renderer = TextRenderer()
        else:
            self.renderer = renderer

        # Create PromptBuilder with phase-specific templates
        self.prompt_builder = PromptBuilder(
            handshake_template=handshake_template,
            turn_template=turn_template,
            conclusion_template=conclusion_template,
        )
        self._uses_default_handshake_template = handshake_template is None

        # Conversation management (CS2)
        self.conversation_manager: Optional[ConversationManager] = None
        self._local_history: List[Dict[str, str]] = []
        self._last_exchange: Dict[str, Dict[str, Any]] = {}

        # Logging
        self.logger: Optional[AgentDeckLogger] = None

    # ------------------------------------------------------------------
    # Cloning support for parallel execution (SPEC-PARALLEL v1.0.0)
    # ------------------------------------------------------------------
    def clone(self) -> "Player":
        """
        Create an isolated copy of the player for parallel execution.

        Default implementation relies on ``copy.deepcopy``. Subclasses that
        maintain non-serializable state (network clients, thread locks, etc.)
        should override this method to construct a fresh instance.
        """
        cloned: Player = copy.deepcopy(self)

        # Clear runtime bindings that will be re-established by Console._prepare_players
        if hasattr(cloned, "conversation_manager"):
            cloned.conversation_manager = None
        if hasattr(cloned, "logger"):
            cloned.logger = None

        return cloned

    # =========================================================================
    # Three-Phase Lifecycle Methods (SPEC-PLAYER §4)
    # =========================================================================

    def build_handshake_bundle(self, context: HandshakeContext) -> PromptBundle:
        """
        Build the handshake prompt bundle without invoking the LLM.

        Per SPEC-PLAYER §5.1 HS1-HS3, Console must emit PLAYER_HANDSHAKE_START
        before the LLM call using the exact prompt bundle returned here.
        """
        empty_render = RenderResult(text="", metadata={})

        handshake_fmt = self.controller.get_handshake_format_instructions()
        turn_fmt = self.controller.get_format_instructions()
        handshake_template_override = None
        template_id_override = None
        if self._uses_default_handshake_template and context.metadata:
            handshake_template_override = context.metadata.get("default_handshake_template")
            if handshake_template_override:
                template_id_override = "game_default_handshake"
        return self.prompt_builder.compose(
            phase=LifecyclePhase.HANDSHAKE,
            render_result=empty_render,
            controller_format=turn_fmt,
            handshake_controller_format=handshake_fmt,
            turn_context=None,
            extras={
                "game_name": context.game_name,
                "game_instructions": (
                    context.metadata.get("game_instructions", "") if context.metadata else ""
                ),
                "player_instructions": (
                    context.metadata.get("player_instructions", "") if context.metadata else ""
                ),
            },
            template_override=handshake_template_override,
            template_id_override=template_id_override,
        )

    def execute_handshake(
        self, bundle: PromptBundle, context: HandshakeContext
    ) -> HandshakeResponse:
        """
        Execute the handshake LLM call and record the exchange.

        Returns:
            HandshakeResponse containing raw response and optional usage metadata.
        """
        self._active_phase = "handshake"
        self._active_match_id = context.match_id
        self._active_turn_number = 0
        try:
            raw_response = self.get_response(bundle.text)
        finally:
            self._active_phase = None
            self._active_match_id = None
            self._active_turn_number = None

        usage_info = getattr(self, "last_usage_info", None)
        retries = getattr(self, "last_retries", None)
        retry_durations = getattr(self, "last_retry_durations", None)
        attempt_durations = getattr(self, "last_attempt_durations", None)
        provider_call = copy.deepcopy(getattr(self, "last_provider_call", None))

        prompt_blocks = self._serialize_prompt_blocks(bundle.blocks)
        self._record_exchange(
            bundle.text,
            raw_response,
            phase="handshake",
            turn_context=None,
            prompt_blocks=prompt_blocks,
            controller_format=self.controller.get_handshake_format_instructions(),
            renderer_output=None,
            usage_info=usage_info,
            provider_call=provider_call,
        )

        return HandshakeResponse(
            response_text=raw_response,
            usage_info=usage_info,
            retries=retries,
            retry_durations=retry_durations,
            attempt_durations=attempt_durations,
            provider_call=provider_call,
        )

    def decide(
        self,
        game_state: Dict[str, Any],
        *,
        turn_context: TurnContext,
        extras: Optional[Dict[str, Any]] = None,
    ) -> ActionResult:
        """
        Execute turn phase (repeated until match ends).

        Per SPEC-PLAYER §5.2-5.3, must keep game_state immutable, build prompt
        via PromptBuilder, invoke LLM, parse via action controller, and return
        ActionResult with complete metadata.

        Args:
            game_state: Immutable game state dict (CS1)
            turn_context: Turn execution metadata (turn_number, etc.)
            extras: Optional extras dict for template placeholders (strategy, hints, etc.)

        Returns:
            ActionResult with parsed action and metadata (DS2)

        Raises:
            RuntimeError: If LLM provider fails after retries

        Example:
            result = player.decide(
                game_state={"health": {"Alice": 100, "Bob": 80}},
                turn_context=TurnContext(match_id="match-123", turn_number=1, ...),
                extras={"strategy": "Be aggressive!"}
            )
            print(result.action)  # "ATTACK"
            print(result.metadata["prompt_length"])  # 512
        """
        # Get player-specific view from game (via Console/TurnLoop in production)
        # For now, assume game_state is already player-specific view
        player_view = game_state

        # Render view via renderer (PP2)
        # Renderer.render() expects state (positional), player, turn_context
        render_result = self.renderer.render(
            player_view,  # Positional arg: state
            player=self.name,
            turn_context=turn_context,
        )

        # Build turn prompt via PromptBuilder (PP1, PP3)
        # Pass extras to enable custom placeholders (strategy, hints, deadlines, etc.)
        bundle = self.prompt_builder.compose(
            phase=LifecyclePhase.TURN,
            render_result=render_result,
            controller_format=self.controller.get_format_instructions(),
            turn_context=turn_context,
            extras=extras or {},  # Console/researcher-provided placeholders
        )

        # Invoke LLM
        self._active_phase = "turn"
        self._active_match_id = turn_context.match_id
        self._active_turn_number = turn_context.turn_number
        try:
            raw_response = self.get_response(bundle.text)
        finally:
            self._active_phase = None
            self._active_match_id = None
            self._active_turn_number = None

        # Parse action via controller (DS1)
        # Per SPEC-CONTROLLER v1.3.0, controllers return ParseResult
        parse_result = self.controller.parse(raw_response)

        # Attach the complete call context before conversion so parse failures retain
        # the same execution truth as successful decisions.
        prompt_blocks = self._serialize_prompt_blocks(bundle.blocks)
        usage_info = copy.deepcopy(getattr(self, "last_usage_info", None))
        provider_call = copy.deepcopy(getattr(self, "last_provider_call", None))
        parse_result.prompt_text = bundle.text
        parse_result.prompt_blocks = copy.deepcopy(prompt_blocks)
        parse_result.renderer_output = copy.deepcopy(
            render_result.metadata if render_result.metadata else {}
        )
        parse_result.controller_format = self.controller.get_format_instructions()
        parse_result.usage_info = usage_info
        parse_result.provider_call = provider_call
        parse_result.retries = int(getattr(self, "last_retries", 0) or 0)
        parse_result.retry_durations = copy.deepcopy(
            getattr(self, "last_retry_durations", []) or []
        )
        parse_result.attempt_durations = copy.deepcopy(
            getattr(self, "last_attempt_durations", []) or []
        )

        # Convert ParseResult to ActionResult (raises ActionParseError if parsing failed)
        # Per SPEC-CONTROLLER v1.2.0 §5.4 (VF2-VF3): No fallback, failures must surface
        action_result = parse_result.to_action_result()

        # Attach metadata (DS2)
        # Per SPEC-PROMPT-BUILDER §5.3 MC3, preserve PromptBlock.metadata (renderer hints)
        action_result.metadata = action_result.metadata or {}
        action_result.metadata.update(
            {
                "raw_prompt": bundle.text,
                "prompt_blocks": prompt_blocks,
                "prompt_length": len(bundle.text),
                "raw_response": raw_response,
                "turn_number": turn_context.turn_number,
                "renderer_output": render_result.metadata if render_result.metadata else {},
                "controller_format": self.controller.get_format_instructions(),
                "template_id": bundle.metadata.get("template_id", "unknown"),
            }
        )
        if usage_info:
            action_result.metadata["usage_info"] = usage_info
        if provider_call:
            action_result.metadata["provider_call"] = provider_call
        action_result.metadata["retries"] = int(getattr(self, "last_retries", 0) or 0)
        action_result.metadata["retry_durations"] = copy.deepcopy(
            getattr(self, "last_retry_durations", []) or []
        )
        action_result.metadata["attempt_durations"] = copy.deepcopy(
            getattr(self, "last_attempt_durations", []) or []
        )

        # Preserve in conversation history (CS2)
        # Capture PM1-PM6 metadata for dialogue array
        self._record_exchange(
            bundle.text,
            raw_response,
            phase="turn",
            turn_context=turn_context,
            prompt_blocks=action_result.metadata.get("prompt_blocks"),
            controller_format=self.controller.get_format_instructions(),
            renderer_output=action_result.metadata.get("renderer_output"),
            usage_info=usage_info,
            provider_call=provider_call,
        )

        return action_result

    def conclude(
        self,
        result: MatchResult,
        *,
        match_context: MatchContext,
    ) -> Optional[str]:
        """
        Execute conclusion phase (optional, called once after match ends).

        Default implementation records prompt metadata and returns None. Subclasses
        can override to provide post-match reflection.

        Args:
            result: Match outcome (winner, final_state, etc.)
            match_context: Match execution metadata

        Returns:
            Optional reflection string (or None)

        Example:
            class ReflectivePlayer(Player):
                def conclude(self, result, *, match_context):
                    if result.winner == self.name:
                        return "GG! I played well and secured the win."
                    return "Tough loss. Need to adjust strategy next time."
        """
        logger = getattr(self, "logger", None)

        def _format_outcome() -> str:
            if result.winner is None:
                return "Draw"
            if result.winner == self.name:
                return f"You ({self.name}) won the match."
            return f"{result.winner} won the match."

        def _parse_conclusion_metadata(response_text: str) -> Dict[str, Any]:
            if not response_text:
                return {}
            try:
                parsed = self.controller.parse_conclusion(response_text)
                return parsed if isinstance(parsed, dict) else {"reflection_text": parsed}
            except Exception as exc:  # pragma: no cover - defensive
                if logger:
                    logger.debug(f"Conclusion parse failed for {self.name}: {exc}")
                return {}

        prompt_text = getattr(match_context, "conclusion_prompt", None)
        prompt_blocks: List[Dict[str, Any]]
        renderer_output: Dict[str, Any]

        if prompt_text:
            prompt_blocks = [{"key": "conclusion_prompt", "content": prompt_text, "metadata": {}}]
            renderer_output = {}
        else:
            try:
                if self.prompt_builder._conclusion_template is None:
                    prompt_text = f"Match concluded.\n\n{_format_outcome()}"
                    prompt_blocks = [
                        {"key": "outcome", "content": _format_outcome(), "metadata": {}}
                    ]
                    renderer_output = {}
                else:
                    final_view = self.renderer.render(
                        result.final_state,
                        player=self.name,
                        turn_context=None,
                    )
                    render_result = (
                        final_view
                        if isinstance(final_view, RenderResult)
                        else RenderResult(
                            text=str(final_view),
                            metadata=(
                                getattr(final_view, "metadata", {})
                                if hasattr(final_view, "metadata")
                                else {}
                            ),
                        )
                    )
                    bundle = self.prompt_builder.compose(
                        phase=LifecyclePhase.CONCLUSION,
                        render_result=render_result,
                        controller_format="",
                        handshake_controller_format=None,
                        turn_context=None,
                        extras={
                            "outcome": _format_outcome(),
                            "player_name": self.name,
                        },
                    )
                    prompt_text = bundle.text
                    prompt_blocks = self._serialize_prompt_blocks(bundle.blocks)
                    renderer_output = render_result.metadata if render_result.metadata else {}
            except Exception as exc:  # pragma: no cover - defensive
                if logger:
                    logger.debug(f"Conclusion prompt build failed for {self.name}: {exc}")
                prompt_text = f"Match concluded.\n\n{_format_outcome()}"
                prompt_blocks = [{"key": "outcome", "content": _format_outcome(), "metadata": {}}]
                renderer_output = {}

        controller_metadata = _parse_conclusion_metadata("")
        self._record_exchange(
            prompt_text,
            "",
            phase="conclusion",
            turn_context=None,
            prompt_blocks=prompt_blocks,
            controller_format="",
            controller_metadata=controller_metadata,
            renderer_output=renderer_output,
            usage_info=None,
        )

        return None  # Default: no reflection

    # =========================================================================
    # Abstract Methods (Subclasses Must Implement)
    # =========================================================================

    @abstractmethod
    def get_response(self, prompt: str) -> str:
        """
        Get raw response from LLM provider.

        Subclasses MUST implement this to integrate with specific LLM APIs
        (OpenAI, Anthropic, Google, etc.).

        Args:
            prompt: Complete prompt text to send to LLM

        Returns:
            Raw response string from LLM

        Raises:
            RuntimeError: If provider fails after retries

        Example:
            def get_response(self, prompt: str) -> str:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.get("temperature", 1.0),
                )
                return response.choices[0].message.content
        """
        raise NotImplementedError("Subclass must implement get_response")

    # =========================================================================
    # Conversation Management (CS2-CS3)
    # =========================================================================

    def bind_conversation_manager(self, manager: ConversationManager) -> None:
        """
        Bind console-injected ConversationManager for history tracking.

        Per SPEC-PLAYER §5.4 CS2, when ConversationManager is bound, players
        MUST delegate history logging to it.

        Args:
            manager: Console-provided conversation manager

        Example:
            manager = ConversationManager()
            player.bind_conversation_manager(manager)
        """
        self.conversation_manager = manager

    def reset_conversation(self) -> None:
        """
        Prepare player for next match by clearing local history.

        Per SPEC-PLAYER §5.4 CS3, MUST clear local history while leaving
        handshake templates intact.

        Example:
            # After match 1
            player.reset_conversation()
            # Ready for match 2
        """
        self._local_history.clear()
        self._last_exchange.clear()
        if self.conversation_manager:
            self.conversation_manager.reset()

    def _serialize_prompt_blocks(self, blocks: List[Any]) -> List[Dict[str, Any]]:
        """Convert PromptBuilder blocks into recorder-friendly dicts."""
        return [
            {
                "key": block.key,
                "content": block.content,
                "metadata": block.metadata if block.metadata else {},
            }
            for block in blocks
        ]

    def _record_exchange(
        self,
        prompt: str,
        response: str,
        *,
        phase: str,
        turn_context: Optional[TurnContext] = None,
        prompt_blocks: Optional[List[Dict]] = None,
        controller_format: Optional[str] = None,
        controller_metadata: Optional[Dict[str, Any]] = None,
        renderer_output: Optional[Dict] = None,
        usage_info: Optional[Dict] = None,
        provider_call: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record prompt/response exchange in conversation history with PM1-PM6 metadata.

        Delegates to ConversationManager if bound, otherwise stores locally.

        Note: Schema v1.3 - ConversationManager no longer emits DIALOGUE_TURN events.
        Prompt metadata is captured directly in lifecycle events by Recorder.

        Args:
            prompt: Prompt sent to LLM (PM1: prompt_text)
            response: Response from LLM (PM3: response_text)
            phase: Lifecycle phase (handshake/turn/conclusion)
            turn_context: Optional turn metadata
            prompt_blocks: Structured prompt components from PromptBuilder (PM2)
            controller_format: Controller type used (PM5)
            controller_metadata: Parsed controller metadata (PM6)
            renderer_output: Rendered view metadata (PM6)
            usage_info: LLM usage metadata - tokens, cost, model (PM4)
        """
        response_metadata: Dict[str, Any] = {}
        if usage_info:
            response_metadata["usage_info"] = usage_info
        if controller_metadata is not None:
            response_metadata["controller_metadata"] = controller_metadata
        if provider_call is not None:
            response_metadata["provider_call"] = copy.deepcopy(provider_call)

        if self.conversation_manager:
            # Delegate to manager (CS2)
            self.conversation_manager.record_turn(
                user_message=prompt,
                assistant_message=response,
                turn_context=turn_context,
                prompt_metadata=[],
                response_metadata=response_metadata,
                phase=phase,
                prompt_blocks=prompt_blocks,
                controller_format=controller_format,
                renderer_output=renderer_output,
            )
        else:
            # Store locally (CS2)
            self._local_history.append({"role": "user", "content": prompt})
            self._local_history.append({"role": "assistant", "content": response})

        # Preserve the latest exchange per phase for conclusion metadata
        self._last_exchange[phase] = {
            "prompt_text": prompt,
            "prompt_blocks": copy.deepcopy(prompt_blocks) if prompt_blocks else [],
            "response_text": response,
            "controller_format": controller_format or "",
            "controller_metadata": (
                copy.deepcopy(controller_metadata) if controller_metadata is not None else {}
            ),
            "renderer_output": copy.deepcopy(renderer_output) if renderer_output else {},
            "usage_info": copy.deepcopy(usage_info) if usage_info else None,
            "provider_call": copy.deepcopy(provider_call) if provider_call else None,
        }

    def _get_last_exchange(self, phase: str) -> Optional[Dict[str, Any]]:
        """Return the last recorded exchange for a lifecycle phase, if available."""
        return self._last_exchange.get(phase)

    # =========================================================================
    # Introspection Helpers (CI2)
    # =========================================================================

    def describe(self) -> Dict[str, Any]:
        """
        Return player configuration for debugging/observability.

        Per SPEC-PLAYER §5.5 CI2, MUST expose controller name, renderer,
        model, temperature, and prompt strategy.

        Returns:
            Dictionary with player configuration

        Example:
            info = player.describe()
            print(info["model"])  # "unspecified" unless explicitly configured
            print(info["controller"])  # {"name": "ActionOnlyController", ...}
        """
        effective_config = copy.deepcopy(self.config)
        for attribute in ("temperature", "max_tokens", "max_retries", "retry_delay"):
            if hasattr(self, attribute):
                effective_config[attribute] = copy.deepcopy(getattr(self, attribute))

        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "module": self.__class__.__module__,
            "model": self.model,
            "config": effective_config,
            "controller": self._describe_component(self.controller),
            "renderer": self._describe_component(self.renderer),
            "templates": {
                "handshake": self.prompt_builder._handshake_template,
                "turn": self.prompt_builder._turn_template,
                "conclusion": self.prompt_builder._conclusion_template,
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Return configuration summary for logging.

        Returns:
            Dictionary with player summary (name, type, controller, model)

        Example:
            summary = player.get_summary()
            logger.info(f"Player: {summary}")
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "model": self.model,
            "controller": self.controller.__class__.__name__,
            "renderer": self.renderer.__class__.__name__,
        }

    def _describe_component(self, component: Any) -> Dict[str, Any]:
        """Describe a component (controller/renderer) for introspection."""
        if hasattr(component, "describe"):
            descriptor = component.describe()
            if isinstance(descriptor, dict):
                return descriptor
        return {
            "type": component.__class__.__name__,
            "module": component.__class__.__module__,
        }

    def _truncate_template(self, template: Optional[str], max_length: int = 200) -> Optional[str]:
        """Truncate template for display in describe()."""
        if template is None:
            return None
        if len(template) <= max_length:
            return template
        return template[:max_length] + f"... ({len(template)} chars total)"
