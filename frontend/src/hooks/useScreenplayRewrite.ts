"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "@/components/common/dialogs";
import { useProjectStore } from "@/store/projectStore";
import { useAsyncAction } from "./useAsyncAction";

/**
 * Hook for the novel → screenplay-format rewrite endpoint.
 *
 * On success: refreshes the project so ``formatted_text`` lands in the
 * store, then toasts a short confirmation. The original text is
 * preserved server-side so this is a non-destructive enrichment.
 */
export function useScreenplayRewrite(scriptId: string | undefined) {
  const updateProject = useProjectStore((s) => s.updateProject);

  const doRewrite = useCallback(async () => {
    if (!scriptId) throw new Error("No active project");
    const result = await api.rewriteToScreenplay(scriptId);
    try {
      const fresh = await api.getProject(scriptId);
      updateProject(scriptId, fresh);
    } catch {
      /* non-fatal */
    }
    toast.success("已生成剧本格式,可在「剧本格式」标签查看");
    return result;
  }, [scriptId, updateProject]);

  return useAsyncAction(doRewrite);
}
