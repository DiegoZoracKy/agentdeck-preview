"""Google Gemini player for AgentDeck."""

from __future__ import annotations

import base64
import binascii
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from ..utils.pricing import calculate_cost
from .llm_player import LLMPlayer


class GeminiPlayer(LLMPlayer):
    """Google Gemini player backed by the Google Gen AI SDK in Vertex mode."""

    PROVIDER = "google"
    default_model = None
    api_key_env_var = None  # Vertex AI uses ADC/Project configuration instead of API keys
    _SERVICE_ACCOUNT_B64_ENV_VAR = "GOOGLE_APPLICATION_CREDENTIALS_B64"
    _VERTEX_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

    def __init__(
        self,
        name: str,
        *,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self._service_account_info = self._load_service_account_info_from_env()
        self._project_id = (
            project_id
            or os.getenv("VERTEX_PROJECT_ID")
            or self._project_id_from_service_account(self._service_account_info)
        )
        self._location = location or os.getenv("VERTEX_LOCATION", "us-central1")
        if not self._project_id:
            raise ValueError(
                "GeminiPlayer requires a Vertex AI project ID. "
                "Set VERTEX_PROJECT_ID, pass project_id= explicitly, or provide "
                "GOOGLE_APPLICATION_CREDENTIALS_B64 with a service-account JSON payload "
                "that includes project_id."
            )
        self._generation_overrides = generation_config or {}
        super().__init__(name=name, **kwargs)

    def _get_api_key_from_env(self) -> str:
        """Override base requirement for API keys (Vertex AI uses ADC)."""
        return ""

    def _initialize_client(self):
        """Initialize Google Gen AI client in Vertex mode."""
        try:
            from google import genai
            from google.oauth2 import service_account
        except ImportError as exc:
            raise ImportError(
                "google-genai is not installed. "
                'Install it via the optional extra: pip install "agentdeck-ai[google]"'
            ) from exc

        credentials = None
        if self._service_account_info is not None:
            credentials = service_account.Credentials.from_service_account_info(
                self._service_account_info,
                scopes=[self._VERTEX_SCOPE],
            )

        self.client = genai.Client(
            vertexai=True,
            project=self._project_id,
            location=self._location,
            credentials=credentials,
        )

    @classmethod
    def _project_id_from_service_account(
        cls, service_account_info: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        if not service_account_info:
            return None
        project_id = service_account_info.get("project_id")
        if not project_id:
            return None
        return str(project_id)

    @classmethod
    def _load_service_account_info_from_env(cls) -> Optional[Dict[str, Any]]:
        encoded = os.getenv(cls._SERVICE_ACCOUNT_B64_ENV_VAR)
        if not encoded:
            return None
        normalized = "".join(encoded.split())

        try:
            decoded = base64.b64decode(normalized, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS_B64 must be valid base64-encoded JSON."
            ) from exc

        try:
            payload = json.loads(decoded.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS_B64 must decode to UTF-8 JSON."
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS_B64 must decode to a JSON object."
            ) from exc

        if not isinstance(payload, dict):
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS_B64 must decode to a JSON object."
            )

        return payload

    def _make_api_call(self, messages: List[Dict[str, str]]) -> Tuple[str, Dict]:
        """Call Gemini through the Google Gen AI SDK using Vertex credentials."""
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

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=generation_config,
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
            "credential_source": (
                self._SERVICE_ACCOUNT_B64_ENV_VAR if self._service_account_info else "adc"
            ),
        }

        return response_text, metadata
