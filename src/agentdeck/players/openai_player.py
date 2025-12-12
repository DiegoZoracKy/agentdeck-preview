"""OpenAI GPT player for AgentDeck."""

from typing import Dict, List, Tuple

from ..utils.pricing import calculate_cost
from .llm_player import LLMPlayer


class GPTPlayer(LLMPlayer):
    """OpenAI GPT player - CORE COMPONENT."""

    PROVIDER = "openai"
    default_model = None
    api_key_env_var = "OPENAI_API_KEY"

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
        """Make API call to OpenAI."""
        # Build API parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            **self.config,  # Additional parameters like top_p, frequency_penalty
        }

        # Handle max_tokens vs max_completion_tokens based on model
        # Newer models (o1, o3, etc.) use max_completion_tokens
        if self.max_tokens:
            if any(prefix in self.model.lower() for prefix in ["o1", "o3", "gpt-5"]):
                api_params["max_completion_tokens"] = self.max_tokens
            else:
                api_params["max_tokens"] = self.max_tokens

        response = self.client.chat.completions.create(**api_params)

        # Extract response
        response_text = response.choices[0].message.content

        # Calculate tokens and cost using YAML pricing
        tokens_used = response.usage.total_tokens

        # Use the pricing utility to calculate cost
        cost = calculate_cost(
            provider=self.PROVIDER,
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        metadata = {
            "tokens_used": tokens_used,
            "cost": cost,
            "model": self.model,
            "provider_model": response.model,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        }

        return response_text, metadata
