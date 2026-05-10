"use client";

import { useEffect, useMemo } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";
import { useInstances } from "@/hooks/useInstances";
import { type InstanceTypeId } from "@/lib/api";
import { useTranslation } from "@/i18n";


export interface InstanceSelectorProps {
    type: InstanceTypeId;
    value: string | null;            // current instance_id reference
    onChange: (id: string | null) => void;
    /** Pretty label rendered above the picker (e.g. "Text-to-Image"). */
    label?: string;
}


/**
 * Per-type ModelInstance picker — used inside project / series settings to
 * point a generation stage at one of the user's configured instances.
 *
 * Selecting "默认" (null) tells the backend to fall back to the user's
 * default instance for that type. Selecting a specific row pins the
 * project to that exact instance, surviving default changes elsewhere.
 */
export function InstanceSelector({ type, value, onChange, label }: InstanceSelectorProps) {
    const { t } = useTranslation();
    const { instances, loading, error } = useInstances(type);

    const sorted = useMemo(
        () => [...instances].sort((a, b) => Number(b.is_default) - Number(a.is_default)),
        [instances],
    );

    // If the project's saved value points to a deleted instance, drop it.
    useEffect(() => {
        if (value && instances.length > 0 && !instances.find((i) => i.id === value)) {
            onChange(null);
        }
    }, [value, instances, onChange]);

    if (loading) {
        return (
            <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
                <Loader2 size={12} className="animate-spin" />
                {t("instances.loadingInstances", undefined, "加载实例...")}
            </div>
        );
    }

    if (error) {
        return <div className="text-xs text-rose-300">{t("instances.loadFailed", undefined, "加载失败")}:{error}</div>;
    }

    if (instances.length === 0) {
        return (
            <div className="text-xs text-gray-500 px-3 py-2 border border-dashed border-white/10 rounded">
                {t("instances.noInstancesForType", { type: type.toUpperCase() }, `还没有 ${type.toUpperCase()} 实例。请先在设置里添加一个。`)}
            </div>
        );
    }

    const isUsingDefault = value === null;

    return (
        <div className="space-y-2">
            {label && <div className="text-xs text-gray-400">{label}</div>}
            <div className="grid grid-cols-1 gap-1.5">
                {/* "Use default" pseudo-row */}
                <button
                    type="button"
                    onClick={() => onChange(null)}
                    className={`flex items-center justify-between p-2.5 rounded-lg border text-left transition-colors ${isUsingDefault ? "border-amber-500/60 bg-amber-500/10" : "border-white/10 bg-white/5 hover:border-white/20"}`}
                >
                    <div>
                        <span className="text-sm text-white">{t("instances.useMyDefault", undefined, "使用我的默认")}</span>
                        <span className="text-[10px] text-gray-500 ml-2">{t("instances.useMyDefaultHint", undefined, "运行时按 type 解析")}</span>
                    </div>
                    {isUsingDefault && <Check size={14} className="text-amber-400" />}
                </button>

                {sorted.map((inst) => (
                    <button
                        key={inst.id}
                        type="button"
                        onClick={() => onChange(inst.id)}
                        className={`flex items-center justify-between p-2.5 rounded-lg border text-left transition-colors ${value === inst.id ? "border-amber-500/60 bg-amber-500/10" : "border-white/10 bg-white/5 hover:border-white/20"}`}
                    >
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                                <span className="text-sm text-white truncate">{inst.display_name}</span>
                                {inst.is_default && (
                                    <Sparkles size={10} className="text-amber-400 shrink-0" />
                                )}
                            </div>
                            <div className="text-[10px] text-gray-500 mt-0.5 font-mono truncate">
                                {inst.vendor_id} · {inst.model_name}
                            </div>
                        </div>
                        {value === inst.id && <Check size={14} className="text-amber-400 ml-2" />}
                    </button>
                ))}
            </div>
        </div>
    );
}
