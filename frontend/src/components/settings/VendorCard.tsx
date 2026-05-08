"use client";

import { useState, useMemo } from "react";
import {
    ChevronDown,
    ChevronRight,
    Check,
    AlertCircle,
    ExternalLink,
    Eye,
    EyeOff,
    Sparkles,
} from "lucide-react";
import type { CredentialFieldDTO, VendorConnectorDTO } from "@/lib/api";

// ── Visual config ────────────────────────────────────────────────────────
//
// Tailwind cannot tree-shake dynamic class names, so accent colors are
// referenced by name in a static map. Each accent comes with three flavors:
// border (configured), ring/glow (active), and stripe (top accent bar).

type AccentKey =
    | "amber"
    | "purple"
    | "cyan"
    | "rose"
    | "orange"
    | "sky"
    | "violet"
    | "emerald";

const ACCENTS: Record<AccentKey, { border: string; stripe: string; glow: string; chip: string }> = {
    amber: {
        border: "border-amber-500/40",
        stripe: "bg-gradient-to-r from-amber-500/40 via-amber-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(245,158,11,0.25)]",
        chip: "bg-amber-500/15 text-amber-200 border-amber-500/30",
    },
    purple: {
        border: "border-purple-500/40",
        stripe: "bg-gradient-to-r from-purple-500/40 via-purple-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(168,85,247,0.25)]",
        chip: "bg-purple-500/15 text-purple-200 border-purple-500/30",
    },
    cyan: {
        border: "border-cyan-500/40",
        stripe: "bg-gradient-to-r from-cyan-500/40 via-cyan-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(6,182,212,0.25)]",
        chip: "bg-cyan-500/15 text-cyan-200 border-cyan-500/30",
    },
    rose: {
        border: "border-rose-500/40",
        stripe: "bg-gradient-to-r from-rose-500/40 via-rose-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(244,63,94,0.25)]",
        chip: "bg-rose-500/15 text-rose-200 border-rose-500/30",
    },
    orange: {
        border: "border-orange-500/40",
        stripe: "bg-gradient-to-r from-orange-500/40 via-orange-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(249,115,22,0.25)]",
        chip: "bg-orange-500/15 text-orange-200 border-orange-500/30",
    },
    sky: {
        border: "border-sky-500/40",
        stripe: "bg-gradient-to-r from-sky-500/40 via-sky-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(14,165,233,0.25)]",
        chip: "bg-sky-500/15 text-sky-200 border-sky-500/30",
    },
    violet: {
        border: "border-violet-500/40",
        stripe: "bg-gradient-to-r from-violet-500/40 via-violet-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(139,92,246,0.25)]",
        chip: "bg-violet-500/15 text-violet-200 border-violet-500/30",
    },
    emerald: {
        border: "border-emerald-500/40",
        stripe: "bg-gradient-to-r from-emerald-500/40 via-emerald-500/15 to-transparent",
        glow: "shadow-[0_0_0_1px_rgba(16,185,129,0.25)]",
        chip: "bg-emerald-500/15 text-emerald-200 border-emerald-500/30",
    },
};

const CAPABILITY_LABELS: Record<string, string> = {
    llm: "LLM",
    t2i: "T2I",
    i2i: "I2I",
    i2v: "I2V",
    t2v: "T2V",
    r2v: "R2V",
    tts: "TTS",
};

const BADGE_STYLES: Record<string, string> = {
    recommended: "bg-amber-500/20 text-amber-200 border-amber-500/40",
    new: "bg-emerald-500/20 text-emerald-200 border-emerald-500/40",
    preview: "bg-violet-500/20 text-violet-200 border-violet-500/40",
    premium: "bg-rose-500/20 text-rose-200 border-rose-500/40",
};

// ── Helpers ──────────────────────────────────────────────────────────────

export type CredsMap = Record<string, string>;

/** Compute the connector's status from current credential values. */
function computeStatus(
    connector: VendorConnectorDTO,
    creds: CredsMap,
): "connected" | "partial" | "missing" {
    const activeMode = connector.mode_env_key ? creds[connector.mode_env_key] || "dashscope" : null;

    const requiredFields: CredentialFieldDTO[] = [];
    for (const f of connector.common_fields) if (f.required) requiredFields.push(f);
    if (activeMode) {
        const mode = connector.modes.find((m) => m.id === activeMode);
        if (mode) for (const f of mode.fields) if (f.required) requiredFields.push(f);
    }

    if (requiredFields.length === 0) return "connected";
    const filled = requiredFields.filter((f) => (creds[f.key] || "").trim().length > 0).length;
    if (filled === 0) return "missing";
    if (filled === requiredFields.length) return "connected";
    return "partial";
}

// ── Subcomponents ────────────────────────────────────────────────────────

function StatusPill({ status }: { status: "connected" | "partial" | "missing" }) {
    if (status === "connected") {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                <Check size={10} /> 已连接
            </span>
        );
    }
    if (status === "partial") {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
                <AlertCircle size={10} /> 待补全
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/5 text-gray-500 border border-white/10">
            未配置
        </span>
    );
}

function CredentialInput({
    field,
    value,
    onChange,
}: {
    field: CredentialFieldDTO;
    value: string;
    onChange: (v: string) => void;
}) {
    const [revealed, setRevealed] = useState(false);
    const inputType = field.secret && !revealed ? "password" : "text";
    return (
        <div>
            <label className="flex items-center justify-between text-xs font-medium text-gray-300 mb-1.5">
                <span>
                    {field.label}
                    {field.required && <span className="text-red-500 ml-0.5">*</span>}
                </span>
                {field.help_text && <span className="text-gray-600 font-normal text-[10px]">{field.help_text}</span>}
            </label>
            <div className="relative">
                <input
                    type={inputType}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={field.placeholder}
                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 pr-9 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-white/30 transition-colors"
                />
                {field.secret && (
                    <button
                        type="button"
                        onClick={() => setRevealed((r) => !r)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-colors"
                        title={revealed ? "隐藏" : "显示"}
                    >
                        {revealed ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                )}
            </div>
        </div>
    );
}

// ── VendorCard ───────────────────────────────────────────────────────────

export interface VendorCardProps {
    connector: VendorConnectorDTO;
    creds: CredsMap;
    onChange: (key: string, value: string) => void;
    /** Optional: force start expanded (e.g. first unconfigured card). */
    defaultExpanded?: boolean;
}

export function VendorCard({ connector, creds, onChange, defaultExpanded = false }: VendorCardProps) {
    const accent: AccentKey = (connector.accent as AccentKey) in ACCENTS
        ? (connector.accent as AccentKey)
        : "amber";
    const a = ACCENTS[accent];

    const status = useMemo(() => computeStatus(connector, creds), [connector, creds]);
    const [expanded, setExpanded] = useState(defaultExpanded || status === "partial");

    const activeMode = connector.mode_env_key ? creds[connector.mode_env_key] || "dashscope" : null;
    const activeModeFields = useMemo(() => {
        if (!activeMode) return [] as CredentialFieldDTO[];
        return connector.modes.find((m) => m.id === activeMode)?.fields ?? [];
    }, [connector.modes, activeMode]);

    const isConfigured = status === "connected";
    const containerCls = `relative rounded-xl border transition-all overflow-hidden ${
        isConfigured ? `bg-white/5 ${a.border} ${a.glow}` : "bg-white/5 border-white/10 hover:border-white/20"
    }`;

    return (
        <div className={containerCls}>
            {/* Top accent stripe (visible when configured) */}
            <div className={`absolute inset-x-0 top-0 h-0.5 ${isConfigured ? a.stripe : "bg-white/5"}`} />

            {/* Header: clickable to expand */}
            <button
                type="button"
                onClick={() => setExpanded((e) => !e)}
                className="w-full flex items-start gap-3 p-4 text-left hover:bg-white/[0.02] transition-colors"
            >
                <div className="mt-0.5 text-gray-500">
                    {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-white truncate">{connector.display_name}</span>
                        <StatusPill status={status} />
                        {connector.badges.map((b) => (
                            <span
                                key={b}
                                className={`px-1.5 py-0.5 text-[9px] rounded border flex items-center gap-1 ${BADGE_STYLES[b] ?? "bg-white/10 text-gray-300 border-white/10"}`}
                            >
                                {b === "recommended" && <Sparkles size={9} />}
                                {b}
                            </span>
                        ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-1 line-clamp-2">{connector.description}</div>
                    <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                        {connector.capabilities.map((c) => (
                            <span key={c} className={`px-1.5 py-0.5 text-[9px] rounded border ${a.chip}`}>
                                {CAPABILITY_LABELS[c] ?? c.toUpperCase()}
                            </span>
                        ))}
                    </div>
                </div>
            </button>

            {/* Expanded body */}
            {expanded && (
                <div className="px-4 pb-4 space-y-4 border-t border-white/5">
                    {/* Mode segmented control */}
                    {connector.mode_env_key && connector.modes.length > 0 && (
                        <div className="pt-4">
                            <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2">路由模式</div>
                            <div className="inline-flex p-0.5 bg-black/40 border border-white/10 rounded-lg">
                                {connector.modes.map((mode) => {
                                    const active = activeMode === mode.id;
                                    return (
                                        <button
                                            key={mode.id}
                                            type="button"
                                            onClick={() => onChange(connector.mode_env_key!, mode.id)}
                                            className={`px-3 py-1.5 text-xs rounded-md transition-all ${
                                                active
                                                    ? `text-white ${a.border} bg-white/10 border`
                                                    : "text-gray-400 hover:text-gray-200 border border-transparent"
                                            }`}
                                        >
                                            {mode.label}
                                        </button>
                                    );
                                })}
                            </div>
                            {activeMode && (
                                <p className="text-[11px] text-gray-500 mt-1.5">
                                    {connector.modes.find((m) => m.id === activeMode)?.description}
                                </p>
                            )}
                        </div>
                    )}

                    {/* Credential fields — common first, then mode-specific */}
                    {(connector.common_fields.length > 0 || activeModeFields.length > 0) && (
                        <div className={connector.mode_env_key ? "" : "pt-4"}>
                            <div className="space-y-3">
                                {connector.common_fields.map((f) => (
                                    <CredentialInput
                                        key={f.key}
                                        field={f}
                                        value={creds[f.key] || ""}
                                        onChange={(v) => onChange(f.key, v)}
                                    />
                                ))}
                                {activeModeFields.map((f) => (
                                    <CredentialInput
                                        key={f.key}
                                        field={f}
                                        value={creds[f.key] || ""}
                                        onChange={(v) => onChange(f.key, v)}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Footer: docs link */}
                    {connector.docs_url && (
                        <div className="pt-2">
                            <a
                                href={connector.docs_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-gray-500 hover:text-gray-300 transition-colors"
                            >
                                <ExternalLink size={11} /> 查看文档
                            </a>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
