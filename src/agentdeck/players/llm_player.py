"""Base LLM player class for AgentDeck."""

import copy
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..core.base.controller import Controller
from ..core.base.player import Player
from ..core.base.renderer import Renderer
from ..core.types import LifecyclePhase, RenderResult


class LLMPlayer(Player, ABC):
    """Base class for all LLM players - CORE functionality."""

    # Subclasses must define these
    default_model: str = None
    api_key_env_var: str = None

    def __init__(
        self,
        name: str,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        controller: Controller,
        renderer: Optional[Renderer] = None,
        handshake_template: Optional[Any] = None,
        turn_template: Optional[Any] = None,
        conclusion_template: Optional[Any] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs,
    ):
        """
        Initialize LLM player with common configuration.

        Args:
            name: Player identifier
            api_key: API key (if not provided, reads from environment)
            model: Model to use (if not provided, uses default_model)
            temperature: Response randomness (0-2, default 1.0)
            max_tokens: Maximum response length (None for no limit)
            controller: Unified controller for all phases (required, game-specific)
            renderer: State formatter (optional, uses TextRenderer if None)
            handshake_template: Template for handshake phase
            turn_template: Template for turn phase
            conclusion_template: Template for conclusion phase
            max_retries: Number of API call retries
            retry_delay: Delay between retries in seconds
            **kwargs: Additional provider-specific parameters
        """
        # Resolve model before calling super().__init__
        resolved_model = model or self.default_model
        if not resolved_model:
            raise ValueError(
                f"{self.__class__.__name__} requires an explicit model name. "
                f"Pass model= when constructing the player (no built-in default)."
            )

        super().__init__(
            name,
            controller=controller,
            renderer=renderer,
            handshake_template=handshake_template,
            turn_template=turn_template,
            conclusion_template=conclusion_template,
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # API configuration
        self.api_key = api_key or self._get_api_key_from_env()
        # Note: self.model already set by Player.__init__
        # Note: temperature and max_tokens are in self.config (set by Player.__init__)

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Legacy attribute support for backward compatibility
        # These are now stored in self.config by Player, but we expose them
        # as properties for easier access in LLMPlayer methods
        self.temperature = self.config.get("temperature", 1.0)
        self.max_tokens = self.config.get("max_tokens", None)
        self.prompt = self.config.get("prompt", None)

        # Tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        self.response_times = []

        self._local_history: List[Dict[str, str]] = []

        # Provider-specific config
        self.config = kwargs

        # Initialize client
        self._initialize_client()

    def clone(self) -> "LLMPlayer":
        """
        Create an isolated copy of the player for parallel execution.

        Recreates the underlying HTTP client instead of copying it so the clone
        is free of thread locks and network connections.
        """
        controller = copy.deepcopy(self.controller)
        renderer = copy.deepcopy(self.renderer) if self.renderer else None

        # Extract templates from PromptBuilder (private attributes by design)
        handshake_template = getattr(self.prompt_builder, "_handshake_template", None)
        turn_template = getattr(self.prompt_builder, "_turn_template", None)
        conclusion_template = getattr(self.prompt_builder, "_conclusion_template", None)

        clone = self.__class__(
            name=self.name,
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            controller=controller,
            renderer=renderer,
            handshake_template=handshake_template,
            turn_template=turn_template,
            conclusion_template=conclusion_template,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            **copy.deepcopy(self.config),
        )

        # Preserve optional system prompt and aggregate metrics
        clone.prompt = self.prompt
        clone.total_tokens = self.total_tokens
        clone.total_cost = self.total_cost
        clone.response_times = copy.deepcopy(self.response_times)

        return clone

    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variable."""
        if not self.api_key_env_var:
            raise NotImplementedError("Subclass must define api_key_env_var")

        key = os.getenv(self.api_key_env_var)
        if not key:
            raise ValueError(
                f"{self.api_key_env_var} environment variable not set. "
                f"Please set it or pass api_key to constructor."
            )
        return key

    @abstractmethod
    def _initialize_client(self):
        """Initialize the API client."""

    @abstractmethod
    def _make_api_call(self, messages: List[Dict[str, str]]) -> Tuple[str, Dict]:
        """
        Make API call to LLM provider.

        Returns:
            Tuple of (response_text, metadata_dict)
            metadata should include: tokens_used, cost, model_used
        """

    def _invoke_model(self, bundle, turn_context):
        user_prompt = bundle.text

        messages = []
        if self.prompt:
            messages.append({"role": "system", "content": self.prompt})

        for entry in self._history_source():
            messages.append(entry)

        current_user_message = {"role": "user", "content": user_prompt}
        messages.append(current_user_message)

        self.last_full_prompt = messages

        logger = getattr(self, "logger", None)
        if logger:
            logger.api_request(
                player=self.name,
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

        retry_durations: List[float] = []
        attempt_durations: List[float] = []

        for attempt in range(self.max_retries):
            start_time = time.time()
            try:
                response_text, metadata = self._make_api_call(messages)
                response_time = time.time() - start_time
                attempt_durations.append(response_time)

                self.response_times.append(response_time)
                self.total_tokens += metadata.get("tokens_used", 0)
                self.total_cost += metadata.get("cost", 0.0)

                self.last_response = response_text

                self.last_usage_info = {
                    "tokens": metadata.get("tokens_used", 0),
                    "total_tokens": self.total_tokens,
                    "prompt_tokens": metadata.get("prompt_tokens", 0),
                    "completion_tokens": metadata.get("completion_tokens", 0),
                    "cost": metadata.get("cost", 0.0),
                    "total_cost": self.total_cost,
                    "latency_ms": round(response_time * 1000, 1),
                    "model": metadata.get("model", self.model),
                }
                if "provider_model" in metadata:
                    self.last_usage_info["provider_model"] = metadata["provider_model"]

                if logger:
                    logger.api_response(player=self.name, response_text=response_text)
                    logger.api_call(
                        player=self.name,
                        model=metadata.get("model_used", self.model),
                        tokens_in=metadata.get("prompt_tokens", 0),
                        tokens_out=metadata.get("completion_tokens", 0),
                        cost=metadata.get("cost", 0.0),
                        duration=response_time,
                    )

                self._append_history(current_user_message, response_text)

                return response_text, {
                    "raw_response": response_text,
                    "usage_info": getattr(self, "last_usage_info", None),
                    "retries": attempt,
                    "retry_durations": retry_durations,
                    "attempt_durations": attempt_durations,
                    "extras": {"messages": messages},
                }
            except Exception as exc:
                response_time = time.time() - start_time
                attempt_durations.append(response_time)
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Failed to get response from {self.model} after {self.max_retries} attempts: {exc}"
                    ) from exc
                delay = self.retry_delay * (2**attempt)
                retry_durations.append(delay)
                if logger:
                    logger.retry(
                        player=self.name, attempt=attempt + 1, error=str(exc), backoff=delay
                    )
                time.sleep(delay)

        raise RuntimeError(f"Failed to get response from {self.model}")

    def reset_conversation(self):
        """Reset conversation history for a new match."""
        super().reset_conversation()

    def _history_source(self) -> List[Dict[str, str]]:
        if self.conversation_manager:
            return self.conversation_manager.history()
        return list(self._local_history)

    def _append_history(self, user_message: Dict[str, str], assistant_text: str) -> None:
        if self.conversation_manager:
            return
        self._local_history.append(user_message)
        self._local_history.append({"role": "assistant", "content": assistant_text})

    def get_response(self, prompt: str) -> str:
        from ..core.prompt_builder import PromptBundle

        response, _ = self._invoke_model(PromptBundle(text=prompt, blocks=[]), None)
        return response

    def describe(self) -> Dict[str, Any]:
        base = super().describe()
        base.update(
            {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "retry_policy": {
                    "max_retries": self.max_retries,
                    "retry_delay": self.retry_delay,
                },
            }
        )
        return base

    def get_stats(self) -> Dict[str, Any]:
        """Get player statistics."""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_response_time": (
                sum(self.response_times) / len(self.response_times) if self.response_times else 0
            ),
            "model": self.model,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Return configuration summary for logging."""
        summary = super().get_summary()
        summary.update(
            {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay,
                "total_cost": self.total_cost,  # Include cost for post-hoc analysis
            }
        )
        if self.prompt:
            summary["strategy"] = (
                self.prompt[:100] + "..." if len(self.prompt) > 100 else self.prompt
            )
        return summary

    def conclude(self, result, *, match_context) -> Optional[str]:
        """
        Execute conclusion phase - provide post-match reflection.

        If conclusion_template is None, returns None (no reflection).
        Otherwise, prompts LLM for reflection on the match outcome.

        Args:
            result: Match outcome (winner, final_state, etc.)
            match_context: Match execution metadata

        Returns:
            Optional reflection string from LLM
        """
        explicit_prompt = getattr(match_context, "conclusion_prompt", None)

        if explicit_prompt:
            try:
                reflection = self.get_response(explicit_prompt)
            except Exception as exc:  # pragma: no cover - defensive
                logger = getattr(self, "logger", None)
                if logger:
                    logger.debug(f"Conclusion failed for {self.name}: {exc}")
                reflection = None
            else:
                self._record_exchange(
                    explicit_prompt,
                    reflection or "",
                    phase="conclusion",
                    turn_context=None,
                    prompt_blocks=[
                        {"key": "conclusion_prompt", "content": explicit_prompt, "metadata": {}}
                    ],
                    controller_format="",
                    renderer_output={},
                    usage_info=None,
                )

            return reflection.strip() if reflection else None

        # Check if conclusion template is configured in PromptBuilder
        if (
            not hasattr(self.prompt_builder, "_conclusion_template")
            or self.prompt_builder._conclusion_template is None
        ):
            return None

        # Build conclusion prompt using PromptBuilder
        try:
            # Render final state from player's perspective
            final_view = self.renderer.render(
                result.final_state,
                player=self.name,
                turn_context=None,
            )

            # Compose conclusion prompt using default template (or user-provided)
            # Note: No controller_format for conclusions - we want free-form reflection
            bundle = self.prompt_builder.compose(
                phase=LifecyclePhase.CONCLUSION,
                render_result=(
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
                ),
                controller_format="",  # Empty string - no format constraints for reflections
                handshake_controller_format=None,
                turn_context=None,
                extras={
                    "outcome": self._format_outcome(result),
                    "player_name": self.name,
                },
            )

            # Get LLM reflection
            reflection, metadata = self._invoke_model(bundle, None)

            # Record dialogue for replay parity (SPEC-RECORDER PM1-PM6)
            self._record_exchange(
                bundle.text,
                reflection or "",
                phase="conclusion",
                turn_context=None,
                prompt_blocks=[
                    {
                        "key": b.key,
                        "content": b.content,
                        "metadata": b.metadata if b.metadata else {},
                    }
                    for b in bundle.blocks
                ],
                controller_format="",  # No controller format for conclusions
                renderer_output=(
                    final_view.metadata
                    if isinstance(final_view, RenderResult) and final_view.metadata
                    else {}
                ),
                usage_info=metadata.get("usage_info") if metadata else None,
            )

            return reflection.strip() if reflection else None
        except Exception as e:
            # Log error but don't fail - conclusion is optional
            logger = getattr(self, "logger", None)
            if logger:
                logger.debug(f"Conclusion failed for {self.name}: {e}")
            return None

    def _format_outcome(self, result) -> str:
        """Helper to generate human-readable outcome string for conclusion prompts."""
        if result.winner is None:
            return "Draw"
        if result.winner == self.name:
            return f"You ( {self.name} ) won the match."
        return f"{result.winner} won the match."
