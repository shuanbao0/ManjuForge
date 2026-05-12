"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "@/components/common/dialogs";
import { useProjectStore } from "@/store/projectStore";
import { useAsyncAction } from "./useAsyncAction";

/**
 * Hook for slicing a frame's ``video_prompt`` into time-axis form.
 *
 * Returns an action that takes ``(frameId, segmentSeconds?, durationOverride?)``.
 * After success, refreshes the project so ``frame.video_prompt_timeline``
 * lands in the store and the StoryboardFrameEditor re-renders.
 */
export function useTimelineSlicer(scriptId: string | undefined) {
  const updateProject = useProjectStore((s) => s.updateProject);

  const doSlice = useCallback(
    async (
      frameId: string,
      opts: { segmentSeconds?: number; durationOverride?: number } = {},
    ) => {
      if (!scriptId) throw new Error("No active project");
      const result = await api.sliceVideoTimeline(scriptId, frameId, opts);
      try {
        const fresh = await api.getProject(scriptId);
        updateProject(scriptId, fresh);
      } catch {
        /* non-fatal */
      }
      toast.success("已生成时间轴切片");
      return result;
    },
    [scriptId, updateProject],
  );

  return useAsyncAction(doSlice);
}
