"""Anthropic Claude player for AgentDeck."""

import inspect

from typing import Any, Dict, List, Tuple

from ..utils.pricing import calculate_cost
from .llm_player import LLMPlayer


class ClaudePlayer(LLMPlayer):
    """Anthropic Claude player - CORE COMPONENT."""

    PROVIDER = "anthropic"
    default_model = None
    api_key_env_var = "ANTHROPIC_API_KEY"
    # Anthropic Messages API requires max_tokens on every request.
    REQUIRED_MAX_TOKENS_FALLBACK = 4096

    def _initialize_client(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "Anthropic client library is not installed. "
                'Install it via the optional extra: pip install "agentdeck-ai[anthropic]"'
            ) from exc

        # LLMPlayer owns retries so every attempt crosses provider-call custody.
        self.client = Anthropic(api_key=self.api_key, max_retries=0)

    def _effective_max_tokens_for_request(self) -> int | None:
        """Anthropic requires an explicit max_tokens on every request."""
        return self.max_tokens or self.REQUIRED_MAX_TOKENS_FALLBACK

    def _make_api_call(self, messages: List[Dict[str, str]]) -> Tuple[str, Dict]:
        """Make API call to Anthropic."""
        # Convert messages to Claude format
        system_prompt = None
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        # Claude requires alternating user/assistant messages
        # If we only have user messages, that's fine
        claude_messages = user_messages

        # Build kwargs, only include system if present
        max_tokens = self.max_tokens
        if not max_tokens:
            max_tokens = self.REQUIRED_MAX_TOKENS_FALLBACK

        kwargs = {
            "model": self.model,
            "messages": claude_messages,
            "max_tokens": max_tokens,
            **self.config,
        }
        if self.temperature is not None:
            parameters = inspect.signature(self.client.messages.create).parameters
            supports_native_temperature = "temperature" in parameters or any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
            )
            if supports_native_temperature:
                kwargs["temperature"] = self.temperature
            else:
                extra_body = dict(kwargs.get("extra_body") or {})
                configured = extra_body.get("temperature")
                if configured is not None and configured != self.temperature:
                    raise ValueError("Anthropic temperature conflicts with extra_body.temperature")
                extra_body["temperature"] = self.temperature
                kwargs["extra_body"] = extra_body
        if system_prompt:
            kwargs["system"] = system_prompt

        self._capture_sdk_request("anthropic.messages.create", kwargs)
        response = self.client.messages.create(**kwargs)

        response_text, content_blocks = self._project_response_content(response.content)

        # Calculate cost using YAML pricing
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        cost = calculate_cost(
            provider=self.PROVIDER,
            model=self.model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

        stop_reason = getattr(response, "stop_reason", None)
        output_details = getattr(response.usage, "output_tokens_details", None)
        thinking_tokens = getattr(output_details, "thinking_tokens", None)
        metadata = {
            "tokens_used": tokens_used,
            "cost": cost,
            "model_used": self.model,
            "provider_model": getattr(response, "model", None),
            "provider_response_id": getattr(response, "id", None),
            "stop_reason": stop_reason,
            "stop_sequence": getattr(response, "stop_sequence", None),
            "response_complete": None if stop_reason is None else stop_reason != "max_tokens",
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            # Add standard keys for LLMPlayer compatibility
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "provider_content_blocks": content_blocks,
        }
        if thinking_tokens is not None:
            metadata["reasoning_usage"] = {
                "tokens": thinking_tokens,
                "kind": "thinking",
                "source": ("anthropic.messages.usage.output_tokens_details.thinking_tokens"),
            }

        return response_text, metadata

    @staticmethod
    def _project_response_content(content: Any) -> Tuple[str, List[Dict[str, Any]]]:
        """Project provider content blocks into Controller text and bounded audit data."""
        text_parts: List[str] = []
        captured_blocks: List[Dict[str, Any]] = []

        for block in content or []:
            block_type = getattr(block, "type", None)
            if block_type is None and isinstance(getattr(block, "text", None), str):
                block_type = "text"
            block_type = str(block_type or "unknown")
            captured: Dict[str, Any] = {"type": block_type}

            if block_type == "text":
                value = getattr(block, "text", None)
                if isinstance(value, str):
                    captured["text"] = value
                    text_parts.append(value)
            elif block_type == "thinking":
                value = getattr(block, "thinking", None)
                if isinstance(value, str):
                    captured["thinking"] = value

            captured_blocks.append(captured)

        return "\n".join(text_parts), captured_blocks
