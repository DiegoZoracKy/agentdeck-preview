"""Anthropic Claude player for AgentDeck."""

from typing import Dict, List, Tuple

from ..utils.pricing import calculate_cost
from .llm_player import LLMPlayer


class ClaudePlayer(LLMPlayer):
    """Anthropic Claude player - CORE COMPONENT."""

    PROVIDER = "anthropic"
    default_model = None
    api_key_env_var = "ANTHROPIC_API_KEY"

    def _initialize_client(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "Anthropic client library is not installed. "
                'Install it via the optional extra: pip install "agentdeck-ai[anthropic]"'
            ) from exc

        self.client = Anthropic(api_key=self.api_key)

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

        response = self.client.messages.create(
            model=self.model,
            system=system_prompt if system_prompt else None,
            messages=claude_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **self.config,
        )

        response_text = response.content[0].text

        # Calculate cost using YAML pricing
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        cost = calculate_cost(
            provider=self.PROVIDER,
            model=self.model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

        metadata = {
            "tokens_used": tokens_used,
            "cost": cost,
            "model_used": self.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            # Add standard keys for LLMPlayer compatibility
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
        }

        return response_text, metadata
