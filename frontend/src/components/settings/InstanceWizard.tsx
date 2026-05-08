"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, X, Eye, EyeOff } from "lucide-react";
import {
    type InstanceTypeId,
    type ModelInstanceOut,
    type ModelInstanceCreate,
    type ModelInstanceUpdate,
} from "@/lib/api";

// ─────────────────────────────────────────────────────────────────────────
// Vendor catalog (frontend mirror; the backend is canonical via
// /registry/vendors but the wizard is fast-loading and the same metadata
// powers other paths too).
//
// To add a new vendor: append to VENDORS, ensure src/utils/vendor_connectors.py
// has the matching entry, and src/utils/model_catalog.py has the model ids.
// ─────────────────────────────────────────────────────────────────────────

interface VendorMeta {
    id: string;
    label: string;
    capabilities: InstanceTypeId[];
    suggested_models: string[];
    default_base_url: string;
    credential_keys: { key: string; label: string }[];
    docs_url?: string;
}

const VENDORS: VendorMeta[] = [
    {
        id: "dashscope",
        label: "阿里云 DashScope",
        capabilities: ["llm", "t2i", "i2i", "i2v", "t2v", "r2v", "tts"],
        suggested_models: [
            "qwen3.5-plus", "qwen3-max", "qwen-plus", "qwen-flash",
            "wan2.6-t2i", "wan2.6-image", "wan2.6-i2v", "wan2.5-t2i-preview",
            "wan2.5-i2i-preview", "wan2.5-i2v-preview",
            "qwen-image", "qwen-image-plus", "flux-schnell", "flux-dev",
            "cosyvoice-v3-flash", "cosyvoice-v3-plus",
        ],
        default_base_url: "https://dashscope.aliyuncs.com",
        credential_keys: [{ key: "DASHSCOPE_API_KEY", label: "API Key" }],
        docs_url: "https://help.aliyun.com/zh/model-studio/",
    },
    {
        id: "openai",
        label: "OpenAI",
        capabilities: ["llm"],
        suggested_models: ["gpt-5", "gpt-5-mini", "gpt-4o", "gpt-4o-mini", "o3-mini"],
        default_base_url: "https://api.openai.com/v1",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key" }],
        docs_url: "https://platform.openai.com/docs",
    },
    {
        id: "anthropic",
        label: "Anthropic Claude",
        capabilities: ["llm"],
        suggested_models: ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
        default_base_url: "https://api.anthropic.com/v1",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key" }],
        docs_url: "https://docs.anthropic.com/",
    },
    {
        id: "deepseek",
        label: "DeepSeek",
        capabilities: ["llm"],
        suggested_models: ["deepseek-chat", "deepseek-reasoner"],
        default_base_url: "https://api.deepseek.com/v1",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key" }],
        docs_url: "https://api-docs.deepseek.com/",
    },
    {
        id: "moonshot",
        label: "Moonshot Kimi",
        capabilities: ["llm"],
        suggested_models: ["kimi-k2", "moonshot-v1-32k", "moonshot-v1-128k"],
        default_base_url: "https://api.moonshot.cn/v1",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key" }],
    },
    {
        id: "minimax",
        label: "MiniMax (Token Plan · LLM)",
        capabilities: ["llm"],
        suggested_models: [
            "MiniMax-M2.7",
            "MiniMax-M2",
            "MiniMax-Text-01",
            "abab6.5s-chat",
        ],
        // 国内官方域名(注意是 minimaxi.com,不是 minimax.io / minimax.chat)
        // 海外用户改用 https://api.minimax.io/v1
        default_base_url: "https://api.minimaxi.com/v1",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key" }],
        docs_url: "https://platform.minimaxi.com/",
    },
    {
        id: "zhipu",
        label: "智谱 GLM",
        capabilities: ["llm"],
        suggested_models: ["glm-5", "glm-4.5", "glm-4-flash"],
        default_base_url: "https://open.bigmodel.cn/api/paas/v4",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key" }],
    },
    {
        id: "google",
        label: "Google Gemini",
        capabilities: ["llm"],
        suggested_models: ["gemini-2.5-pro", "gemini-2.5-flash"],
        default_base_url: "https://generativelanguage.googleapis.com/v1beta/openai",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key" }],
    },
    {
        id: "ollama",
        label: "本地 Ollama",
        capabilities: ["llm"],
        suggested_models: ["qwen2.5:72b", "llama3.3:70b", "deepseek-r1:32b"],
        default_base_url: "http://localhost:11434/v1",
        credential_keys: [{ key: "OPENAI_API_KEY", label: "API Key (一般填 ollama)" }],
        docs_url: "https://ollama.com/",
    },
    {
        id: "kling",
        label: "Kling AI (vendor-direct)",
        capabilities: ["i2v", "t2v"],
        suggested_models: ["kling-v3", "kling-2.1-master"],
        default_base_url: "https://api-beijing.klingai.com/v1",
        credential_keys: [
            { key: "KLING_ACCESS_KEY", label: "Access Key" },
            { key: "KLING_SECRET_KEY", label: "Secret Key" },
        ],
    },
    {
        id: "vidu",
        label: "Vidu (vendor-direct)",
        capabilities: ["i2v", "t2v"],
        suggested_models: ["viduq3-pro", "viduq3-turbo"],
        default_base_url: "https://api.vidu.cn/ent/v2",
        credential_keys: [{ key: "VIDU_API_KEY", label: "API Key" }],
    },
    {
        id: "pixverse",
        label: "Pixverse (vendor-direct)",
        capabilities: ["i2v", "t2v"],
        suggested_models: ["pixverse-v4"],
        default_base_url: "https://app-api.pixverse.ai/openapi/v2",
        credential_keys: [{ key: "PIXVERSE_API_KEY", label: "API Key" }],
    },
    {
        id: "doubao",
        label: "字节豆包 Seedance",
        capabilities: ["i2v", "t2v"],
        suggested_models: ["doubao-seedance-1.0-pro"],
        default_base_url: "https://ark.cn-beijing.volces.com/api/v3",
        credential_keys: [{ key: "DOUBAO_API_KEY", label: "API Key" }],
    },
    {
        id: "hailuo",
        label: "MiniMax 海螺 (Token Plan · Video)",
        capabilities: ["i2v", "t2v"],
        // Token plan 实际可用的视频模型 IDs(国际版用 minimax.io,国内 minimaxi.com)
        suggested_models: [
            "hailuo-2.3-fast-768p",
            "hailuo-2.3-768p",
            "hailuo-2.3",
            "hailuo-02",
        ],
        default_base_url: "https://api.minimaxi.com/v1",
        credential_keys: [{ key: "HAILUO_API_KEY", label: "API Key" }],
        docs_url: "https://platform.minimaxi.com/",
    },
];

const TYPE_LABELS: Record<InstanceTypeId, string> = {
    llm: "LLM (剧本/润色)",
    t2i: "Text-to-Image",
    i2i: "Image-to-Image (storyboard)",
    i2v: "Image-to-Video",
    t2v: "Text-to-Video",
    r2v: "Reference-to-Video",
    tts: "Text-to-Speech",
};


export interface InstanceWizardProps {
    initialType?: InstanceTypeId;
    /** When provided, the wizard runs in "edit" mode for that instance. */
    editing?: ModelInstanceOut | null;
    onClose: () => void;
    onSave: (
        payload: ModelInstanceCreate | ModelInstanceUpdate,
        editingId: string | null,
    ) => Promise<void>;
}


export function InstanceWizard({ initialType, editing, onClose, onSave }: InstanceWizardProps) {
    const isEdit = !!editing;
    // When the user opened the wizard from a specific type section (e.g.
    // "添加 LLM 实例"), skip step 1 — type is already known.
    const [step, setStep] = useState<1 | 2 | 3>(isEdit ? 3 : initialType ? 2 : 1);
    const [type, setType] = useState<InstanceTypeId>(initialType ?? "llm");
    const [vendorId, setVendorId] = useState<string>(editing?.vendor_id ?? "");
    const [modelName, setModelName] = useState<string>(editing?.model_name ?? "");
    const [displayName, setDisplayName] = useState<string>(editing?.display_name ?? "");
    const [baseUrl, setBaseUrl] = useState<string>(editing?.base_url ?? "");
    const [credentials, setCredentials] = useState<Record<string, string>>({});
    const [revealed, setRevealed] = useState<Record<string, boolean>>({});
    const [setAsDefault, setSetAsDefault] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState("");

    const eligibleVendors = useMemo(() => VENDORS.filter((v) => v.capabilities.includes(type)), [type]);
    const vendorMeta = useMemo(() => VENDORS.find((v) => v.id === vendorId), [vendorId]);

    // When type changes, reset vendor selection if the current vendor no longer fits.
    useEffect(() => {
        if (vendorId && !eligibleVendors.find((v) => v.id === vendorId)) {
            setVendorId("");
        }
    }, [type, eligibleVendors, vendorId]);

    // When vendor changes, prefill suggested model + base url.
    useEffect(() => {
        if (!vendorMeta) return;
        if (!modelName) setModelName(vendorMeta.suggested_models[0] ?? "");
        if (!baseUrl) setBaseUrl(vendorMeta.default_base_url);
    }, [vendorId]); // eslint-disable-line react-hooks/exhaustive-deps

    const requiredCredKeys = vendorMeta?.credential_keys ?? [];
    const credsValid = requiredCredKeys.every((k) => (credentials[k.key] || "").trim().length > 0);
    const canSubmit = vendorId && modelName && displayName && (isEdit || credsValid);

    const handleSave = async () => {
        if (!canSubmit) return;
        setSaving(true);
        setSaveError("");
        try {
            if (isEdit) {
                const update: ModelInstanceUpdate = {
                    display_name: displayName,
                    model_name: modelName,
                    base_url: baseUrl,
                };
                if (Object.keys(credentials).length > 0) {
                    update.credentials = credentials;
                }
                await onSave(update, editing!.id);
            } else {
                const create: ModelInstanceCreate = {
                    instance_type: type,
                    vendor_id: vendorId,
                    model_name: modelName,
                    display_name: displayName,
                    credentials,
                    base_url: baseUrl,
                    is_default: setAsDefault,
                };
                await onSave(create, null);
            }
            onClose();
        } catch (e) {
            setSaveError(e instanceof Error ? e.message : String(e));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-zinc-950 border border-white/10 rounded-2xl shadow-2xl">
                <button
                    type="button"
                    onClick={onClose}
                    className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-white/5 transition-colors z-10"
                >
                    <X size={18} />
                </button>

                <div className="p-6">
                    <h2 className="text-lg font-bold text-white">
                        {isEdit
                            ? `编辑实例 · ${editing?.display_name}`
                            : initialType
                                ? `添加 ${TYPE_LABELS[initialType]} 实例`
                                : "添加模型实例"}
                    </h2>
                    <p className="text-xs text-gray-500 mt-1">
                        {isEdit
                            ? "改完保存即可。留空凭证字段会保留原值。"
                            : initialType
                                ? "两步完成:选厂商 → 填凭证"
                                : "三步完成:选类型 → 选厂商 → 填凭证"}
                    </p>

                    {/* Stepper — only the visible steps. When initialType
                        was provided, step 1 is suppressed so the bar shows
                        two segments instead of three. */}
                    {!isEdit && (
                        <div className="flex items-center gap-2 mt-4 mb-6">
                            {(initialType ? [2, 3] : [1, 2, 3]).map((n) => (
                                <div
                                    key={n}
                                    className={`flex-1 h-1 rounded-full transition-colors ${step >= n ? "bg-amber-500" : "bg-white/10"}`}
                                />
                            ))}
                        </div>
                    )}

                    {/* Step 1: Type */}
                    {step === 1 && !isEdit && (
                        <div className="space-y-3">
                            <div className="text-xs uppercase tracking-wider text-gray-500">第 1 步 · 选类型</div>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                                {(Object.keys(TYPE_LABELS) as InstanceTypeId[]).map((t) => (
                                    <button
                                        key={t}
                                        type="button"
                                        onClick={() => setType(t)}
                                        className={`p-3 rounded-lg border text-left transition-colors ${type === t ? "border-amber-500/60 bg-amber-500/10 text-amber-200" : "border-white/10 bg-white/5 text-gray-300 hover:border-white/20"}`}
                                    >
                                        <div className="text-xs font-mono uppercase">{t}</div>
                                        <div className="text-[10px] text-gray-500 mt-0.5">{TYPE_LABELS[t]}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Vendor */}
                    {step === 2 && !isEdit && (
                        <div className="space-y-3">
                            <div className="text-xs uppercase tracking-wider text-gray-500">第 2 步 · 选厂商</div>
                            <div className="grid grid-cols-2 gap-2">
                                {eligibleVendors.map((v) => (
                                    <button
                                        key={v.id}
                                        type="button"
                                        onClick={() => setVendorId(v.id)}
                                        className={`p-3 rounded-lg border text-left transition-colors ${vendorId === v.id ? "border-amber-500/60 bg-amber-500/10 text-amber-200" : "border-white/10 bg-white/5 text-gray-300 hover:border-white/20"}`}
                                    >
                                        <div className="text-sm font-medium text-white">{v.label}</div>
                                        <div className="text-[10px] text-gray-500 mt-0.5 truncate font-mono">{v.suggested_models.slice(0, 3).join(", ")}</div>
                                    </button>
                                ))}
                            </div>
                            {eligibleVendors.length === 0 && (
                                <p className="text-xs text-gray-500">该类型暂无可用厂商。</p>
                            )}
                        </div>
                    )}

                    {/* Step 3: Details */}
                    {step === 3 && (
                        <div className="space-y-4">
                            <div className="text-xs uppercase tracking-wider text-gray-500">第 3 步 · 填详情</div>

                            <div>
                                <label className="block text-xs font-medium text-gray-300 mb-1.5">别名 <span className="text-rose-500">*</span></label>
                                <input
                                    type="text"
                                    value={displayName}
                                    onChange={(e) => setDisplayName(e.target.value)}
                                    placeholder="例如:工作室主力 LLM"
                                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/30"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-gray-300 mb-1.5">模型 <span className="text-rose-500">*</span></label>
                                <input
                                    type="text"
                                    value={modelName}
                                    onChange={(e) => setModelName(e.target.value)}
                                    placeholder="模型 ID"
                                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/30 font-mono"
                                />
                                {vendorMeta && (
                                    <div className="flex flex-wrap gap-1 mt-2">
                                        {vendorMeta.suggested_models.map((m) => (
                                            <button
                                                key={m}
                                                type="button"
                                                onClick={() => setModelName(m)}
                                                className={`px-2 py-1 text-[11px] rounded border transition-colors ${modelName === m ? "border-amber-500/60 bg-amber-500/15 text-amber-200" : "border-white/10 bg-white/5 text-gray-400 hover:text-gray-200"}`}
                                            >
                                                {m}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div>
                                <label className="flex items-center justify-between text-xs font-medium text-gray-300 mb-1.5">
                                    <span>Base URL</span>
                                    <span className="text-[10px] text-gray-600">留空使用厂商默认</span>
                                </label>
                                <input
                                    type="text"
                                    value={baseUrl}
                                    onChange={(e) => setBaseUrl(e.target.value)}
                                    placeholder={vendorMeta?.default_base_url ?? ""}
                                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/30 font-mono"
                                />
                            </div>

                            {requiredCredKeys.map((ck) => (
                                <div key={ck.key}>
                                    <label className="block text-xs font-medium text-gray-300 mb-1.5">
                                        {ck.label} {!isEdit && <span className="text-rose-500">*</span>}
                                        {isEdit && <span className="text-[10px] text-gray-600 ml-1">留空保留原值</span>}
                                    </label>
                                    <div className="relative">
                                        <input
                                            type={revealed[ck.key] ? "text" : "password"}
                                            value={credentials[ck.key] || ""}
                                            onChange={(e) => setCredentials((c) => ({ ...c, [ck.key]: e.target.value }))}
                                            placeholder="••••••••"
                                            className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 pr-9 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/30"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setRevealed((r) => ({ ...r, [ck.key]: !r[ck.key] }))}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-gray-500 hover:text-gray-300 hover:bg-white/5"
                                        >
                                            {revealed[ck.key] ? <EyeOff size={14} /> : <Eye size={14} />}
                                        </button>
                                    </div>
                                </div>
                            ))}

                            {!isEdit && (
                                <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={setAsDefault}
                                        onChange={(e) => setSetAsDefault(e.target.checked)}
                                        className="rounded border-white/20"
                                    />
                                    设为该类型的默认实例
                                </label>
                            )}

                            {vendorMeta?.docs_url && (
                                <a
                                    href={vendorMeta.docs_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-[11px] text-gray-500 hover:text-gray-300"
                                >
                                    查看 {vendorMeta.label} 文档
                                </a>
                            )}

                            {saveError && (
                                <div className="px-3 py-2 rounded bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
                                    {saveError}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Footer */}
                    <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
                        {/* "上一步" only available when there's a previous
                            visible step. With initialType, step 1 is hidden
                            so step 2 is the first visible step. */}
                        {!isEdit && step > (initialType ? 2 : 1) ? (
                            <button
                                type="button"
                                onClick={() => setStep((s) => (s - 1) as 1 | 2 | 3)}
                                className="flex items-center gap-1 px-3 py-2 text-xs text-gray-400 hover:text-white transition-colors"
                            >
                                <ChevronLeft size={14} />
                                上一步
                            </button>
                        ) : (
                            <div />
                        )}

                        {step < 3 && !isEdit ? (
                            <button
                                type="button"
                                onClick={() => setStep((s) => (s + 1) as 1 | 2 | 3)}
                                disabled={(step === 1 && !type) || (step === 2 && !vendorId)}
                                className="flex items-center gap-1 px-4 py-2 text-xs font-medium bg-amber-600 hover:bg-amber-500 text-white rounded-lg transition-colors disabled:opacity-50"
                            >
                                下一步
                                <ChevronRight size={14} />
                            </button>
                        ) : (
                            <button
                                type="button"
                                onClick={handleSave}
                                disabled={!canSubmit || saving}
                                className="flex items-center gap-1 px-4 py-2 text-xs font-medium bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white rounded-lg transition-colors disabled:opacity-50"
                            >
                                {saving && <Loader2 size={14} className="animate-spin" />}
                                {isEdit ? "保存" : "创建实例"}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
