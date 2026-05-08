"""
Model catalog — single source of truth for selectable models / LLM presets.

Design notes
============
This module follows the same dataclass-driven Registry pattern as
:mod:`src.utils.provider_registry`. Each model is a declarative entry; adding
a new model only requires appending a :class:`ModelCard` (or :class:`LLMPreset`)
to the catalog — no ``if/elif`` branches, no UI hardcoding.

The frontend reads the resulting catalog through ``GET /registry/models`` and
``GET /registry/llm-presets`` so the dropdowns shown in the Settings page stay
in lockstep with what the backend can actually route.

Keep this file declarative. Provider-specific HTTP clients still live under
``src/models/`` and are dispatched via the ``family`` field below.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ─────────────────────────────────────────────────────────────────────────
# Model cards
# ─────────────────────────────────────────────────────────────────────────

# Capability strings used across the codebase / FE registry.
CAPABILITIES = ("t2i", "i2i", "i2v", "t2v", "r2v", "tts", "llm")

# Badges purely drive the UI — no behavior depends on them.
ALLOWED_BADGES = ("recommended", "new", "preview", "fast", "premium", "open-source")


@dataclass(frozen=True)
class ModelCard:
    """Declarative metadata for one selectable model.

    Fields:
        id:            stable model identifier the backend / providers use.
        family:        provider-routing family key (matches ProviderRegistry).
        display_name:  short human-readable name.
        description:   one-line user-facing blurb.
        capabilities:  which generation stages this model supports.
        provider_key:  endpoint provider (DASHSCOPE / KLING / VIDU / ...).
        requires_credentials: env keys that must be set for this model to run.
        params:        UI hints (resolution options, duration ranges, etc).
        available:     False = shown disabled with "coming soon" label.
        badges:        decorative tags for the UI.
    """

    id: str
    family: str
    display_name: str
    description: str = ""
    capabilities: Tuple[str, ...] = ()
    provider_key: str = "DASHSCOPE"
    requires_credentials: Tuple[str, ...] = ("DASHSCOPE_API_KEY",)
    params: Dict[str, object] = field(default_factory=dict)
    available: bool = True
    badges: Tuple[str, ...] = ()


# ── Reusable parameter presets (kept here so adding a card stays one-liner) ──

_RES_LADDER = {"options": ["480p", "720p", "1080p"], "default": "720p"}
_VIDU_RES_LADDER = {"options": ["540p", "720p", "1080p"], "default": "720p"}
_HAILUO_RES_LADDER = {"options": ["768p", "1080p"], "default": "768p"}

_WAN26_PARAMS: Dict[str, object] = {
    "resolution": _RES_LADDER,
    "seed": True,
    "negativePrompt": True,
    "promptExtend": True,
    "shotType": True,
    "audio": True,
}
_WAN25_PARAMS: Dict[str, object] = {
    "resolution": _RES_LADDER,
    "seed": True,
    "negativePrompt": True,
    "audio": True,
}
_WAN22_PARAMS: Dict[str, object] = {
    "resolution": _RES_LADDER,
    "seed": True,
    "negativePrompt": True,
}
_KLING_PARAMS: Dict[str, object] = {
    "negativePrompt": True,
    "mode": {"options": ["std", "pro"], "default": "std"},
    "sound": True,
    "cfgScale": {"min": 0, "max": 1, "step": 0.1, "default": 0.5},
}
_VIDU_PARAMS: Dict[str, object] = {
    "resolution": _VIDU_RES_LADDER,
    "seed": True,
    "viduAudio": True,
    "movementAmplitude": {"options": ["auto", "small", "medium", "large"], "default": "auto"},
}
_PIXVERSE_PARAMS: Dict[str, object] = {
    "resolution": _RES_LADDER,
    "negativePrompt": True,
    "seed": True,
}
_SEEDANCE_PARAMS: Dict[str, object] = {
    "resolution": {"options": ["720p", "1080p", "2k"], "default": "1080p"},
    "seed": True,
    "negativePrompt": True,
}
_HAILUO_PARAMS: Dict[str, object] = {
    "resolution": _HAILUO_RES_LADDER,
    "negativePrompt": True,
}


def _duration(kind: str, **kw) -> Dict[str, object]:
    """Convenience packer matching the FE ``DurationConfig`` shape."""
    return {"type": kind, **kw}


# ── Catalog: T2I / I2I (image generation) ────────────────────────────────

T2I_CARDS: Tuple[ModelCard, ...] = (
    ModelCard(
        id="wan2.6-t2i",
        family="wan2.6-",
        display_name="Wan 2.6 T2I",
        description="通义万相 2.6,默认 T2I,质量与速度均衡",
        capabilities=("t2i",),
        params={"size_presets": ["1024*1024", "1024*576", "576*1024"]},
        badges=("recommended",),
    ),
    ModelCard(
        id="wan2.5-t2i-preview",
        family="wan2.5-",
        display_name="Wan 2.5 T2I Preview",
        description="通义万相 2.5 预览版",
        capabilities=("t2i",),
    ),
    ModelCard(
        id="wan2.2-t2i-plus",
        family="wan2.2-",
        display_name="Wan 2.2 T2I Plus",
        description="通义万相 2.2,高质量",
        capabilities=("t2i",),
    ),
    ModelCard(
        id="wan2.2-t2i-flash",
        family="wan2.2-",
        display_name="Wan 2.2 T2I Flash",
        description="通义万相 2.2,快速生成",
        capabilities=("t2i",),
        badges=("fast",),
    ),
    ModelCard(
        id="qwen-image",
        family="qwen-image",
        display_name="Qwen-Image",
        description="千问图像基础模型,擅长中文文字渲染",
        capabilities=("t2i",),
        badges=("new",),
    ),
    ModelCard(
        id="qwen-image-plus",
        family="qwen-image",
        display_name="Qwen-Image Plus",
        description="千问图像增强版,2K 原生分辨率,精细排版",
        capabilities=("t2i",),
        badges=("new", "premium"),
    ),
    ModelCard(
        id="flux-schnell",
        family="flux-",
        display_name="FLUX.1 Schnell",
        description="FLUX 中文优化版,快速生成",
        capabilities=("t2i",),
        badges=("fast", "open-source"),
    ),
    ModelCard(
        id="flux-dev",
        family="flux-",
        display_name="FLUX.1 Dev",
        description="FLUX 高质量版,适合高细节场景",
        capabilities=("t2i",),
        badges=("open-source",),
    ),
)


I2I_CARDS: Tuple[ModelCard, ...] = (
    ModelCard(
        id="wan2.6-image",
        family="wan2.6-",
        display_name="Wan 2.6 Image",
        description="多参考图编辑,默认 I2I (HTTP)",
        capabilities=("i2i",),
        badges=("recommended",),
    ),
    ModelCard(
        id="wan2.5-i2i-preview",
        family="wan2.5-",
        display_name="Wan 2.5 I2I Preview",
        description="通义万相 2.5 I2I 预览版",
        capabilities=("i2i",),
    ),
    ModelCard(
        id="qwen-image-edit",
        family="qwen-image",
        display_name="Qwen-Image Edit",
        description="千问图像编辑模型,支持指令式修改",
        capabilities=("i2i",),
        badges=("new",),
    ),
)


# ── Catalog: I2V / T2V / R2V (video generation) ──────────────────────────

I2V_CARDS: Tuple[ModelCard, ...] = (
    ModelCard(
        id="wan2.6-i2v",
        family="wan2.6-",
        display_name="Wan 2.6 I2V / R2V",
        description="通义万相 2.6,支持 I2V 和参考视频",
        capabilities=("i2v", "r2v", "t2v"),
        params={**_WAN26_PARAMS, "duration": _duration("slider", min=2, max=15, step=1, default=5)},
        badges=("recommended",),
    ),
    ModelCard(
        id="wan2.6-i2v-flash",
        family="wan2.6-",
        display_name="Wan 2.6 I2V Flash",
        description="通义万相 2.6 快速版",
        capabilities=("i2v",),
        params={**_WAN26_PARAMS, "duration": _duration("slider", min=2, max=15, step=1, default=5)},
        badges=("fast",),
    ),
    ModelCard(
        id="wan2.5-i2v-preview",
        family="wan2.5-",
        display_name="Wan 2.5 I2V Preview",
        description="通义万相 2.5 默认 I2V",
        capabilities=("i2v",),
        params={**_WAN25_PARAMS, "duration": _duration("buttons", options=[5, 10], default=5)},
    ),
    ModelCard(
        id="wan2.2-i2v-plus",
        family="wan2.2-",
        display_name="Wan 2.2 I2V Plus",
        description="通义万相 2.2 高质量版",
        capabilities=("i2v",),
        params={**_WAN22_PARAMS, "duration": _duration("fixed", value=5)},
    ),
    ModelCard(
        id="wan2.2-i2v-flash",
        family="wan2.2-",
        display_name="Wan 2.2 I2V Flash",
        description="通义万相 2.2 快速版",
        capabilities=("i2v",),
        params={**_WAN22_PARAMS, "duration": _duration("fixed", value=5)},
        badges=("fast",),
    ),
    ModelCard(
        id="kling-v3",
        family="kling-",
        display_name="Kling v3",
        description="Kling AI 最新模型,擅长人像与运镜",
        capabilities=("i2v", "t2v"),
        provider_key="KLING",
        # DashScope routes use DASHSCOPE_API_KEY; vendor-direct switches via KLING_PROVIDER_MODE.
        params={**_KLING_PARAMS, "duration": _duration("slider", min=3, max=15, step=1, default=5)},
    ),
    ModelCard(
        id="kling-2.1-master",
        family="kling-",
        display_name="Kling 2.1 Master",
        description="Kling 2.1 Master,电影级镜头与多人同框",
        capabilities=("i2v", "t2v"),
        provider_key="KLING",
        params={**_KLING_PARAMS, "duration": _duration("slider", min=3, max=10, step=1, default=5)},
        badges=("premium", "new"),
    ),
    ModelCard(
        id="viduq3-pro",
        family="vidu",
        display_name="Vidu Q3 Pro",
        description="Vidu Q3 高质量版",
        capabilities=("i2v", "t2v"),
        provider_key="VIDU",
        params={**_VIDU_PARAMS, "duration": _duration("slider", min=1, max=16, step=1, default=5)},
    ),
    ModelCard(
        id="viduq3-turbo",
        family="vidu",
        display_name="Vidu Q3 Turbo",
        description="Vidu Q3 快速版",
        capabilities=("i2v", "t2v"),
        provider_key="VIDU",
        params={**_VIDU_PARAMS, "duration": _duration("slider", min=1, max=16, step=1, default=5)},
        badges=("fast",),
    ),
    ModelCard(
        id="pixverse-v4",
        family="pixverse-",
        display_name="Pixverse v4",
        description="Pixverse v4 (DashScope or vendor-direct)",
        capabilities=("i2v", "t2v"),
        provider_key="PIXVERSE",
        params={**_PIXVERSE_PARAMS, "duration": _duration("buttons", options=[5, 8], default=5)},
    ),
    # Vendor-direct only (Doubao/Volcano Engine; not on DashScope yet).
    ModelCard(
        id="doubao-seedance-1.0-pro",
        family="doubao-seedance-",
        display_name="Doubao Seedance 1.0 Pro",
        description="字节豆包 Seedance 1.0 Pro,高质量长镜头",
        capabilities=("i2v", "t2v"),
        provider_key="DOUBAO",
        requires_credentials=("DOUBAO_API_KEY",),
        params={**_SEEDANCE_PARAMS, "duration": _duration("slider", min=5, max=10, step=1, default=5)},
        available=False,
        badges=("preview", "premium"),
    ),
    ModelCard(
        id="hailuo-02",
        family="hailuo-",
        display_name="MiniMax Hailuo 02",
        description="MiniMax 海螺 02,日常向 i2v",
        capabilities=("i2v", "t2v"),
        provider_key="HAILUO",
        requires_credentials=("HAILUO_API_KEY",),
        params={**_HAILUO_PARAMS, "duration": _duration("buttons", options=[6, 10], default=6)},
        available=False,
        badges=("preview",),
    ),
)


# ── Aspect ratios used by the FE Settings page ───────────────────────────

ASPECT_RATIOS: Tuple[Dict[str, str], ...] = (
    {"id": "9:16", "name": "9:16", "description": "竖屏 (576*1024)"},
    {"id": "16:9", "name": "16:9", "description": "横屏 (1024*576)"},
    {"id": "1:1", "name": "1:1", "description": "正方形 (1024*1024)"},
)


# ─────────────────────────────────────────────────────────────────────────
# LLM presets
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LLMPreset:
    """LLM provider preset surfaced in the Settings UI dropdown.

    Selecting a preset auto-fills ``OPENAI_BASE_URL`` and a suggested
    ``OPENAI_MODEL``; the user only has to paste the API key.
    """

    id: str
    provider: str  # value written to LLM_PROVIDER (dashscope / openai)
    display_name: str
    description: str = ""
    base_url: str = ""
    suggested_models: Tuple[str, ...] = ()
    api_key_env: str = "OPENAI_API_KEY"
    docs_url: str = ""
    badges: Tuple[str, ...] = ()


LLM_PRESETS: Tuple[LLMPreset, ...] = (
    LLMPreset(
        id="dashscope-qwen",
        provider="dashscope",
        display_name="阿里云 DashScope (Qwen 系列)",
        description="默认 LLM,使用 DashScope API Key,无需额外配置",
        base_url="",
        suggested_models=("qwen3.5-plus", "qwen3-max", "qwen-plus", "qwen-flash"),
        api_key_env="DASHSCOPE_API_KEY",
        docs_url="https://help.aliyun.com/zh/model-studio/",
        badges=("recommended",),
    ),
    LLMPreset(
        id="openai-gpt",
        provider="openai",
        display_name="OpenAI GPT",
        description="OpenAI 官方,GPT-5 / GPT-4o 系列",
        base_url="https://api.openai.com/v1",
        suggested_models=("gpt-5", "gpt-5-mini", "gpt-4o", "gpt-4o-mini"),
        docs_url="https://platform.openai.com/docs",
        badges=("premium",),
    ),
    LLMPreset(
        id="anthropic-claude",
        provider="openai",
        display_name="Anthropic Claude",
        description="通过 OpenAI 兼容代理调用 Claude(Opus 4.7 / Sonnet 4.6)",
        base_url="https://api.anthropic.com/v1",
        suggested_models=("claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"),
        docs_url="https://docs.anthropic.com/",
        badges=("premium",),
    ),
    LLMPreset(
        id="deepseek",
        provider="openai",
        display_name="DeepSeek",
        description="DeepSeek V3 / R1,推理与代码能力强",
        base_url="https://api.deepseek.com/v1",
        suggested_models=("deepseek-chat", "deepseek-reasoner"),
        docs_url="https://api-docs.deepseek.com/",
        badges=("recommended",),
    ),
    LLMPreset(
        id="moonshot-kimi",
        provider="openai",
        display_name="Moonshot Kimi",
        description="月之暗面 Kimi K2,长上下文",
        base_url="https://api.moonshot.cn/v1",
        suggested_models=("kimi-k2", "moonshot-v1-32k", "moonshot-v1-128k"),
    ),
    LLMPreset(
        id="zhipu-glm",
        provider="openai",
        display_name="智谱 GLM",
        description="智谱清言 GLM-5 系列",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        suggested_models=("glm-5", "glm-4.5", "glm-4-flash"),
    ),
    LLMPreset(
        id="google-gemini",
        provider="openai",
        display_name="Google Gemini",
        description="Gemini 2.5 Pro / Flash,需 OpenAI 兼容代理",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        suggested_models=("gemini-2.5-pro", "gemini-2.5-flash"),
    ),
    LLMPreset(
        id="ollama-local",
        provider="openai",
        display_name="本地 Ollama",
        description="本地部署的开源模型(qwen / llama / deepseek 等)",
        base_url="http://localhost:11434/v1",
        suggested_models=("qwen2.5:72b", "llama3.3:70b", "deepseek-r1:32b"),
        docs_url="https://ollama.com/",
        badges=("open-source",),
    ),
)


# ─────────────────────────────────────────────────────────────────────────
# Public registry API
# ─────────────────────────────────────────────────────────────────────────


class ModelCatalog:
    """Small façade that lets call sites query cards by capability / id."""

    def __init__(
        self,
        cards: Sequence[ModelCard] = (),
        presets: Sequence[LLMPreset] = (),
        aspect_ratios: Sequence[Mapping[str, str]] = (),
    ):
        self._cards: Tuple[ModelCard, ...] = tuple(cards)
        self._presets: Tuple[LLMPreset, ...] = tuple(presets)
        self._aspect_ratios: Tuple[Dict[str, str], ...] = tuple(dict(r) for r in aspect_ratios)

    # — Cards —

    @property
    def cards(self) -> Tuple[ModelCard, ...]:
        return self._cards

    def by_capability(self, capability: str) -> List[ModelCard]:
        cap = capability.strip().lower()
        return [c for c in self._cards if cap in c.capabilities]

    def by_id(self, model_id: str) -> Optional[ModelCard]:
        target = model_id.strip().lower()
        for card in self._cards:
            if card.id.lower() == target:
                return card
        return None

    # — LLM presets —

    @property
    def presets(self) -> Tuple[LLMPreset, ...]:
        return self._presets

    def preset_by_id(self, preset_id: str) -> Optional[LLMPreset]:
        for preset in self._presets:
            if preset.id == preset_id:
                return preset
        return None

    # — Aspect ratios —

    @property
    def aspect_ratios(self) -> Tuple[Dict[str, str], ...]:
        return self._aspect_ratios

    # — Serialization for the REST endpoint —

    def serialize(self, capability: Optional[str] = None) -> Dict[str, object]:
        cards = self.by_capability(capability) if capability else list(self._cards)
        return {
            "cards": [_card_to_dict(c) for c in cards],
            "presets": [asdict(p) for p in self._presets],
            "aspect_ratios": [dict(r) for r in self._aspect_ratios],
        }


def _card_to_dict(card: ModelCard) -> Dict[str, object]:
    payload = asdict(card)
    # Drop empty params dicts to keep the payload tidy on the wire.
    if not payload.get("params"):
        payload.pop("params", None)
    return payload


_DEFAULT_CARDS: Tuple[ModelCard, ...] = (*T2I_CARDS, *I2I_CARDS, *I2V_CARDS)


def get_default_catalog() -> ModelCatalog:
    """Return the default singleton-style catalog used by the REST endpoint."""
    return ModelCatalog(
        cards=_DEFAULT_CARDS,
        presets=LLM_PRESETS,
        aspect_ratios=ASPECT_RATIOS,
    )


__all__ = [
    "ModelCard",
    "LLMPreset",
    "ModelCatalog",
    "T2I_CARDS",
    "I2I_CARDS",
    "I2V_CARDS",
    "ASPECT_RATIOS",
    "LLM_PRESETS",
    "get_default_catalog",
]
