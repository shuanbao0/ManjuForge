"""English (US) backend messages.

Mirrors `src/i18n/locales/zh_cn.py`. Missing keys here fall back to zh-CN.
"""

messages = {
    "errors": {
        # Validation / input
        "import_episodes_out_of_range": "Suggested episode count must be between 1 and 50",
        "import_file_empty": "Uploaded file is empty",
        # LLM
        "llm_api_key_missing": "LLM API key is not configured. Please set the API key in API Configuration and retry.",
        "llm_script_parse_failed": "Failed to parse script: {error}",
        "llm_json_parse_failed": "LLM returned malformed JSON, cannot parse: {error}",
        # Generation
        "generation_failed_check_config": "Generation failed. Please check the API configuration or revise the description and retry.",
        "storyboard_no_frames": "AI storyboard analysis returned no frames. Please retry.",
    },
    # Per-model English descriptions surfaced through `GET /registry/models`.
    # Keys mirror `ModelCard.id`. Update both this dict and `zh_cn.py` when
    # adding a new card.
    "model_descriptions": {
        # ── T2I ────────────────────────────────────────────────────────────
        "wan2.6-t2i": "Wan 2.6, default T2I — balanced quality and speed",
        "wan2.5-t2i-preview": "Wan 2.5 preview",
        "wan2.2-t2i-plus": "Wan 2.2, high quality",
        "wan2.2-t2i-flash": "Wan 2.2, fast generation",
        "qwen-image": "Qwen Image base — strong at Chinese text rendering",
        "qwen-image-plus": "Qwen Image enhanced, native 2K resolution with crisp typography",
        "flux-schnell": "FLUX Chinese-tuned, fast generation",
        "flux-dev": "FLUX high quality, ideal for highly detailed scenes",
        "flux-2-pro": "2026 photorealism benchmark, $0.03/MP, high fidelity with 200-word prompts",
        "flux-2-max": "FLUX.2 flagship, Elo 1201 — strongest photorealism in the industry",
        "flux-2-flash": "FLUX.2 fast tier, lower latency",
        "doubao-seedream-5.0": "ByteDance Seedream 5.0 with built-in real-time web search; best-in-class CN/EN poster generation",
        "doubao-seedream-4.5": "Seedream 4.5, $0.04/image — industry-leading price/performance",
        "gemini-3.1-flash-image": "Up to 14 reference images, $0.084/image — best price/performance for character consistency",
        "nano-banana-pro": "Google native 4K output, Elo 1220 — most complete tooling",
        "nano-banana-2": "Nano Banana 2, Elo 1261, $0.08/image",
        "gpt-image-2": "OpenAI flagship image model, Elo 1338 (#1 ranked)",
        "gpt-image-1.5": "GPT Image 1.5, Elo 1272, flexible tiered pricing",
        "gpt-image-1": "OpenAI general-purpose image, Images / Edits API",
        # ── I2I ────────────────────────────────────────────────────────────
        "wan2.6-image": "Multi-reference image editing, default I2I (HTTP)",
        "wan2.5-i2i-preview": "Wan 2.5 I2I preview",
        "qwen-image-edit": "Qwen Image edit — supports instruction-driven modifications",
        "gemini-3.1-flash-image-i2i": "Up to 14 reference images, best price/performance for character consistency ($0.084/image)",
        "flux-2-pro-i2i": "Up to 10 reference images — best for character / product / style preservation",
        # ── I2V / T2V / R2V ────────────────────────────────────────────────
        "wan2.6-i2v": "Wan 2.6 — supports I2V and reference videos",
        "wan2.6-i2v-flash": "Wan 2.6 fast tier",
        "wan2.5-i2v-preview": "Wan 2.5 default I2V",
        "wan2.2-i2v-plus": "Wan 2.2 high-quality tier",
        "wan2.2-i2v-flash": "Wan 2.2 fast tier",
        "kling-v3": "Kling AI latest model — strong portraits and camera moves",
        "kling-2.1-master": "Kling 2.1 Master — cinematic shots and multi-character scenes",
        "viduq3-pro": "Vidu Q3 high-quality tier",
        "viduq3-turbo": "Vidu Q3 fast tier",
        "pixverse-v4": "Pixverse v4 (DashScope or vendor-direct)",
        "doubao-seedance-1.0-pro": "ByteDance Doubao Seedance 1.0 Pro — high-quality long takes",
        "hailuo-02": "MiniMax Hailuo 02, everyday-use I2V",
        "kling-v3.0": "Kling 3.0 — multi-shot narratives + subject consistency, ~$0.10/sec",
        "doubao-seedance-2.0-pro": "Released 2026-02 — joint audio/video generation, lip-sync in 8+ languages, multi-shot narratives",
        "doubao-seedance-2.0": "Seedance 2.0 standard — top scores in creator blind tests",
        "doubao-seedance-1.5-pro": "Seedance 1.5 Pro — stable production tier",
        "veo-3.1": "2026 overall #1 — native 4K + native audio, $0.15/sec (fast tier)",
        "veo-3.1-fast": "Veo 3.1 fast tier, lower latency",
        "fal-veo-3.1": "Google Veo 3.1 via fal.ai",
        "fal-kling-3.0": "Kling 3.0 via fal.ai",
        "fal-seedance-1.5-pro": "ByteDance Seedance 1.5 Pro via fal.ai",
        # ── TTS ────────────────────────────────────────────────────────────
        "cosyvoice-v3-plus": "Alibaba CosyVoice v3 Plus — stable Chinese emotional delivery",
        "cosyvoice-v3-flash": "CosyVoice fast tier",
        "speech-2.6-hd": "MiniMax HD — 40+ languages, strong emotional range",
        "speech-2.6-turbo": "MiniMax fast tier — low latency",
        "eleven_turbo_v2_5": "3x speedup, 32 languages — industry benchmark for emotional depth",
        "eleven_multilingual_v2": "Top pick for multilingual long-form narration; best-in-class voice cloning quality",
        "eleven_v3": "ElevenLabs v3 latest — dramatic character voiceover",
        "fish-s2": "80+ languages, 15-second cloning, Elo #1 — about 1/10 the price of ElevenLabs",
        "fish-s1": "Fish Audio S1 — stable production tier",
        "sonic-3": "~40-90ms time-to-first-byte — best for real-time voice agents",
        "sonic-2": "Cartesia Sonic 2 — stable production tier",
    },
    # Per-LLM-preset English descriptions surfaced through `GET /registry/llm-presets`.
    "llm_preset_descriptions": {
        "dashscope-qwen": "Default LLM — uses your DashScope API key, no extra setup required",
        "openai-gpt": "OpenAI official — GPT-5 / GPT-4o family",
        "anthropic-claude": "Claude (Opus 4.7 / Sonnet 4.6) via OpenAI-compatible proxy",
        "deepseek": "DeepSeek V3 / R1 — strong reasoning and code abilities",
        "moonshot-kimi": "Moonshot Kimi K2 — long context",
        "zhipu-glm": "Zhipu GLM-5 family",
        "google-gemini": "Gemini 2.5 Pro / Flash — requires OpenAI-compatible proxy",
        "ollama-local": "Locally-hosted open-source models (qwen / llama / deepseek, ...)",
    },
    # Per-LLM-preset display names (English).
    "llm_preset_display_names": {
        "dashscope-qwen": "Alibaba DashScope (Qwen series)",
        "ollama-local": "Local Ollama",
    },
}
