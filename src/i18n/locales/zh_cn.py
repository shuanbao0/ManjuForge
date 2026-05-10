"""Chinese (Simplified) backend messages.

Mirrors the structure used by the frontend's locale files. Keep keys in sync
with `src/i18n/locales/en_us.py` — every key here should have an English
counterpart (and vice versa).
"""

messages = {
    "errors": {
        # Validation / input
        "import_episodes_out_of_range": "建议集数应在 1-50 之间",
        "import_file_empty": "文件内容为空",
        # LLM
        "llm_api_key_missing": "LLM API Key 未配置。请在 API 配置中设置对应的 API Key 后重试。",
        "llm_script_parse_failed": "剧本解析失败：{error}",
        "llm_json_parse_failed": "LLM 返回的数据格式错误，无法解析 JSON：{error}",
        # Generation
        "generation_failed_check_config": "生成失败，请检查 API 配置或修改描述内容后重试。",
        "storyboard_no_frames": "AI 分镜分析未返回任何帧数据，请重试。",
    },
    # Per-model Chinese descriptions surfaced through `GET /registry/models`.
    # Values mirror the original `description=` strings in
    # `src/utils/model_catalog.py` — keep both in sync when adding cards.
    "model_descriptions": {
        # ── T2I ────────────────────────────────────────────────────────────
        "wan2.6-t2i": "通义万相 2.6,默认 T2I,质量与速度均衡",
        "wan2.5-t2i-preview": "通义万相 2.5 预览版",
        "wan2.2-t2i-plus": "通义万相 2.2,高质量",
        "wan2.2-t2i-flash": "通义万相 2.2,快速生成",
        "qwen-image": "千问图像基础模型,擅长中文文字渲染",
        "qwen-image-plus": "千问图像增强版,2K 原生分辨率,精细排版",
        "flux-schnell": "FLUX 中文优化版,快速生成",
        "flux-dev": "FLUX 高质量版,适合高细节场景",
        "flux-2-pro": "2026 写实摄影基准,$0.03/MP,200 词长 prompt 高保真",
        "flux-2-max": "FLUX.2 顶配,Elo 1201,业内最强写实",
        "flux-2-flash": "FLUX.2 快速档,延迟更低",
        "doubao-seedream-5.0": "ByteDance Seedream 5.0,集成实时联网搜索,中英文海报最强",
        "doubao-seedream-4.5": "Seedream 4.5,$0.04/张,业内主流性价比之选",
        "gemini-3.1-flash-image": "多参考图最多 14 张,$0.084/张,角色一致性最佳性价比",
        "nano-banana-pro": "Google 原生 4K 输出,Elo 1220,工具完整度最高",
        "nano-banana-2": "Nano Banana 2,Elo 1261,$0.08/张",
        "gpt-image-2": "OpenAI 旗舰图像,Elo 1338(榜首)",
        "gpt-image-1.5": "GPT Image 1.5,Elo 1272,分档定价灵活",
        "gpt-image-1": "OpenAI 通用图像,Images / Edits API",
        # ── I2I ────────────────────────────────────────────────────────────
        "wan2.6-image": "多参考图编辑,默认 I2I (HTTP)",
        "wan2.5-i2i-preview": "通义万相 2.5 I2I 预览版",
        "qwen-image-edit": "千问图像编辑模型,支持指令式修改",
        "gemini-3.1-flash-image-i2i": "多达 14 张参考图,角色一致性最强性价比($0.084/张)",
        "flux-2-pro-i2i": "支持最多 10 张参考图,角色 / 商品 / 风格保持最佳",
        # ── I2V / T2V / R2V ────────────────────────────────────────────────
        "wan2.6-i2v": "通义万相 2.6,支持 I2V 和参考视频",
        "wan2.6-i2v-flash": "通义万相 2.6 快速版",
        "wan2.5-i2v-preview": "通义万相 2.5 默认 I2V",
        "wan2.2-i2v-plus": "通义万相 2.2 高质量版",
        "wan2.2-i2v-flash": "通义万相 2.2 快速版",
        "kling-v3": "Kling AI 最新模型,擅长人像与运镜",
        "kling-2.1-master": "Kling 2.1 Master,电影级镜头与多人同框",
        "viduq3-pro": "Vidu Q3 高质量版",
        "viduq3-turbo": "Vidu Q3 快速版",
        "pixverse-v4": "Pixverse v4 (DashScope or vendor-direct)",
        "doubao-seedance-1.0-pro": "字节豆包 Seedance 1.0 Pro,高质量长镜头",
        "hailuo-02": "MiniMax 海螺 02,日常向 i2v",
        "kling-v3.0": "Kling 3.0,多镜头叙事 + 主体一致性,~$0.10/秒",
        "doubao-seedance-2.0-pro": "2026-02 发布,音视频联合生成,8+ 语言唇音同步,多镜头叙事",
        "doubao-seedance-2.0": "Seedance 2.0 标准版,创作者盲测高分",
        "doubao-seedance-1.5-pro": "Seedance 1.5 Pro,稳定生产档",
        "veo-3.1": "2026 综合第一,原生 4K + 原生音频,$0.15/秒(fast 档)",
        "veo-3.1-fast": "Veo 3.1 快速档,延迟更低",
        "fal-veo-3.1": "通过 fal.ai 调用 Google Veo 3.1",
        "fal-kling-3.0": "通过 fal.ai 调用 Kling 3.0",
        "fal-seedance-1.5-pro": "通过 fal.ai 调用 ByteDance Seedance 1.5 Pro",
        # ── TTS ────────────────────────────────────────────────────────────
        "cosyvoice-v3-plus": "阿里 CosyVoice v3 Plus,中文情感表达稳定",
        "cosyvoice-v3-flash": "CosyVoice 快速档",
        "speech-2.6-hd": "MiniMax 高清版,40+ 语言,情感表达强",
        "speech-2.6-turbo": "MiniMax 快速档,低延迟",
        "eleven_turbo_v2_5": "3× 加速,32 语言,情感深度业内基准",
        "eleven_multilingual_v2": "多语言长篇朗读首选,音色克隆质量最高",
        "eleven_v3": "ElevenLabs v3 最新模型,戏剧化角色配音",
        "fish-s2": "80+ 语言,15 秒克隆,Elo #1,价格约 ElevenLabs 1/10",
        "fish-s1": "Fish Audio S1,稳定生产档",
        "sonic-3": "首字节 ~40-90ms,语音 Agent 实时对话最佳",
        "sonic-2": "Cartesia Sonic 2,稳定生产档",
    },
    # Per-LLM-preset Chinese descriptions surfaced through `GET /registry/llm-presets`.
    "llm_preset_descriptions": {
        "dashscope-qwen": "默认 LLM,使用 DashScope API Key,无需额外配置",
        "openai-gpt": "OpenAI 官方,GPT-5 / GPT-4o 系列",
        "anthropic-claude": "通过 OpenAI 兼容代理调用 Claude(Opus 4.7 / Sonnet 4.6)",
        "deepseek": "DeepSeek V3 / R1,推理与代码能力强",
        "moonshot-kimi": "月之暗面 Kimi K2,长上下文",
        "zhipu-glm": "智谱清言 GLM-5 系列",
        "google-gemini": "Gemini 2.5 Pro / Flash,需 OpenAI 兼容代理",
        "ollama-local": "本地部署的开源模型(qwen / llama / deepseek 等)",
    },
    # Per-LLM-preset display names (Chinese).
    "llm_preset_display_names": {
        "dashscope-qwen": "阿里云 DashScope (Qwen 系列)",
        "ollama-local": "本地 Ollama",
    },
}
