"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Settings, X, Layout, Check, User, Building, Box, Loader2 } from "lucide-react";
import { useProjectStore, ASPECT_RATIOS } from "@/store/projectStore";
import { api } from "@/lib/api";
import { InstanceSelector } from "@/components/settings/InstanceSelector";
import { useTranslation } from "@/i18n";


interface Props {
    isOpen: boolean;
    onClose: () => void;
}


export default function ModelSettingsModal({ isOpen, onClose }: Props) {
    const { t } = useTranslation();
    const currentProject = useProjectStore((state) => state.currentProject);
    const updateProject = useProjectStore((state) => state.updateProject);

    const ms = currentProject?.model_settings;
    const [llmId, setLlmId] = useState<string | null>(ms?.llm_instance_id ?? null);
    const [t2iId, setT2iId] = useState<string | null>(ms?.t2i_instance_id ?? null);
    const [i2iId, setI2iId] = useState<string | null>(ms?.i2i_instance_id ?? null);
    const [i2vId, setI2vId] = useState<string | null>(ms?.i2v_instance_id ?? null);
    const [ttsId, setTtsId] = useState<string | null>(ms?.tts_instance_id ?? null);
    const [characterAspectRatio, setCharacterAspectRatio] = useState(ms?.character_aspect_ratio || "9:16");
    const [sceneAspectRatio, setSceneAspectRatio] = useState(ms?.scene_aspect_ratio || "16:9");
    const [propAspectRatio, setPropAspectRatio] = useState(ms?.prop_aspect_ratio || "1:1");
    const [storyboardAspectRatio, setStoryboardAspectRatio] = useState(ms?.storyboard_aspect_ratio || "16:9");
    const [isSaving, setIsSaving] = useState(false);

    // Sync state when project changes.
    useEffect(() => {
        const m = currentProject?.model_settings;
        if (!m) return;
        setLlmId(m.llm_instance_id ?? null);
        setT2iId(m.t2i_instance_id ?? null);
        setI2iId(m.i2i_instance_id ?? null);
        setI2vId(m.i2v_instance_id ?? null);
        setTtsId(m.tts_instance_id ?? null);
        setCharacterAspectRatio(m.character_aspect_ratio || "9:16");
        setSceneAspectRatio(m.scene_aspect_ratio || "16:9");
        setPropAspectRatio(m.prop_aspect_ratio || "1:1");
        setStoryboardAspectRatio(m.storyboard_aspect_ratio || "16:9");
    }, [currentProject?.model_settings]);

    const handleSave = async () => {
        if (!currentProject) return;
        setIsSaving(true);
        try {
            const updated = await api.updateModelSettings(currentProject.id, {
                llm_instance_id: llmId,
                t2i_instance_id: t2iId,
                i2i_instance_id: i2iId,
                i2v_instance_id: i2vId,
                tts_instance_id: ttsId,
                character_aspect_ratio: characterAspectRatio,
                scene_aspect_ratio: sceneAspectRatio,
                prop_aspect_ratio: propAspectRatio,
                storyboard_aspect_ratio: storyboardAspectRatio,
            });
            updateProject(currentProject.id, updated);
            onClose();
        } catch (e) {
            console.error("Failed to save model settings:", e);
            alert(t("modals.modelSettings.saveFailed", undefined, "保存失败"));
        } finally {
            setIsSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-[#1a1a1a] rounded-2xl border border-white/10 w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="flex items-center justify-between p-5 border-b border-white/10">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg">
                                <Settings size={20} className="text-blue-400" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-white">{t("modals.modelSettings.title", undefined, "模型设置")}</h2>
                                <p className="text-xs text-gray-500">{t("modals.modelSettings.subtitle", undefined, "为本项目选择模型实例（按生成阶段）")}</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                            <X size={20} className="text-gray-400" />
                        </button>
                    </div>

                    <div className="p-5 space-y-6 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <InstanceSelector type="llm" value={llmId} onChange={setLlmId} label={t("modals.modelSettings.llmStage", undefined, "脚本/对话（LLM）")} />
                            <InstanceSelector type="t2i" value={t2iId} onChange={setT2iId} label={t("modals.modelSettings.t2iStage", undefined, "文生图")} />
                            <InstanceSelector type="i2i" value={i2iId} onChange={setI2iId} label={t("modals.modelSettings.i2iStage", undefined, "图生图")} />
                            <InstanceSelector type="i2v" value={i2vId} onChange={setI2vId} label={t("modals.modelSettings.i2vStage", undefined, "视频（I2V）")} />
                            <InstanceSelector type="tts" value={ttsId} onChange={setTtsId} label={t("modals.modelSettings.ttsStage", undefined, "配音（TTS）")} />
                        </div>

                        <div className="border-t border-white/10" />

                        <div className="space-y-4">
                            <div className="flex items-center gap-2 text-sm font-bold text-white">
                                <Layout size={16} className="text-blue-400" />
                                {t("modals.modelSettings.aspectRatioLabel", undefined, "默认画幅")}
                            </div>

                            <div className="grid grid-cols-3 gap-4">
                                {([
                                    { key: "character", label: t("modals.modelSettings.characterAspect", undefined, "角色"), icon: User, value: characterAspectRatio, setter: setCharacterAspectRatio },
                                    { key: "scene", label: t("modals.modelSettings.sceneAspect", undefined, "场景"), icon: Building, value: sceneAspectRatio, setter: setSceneAspectRatio },
                                    { key: "prop", label: t("modals.modelSettings.propAspect", undefined, "道具"), icon: Box, value: propAspectRatio, setter: setPropAspectRatio },
                                ] as const).map(({ key, label, icon: Icon, value, setter }) => (
                                    <div key={key} className="space-y-2">
                                        <div className="flex items-center gap-1 text-xs text-gray-400">
                                            <Icon size={12} />
                                            <label>{label}</label>
                                        </div>
                                        <div className="space-y-1">
                                            {ASPECT_RATIOS.map((ratio) => (
                                                <button
                                                    key={ratio.id}
                                                    onClick={() => setter(ratio.id)}
                                                    className={`w-full py-2 px-2 rounded border transition-all ${value === ratio.id ? "border-blue-500/50 bg-blue-500/10" : "border-white/10 hover:border-white/20 bg-white/5"}`}
                                                >
                                                    <span className="text-xs font-medium text-white">{ratio.name}</span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="space-y-2 pt-2">
                                <label className="text-xs text-gray-400">{t("modals.modelSettings.storyboardAspect", undefined, "分镜")}</label>
                                <div className="grid grid-cols-3 gap-2">
                                    {ASPECT_RATIOS.map((ratio) => (
                                        <button
                                            key={ratio.id}
                                            onClick={() => setStoryboardAspectRatio(ratio.id)}
                                            className={`flex flex-col items-center p-3 rounded-lg border transition-all ${storyboardAspectRatio === ratio.id ? "border-blue-500/50 bg-blue-500/10" : "border-white/10 hover:border-white/20 bg-white/5"}`}
                                        >
                                            <span className="text-sm font-medium text-white">{ratio.name}</span>
                                            <span className="text-[10px] text-gray-500">{t(ratio.description)}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 p-5 border-t border-white/10 bg-black/20">
                        <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
                            {t("common.cancel", undefined, "取消")}
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50"
                        >
                            {isSaving ? <><Loader2 size={16} className="animate-spin" />{t("common.saving", undefined, "保存中...")}</> : <><Check size={16} />{t("common.save", undefined, "保存")}</>}
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
