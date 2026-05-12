"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "@/components/common/dialogs";
import { useProjectStore } from "@/store/projectStore";
import { useAsyncAction } from "./useAsyncAction";

export type BatchKeyframeMode = "first_frame" | "first_last" | "multi_ref";

/**
 * Hook for batch keyframe generation across multiple frames.
 *
 * Returns an action that takes
 * ``(frameIds, { mode, forcePerShot })``. On success refreshes the
 * project (frame ``rendered_image_asset`` / ``end_frame_asset`` /
 * variants now carry new tiles) and toasts a summary of method used
 * (grid vs per-shot) plus the vendor that handled the call.
 */
export function useBatchKeyframes(scriptId: string | undefined) {
  const updateProject = useProjectStore((s) => s.updateProject);

  const doBatch = useCallback(
    async (
      frameIds: string[],
      opts: { mode?: BatchKeyframeMode; forcePerShot?: boolean } = {},
    ) => {
      if (!scriptId) throw new Error("No active project");
      if (frameIds.length === 0) throw new Error("Pick at least one frame");
      const result = await api.batchKeyframes(scriptId, frameIds, opts);
      try {
        const fresh = await api.getProject(scriptId);
        updateProject(scriptId, fresh);
      } catch {
        /* non-fatal */
      }
      const tileCount = Object.values(result.assignments || {}).reduce(
        (sum, urls) => sum + (urls?.length ?? 0),
        0,
      );
      const methodLabel = result.method === "grid" ? "网格出图" : "逐镜出图";
      toast.success(
        `${methodLabel}完成(${result.vendor ?? "默认"}):${frameIds.length} 镜 · ${tileCount} 张图`,
      );
      return result;
    },
    [scriptId, updateProject],
  );

  return useAsyncAction(doBatch);
}
