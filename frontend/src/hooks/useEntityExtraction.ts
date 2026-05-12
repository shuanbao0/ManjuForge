"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "@/components/common/dialogs";
import { useProjectStore } from "@/store/projectStore";
import { useAsyncAction } from "./useAsyncAction";

/**
 * Hook for the incremental / full entity-extraction backend endpoint.
 *
 * On success: refreshes the active project so newly-created
 * characters/scenes/props show up in the entity panel, and surfaces a
 * toast summarising "created N · reused M" so the user can immediately
 * tell whether the run actually pulled in new entities.
 */
type ExtractStrategy = "incremental" | "full";

export function useEntityExtraction(scriptId: string | undefined) {
  const updateProject = useProjectStore((s) => s.updateProject);

  const doExtract = useCallback(
    async (strategy: ExtractStrategy) => {
      if (!scriptId) throw new Error("No active project");
      const result = await api.extractEntities(scriptId, strategy);
      try {
        const fresh = await api.getProject(scriptId);
        updateProject(scriptId, fresh);
      } catch {
        /* refresh failure is non-fatal */
      }
      const created =
        (result.created.characters?.length ?? 0)
        + (result.created.scenes?.length ?? 0)
        + (result.created.props?.length ?? 0);
      const reused =
        (result.reused.characters?.length ?? 0)
        + (result.reused.scenes?.length ?? 0)
        + (result.reused.props?.length ?? 0);
      toast.success(
        `${strategy === "incremental" ? "智能补齐" : "全量重提"}完成:新增 ${created} 项,复用 ${reused} 项`,
      );
      return result;
    },
    [scriptId, updateProject],
  );

  return useAsyncAction(doExtract);
}
