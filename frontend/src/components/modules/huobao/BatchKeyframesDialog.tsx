"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { X, CheckSquare, Square, Image as ImageIcon, Loader2 } from "lucide-react";
import clsx from "clsx";
import { useBatchKeyframes, type BatchKeyframeMode } from "@/hooks/useBatchKeyframes";
import KeyframeModeSelector, { KEYFRAME_MODES } from "./KeyframeModeSelector";

/**
 * Self-contained dialog for batch keyframe generation.
 *
 * Three columns of state:
 * - mode    : which Strategy to send (first_frame / first_last / multi_ref).
 * - frames  : which storyboard frames participate (multi-select).
 * - force   : bypass grid path even on a grid-capable vendor.
 *
 * The frame list shows ALL frames in the project so users can pick
 * directly — no need to enter "multi-select mode" in the outer
 * storyboard view first. Existing thumbnails carry over so the user
 * sees what they're selecting.
 */
interface FrameLike {
  id: string;
  title?: string | null;
  action_description?: string;
  rendered_image_url?: string;
  image_url?: string;
}

interface BatchKeyframesDialogProps {
  scriptId: string | undefined;
  frames: FrameLike[];
  initialSelectedIds?: string[];
  onClose: () => void;
  onComplete?: () => void;
}

export default function BatchKeyframesDialog({
  scriptId,
  frames,
  initialSelectedIds = [],
  onClose,
  onComplete,
}: BatchKeyframesDialogProps) {
  const [mode, setMode] = useState<BatchKeyframeMode>("first_frame");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(initialSelectedIds.length > 0 ? initialSelectedIds : frames.map((f) => f.id)),
  );
  const [forcePerShot, setForcePerShot] = useState(false);

  const batch = useBatchKeyframes(scriptId);

  const selectedCount = selectedIds.size;
  const modeConfig = useMemo(
    () => KEYFRAME_MODES.find((m) => m.id === mode)!,
    [mode],
  );
  const willDegrade = !forcePerShot && selectedCount > modeConfig.maxFrames;
  const canSubmit = selectedCount > 0 && !!scriptId;

  const toggleFrame = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set(frames.map((f) => f.id)));
  const selectNone = () => setSelectedIds(new Set());

  // Auto-close after a successful run so the user sees their refreshed
  // storyboard. Errors keep the dialog open so the user can adjust.
  const handleSubmit = async () => {
    const result = await batch.run(Array.from(selectedIds), {
      mode,
      forcePerShot,
    });
    if (result) {
      onComplete?.();
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-[#1a1a1a] border border-white/10 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl"
      >
        {/* Header */}
        <div className="h-14 border-b border-white/10 flex justify-between items-center px-5 bg-black/20">
          <h2 className="text-base font-bold text-white">批量生成关键帧</h2>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Mode selector */}
          <section>
            <div className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              出图模式
            </div>
            <KeyframeModeSelector
              value={mode}
              onChange={setMode}
              frameCount={selectedCount}
            />
          </section>

          {/* Frame multi-select */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-bold uppercase tracking-wider text-gray-400">
                选择镜头 ({selectedCount}/{frames.length})
              </div>
              <div className="flex items-center gap-2 text-xs">
                <button
                  onClick={selectAll}
                  className="text-gray-400 hover:text-white"
                >
                  全选
                </button>
                <span className="text-gray-600">·</span>
                <button
                  onClick={selectNone}
                  className="text-gray-400 hover:text-white"
                >
                  清空
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-72 overflow-y-auto p-1">
              {frames.map((frame, idx) => {
                const isSelected = selectedIds.has(frame.id);
                const thumb = frame.rendered_image_url || frame.image_url;
                return (
                  <button
                    key={frame.id}
                    type="button"
                    onClick={() => toggleFrame(frame.id)}
                    className={clsx(
                      "flex items-center gap-2 p-2 rounded border text-left transition-colors",
                      isSelected
                        ? "border-primary bg-primary/10"
                        : "border-white/10 bg-white/[0.02] hover:border-white/30",
                    )}
                  >
                    {isSelected ? (
                      <CheckSquare size={14} className="text-primary shrink-0" />
                    ) : (
                      <Square size={14} className="text-gray-500 shrink-0" />
                    )}
                    <div className="w-10 h-6 rounded bg-black/40 shrink-0 overflow-hidden flex items-center justify-center">
                      {thumb ? (
                        <img src={thumb} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <ImageIcon size={10} className="text-gray-600" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[11px] font-medium text-white truncate">
                        #{idx + 1}
                        {frame.title && <span className="ml-1 text-gray-400">· {frame.title}</span>}
                      </div>
                      <div className="text-[10px] text-gray-500 truncate">
                        {frame.action_description || "—"}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Force per-shot toggle */}
          <section>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300">
              <input
                type="checkbox"
                checked={forcePerShot}
                onChange={(e) => setForcePerShot(e.target.checked)}
                className="rounded border-white/20 bg-black/40 accent-primary"
              />
              <span>强制逐镜出图(跳过网格,适合精修单镜)</span>
            </label>
          </section>

          {/* Degrade warning */}
          {willDegrade && (
            <div className="text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-2">
              选中 {selectedCount} 镜超过「{modeConfig.title}」的 {modeConfig.maxFrames} 镜上限,
              后端会自动降级到逐镜出图(失去网格一致性)。建议拆成多批或选更少镜头。
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="h-14 border-t border-white/10 px-5 flex items-center justify-end gap-3 bg-black/20">
          <button
            onClick={onClose}
            disabled={batch.isPending}
            className="h-9 px-4 rounded-lg text-sm text-gray-300 hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            取消
          </button>
          {/* Use a custom button (not ActionButton) so the submit flow can
              chain onComplete + onClose after a successful run. */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit || batch.isPending}
            title={!canSubmit ? "至少选一镜" : "开始生成"}
            className={clsx(
              "inline-flex items-center gap-2 h-9 px-4 rounded-lg font-medium text-sm",
              "bg-primary hover:bg-primary/90 text-white",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            )}
          >
            {batch.isPending && <Loader2 size={14} className="animate-spin" />}
            开始生成 ({selectedCount} 镜)
          </button>
        </div>
      </motion.div>
    </div>
  );
}
