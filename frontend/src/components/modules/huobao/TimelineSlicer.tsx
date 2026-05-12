"use client";

import { useState } from "react";
import { Clock, ChevronDown, ChevronRight } from "lucide-react";
import { ActionButton } from "@/components/common/ActionButton";
import { useTimelineSlicer } from "@/hooks/useTimelineSlicer";
import TimelineDisplay from "./TimelineDisplay";

/**
 * Collapsible section in the StoryboardFrameEditor showing the
 * time-axis slice of a frame's ``video_prompt``.
 *
 * Auto-collapses when no timeline exists yet — keeps the editor panel
 * short for users who don't need this feature. Expands automatically
 * after a successful slice so the user sees the result without
 * clicking again.
 */
interface TimelineSlicerProps {
  scriptId: string | undefined;
  frame: {
    id: string;
    video_prompt?: string;
    video_prompt_timeline?: string;
  };
}

export default function TimelineSlicer({ scriptId, frame }: TimelineSlicerProps) {
  const hasTimeline = !!frame.video_prompt_timeline;
  const [expanded, setExpanded] = useState(hasTimeline);
  const action = useTimelineSlicer(scriptId);
  const canSlice = !!scriptId && !!frame.video_prompt && frame.video_prompt.trim().length > 0;

  return (
    <div className="border-t border-white/5 pt-4 mt-4">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-400 hover:text-white transition-colors"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Clock size={12} />
        时间轴切片
        <span className="font-normal text-gray-600 normal-case tracking-normal">
          (Seedance / Veo 长镜头优化)
        </span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {hasTimeline ? (
            <TimelineDisplay timeline={frame.video_prompt_timeline!} />
          ) : (
            <div className="text-xs text-gray-500 leading-relaxed">
              将 video_prompt 切成 3 秒一段的 <code className="px-1 bg-white/10 rounded">&lt;nA-B&gt;</code> 时间窗,
              带 location / role / sound 元标签,适合长镜头 i2v 模型。
            </div>
          )}
          <ActionButton
            action={action}
            args={[frame.id]}
            icon={<Clock size={14} />}
            variant={hasTimeline ? "ghost" : "outline"}
            size="sm"
            disabled={!canSlice}
            title={
              !canSlice
                ? "需要先有 video_prompt 才能切时间轴"
                : "调用 LLM 把当前 video_prompt 切成时间窗"
            }
          >
            {hasTimeline ? "重新生成时间轴" : "生成时间轴"}
          </ActionButton>
        </div>
      )}
    </div>
  );
}
