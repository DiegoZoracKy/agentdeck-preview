"""OpenAI GPT player for AgentDeck."""

from typing import Any, Dict, List, Tuple

from ..utils.pricing import calculate_cost
from .llm_player import LLMPlayer


class GPTPlayer(LLMPlayer):
    """OpenAI GPT player - CORE COMPONENT."""

    PROVIDER = "openai"
    default_model = None
    api_key_env_var = "OPENAI_API_KEY"
    _RESPONSES_API_ALLOWLIST = {
        "max_output_tokens",
        "max_tokens",
        "max_completion_tokens",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "logit_bias",
        "text",
        "tools",
        "tool_choice",
        "parallel_tool_calls",
        "reasoning",
        "truncation",
        "metadata",
        "service_tier",
        "user",
    }

    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "OpenAI client library is not installed. "
                'Install it via the optional extra: pip install "agentdeck-ai[openai]"'
            ) from exc

        self.client = OpenAI(api_key=self.api_key)

    def _make_api_call(self, messages: List[Dict[str, str]]) -> Tuple[str, Dict]:
        """Make API call to OpenAI Responses API."""
        instructions, input_messages = self._split_system_messages(messages)
        config = self._validate_and_remap_config(self.config)

        if self.max_tokens is not None:
            configured = config.get("max_output_tokens")
            if configured is not None and configured != self.max_tokens:
                raise ValueError(
                    "Conflicting max token settings: max_tokens and max_output_tokens differ."
                )
            config["max_output_tokens"] = self.max_tokens

        # Phase 1 migration: keep history client-side for deterministic replay artifacts.
        api_params = {
            "model": self.model,
            "input": input_messages,
            "temperature": self.temperature,
            "store": False,
            **config,
        }
        if instructions:
            api_params["instructions"] = instructions

        response = self.client.responses.create(**api_params)
        response_text = self._extract_response_text(response)
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "input_tokens", 0) or 0
        completion_tokens = getattr(usage, "output_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", None)
        tokens_used = (
            total_tokens if total_tokens is not None else prompt_tokens + completion_tokens
        )

        # Use the pricing utility to calculate cost
        cost = calculate_cost(
            provider=self.PROVIDER,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        metadata = {
            "tokens_used": tokens_used,
            "cost": cost,
            "model": self.model,
            "provider_model": getattr(response, "model", self.model),
            # Keep internal naming stable for pricing/spectators.
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            # Preserve provider-native fields for transparency.
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
        }

        return response_text, metadata

    def _validate_and_remap_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate OpenAI Responses API params and normalize token limit aliases."""
        normalized: Dict[str, Any] = {}
        max_output_tokens = None

        for key, value in config.items():
            if key not in self._RESPONSES_API_ALLOWLIST:
                allowed = ", ".join(sorted(self._RESPONSES_API_ALLOWLIST))
                raise ValueError(
                    f"Unsupported OpenAI Responses API config key: '{key}'. "
                    f"Allowed keys: {allowed}"
                )

            if key in {"max_tokens", "max_completion_tokens", "max_output_tokens"}:
                if max_output_tokens is None:
                    max_output_tokens = value
                elif max_output_tokens != value:
                    raise ValueError(
                        "Conflicting token limit keys in OpenAI config: "
                        "max_tokens/max_completion_tokens/max_output_tokens."
                    )
                continue

            normalized[key] = value

        if max_output_tokens is not None:
            normalized["max_output_tokens"] = max_output_tokens

        return normalized

    def _split_system_messages(
        self, messages: List[Dict[str, str]]
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Extract system instructions and keep user/assistant history as input."""
        system_parts: List[str] = []
        input_messages: List[Dict[str, str]] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                if content:
                    system_parts.append(str(content))
                continue
            input_messages.append(msg)

        instructions = "\n\n".join(system_parts)
        return instructions, input_messages

    def _extract_response_text(self, response: Any) -> str:
        """Extract plain text from Responses API response with robust fallback."""
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        collected: List[str] = []
        for item in getattr(response, "output", []) or []:
            item_type = getattr(item, "type", None)
            if item_type != "message":
                continue

            for chunk in getattr(item, "content", []) or []:
                chunk_type = getattr(chunk, "type", None)
                if chunk_type in {"output_text", "text"}:
                    text = getattr(chunk, "text", None)
                    if isinstance(text, str) and text:
                        collected.append(text)

        joined = "\n".join(part for part in collected if part).strip()
        if joined:
            return joined

        raise RuntimeError(
            "OpenAI Responses API returned no text output. " f"Raw response: {response!r}"
        )
