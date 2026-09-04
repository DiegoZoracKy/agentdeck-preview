"""Base LLM player class for AgentDeck."""

import copy
import hashlib
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..core.base.controller import Controller
from ..core.base.player import Player
from ..core.prompt_builder import _DEFAULT_TEMPLATE
from ..core.provider_call_journal import (
    MemoryProviderCallJournal,
    ProviderCallCustodyError,
)
from ..core.base.renderer import Renderer
from ..core.types import LifecyclePhase, PlayerResponseUnavailableError, RenderResult


class LLMPlayer(Player, ABC):
    """Base class for all LLM players - CORE functionality."""

    # Subclasses must define these
    default_model: str = None
    api_key_env_var: str = None
    _ENGINE_INTERNAL_STATE_KEYS = {"_turn_count", "_first_player_idx"}

    def __init__(
        self,
        name: str,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = 1.0,
        max_tokens: Optional[int] = None,
        prompt: Optional[str] = None,
        context_policy: Optional[Dict[str, Any] | str] = None,
        controller: Controller,
        renderer: Optional[Renderer] = None,
        handshake_template: Optional[Any] = None,
        turn_template: Optional[Any] = None,
        conclusion_template: object = _DEFAULT_TEMPLATE,
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
            temperature: Response randomness (0-2, default 1.0), or None to
                leave the setting to a supporting provider
            max_tokens: Maximum response length (None for no limit)
            prompt: Optional provider-neutral system instruction
            controller: Unified controller for all phases (required, game-specific)
            renderer: State formatter (optional, uses TextRenderer if None)
            handshake_template: Template for handshake phase
            turn_template: Template for turn phase
            conclusion_template: Template for conclusion phase (use None to disable)
            max_retries: Number of retries after the initial API call
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
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise TypeError("max_retries must be a non-negative integer")
        if max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if prompt is not None and not isinstance(prompt, str):
            raise TypeError("prompt must be a string or None")

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
        self.prompt = prompt
        self.context_policy = self._normalize_context_policy(context_policy)

        # Tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        self.response_times = []

        self._local_history: List[Dict[str, str]] = []
        self.last_provider_call: Optional[Dict[str, Any]] = None
        self._pending_sdk_request: Optional[Dict[str, Any]] = None
        self._active_provider_call_id: Optional[str] = None
        self._active_provider_attempt_index: Optional[int] = None
        self.provider_call_journal = MemoryProviderCallJournal()

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
        handshake_template = (
            None
            if getattr(self, "_uses_default_handshake_template", False)
            else getattr(self.prompt_builder, "_handshake_template", None)
        )
        turn_template = getattr(self.prompt_builder, "_turn_template", None)
        conclusion_template = getattr(self.prompt_builder, "_conclusion_template", None)

        clone = self.__class__(
            name=self.name,
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            prompt=self.prompt,
            context_policy=copy.deepcopy(self.context_policy),
            controller=controller,
            renderer=renderer,
            handshake_template=handshake_template,
            turn_template=turn_template,
            conclusion_template=conclusion_template,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            **copy.deepcopy(self.config),
        )

        # Preserve aggregate metrics
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

    def _effective_max_tokens_for_request(self) -> int | None:
        """Return the provider-effective max_tokens value for logging/observability."""
        return self.max_tokens

    @staticmethod
    def _normalize_context_policy(value: Optional[Dict[str, Any] | str]) -> Dict[str, Any]:
        """Normalize the explicit policy used to select retained conversation history."""
        if value is None:
            return {"id": "full_history", "version": "1", "parameters": {}}
        if isinstance(value, str):
            value = {"id": value, "version": "1", "parameters": {}}
        if not isinstance(value, dict):
            raise TypeError("context_policy must be a string or dictionary")

        policy_id = str(value.get("id") or "").strip()
        supported = {
            "full_history",
            "no_history",
            "last_n_messages",
            "handshake_plus_recent",
        }
        if policy_id not in supported:
            raise ValueError(f"Unsupported context policy: {policy_id or '<empty>'}")

        parameters = copy.deepcopy(value.get("parameters") or {})
        if not isinstance(parameters, dict):
            raise TypeError("context_policy.parameters must be a dictionary")
        if policy_id in {"last_n_messages", "handshake_plus_recent"}:
            count = parameters.get("recent_count", parameters.get("count", 0))
            if not isinstance(count, int) or count < 0:
                raise ValueError("bounded context policies require a non-negative message count")
            parameters["recent_count"] = count

        return {
            "id": policy_id,
            "version": str(value.get("version") or "1"),
            "parameters": parameters,
        }

    @staticmethod
    def _sha256_json(value: Any) -> str:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _history_entries_source(self) -> List[Dict[str, Any]]:
        if self.conversation_manager and hasattr(self.conversation_manager, "history_entries"):
            return self.conversation_manager.history_entries()
        return [
            {
                "message_id": f"legacy-{index}",
                "exchange_id": f"legacy-{index // 2}",
                "phase": "unknown",
                "role": entry.get("role", "user"),
                "content": entry.get("content", ""),
            }
            for index, entry in enumerate(self._local_history)
        ]

    def _select_history_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        policy_id = self.context_policy["id"]
        parameters = self.context_policy["parameters"]
        if policy_id == "full_history":
            return list(entries)
        if policy_id == "no_history":
            return []

        count = parameters.get("recent_count", 0)
        recent = list(entries[-count:]) if count else []
        if policy_id == "last_n_messages":
            return recent

        handshake = [entry for entry in entries if entry.get("phase") == "handshake"]
        handshake_ids = {entry.get("message_id") for entry in handshake}
        return handshake + [
            entry for entry in recent if entry.get("message_id") not in handshake_ids
        ]

    def _capture_sdk_request(
        self,
        method: str,
        arguments: Dict[str, Any],
        *,
        assurance: str = "sent_to_official_sdk",
    ) -> None:
        """Capture the exact serializable arguments supplied to the official SDK."""
        snapshot = copy.deepcopy(arguments)
        self._pending_sdk_request = {
            "sdk": getattr(self, "PROVIDER", "unknown"),
            "method": method,
            "arguments": snapshot,
            "arguments_sha256": self._sha256_json(snapshot),
            "assurance": assurance,
        }
        call_id = self._active_provider_call_id
        attempt_index = self._active_provider_attempt_index
        if call_id is not None and attempt_index is not None:
            self.provider_call_journal.mark_dispatch_started(
                call_id=call_id,
                attempt_index=attempt_index,
                sdk_request=self._pending_sdk_request,
            )

    def _invoke_model(self, bundle, turn_context):
        user_prompt = bundle.text
        phase = getattr(self, "_active_phase", None)
        match_id = getattr(self, "_active_match_id", None)
        turn_number = getattr(self, "_active_turn_number", None)
        if turn_context is not None:
            phase = "turn"
            match_id = getattr(turn_context, "match_id", match_id)
            turn_number = getattr(turn_context, "turn_number", turn_number)
        if phase is None:
            phase = "unknown"
        call_id = uuid.uuid4().hex[:8]

        history_entries = self._history_entries_source()
        selected_entries = self._select_history_entries(history_entries)
        messages: List[Dict[str, str]] = []
        if self.prompt:
            messages.append({"role": "system", "content": self.prompt})
        messages.extend(
            {"role": str(entry["role"]), "content": str(entry["content"])}
            for entry in selected_entries
        )
        messages.append({"role": "user", "content": user_prompt})
        self.last_full_prompt = copy.deepcopy(messages)

        selected_ids = [str(entry["message_id"]) for entry in selected_entries]
        selected_id_set = set(selected_ids)
        context_selection = {
            "policy": copy.deepcopy(self.context_policy),
            "available_message_ids": [str(entry["message_id"]) for entry in history_entries],
            "selected_message_ids": selected_ids,
            "omitted_message_ids": [
                str(entry["message_id"])
                for entry in history_entries
                if str(entry["message_id"]) not in selected_id_set
            ],
            "selected_history_messages": len(selected_entries),
            "available_history_messages": len(history_entries),
        }
        composed_input = {
            "messages": copy.deepcopy(messages),
            "ordered_messages_sha256": self._sha256_json(messages),
            "current_message_index": len(messages) - 1,
        }

        logger = getattr(self, "logger", None)
        if logger:
            logger.api_request(
                player=self.name,
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self._effective_max_tokens_for_request(),
                phase=phase,
                match_id=match_id,
                turn_number=turn_number,
                call_id=call_id,
            )

        retry_durations: List[float] = []
        attempt_durations: List[float] = []
        attempts: List[Dict[str, Any]] = []

        total_attempts = self.max_retries + 1
        for attempt in range(total_attempts):
            attempt_index = attempt + 1
            start_time = time.time()
            started_at = time.time_ns()
            self._pending_sdk_request = None
            self._active_provider_call_id = call_id
            self._active_provider_attempt_index = attempt_index
            try:
                self.provider_call_journal.begin_attempt(
                    call_id=call_id,
                    attempt_index=attempt_index,
                    intent={
                        "player": self.name,
                        "provider": getattr(self, "PROVIDER", "unknown"),
                        "model": self.model,
                        "phase": phase,
                        "match_id": match_id,
                        "turn_number": turn_number,
                        "composed_input_sha256": composed_input["ordered_messages_sha256"],
                    },
                )
                response_text, metadata = self._make_api_call(messages)
                response_time = time.time() - start_time
                attempt_durations.append(response_time)
                attempts.append(
                    {
                        "attempt": attempt + 1,
                        "started_at_unix_ns": started_at,
                        "duration_ms": round(response_time * 1000, 1),
                        "outcome": "completed",
                        "sdk_request": copy.deepcopy(self._pending_sdk_request),
                    }
                )

                # MA1: Include provider identifier in usage_info
                provider = getattr(self, "PROVIDER", "unknown")
                usage_info = {
                    "tokens": metadata.get("tokens_used", 0),
                    "total_tokens": self.total_tokens + metadata.get("tokens_used", 0),
                    "prompt_tokens": metadata.get("prompt_tokens", 0),
                    "completion_tokens": metadata.get("completion_tokens", 0),
                    "cost": metadata.get("cost", 0.0),
                    "total_cost": self.total_cost + metadata.get("cost", 0.0),
                    "latency_ms": round(response_time * 1000, 1),
                    "model": metadata.get("model", self.model),
                    "provider": provider,
                    "call_id": call_id,
                }
                if "provider_model" in metadata:
                    usage_info["provider_model"] = metadata["provider_model"]
                if "reasoning_usage" in metadata:
                    usage_info["reasoning_usage"] = copy.deepcopy(metadata["reasoning_usage"])
                # MA4: Propagate estimated flag when present
                if metadata.get("estimated"):
                    usage_info["estimated"] = True

                sdk_response = {
                    "response_text": response_text,
                    "response_id": metadata.get("provider_response_id"),
                    "provider_model": metadata.get("provider_model"),
                    "stop_reason": metadata.get("stop_reason"),
                    "stop_sequence": metadata.get("stop_sequence"),
                    "response_complete": metadata.get("response_complete"),
                    "service_tier": metadata.get("service_tier"),
                    "usage": {
                        "input_tokens": metadata.get("prompt_tokens", 0),
                        "output_tokens": metadata.get("completion_tokens", 0),
                        "total_tokens": metadata.get("tokens_used", 0),
                    },
                    "content_blocks": copy.deepcopy(metadata.get("provider_content_blocks")),
                    "assurance": "returned_by_official_sdk",
                }
                if "reasoning_usage" in metadata:
                    sdk_response["usage"]["reasoning_usage"] = copy.deepcopy(
                        metadata["reasoning_usage"]
                    )
                sdk_response = {
                    key: value for key, value in sdk_response.items() if value is not None
                }
                provider_call = {
                    "schema_version": "0.1",
                    "call_id": call_id,
                    "player": self.name,
                    "phase": phase,
                    "match_id": match_id,
                    "turn_number": turn_number,
                    "context_selection": context_selection,
                    "composed_input": composed_input,
                    "sdk_request": copy.deepcopy(self._pending_sdk_request),
                    "sdk_response": sdk_response,
                    "attempts": copy.deepcopy(attempts),
                    "custody": self.provider_call_journal.describe(),
                }

                self.provider_call_journal.commit_response(
                    call_id=call_id,
                    attempt_index=attempt_index,
                    provider_call=provider_call,
                    usage_info=usage_info,
                )

                self.response_times.append(response_time)
                self.total_tokens += metadata.get("tokens_used", 0)
                self.total_cost += metadata.get("cost", 0.0)
                self.last_response = response_text
                self.last_usage_info = usage_info
                self.last_provider_call = provider_call

                if logger:
                    logger.api_response(
                        player=self.name,
                        response_text=response_text,
                        phase=phase,
                        match_id=match_id,
                        turn_number=turn_number,
                        call_id=call_id,
                    )
                    logger.api_call(
                        player=self.name,
                        model=metadata.get("model_used", self.model),
                        tokens_in=metadata.get("prompt_tokens", 0),
                        tokens_out=metadata.get("completion_tokens", 0),
                        cost=metadata.get("cost", 0.0),
                        duration=response_time,
                        phase=phase,
                        match_id=match_id,
                        turn_number=turn_number,
                        call_id=call_id,
                    )

                # CH2: History is recorded by Player._record_exchange() in lifecycle methods.
                # Don't call _append_history here to avoid duplication.

                return response_text, {
                    "raw_response": response_text,
                    "response_text": response_text,  # PM2: response_text key
                    "phase": phase,  # PM3: phase context
                    "usage_info": getattr(self, "last_usage_info", None),
                    "call_id": call_id,
                    "match_id": match_id,
                    "turn_number": turn_number,
                    "retries": attempt,
                    "retry_durations": retry_durations,
                    "attempt_durations": attempt_durations,
                    "provider_call": copy.deepcopy(self.last_provider_call),
                }
            except ProviderCallCustodyError:
                raise
            except Exception as exc:
                response_time = time.time() - start_time
                attempt_durations.append(response_time)
                attempts.append(
                    {
                        "attempt": attempt + 1,
                        "started_at_unix_ns": started_at,
                        "duration_ms": round(response_time * 1000, 1),
                        "outcome": "failed",
                        "sdk_request": copy.deepcopy(self._pending_sdk_request),
                        "error": {
                            "type": exc.__class__.__name__,
                            "message": str(exc)[:500],
                        },
                    }
                )
                self.provider_call_journal.commit_error(
                    call_id=call_id,
                    attempt_index=attempt_index,
                    error={
                        "type": exc.__class__.__name__,
                        "message": str(exc)[:500],
                    },
                )
                if attempt == total_attempts - 1:
                    self.last_provider_call = {
                        "schema_version": "0.1",
                        "call_id": call_id,
                        "player": self.name,
                        "phase": phase,
                        "match_id": match_id,
                        "turn_number": turn_number,
                        "context_selection": context_selection,
                        "composed_input": composed_input,
                        "sdk_request": copy.deepcopy(self._pending_sdk_request),
                        "sdk_response": None,
                        "attempts": copy.deepcopy(attempts),
                        "custody": self.provider_call_journal.describe(),
                    }
                    self.last_usage_info = None
                    self.last_retries = attempt
                    self.last_retry_durations = list(retry_durations)
                    self.last_attempt_durations = list(attempt_durations)
                    provider = getattr(self, "PROVIDER", "unknown")
                    raise PlayerResponseUnavailableError(
                        player_name=self.name,
                        provider=provider,
                        model=self.model,
                        call_id=call_id,
                        provider_call=self.last_provider_call,
                        retries=attempt,
                        retry_durations=retry_durations,
                        attempt_durations=attempt_durations,
                        cause_type=exc.__class__.__name__,
                        cause_message=str(exc)[:500],
                    ) from exc
                delay = self.retry_delay * (2**attempt)
                retry_durations.append(delay)
                if logger:
                    logger.retry(
                        player=self.name, attempt=attempt + 1, error=str(exc), backoff=delay
                    )
                time.sleep(delay)
            finally:
                self._active_provider_call_id = None
                self._active_provider_attempt_index = None

        # RE3: Include provider identifier in error message
        provider = getattr(self, "PROVIDER", "unknown")
        raise RuntimeError(
            f"Failed to get response from {provider}/{self.model} "
            f"after {total_attempts} attempts"
        )

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

        response, metadata = self._invoke_model(PromptBundle(text=prompt, blocks=[]), None)
        self.last_retries = metadata.get("retries")
        self.last_retry_durations = metadata.get("retry_durations")
        self.last_attempt_durations = metadata.get("attempt_durations")
        return response

    def describe(self) -> Dict[str, Any]:
        base = super().describe()
        base.update(
            {
                "provider": getattr(self, "PROVIDER", self.__class__.__module__),
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "retry_policy": {
                    "max_retries": self.max_retries,
                    "retry_delay": self.retry_delay,
                },
                "context_policy": copy.deepcopy(self.context_policy),
            }
        )
        provider_config: Dict[str, Any] = {}
        if hasattr(self, "_project_id"):
            provider_config["project_id"] = self._project_id
        if hasattr(self, "_location"):
            provider_config["location"] = self._location
        if hasattr(self, "_generation_overrides"):
            provider_config["generation_config"] = copy.deepcopy(self._generation_overrides)
        if provider_config:
            base["provider_config"] = provider_config
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

        If conclusion_template is None, records minimal prompt metadata and returns None.
        Otherwise, prompts LLM for reflection on the match outcome.

        Args:
            result: Match outcome (winner, final_state, etc.)
            match_context: Match execution metadata

        Returns:
            Optional reflection string from LLM
        """
        logger = getattr(self, "logger", None)

        def _parse_conclusion_metadata(text: str) -> Dict[str, Any]:
            try:
                parsed = self.controller.parse_conclusion(text)
                return parsed if isinstance(parsed, dict) else {"reflection_text": parsed}
            except Exception as exc:  # pragma: no cover - defensive
                if logger:
                    logger.debug(f"Conclusion parse failed for {self.name}: {exc}")
                return {}

        explicit_prompt = getattr(match_context, "conclusion_prompt", None)

        if explicit_prompt:
            self._active_phase = "conclusion"
            self._active_match_id = getattr(match_context, "match_id", None)
            self._active_turn_number = 0
            try:
                reflection = self.get_response(explicit_prompt)
            except Exception as exc:  # pragma: no cover - defensive
                if logger:
                    logger.debug(f"Conclusion failed for {self.name}: {exc}")
                reflection = None
            finally:
                self._active_phase = None
                self._active_match_id = None
                self._active_turn_number = None
            if reflection is not None:
                usage_info = getattr(self, "last_usage_info", None)
                controller_metadata = (
                    _parse_conclusion_metadata(reflection) if reflection is not None else {}
                )
                self._record_exchange(
                    explicit_prompt,
                    reflection or "",
                    phase="conclusion",
                    turn_context=None,
                    prompt_blocks=[
                        {"key": "conclusion_prompt", "content": explicit_prompt, "metadata": {}}
                    ],
                    controller_format="",
                    controller_metadata=controller_metadata,
                    renderer_output={},
                    usage_info=usage_info,
                    provider_call=copy.deepcopy(self.last_provider_call),
                )

            return reflection.strip() if reflection else None

        # Check if conclusion template is configured in PromptBuilder
        if self.prompt_builder._conclusion_template is None:
            return super().conclude(result, match_context=match_context)

        # Build conclusion prompt using PromptBuilder
        try:
            final_state_for_prompt = self._sanitize_conclusion_state(result.final_state)

            # Render final state from player's perspective
            final_view = self.renderer.render(
                final_state_for_prompt,
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
            self._active_phase = "conclusion"
            self._active_match_id = getattr(match_context, "match_id", None)
            self._active_turn_number = 0
            try:
                reflection, metadata = self._invoke_model(bundle, None)
            finally:
                self._active_phase = None
                self._active_match_id = None
                self._active_turn_number = None
            controller_metadata = (
                _parse_conclusion_metadata(reflection) if reflection is not None else {}
            )

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
                controller_metadata=controller_metadata,
                renderer_output=(
                    final_view.metadata
                    if isinstance(final_view, RenderResult) and final_view.metadata
                    else {}
                ),
                usage_info=metadata.get("usage_info") if metadata else None,
                provider_call=(copy.deepcopy(metadata.get("provider_call")) if metadata else None),
            )

            return reflection.strip() if reflection else None
        except Exception as e:
            # Log error but don't fail - conclusion is optional
            logger = getattr(self, "logger", None)
            if logger:
                logger.debug(f"Conclusion failed for {self.name}: {e}")
            return None

    def _sanitize_conclusion_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove engine bookkeeping keys from LLM-facing conclusion prompts.
        """
        if not isinstance(state, dict):
            return {}

        sanitized = copy.deepcopy(state)
        for key in self._ENGINE_INTERNAL_STATE_KEYS:
            sanitized.pop(key, None)
        return sanitized

    def _format_outcome(self, result) -> str:
        """Helper to generate human-readable outcome string for conclusion prompts."""
        if result.winner is None:
            return "Draw"
        if result.winner == self.name:
            return f"You ( {self.name} ) won the match."
        return f"{result.winner} won the match."
