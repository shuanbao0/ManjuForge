"use client";

import { useEffect, useState } from "react";
import { registry, type VendorConnectorDTO, type ModelCapability } from "@/lib/api";

let cachedPromise: Promise<{ connectors: VendorConnectorDTO[] }> | null = null;

function fetchOnce() {
    if (!cachedPromise) {
        cachedPromise = registry.getVendors().catch((err) => {
            cachedPromise = null;
            throw err;
        });
    }
    return cachedPromise;
}

export function invalidateVendorConnectors() {
    cachedPromise = null;
}

export interface VendorConnectorsState {
    connectors: VendorConnectorDTO[];
    loading: boolean;
    error: string | null;
}

// Hardcoded mirror of src/utils/vendor_connectors.py, used as a fallback so
// the Settings page renders something usable even if /registry/vendors is
// unreachable (e.g. an outdated backend that doesn't have the endpoint yet).
// Keep in sync with the Python registry — the backend stays canonical.
const FALLBACK: VendorConnectorDTO[] = [
    {
        id: "dashscope",
        display_name: "阿里云 DashScope",
        description: "百炼平台,默认 LLM/T2I/I2I/I2V 后端,支持 Qwen / Wan / FLUX 等",
        capabilities: ["llm", "t2i", "i2i", "i2v", "t2v", "r2v", "tts"],
        common_fields: [
            { key: "DASHSCOPE_API_KEY", label: "API Key", placeholder: "sk-...", secret: true, help_text: "", required: true },
            { key: "DASHSCOPE_BASE_URL", label: "Base URL", placeholder: "https://dashscope.aliyuncs.com", secret: false, help_text: "海外部署可改为 https://dashscope-intl.aliyuncs.com", required: false },
        ],
        modes: [],
        mode_env_key: null,
        family_prefixes: ["wan2.7-", "wan2.6-", "wan2.5-", "wan2.2-", "qwen-image", "flux-"],
        docs_url: "https://help.aliyun.com/zh/model-studio/",
        badges: ["recommended"],
        accent: "amber",
    },
    {
        id: "kling",
        display_name: "Kling AI",
        description: "可灵 AI,人像与运镜表现优秀",
        capabilities: ["i2v", "t2v"],
        common_fields: [],
        modes: [
            { id: "dashscope", label: "DashScope", description: "通过百炼路由,复用 DashScope API Key", fields: [] },
            {
                id: "vendor", label: "Vendor Direct", description: "直连厂商 API,需要独立凭证",
                fields: [
                    { key: "KLING_ACCESS_KEY", label: "Access Key", placeholder: "Kling Access Key", secret: true, help_text: "", required: true },
                    { key: "KLING_SECRET_KEY", label: "Secret Key", placeholder: "Kling Secret Key", secret: true, help_text: "", required: true },
                    { key: "KLING_BASE_URL", label: "Base URL", placeholder: "https://api-beijing.klingai.com/v1", secret: false, help_text: "留空使用默认。海外部署可填 https://api.klingai.com/v1", required: false },
                ],
            },
        ],
        mode_env_key: "KLING_PROVIDER_MODE",
        family_prefixes: ["kling-"],
        docs_url: "https://app.klingai.com/cn/dev/document-api",
        badges: [],
        accent: "purple",
    },
    {
        id: "vidu",
        display_name: "Vidu",
        description: "Vidu Q3 Pro / Turbo,支持音视频联动生成",
        capabilities: ["i2v", "t2v"],
        common_fields: [],
        modes: [
            { id: "dashscope", label: "DashScope", description: "通过百炼路由,复用 DashScope API Key", fields: [] },
            {
                id: "vendor", label: "Vendor Direct", description: "直连厂商 API,需要独立凭证",
                fields: [
                    { key: "VIDU_API_KEY", label: "API Key", placeholder: "Vidu API Key", secret: true, help_text: "", required: true },
                    { key: "VIDU_BASE_URL", label: "Base URL", placeholder: "https://api.vidu.cn/ent/v2", secret: false, help_text: "", required: false },
                ],
            },
        ],
        mode_env_key: "VIDU_PROVIDER_MODE",
        family_prefixes: ["vidu", "viduq2", "viduq3"],
        docs_url: "https://platform.vidu.com/",
        badges: [],
        accent: "cyan",
    },
    {
        id: "pixverse",
        display_name: "Pixverse",
        description: "Pixverse v4,适合短动画与角色表演",
        capabilities: ["i2v", "t2v"],
        common_fields: [],
        modes: [
            { id: "dashscope", label: "DashScope", description: "通过百炼路由,复用 DashScope API Key", fields: [] },
            {
                id: "vendor", label: "Vendor Direct", description: "直连厂商 API,需要独立凭证",
                fields: [
                    { key: "PIXVERSE_API_KEY", label: "API Key", placeholder: "Pixverse API Key", secret: true, help_text: "", required: true },
                    { key: "PIXVERSE_BASE_URL", label: "Base URL", placeholder: "https://app-api.pixverse.ai/openapi/v2", secret: false, help_text: "", required: false },
                ],
            },
        ],
        mode_env_key: "PIXVERSE_PROVIDER_MODE",
        family_prefixes: ["pixverse-"],
        docs_url: "https://platform.pixverse.ai/",
        badges: [],
        accent: "rose",
    },
    {
        id: "doubao",
        display_name: "字节豆包 Seedance",
        description: "ByteDance Seedance 1.0 Pro,长镜头与电影级运动",
        capabilities: ["i2v", "t2v"],
        common_fields: [
            { key: "DOUBAO_API_KEY", label: "API Key", placeholder: "Volcano Engine API Key", secret: true, help_text: "", required: true },
            { key: "DOUBAO_BASE_URL", label: "Base URL", placeholder: "https://ark.cn-beijing.volces.com/api/v3", secret: false, help_text: "", required: false },
        ],
        modes: [],
        mode_env_key: null,
        family_prefixes: ["doubao-seedance-"],
        docs_url: "https://www.volcengine.com/docs/82379",
        badges: ["preview", "premium"],
        accent: "orange",
    },
    {
        id: "hailuo",
        display_name: "MiniMax Hailuo 海螺",
        description: "MiniMax 海螺 02,日常向 i2v / t2v",
        capabilities: ["i2v", "t2v"],
        common_fields: [
            { key: "HAILUO_API_KEY", label: "API Key", placeholder: "Hailuo API Key", secret: true, help_text: "", required: true },
            { key: "HAILUO_BASE_URL", label: "Base URL", placeholder: "https://api.minimax.chat/v1", secret: false, help_text: "", required: false },
        ],
        modes: [],
        mode_env_key: null,
        family_prefixes: ["hailuo-"],
        docs_url: "https://platform.minimaxi.com/",
        badges: ["preview"],
        accent: "sky",
    },
];

/**
 * Fetch the canonical vendor connector list (DashScope / Kling / Vidu / ...).
 * The Settings UI renders one VendorCard per connector — adding a new vendor
 * to ``src/utils/vendor_connectors.py`` flows through automatically.
 */
function filterByCapability(list: VendorConnectorDTO[], capability?: ModelCapability) {
    return capability ? list.filter((c) => c.capabilities.includes(capability)) : list;
}

export function useVendorConnectors(capability?: ModelCapability): VendorConnectorsState {
    const [state, setState] = useState<VendorConnectorsState>({
        // Show fallback immediately so the cards render on first paint and
        // never collapse to nothing while waiting for the network.
        connectors: filterByCapability(FALLBACK, capability),
        loading: true,
        error: null,
    });

    useEffect(() => {
        let alive = true;
        fetchOnce()
            .then((res) => {
                if (!alive) return;
                setState({
                    connectors: filterByCapability(res.connectors, capability),
                    loading: false,
                    error: null,
                });
            })
            .catch((err: unknown) => {
                if (!alive) return;
                // Keep the FALLBACK rendering so the user can still configure;
                // surface the error so the UI can show a banner pointing at
                // the likely cause (outdated backend / 401).
                setState({
                    connectors: filterByCapability(FALLBACK, capability),
                    loading: false,
                    error: err instanceof Error ? err.message : String(err),
                });
            });
        return () => {
            alive = false;
        };
    }, [capability]);

    return state;
}
