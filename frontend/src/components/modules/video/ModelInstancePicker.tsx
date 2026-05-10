"use client";

import { useEffect } from "react";
import { Loader2, Plus, Star, AlertCircle, ArrowRight } from "lucide-react";
import { useTranslation } from "@/i18n";
import {
    useI2VInstances,
    type EnrichedInstance,
} from "@/hooks/useI2VInstances";

interface ModelInstancePickerProps {
    /** Currently selected ``ModelInstance.id`` (``null`` falls back to default). */
    value: string | null;
    /** Generation mode — ``"r2v"`` greys out non-Wan-2.6 entries. */
    mode: "i2v" | "r2v";
    /** Fired when the user picks a different instance. */
    onChange: (instance: EnrichedInstance) => void;
}

/**
 * I2V instance picker for the Video Generation sidebar.
 *
 * Self-contained: handles loading / empty / error states, renders the list,
 * and offers a deep-link CTA to ``#/settings`` when the user has no I2V
 * instance configured yet.
 */
export default function ModelInstancePicker({
    value,
    mode,
    onChange,
}: ModelInstancePickerProps) {
    const { t } = useTranslation();
    const { instances, defaultInstance, loading, error } = useI2VInstances();

    const isR2V = mode === "r2v";
    const selectedId = value ?? defaultInstance?.id ?? null;

    // Auto-correction effect — keeps the picker's contract simple for the
    // parent: it never has to think about "did the user pick something yet?"
    // or "is the selected instance still legal under the current mode?".
    //
    //   1. First render: emit defaultInstance so duration/resolution controls
    //      know which family to render.
    //   2. Mode flip (i2v → r2v): if the active instance can't do R2V, switch
    //      to the first wan2.6 entry; otherwise keep it.
    //
    // ``onChange`` is intentionally absent from deps — it's captured fresh
    // each render, but since onChange flips ``value`` to the target id, the
    // next pass finds the predicates already satisfied and won't re-emit.
    useEffect(() => {
        if (loading || instances.length === 0) return;
        const current = value ? instances.find((i) => i.id === value) ?? null : null;
        if (isR2V && current && !current.r2vEligible) {
            const eligible = instances.find((i) => i.r2vEligible);
            if (eligible) onChange(eligible);
            return;
        }
        if (!current && defaultInstance) {
            onChange(defaultInstance);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [loading, value, isR2V, instances]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-6 text-gray-500 text-xs gap-2">
                <Loader2 size={14} className="animate-spin" />
                {t("instances.loading", undefined, "Loading instances…")}
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-start gap-2 p-3 rounded-lg border border-red-500/20 bg-red-500/5 text-xs text-red-300">
                <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                <span>{error}</span>
            </div>
        );
    }

    if (instances.length === 0) {
        return <EmptyState />;
    }

    return (
        <div className="space-y-2">
            {instances.map((inst) => (
                <InstanceCard
                    key={inst.id}
                    instance={inst}
                    selected={inst.id === selectedId}
                    disabled={isR2V && !inst.r2vEligible}
                    onSelect={onChange}
                />
            ))}
            <AddInstanceLink />
        </div>
    );
}

// ── sub-components ─────────────────────────────────────────────────────────

interface InstanceCardProps {
    instance: EnrichedInstance;
    selected: boolean;
    disabled: boolean;
    onSelect: (instance: EnrichedInstance) => void;
}

function InstanceCard({ instance, selected, disabled, onSelect }: InstanceCardProps) {
    const { t } = useTranslation();
    const family = instance.family;
    const accent = family?.accent ?? "bg-gray-500";

    return (
        <button
            type="button"
            onClick={() => !disabled && onSelect(instance)}
            disabled={disabled}
            title={
                disabled
                    ? t("modules.video.r2vOnlyWan26", undefined, "(R2V 仅支持 Wan 2.6)")
                    : instance.display_name
            }
            className={`group w-full flex items-center gap-3 p-2.5 rounded-lg border text-left transition-all ${
                selected
                    ? "border-primary/60 bg-primary/10 shadow-[0_0_0_1px_rgba(99,102,241,0.3)]"
                    : "border-white/10 bg-white/[0.03] hover:border-white/25 hover:bg-white/[0.06]"
            } ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
        >
            {/* Vendor accent dot */}
            <div className={`w-2 h-2 rounded-full ${accent} flex-shrink-0`} />

            {/* Name + model_name */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                    {instance.is_default && (
                        <Star size={10} className="text-yellow-400 fill-yellow-400 flex-shrink-0" />
                    )}
                    <span className="text-xs font-medium text-white truncate">
                        {instance.display_name}
                    </span>
                </div>
                <p className="text-[10px] text-gray-500 font-mono truncate mt-0.5">
                    {instance.model_name}
                </p>
            </div>

            {/* Family badge */}
            {family && (
                <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-gray-300 flex-shrink-0">
                    {family.displayName}
                </span>
            )}

            {/* Selected indicator */}
            <div
                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 transition-opacity ${
                    selected ? "bg-primary opacity-100" : "opacity-0"
                }`}
            />
        </button>
    );
}

function AddInstanceLink() {
    const { t } = useTranslation();
    return (
        <button
            type="button"
            onClick={() => {
                window.location.hash = "#/settings";
            }}
            className="w-full flex items-center justify-center gap-1.5 mt-1 py-1.5 text-[11px] text-gray-500 hover:text-primary border border-dashed border-white/10 hover:border-primary/40 rounded-lg transition-colors"
        >
            <Plus size={12} />
            {t("modules.video.addI2VInstance", undefined, "添加 I2V 实例")}
            <ArrowRight size={11} className="opacity-60" />
        </button>
    );
}

function EmptyState() {
    const { t } = useTranslation();
    return (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-3">
            <div className="flex items-start gap-2 text-xs text-amber-300">
                <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                <span>
                    {t(
                        "modules.video.noI2VInstance",
                        undefined,
                        "尚未配置 I2V 模型实例，无法生成视频。",
                    )}
                </span>
            </div>
            <button
                type="button"
                onClick={() => {
                    window.location.hash = "#/settings";
                }}
                className="w-full flex items-center justify-center gap-1.5 py-2 text-xs font-medium text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors"
            >
                <Plus size={12} />
                {t("modules.video.goToSettingsAddInstance", undefined, "去 Settings 添加")}
                <ArrowRight size={12} />
            </button>
        </div>
    );
}
