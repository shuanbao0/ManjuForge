"use client";

import { useState } from "react";
import {
    Star, Trash2, Pencil, ZapOff, Zap, Loader2, Check, X,
} from "lucide-react";
import { instances as instancesApi, type ModelInstanceOut } from "@/lib/api";
import { useTranslation } from "@/i18n";

const VENDOR_ACCENT: Record<string, string> = {
    dashscope: "border-amber-500/40 bg-amber-500/5",
    openai: "border-emerald-500/40 bg-emerald-500/5",
    anthropic: "border-orange-500/40 bg-orange-500/5",
    deepseek: "border-cyan-500/40 bg-cyan-500/5",
    moonshot: "border-purple-500/40 bg-purple-500/5",
    zhipu: "border-rose-500/40 bg-rose-500/5",
    google: "border-sky-500/40 bg-sky-500/5",
    ollama: "border-slate-500/40 bg-slate-500/5",
    kling: "border-purple-500/40 bg-purple-500/5",
    vidu: "border-cyan-500/40 bg-cyan-500/5",
    pixverse: "border-rose-500/40 bg-rose-500/5",
    doubao: "border-orange-500/40 bg-orange-500/5",
    hailuo: "border-sky-500/40 bg-sky-500/5",
};

// Vendor display names — kept as-is because they're brand names.
const VENDOR_LABEL: Record<string, string> = {
    dashscope: "阿里云 DashScope",
    openai: "OpenAI",
    anthropic: "Anthropic Claude",
    deepseek: "DeepSeek",
    moonshot: "Moonshot Kimi",
    zhipu: "智谱 GLM",
    google: "Google Gemini",
    ollama: "本地 Ollama",
    kling: "Kling AI",
    vidu: "Vidu",
    pixverse: "Pixverse",
    doubao: "字节 Doubao",
    hailuo: "MiniMax Hailuo",
};


export interface InstanceCardProps {
    instance: ModelInstanceOut;
    onSetDefault: (id: string) => Promise<void>;
    onDelete: (id: string) => Promise<void>;
    onEdit: (instance: ModelInstanceOut) => void;
}


export function InstanceCard({ instance, onSetDefault, onDelete, onEdit }: InstanceCardProps) {
    const { t } = useTranslation();
    const accent = VENDOR_ACCENT[instance.vendor_id] ?? "border-white/10 bg-white/5";
    const vendorLabel = VENDOR_LABEL[instance.vendor_id] ?? instance.vendor_id;

    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<"ok" | "fail" | null>(null);
    const [testError, setTestError] = useState("");

    const handleTest = async () => {
        setTesting(true);
        setTestError("");
        try {
            const res = await instancesApi.test(instance.id);
            setTestResult(res.ok ? "ok" : "fail");
            if (!res.ok) setTestError(res.error || t("instances.unknownError", undefined, "未知错误"));
        } catch (e) {
            setTestResult("fail");
            setTestError(e instanceof Error ? e.message : String(e));
        } finally {
            setTesting(false);
            setTimeout(() => {
                setTestResult(null);
                setTestError("");
            }, 5000);
        }
    };

    const handleDelete = async () => {
        if (!confirm(t("instances.deleteConfirm", { name: instance.display_name }))) return;
        await onDelete(instance.id);
    };

    return (
        <div className={`rounded-xl border p-4 transition-colors ${accent} ${instance.is_default ? "ring-1 ring-white/20" : ""}`}>
            <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-white truncate">{instance.display_name}</span>
                        {instance.is_default && (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[9px] rounded border border-amber-500/40 bg-amber-500/15 text-amber-200">
                                <Star size={9} className="fill-amber-400 text-amber-400" />
                                {t("instances.isDefault")}
                            </span>
                        )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1 truncate">
                        {vendorLabel} · <span className="font-mono text-gray-400">{instance.model_name}</span>
                    </div>
                    <div className="text-[10px] text-gray-600 mt-1">
                        {instance.credential_keys.length > 0
                            ? `${t("instances.credentialsLabel", undefined, "凭证")}: ${instance.credential_keys.join(", ")}`
                            : t("instances.noCredentials", undefined, "未填凭证")}
                    </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                    {!instance.is_default && (
                        <button
                            type="button"
                            onClick={() => onSetDefault(instance.id)}
                            title={t("instances.setDefault")}
                            className="p-1.5 rounded text-gray-500 hover:text-amber-400 hover:bg-white/5 transition-colors"
                        >
                            <Star size={14} />
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={handleTest}
                        disabled={testing}
                        title={testing ? t("instances.testing") : t("instances.testConnectivity", undefined, "测试连通")}
                        className="p-1.5 rounded text-gray-500 hover:text-emerald-400 hover:bg-white/5 transition-colors disabled:opacity-50"
                    >
                        {testing ? <Loader2 size={14} className="animate-spin" /> : testResult === "ok" ? <Zap size={14} className="text-emerald-400" /> : testResult === "fail" ? <ZapOff size={14} className="text-rose-400" /> : <Zap size={14} />}
                    </button>
                    <button
                        type="button"
                        onClick={() => onEdit(instance)}
                        title={t("instances.edit")}
                        className="p-1.5 rounded text-gray-500 hover:text-blue-400 hover:bg-white/5 transition-colors"
                    >
                        <Pencil size={14} />
                    </button>
                    <button
                        type="button"
                        onClick={handleDelete}
                        title={t("instances.delete")}
                        className="p-1.5 rounded text-gray-500 hover:text-rose-400 hover:bg-white/5 transition-colors"
                    >
                        <Trash2 size={14} />
                    </button>
                </div>
            </div>
            {testError && (
                <div className="mt-2 px-2 py-1 rounded bg-rose-500/10 border border-rose-500/30 text-[11px] text-rose-300">
                    <X size={11} className="inline mr-1" />
                    {testError}
                </div>
            )}
            {testResult === "ok" && !testError && (
                <div className="mt-2 px-2 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-[11px] text-emerald-300">
                    <Check size={11} className="inline mr-1" />
                    {t("instances.connectivityOk", undefined, "连通正常")}
                </div>
            )}
        </div>
    );
}
