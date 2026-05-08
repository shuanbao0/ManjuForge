"use client";

import { useMemo, useState } from "react";
import { Plus, Cpu, Image, Layout, Video, Mic, Loader2, type LucideIcon } from "lucide-react";
import { useInstances } from "@/hooks/useInstances";
import { type InstanceTypeId, type ModelInstanceCreate, type ModelInstanceOut, type ModelInstanceUpdate, instances as instancesApi } from "@/lib/api";
import { InstanceCard } from "./InstanceCard";
import { InstanceWizard } from "./InstanceWizard";


// Display order + iconography for the type-grouped list.
const TYPE_GROUPS: { id: InstanceTypeId; label: string; description: string; Icon: LucideIcon }[] = [
    { id: "llm", label: "LLM", description: "剧本分析、prompt 润色", Icon: Cpu },
    { id: "t2i", label: "Text-to-Image", description: "角色 / 场景 / 道具图", Icon: Image },
    { id: "i2i", label: "Image-to-Image", description: "分镜帧多参考合成", Icon: Layout },
    { id: "i2v", label: "Image-to-Video", description: "动作生成", Icon: Video },
    { id: "tts", label: "Text-to-Speech", description: "角色配音", Icon: Mic },
];


export function InstanceList() {
    const { instances, loading, error, reload, create, update, remove, setDefault } = useInstances();
    const [wizardOpen, setWizardOpen] = useState<{ type: InstanceTypeId | undefined; editing: ModelInstanceOut | null } | null>(null);

    const grouped = useMemo(() => {
        const m = new Map<InstanceTypeId, ModelInstanceOut[]>();
        for (const t of TYPE_GROUPS) m.set(t.id, []);
        for (const inst of instances) {
            if (!m.has(inst.instance_type)) m.set(inst.instance_type, []);
            m.get(inst.instance_type)!.push(inst);
        }
        return m;
    }, [instances]);

    const handleSave = async (
        payload: ModelInstanceCreate | ModelInstanceUpdate,
        editingId: string | null,
    ) => {
        if (editingId) {
            await update(editingId, payload as ModelInstanceUpdate);
        } else {
            await create(payload as ModelInstanceCreate);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12 text-gray-400">
                <Loader2 size={20} className="animate-spin text-amber-400 mr-2" />
                <span className="text-sm">加载中…</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-4 text-sm text-rose-300">
                加载失败:{error}
                <button onClick={reload} className="ml-3 underline hover:text-rose-200">重试</button>
            </div>
        );
    }

    return (
        <>
            <div className="space-y-6">
                {TYPE_GROUPS.map(({ id, label, description, Icon }) => {
                    const list = grouped.get(id) ?? [];
                    return (
                        <section key={id} className="space-y-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Icon size={16} className="text-gray-400" />
                                    <h3 className="text-sm font-bold text-white">{label}</h3>
                                    <span className="text-[10px] text-gray-500">{description}</span>
                                </div>
                                <span className="text-[10px] text-gray-500">{list.length} 个实例</span>
                            </div>

                            {list.length === 0 ? (
                                <button
                                    type="button"
                                    onClick={() => setWizardOpen({ type: id, editing: null })}
                                    className="w-full p-6 rounded-xl border border-dashed border-white/15 text-gray-500 hover:text-white hover:border-amber-500/40 hover:bg-amber-500/5 transition-colors flex items-center justify-center gap-2"
                                >
                                    <Plus size={14} />
                                    <span className="text-sm">添加 {label} 实例</span>
                                </button>
                            ) : (
                                <>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {list.map((inst) => (
                                            <InstanceCard
                                                key={inst.id}
                                                instance={inst}
                                                onSetDefault={async (id) => { await setDefault(id); }}
                                                onDelete={async (id) => { await remove(id); }}
                                                onEdit={(inst) => setWizardOpen({ type: inst.instance_type, editing: inst })}
                                            />
                                        ))}
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => setWizardOpen({ type: id, editing: null })}
                                        className="text-xs text-gray-500 hover:text-amber-400 transition-colors flex items-center gap-1"
                                    >
                                        <Plus size={12} />
                                        添加另一个 {label} 实例
                                    </button>
                                </>
                            )}
                        </section>
                    );
                })}
            </div>

            {wizardOpen && (
                <InstanceWizard
                    initialType={wizardOpen.type}
                    editing={wizardOpen.editing}
                    onClose={() => setWizardOpen(null)}
                    onSave={handleSave}
                />
            )}
        </>
    );
}
