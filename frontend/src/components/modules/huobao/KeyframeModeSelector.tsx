"use client";

import clsx from "clsx";
import { Grid3x3, Film, Compass } from "lucide-react";
import type { BatchKeyframeMode } from "@/hooks/useBatchKeyframes";

/**
 * Radio-style selector for the three keyframe modes.
 *
 * The Strategy decision is encoded as a config array (Strategy in
 * data form): each entry pairs a mode id with its UI hints —
 * icon / title / description / per-frame panel count / max-frames
 * advisory. Adding a new mode means appending one config object;
 * no JSX changes.
 */
export interface ModeConfig {
  id: BatchKeyframeMode;
  title: string;
  icon: React.ReactNode;
  description: string;
  panelsPerFrame: number;
  maxFrames: number;
  badge?: string;
}

export const KEYFRAME_MODES: ModeConfig[] = [
  {
    id: "first_frame",
    title: "首帧网格",
    icon: <Grid3x3 size={18} />,
    description: "每镜出 1 张开场画面,9 镜挤一张 3×3 大图,跨镜头风格最一致",
    panelsPerFrame: 1,
    maxFrames: 9,
  },
  {
    id: "first_last",
    title: "首尾帧",
    icon: <Film size={18} />,
    description: "每镜出 2 张(开场 + 落幅),给 i2v 长镜头当首尾关键帧",
    panelsPerFrame: 2,
    maxFrames: 4,
    badge: "i2v 优化",
  },
  {
    id: "multi_ref",
    title: "多角度参考",
    icon: <Compass size={18} />,
    description: "每镜出 3 个角度(正/侧/俯),做完后用户挑一张当主图",
    panelsPerFrame: 3,
    maxFrames: 3,
  },
];

interface KeyframeModeSelectorProps {
  value: BatchKeyframeMode;
  onChange: (mode: BatchKeyframeMode) => void;
  frameCount: number;
}

export default function KeyframeModeSelector({
  value,
  onChange,
  frameCount,
}: KeyframeModeSelectorProps) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {KEYFRAME_MODES.map((mode) => {
        const tooManyFrames = frameCount > mode.maxFrames;
        const isSelected = value === mode.id;
        return (
          <button
            key={mode.id}
            type="button"
            onClick={() => onChange(mode.id)}
            className={clsx(
              "text-left p-3 rounded-lg border transition-all",
              isSelected
                ? "border-primary bg-primary/10"
                : "border-white/10 bg-white/[0.02] hover:border-white/30",
            )}
          >
            <div className="flex items-center gap-2 mb-1.5">
              <div className={clsx(isSelected ? "text-primary" : "text-gray-300")}>
                {mode.icon}
              </div>
              <span className="font-bold text-sm text-white">{mode.title}</span>
              {mode.badge && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300">
                  {mode.badge}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 leading-relaxed">{mode.description}</p>
            <p className="text-[10px] text-gray-500 mt-2">
              {mode.panelsPerFrame} 格/镜 · 最多 {mode.maxFrames} 镜
              {tooManyFrames && (
                <span className="ml-1 text-amber-400">(当前 {frameCount} 镜超出,会自动降级到逐镜)</span>
              )}
            </p>
          </button>
        );
      })}
    </div>
  );
}
