"""
LLM Adapter - Unified interface for DashScope and OpenAI-compatible APIs.

Supports two providers:
  - dashscope (default): Alibaba Cloud DashScope via OpenAI-compatible endpoint
  - openai: Any OpenAI-compatible API (OpenAI, DeepSeek, Ollama, etc.)

Credentials are resolved per-request via :mod:`src.runtime` so each user
has their own ``LLM_PROVIDER`` / ``DASHSCOPE_API_KEY`` / ``OPENAI_*``.
Outside a request the helpers fall back to the process environment.
"""
import logging
from typing import Dict, List, Optional, Any

from src.runtime import get_cred
from ...utils.endpoints import get_provider_base_url

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Unified LLM call interface supporting DashScope and OpenAI-compatible APIs."""

    def __init__(self):
        # Nothing cached here: credentials are resolved on every call so
        # users can update their keys without forcing a process restart.
        logger.info("LLM Adapter initialized (credentials resolved per request)")

    @property
    def provider(self) -> str:
        return (get_cred("LLM_PROVIDER") or "dashscope").lower()

    @property
    def is_configured(self) -> bool:
        if self.provider == "openai":
            return bool(get_cred("OPENAI_API_KEY"))
        return bool(get_cred("DASHSCOPE_API_KEY"))

    def _get_client(self):
        """Build a fresh OpenAI-compatible client for the current request."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai>=1.0.0"
            )

        if self.provider == "openai":
            return OpenAI(
                api_key=get_cred("OPENAI_API_KEY"),
                base_url=get_cred("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            )
        # DashScope uses OpenAI-compatible endpoint
        return OpenAI(
            api_key=get_cred("DASHSCOPE_API_KEY"),
            base_url=f"{get_provider_base_url('DASHSCOPE')}/compatible-mode/v1",
        )

    def _get_default_model(self) -> str:
        if self.provider == "openai":
            return get_cred("OPENAI_MODEL") or "gpt-4o"
        return "qwen3.5-plus"

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Send a chat completion request and return the response content.

        Args:
            messages: List of {"role": ..., "content": ...} dicts
            model: Model name override (uses provider default if None)
            response_format: Optional {"type": "json_object"} constraint

        Returns:
            The assistant's response content as a string.

        Raises:
            RuntimeError: If the API call fails.
        """
        client = self._get_client()
        model = model or self._get_default_model()

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            provider_label = "DashScope" if self.provider != "openai" else "OpenAI"
            raise RuntimeError(f"{provider_label} API error: {e}") from e
