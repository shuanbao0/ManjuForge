"use client";

import { useEffect, useState } from "react";
import {
    registry,
    type ModelCardDTO,
    type LLMPresetDTO,
    type AspectRatioDTO,
    type ModelCapability,
    type ModelCatalogDTO,
} from "@/lib/api";
import {
    T2I_MODELS as FALLBACK_T2I,
    I2I_MODELS as FALLBACK_I2I,
    I2V_MODELS as FALLBACK_I2V,
    ASPECT_RATIOS as FALLBACK_ASPECT_RATIOS,
} from "@/store/projectStore";

// ─────────────────────────────────────────────────────────────────────────
// Why this hook?
//
// The legacy `T2I_MODELS` / `I2I_MODELS` / `I2V_MODELS` arrays in
// `projectStore.ts` were the single hardcoded source. Every time the team
// added a model, both the backend (provider routing) AND the frontend
// (display dropdown) had to be edited in lockstep, which drifted in practice.
//
// Now the backend `/registry/models` endpoint is canonical. This hook fetches
// it once per mount and caches the response in module state so subsequent
// callers reuse it. The hardcoded arrays still live in `projectStore.ts` so
// the UI renders something reasonable on first paint / when offline.
//
// Adding a new model = one entry in `src/utils/model_catalog.py`. Done.
// ─────────────────────────────────────────────────────────────────────────

let cachedPromise: Promise<ModelCatalogDTO> | null = null;

function fetchOnce(): Promise<ModelCatalogDTO> {
    if (!cachedPromise) {
        cachedPromise = registry.getCatalog().catch((err) => {
            // Reset on failure so the next consumer retries instead of being
            // stuck with a rejected promise forever.
            cachedPromise = null;
            throw err;
        });
    }
    return cachedPromise;
}

/** Reset the in-memory cache (useful after admin updates the registry). */
export function invalidateModelCatalog() {
    cachedPromise = null;
}

export interface ModelCatalogState {
    cards: ModelCardDTO[];
    presets: LLMPresetDTO[];
    aspectRatios: AspectRatioDTO[];
    loading: boolean;
    error: string | null;
}

const FALLBACK_CARDS: ModelCardDTO[] = [
    ...FALLBACK_T2I.map(legacyToCard("t2i")),
    ...FALLBACK_I2I.map(legacyToCard("i2i")),
    ...FALLBACK_I2V.map((m) => legacyToCard("i2v")(m)),
];

const FALLBACK_ASPECT: AspectRatioDTO[] = FALLBACK_ASPECT_RATIOS.map((r) => ({
    id: r.id,
    name: r.name,
    description: r.description,
}));

// Hardcoded mirror of LLM_PRESETS in src/utils/model_catalog.py — keeps the
// LLM Provider chooser populated when /registry/models is unreachable.
const FALLBACK_PRESETS: LLMPresetDTO[] = [
    { id: "dashscope-qwen", provider: "dashscope", display_name: "阿里云 DashScope (Qwen 系列)",
      description: "默认 LLM,使用 DashScope API Key,无需额外配置",
      base_url: "", suggested_models: ["qwen3.5-plus", "qwen3-max", "qwen-plus", "qwen-flash"],
      api_key_env: "DASHSCOPE_API_KEY", docs_url: "https://help.aliyun.com/zh/model-studio/", badges: ["recommended"] },
    { id: "openai-gpt", provider: "openai", display_name: "OpenAI GPT",
      description: "OpenAI 官方,GPT-5 / GPT-4o 系列",
      base_url: "https://api.openai.com/v1", suggested_models: ["gpt-5", "gpt-5-mini", "gpt-4o", "gpt-4o-mini"],
      api_key_env: "OPENAI_API_KEY", docs_url: "https://platform.openai.com/docs", badges: ["premium"] },
    { id: "anthropic-claude", provider: "openai", display_name: "Anthropic Claude",
      description: "通过 OpenAI 兼容代理调用 Claude(Opus 4.7 / Sonnet 4.6)",
      base_url: "https://api.anthropic.com/v1", suggested_models: ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
      api_key_env: "OPENAI_API_KEY", docs_url: "https://docs.anthropic.com/", badges: ["premium"] },
    { id: "deepseek", provider: "openai", display_name: "DeepSeek",
      description: "DeepSeek V3 / R1,推理与代码能力强",
      base_url: "https://api.deepseek.com/v1", suggested_models: ["deepseek-chat", "deepseek-reasoner"],
      api_key_env: "OPENAI_API_KEY", docs_url: "https://api-docs.deepseek.com/", badges: ["recommended"] },
    { id: "moonshot-kimi", provider: "openai", display_name: "Moonshot Kimi",
      description: "月之暗面 Kimi K2,长上下文",
      base_url: "https://api.moonshot.cn/v1", suggested_models: ["kimi-k2", "moonshot-v1-32k", "moonshot-v1-128k"],
      api_key_env: "OPENAI_API_KEY", docs_url: "", badges: [] },
    { id: "zhipu-glm", provider: "openai", display_name: "智谱 GLM",
      description: "智谱清言 GLM-5 系列",
      base_url: "https://open.bigmodel.cn/api/paas/v4", suggested_models: ["glm-5", "glm-4.5", "glm-4-flash"],
      api_key_env: "OPENAI_API_KEY", docs_url: "", badges: [] },
    { id: "google-gemini", provider: "openai", display_name: "Google Gemini",
      description: "Gemini 2.5 Pro / Flash,需 OpenAI 兼容代理",
      base_url: "https://generativelanguage.googleapis.com/v1beta/openai", suggested_models: ["gemini-2.5-pro", "gemini-2.5-flash"],
      api_key_env: "OPENAI_API_KEY", docs_url: "", badges: [] },
    { id: "ollama-local", provider: "openai", display_name: "本地 Ollama",
      description: "本地部署的开源模型(qwen / llama / deepseek 等)",
      base_url: "http://localhost:11434/v1", suggested_models: ["qwen2.5:72b", "llama3.3:70b", "deepseek-r1:32b"],
      api_key_env: "OPENAI_API_KEY", docs_url: "https://ollama.com/", badges: ["open-source"] },
];

function legacyToCard(capability: ModelCapability) {
    return (m: { id: string; name: string; description: string }): ModelCardDTO => ({
        id: m.id,
        family: m.id.split(/[-]/)[0],
        display_name: m.name,
        description: m.description,
        capabilities: [capability],
        provider_key: "DASHSCOPE",
        requires_credentials: ["DASHSCOPE_API_KEY"],
        available: true,
        badges: [],
    });
}

/**
 * Fetch the full model catalog with stable fallbacks.
 *
 * Returns immediately with hardcoded fallbacks so consumers can render
 * dropdowns without waiting; replaces them once the backend response lands.
 */
export function useModelCatalog(): ModelCatalogState {
    const [state, setState] = useState<ModelCatalogState>({
        cards: FALLBACK_CARDS,
        presets: FALLBACK_PRESETS,
        aspectRatios: FALLBACK_ASPECT,
        loading: true,
        error: null,
    });

    useEffect(() => {
        let alive = true;
        fetchOnce()
            .then((catalog) => {
                if (!alive) return;
                setState({
                    cards: catalog.cards.length ? catalog.cards : FALLBACK_CARDS,
                    presets: catalog.presets.length ? catalog.presets : FALLBACK_PRESETS,
                    aspectRatios: catalog.aspect_ratios.length ? catalog.aspect_ratios : FALLBACK_ASPECT,
                    loading: false,
                    error: null,
                });
            })
            .catch((err: unknown) => {
                if (!alive) return;
                // Keep the fallback data so the UI never goes blank; expose
                // the error so the page can show a banner with a fix hint.
                setState({
                    cards: FALLBACK_CARDS,
                    presets: FALLBACK_PRESETS,
                    aspectRatios: FALLBACK_ASPECT,
                    loading: false,
                    error: err instanceof Error ? err.message : String(err),
                });
            });
        return () => {
            alive = false;
        };
    }, []);

    return state;
}

/** Filter the catalog by a single capability (t2i / i2i / i2v / ...). */
export function useModelsByCapability(capability: ModelCapability) {
    const { cards, loading, error } = useModelCatalog();
    return {
        models: cards.filter((c) => c.capabilities.includes(capability)),
        loading,
        error,
    };
}
