"""
LLM Adapter - Unified OpenAI-compatible client for any LLM vendor.

Now driven by :class:`ModelInstance` injected via ``with_instance(...)``.
When an instance is bound:
  - ``model_name`` comes from ``instance.model_name``
  - ``base_url`` comes from ``instance.base_url`` (or vendor default)
  - API key comes from ``instance.credentials`` (OPENAI_API_KEY or
    DASHSCOPE_API_KEY depending on vendor)

When no instance is bound (CLI / tests) the adapter falls back to env vars
so existing scripts keep working.
"""
import logging
from typing import Dict, List, Optional, Any

from src.runtime import current_instance, get_cred
from ...utils.endpoints import get_provider_base_url

logger = logging.getLogger(__name__)


_VENDOR_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "minimax": "https://api.minimaxi.com/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama": "http://localhost:11434/v1",
}


class LLMAdapter:
    """Unified LLM call interface supporting DashScope and OpenAI-compatible APIs."""

    def __init__(self):
        # Nothing cached here: credentials are resolved on every call so
        # users can update their keys without forcing a process restart.
        logger.info("LLM Adapter initialized (credentials resolved per request)")

    @property
    def provider(self) -> str:
        """Vendor family for the current call. Reads strictly from the bound
        LLM ModelInstance; raises if no instance is configured."""
        inst = self._require_inst()
        return "dashscope" if inst.vendor_id == "dashscope" else "openai"

    @property
    def is_configured(self) -> bool:
        """True iff an LLM instance is bound and carries a usable API key.

        This is a pre-flight probe — never silently consults env vars; if
        no instance is bound it returns False so the caller surfaces the
        configuration gap instead of trying anyway."""
        inst = current_instance()
        if not inst:
            return False
        return bool(
            inst.credentials.get("OPENAI_API_KEY")
            or inst.credentials.get("MINIMAX_API_KEY")
            or inst.credentials.get("DASHSCOPE_API_KEY")
        )

    @staticmethod
    def _require_inst():
        """Strict instance fetch — raises ``InstanceNotConfiguredError`` if
        no LLM ModelInstance is currently scoped. The whole adapter is
        instance-driven; there is no env-based fallback path anymore."""
        from ...models.instance import InstanceNotConfiguredError, InstanceType
        inst = current_instance()
        if inst is None:
            raise InstanceNotConfiguredError(InstanceType.LLM)
        return inst

    def _get_client(self):
        """Build a fresh OpenAI-compatible client for the current request,
        driven entirely by the bound LLM ModelInstance (api key + base url
        + vendor → SDK route). No env fallback — calls outside an instance
        scope raise immediately."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai>=1.0.0"
            )

        inst = self._require_inst()
        api_key = (
            inst.credentials.get("OPENAI_API_KEY")
            or inst.credentials.get("MINIMAX_API_KEY")
            or inst.credentials.get("DASHSCOPE_API_KEY")
            or ""
        )
        base_url = inst.base_url or _VENDOR_BASE_URLS.get(
            inst.vendor_id, "https://api.openai.com/v1"
        )
        if inst.vendor_id == "dashscope" and not inst.base_url:
            base_url = f"{get_provider_base_url('DASHSCOPE')}/compatible-mode/v1"
        return OpenAI(api_key=api_key, base_url=base_url)

    def _get_default_model(self) -> str:
        return self._require_inst().model_name

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
