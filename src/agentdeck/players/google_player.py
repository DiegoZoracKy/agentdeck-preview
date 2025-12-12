"""Google Gemini player for AgentDeck."""

from __future__ import annotations

import os
import warnings
from typing import Any, Dict, List, Optional, Tuple

from ..utils.pricing import calculate_cost
from .llm_player import LLMPlayer


class GeminiPlayer(LLMPlayer):
    """Google Gemini player backed by Vertex AI."""

    PROVIDER = "google"
    default_model = None
    api_key_env_var = None  # Vertex AI uses ADC/Project configuration instead of API keys

    _vertex_initialized: bool = False

    def __init__(
        self,
        name: str,
        *,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self._project_id = project_id or os.getenv("VERTEX_PROJECT_ID")
        self._location = location or os.getenv("VERTEX_LOCATION", "us-central1")
        if not self._project_id:
            raise ValueError(
                "GeminiPlayer requires a Vertex AI project ID. "
                "Set VERTEX_PROJECT_ID or pass project_id= explicitly."
            )
        self._generation_overrides = generation_config or {}
        super().__init__(name=name, **kwargs)

    def _get_api_key_from_env(self) -> str:
        """Override base requirement for API keys (Vertex AI uses ADC)."""
        return ""

    def _initialize_client(self):
        """Initialize Vertex AI GenerativeModel client."""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
        except ImportError as exc:
            raise ImportError(
                "google-cloud-aiplatform is not installed. "
                'Install it via the optional extra: pip install "agentdeck-ai[google]"'
            ) from exc

        if not GeminiPlayer._vertex_initialized:
            vertexai.init(project=self._project_id, location=self._location)
            GeminiPlayer._vertex_initialized = True

        warnings.filterwarnings(
            "ignore",
            message="This feature is deprecated as of June 24, 2025",
            category=UserWarning,
            module="vertexai.generative_models._generative_models",
        )

        self.client = GenerativeModel(self.model)

    def _make_api_call(self, messages: List[Dict[str, str]]) -> Tuple[str, Dict]:
        """Call Vertex AI Gemini model."""
        prompt_parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            role_label = role.capitalize()
            prompt_parts.append(f"{role_label}: {content}")
        prompt = "\n\n".join(prompt_parts)

        generation_config = {
            "temperature": self.temperature,
        }
        if self.max_tokens:
            generation_config["max_output_tokens"] = self.max_tokens

        # Allow users to override Vertex generation settings via kwargs
        generation_config.update(self._generation_overrides or {})

        response = self.client.generate_content(
            [prompt],
            generation_config=generation_config,
        )

        response_text = getattr(response, "text", "") or ""

        usage = getattr(response, "usage_metadata", None)
        if usage:
            prompt_tokens = getattr(usage, "prompt_token_count", 0)
            completion_tokens = getattr(usage, "candidates_token_count", 0)
            total_tokens = getattr(usage, "total_token_count", prompt_tokens + completion_tokens)
            estimated = False
        else:
            # Fallback estimate: 1 token ≈ 4 characters
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(response_text) // 4
            total_tokens = prompt_tokens + completion_tokens
            estimated = True

        cost = calculate_cost(
            provider=self.PROVIDER,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        metadata = {
            "tokens_used": total_tokens,
            "cost": cost,
            "model_used": self.model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated": estimated,
            "project_id": self._project_id,
            "location": self._location,
        }

        return response_text, metadata
