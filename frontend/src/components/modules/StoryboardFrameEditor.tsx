"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, RefreshCw, Check, AlertTriangle, Image as ImageIcon, Lock, Unlock, ChevronRight, Maximize2 } from "lucide-react";
import { api, API_URL } from "@/lib/api";
import { VariantSelector } from "../common/VariantSelector";
import { useProjectStore } from "@/store/projectStore";
import { useTranslation } from "@/i18n";
import TimelineSlicer from "./huobao/TimelineSlicer";

interface StoryboardFrameEditorProps {
    frame: any;
    onClose: () => void;
}

export default function StoryboardFrameEditor({ frame: initialFrame, onClose }: StoryboardFrameEditorProps) {
    const { t } = useTranslation();
    const currentProject = useProjectStore(state => state.currentProject);
    const updateProject = useProjectStore(state => state.updateProject);

    // Get the latest frame data from the store (instead of using stale prop)
    const frame = useMemo(() => {
        if (!currentProject?.frames) return initialFrame;
        return currentProject.frames.find((f: any) => f.id === initialFrame.id) || initialFrame;
    }, [currentProject?.frames, initialFrame.id, initialFrame]);

    const [prompt, setPrompt] = useState(frame.image_prompt || frame.action_description || "");
    const [isGenerating, setIsGenerating] = useState(false);

    // Local state for title / duration_seconds — debounced-saved on blur so
    // every keystroke doesn't hit the backend. Initial values come from
    // the frame; changing frames resets them.
    const [title, setTitle] = useState<string>(frame.title ?? "");
    const [duration, setDuration] = useState<string>(
        frame.duration_seconds != null ? String(frame.duration_seconds) : ""
    );
    const saveMetaTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Sync prompt when frame changes
    useEffect(() => {
        setPrompt(frame.image_prompt || frame.action_description || "");
        setTitle(frame.title ?? "");
        setDuration(frame.duration_seconds != null ? String(frame.duration_seconds) : "");
    }, [frame.id, frame.image_prompt, frame.action_description, frame.title, frame.duration_seconds]);

    const saveMeta = async (patch: { title?: string | null; duration_seconds?: number | null }) => {
        if (!currentProject) return;
        try {
            const updated = await api.updateFrame(currentProject.id, frame.id, patch);
            updateProject(currentProject.id, updated);
        } catch (e) {
            console.error("Failed to save frame metadata:", e);
        }
    };

    const handleTitleBlur = () => {
        const trimmed = title.trim();
        const next = trimmed.length > 0 ? trimmed : null;
        if ((frame.title ?? null) === next) return;
        saveMeta({ title: next });
    };

    const handleDurationBlur = () => {
        if (duration === "") {
            if (frame.duration_seconds == null) return;
            saveMeta({ duration_seconds: null });
            return;
        }
        const n = parseInt(duration, 10);
        if (!Number.isFinite(n) || n < 1 || n > 60) {
            // Reset to last-saved value rather than POSTing garbage.
            setDuration(frame.duration_seconds != null ? String(frame.duration_seconds) : "");
            return;
        }
        if (frame.duration_seconds === n) return;
        saveMeta({ duration_seconds: n });
    };

    const handleGenerate = async (batchSize: number) => {
        if (!currentProject) return;

        setIsGenerating(true);
        try {
            // Construct composition data (simplified for now, ideally passed from parent or re-calculated)
            // For re-rendering, we might want to reuse existing composition data or just rely on prompt/I2I
            // The api.renderFrame expects compositionData.
            // If we don't pass it, pipeline uses existing.

            const updatedProject = await api.renderFrame(
                currentProject.id,
                frame.id,
                null, // Use existing composition data
                prompt,
                batchSize
            );
            updateProject(currentProject.id, updatedProject);
        } catch (error) {
            console.error("Failed to generate frame:", error);
            alert(t("modules.storyboard.generateFrameFailed", undefined, "Failed to generate frame"));
        } finally {
            setIsGenerating(false);
        }
    };

    const handleSelectVariant = async (variantId: string) => {
        if (!currentProject) return;
        try {
            const updatedProject = await api.selectAssetVariant(currentProject.id, frame.id, "storyboard_frame", variantId);
            updateProject(currentProject.id, updatedProject);
        } catch (error) {
            console.error("Failed to select variant:", error);
        }
    };

    const handleDeleteVariant = async (variantId: string) => {
        if (!currentProject) return;
        try {
            const updatedProject = await api.deleteAssetVariant(currentProject.id, frame.id, "storyboard_frame", variantId);
            updateProject(currentProject.id, updatedProject);
        } catch (error) {
            console.error("Failed to delete variant:", error);
        }
    };

    const handleSavePrompt = async () => {
        if (!currentProject) return;
        // We can update the prompt without generating
        // But currently we don't have a specific endpoint for just updating frame prompt without render?
        // We can use updateAssetAttributes?
        // But frame is not exactly an asset in the same way.
        // Let's assume prompt is saved on generation for now.
    };

    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4 md:p-8">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-[#1a1a1a] border border-white/10 rounded-2xl w-full max-w-6xl h-[85vh] flex flex-col overflow-hidden shadow-2xl"
            >
                {/* Header */}
                <div className="h-16 border-b border-white/10 flex justify-between items-center px-6 bg-black/20">
                    <div className="flex items-center gap-4">
                        <h2 className="text-xl font-bold text-white">{t("modules.storyboard.frameEditorTitle", undefined, "Frame Editor")} <span className="text-gray-500 font-normal text-sm ml-2">#{frame.id.substring(0, 8)}</span></h2>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 flex overflow-hidden">
                    {/* Left: Variant Selector */}
                    <div className="flex-1 bg-black/40 p-4 flex flex-col overflow-hidden relative">
                        <VariantSelector
                            asset={frame.rendered_image_asset}
                            currentImageUrl={frame.rendered_image_url || frame.image_url}
                            onSelect={handleSelectVariant}
                            onDelete={handleDeleteVariant}
                            onGenerate={handleGenerate}
                            isGenerating={isGenerating}
                            aspectRatio="16:9"
                            className="h-full"
                        />
                    </div>

                    {/* Right: Controls & Prompt */}
                    <div className="w-1/3 min-w-[350px] border-l border-white/10 bg-[#111] flex flex-col overflow-y-auto">
                        <div className="p-4 border-b border-white/5 space-y-3">
                            <h3 className="font-bold text-sm uppercase tracking-wider text-gray-400">
                                {t("modules.storyboard.sceneContext", undefined, "Scene Context")}
                            </h3>
                            {/* huobao-parity: title + duration_seconds inline edit */}
                            <div className="grid grid-cols-[1fr_90px] gap-2">
                                <div>
                                    <label className="text-[10px] uppercase text-gray-500 font-bold">镜头标题</label>
                                    <input
                                        type="text"
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        onBlur={handleTitleBlur}
                                        placeholder="如:震动惊醒"
                                        maxLength={20}
                                        className="w-full mt-1 bg-black/20 border border-white/10 rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] uppercase text-gray-500 font-bold">时长(秒)</label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={60}
                                        value={duration}
                                        onChange={(e) => setDuration(e.target.value)}
                                        onBlur={handleDurationBlur}
                                        placeholder="—"
                                        className="w-full mt-1 bg-black/20 border border-white/10 rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>
                            <p className="text-xs text-gray-300">
                                <span className="font-bold text-gray-500">{t("modules.storyboard.actionLabel", undefined, "Action:")}</span> {frame.action_description}
                            </p>
                            {frame.dialogue && (
                                <p className="text-xs text-gray-300 italic">
                                    <span className="font-bold text-gray-500 not-italic">{t("modules.storyboard.dialogueLabel", undefined, "Dialogue:")}</span> "{frame.dialogue}"
                                </p>
                            )}
                        </div>

                        <div className="flex-1 p-4 flex flex-col">
                            <h3 className="font-bold text-sm uppercase tracking-wider text-gray-400 mb-2">
                                {t("modules.storyboard.generationPrompt", undefined, "Generation Prompt")}
                            </h3>
                            <textarea
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                className="flex-1 min-h-[160px] w-full bg-black/20 border border-white/10 rounded-lg p-4 text-sm text-gray-300 resize-none focus:outline-none focus:border-primary/50 font-mono leading-relaxed"
                                placeholder={t("modules.storyboard.promptPlaceholder", undefined, "Enter prompt description...")}
                            />
                            <p className="text-xs text-gray-500 mt-2">
                                {t("modules.storyboard.promptHint", undefined, "Modify the prompt to refine the generated image.")}
                            </p>

                            {/* huobao-parity: time-axis slicer for video_prompt (Seedance / Veo) */}
                            <TimelineSlicer scriptId={currentProject?.id} frame={frame} />
                        </div>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
