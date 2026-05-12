"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "@/components/common/dialogs";
import { useProjectStore } from "@/store/projectStore";
import { useAsyncAction } from "./useAsyncAction";

/**
 * Hook driving "auto-assign voices" — wraps the API call, refreshes the
 * project after success, and surfaces a toast summary.
 *
 * Returns an :type:`AsyncAction` for direct use with ``<ActionButton>``.
 */
export function useAutoVoices(scriptId: string | undefined) {
  const updateProject = useProjectStore((s) => s.updateProject);

  const doAssign = useCallback(async () => {
    if (!scriptId) throw new Error("No active project");
    const result = await api.autoAssignVoices(scriptId);
    // Refresh project so character.voice_id / voice_name show through.
    try {
      const fresh = await api.getProject(scriptId);
      updateProject(scriptId, fresh);
    } catch {
      /* refresh failure is non-fatal — the assignment already persisted */
    }
    const assigned = Object.keys(result.assignments || {}).length;
    const skipped = (result.skipped || []).length;
    if (assigned > 0) {
      toast.success(
        skipped > 0
          ? `自动配音完成:已分配 ${assigned} 个角色,跳过 ${skipped} 个已锁定角色`
          : `自动配音完成:已分配 ${assigned} 个角色`,
      );
    } else {
      toast.info(
        skipped > 0
          ? `所有 ${skipped} 个角色都已手动锁定,跳过自动分配`
          : "没有可分配的角色",
      );
    }
    return result;
  }, [scriptId, updateProject]);

  return useAsyncAction(doAssign);
}
