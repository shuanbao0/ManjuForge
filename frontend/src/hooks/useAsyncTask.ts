"use client";

import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";

/**
 * Shape of the task-status response from ``GET /tasks/{task_id}``.
 *
 * Fields are intentionally optional because different backend task types
 * surface different subsets — batch tasks expose progress counters,
 * one-shot tasks expose ``result``, export tasks expose ``output_url``,
 * etc. Read defensively and let TypeScript narrow per use case.
 */
export interface TaskStatus {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress?: number;
  error?: string | null;
  task_type?: string;

  // Batch fields
  total_count?: number;
  pending_count?: number;
  completed_count?: number;
  failed_count?: number;
  current_item_id?: string | null;
  current_frame_id?: string | null; // legacy alias for storyboard batch
  errors?: Record<string, string>;

  // One-shot / export fields
  result?: any;
  output_url?: string | null;
  current_stage?: string | null;
}

interface SubmitResponse {
  _task_id?: string;
  [k: string]: any;
}

interface AsyncTaskOpts {
  /** Function that POSTs the work and returns the response containing _task_id. */
  submit: () => Promise<SubmitResponse>;
  /** Called whenever a poll returns — use to drive a progress bar. */
  onProgress?: (status: TaskStatus) => void;
  /** Called once on terminal "completed". Receives the final TaskStatus. */
  onComplete?: (status: TaskStatus) => void | Promise<void>;
  /** Called once on terminal "failed". */
  onFail?: (err: Error, status?: TaskStatus) => void;
  /** Poll interval in ms (default 2000). */
  pollInterval?: number;
  /**
   * Optional side-effect run every ``refreshEvery`` polls — useful for
   * "refresh the project so finished items show up live during a long
   * batch". Errors here are swallowed (it's a polling nicety, not a
   * correctness path).
   */
  onPeriodicRefresh?: () => Promise<void>;
  refreshEvery?: number;
}

/**
 * Hook that submits a backend task, polls ``/tasks/{id}`` until terminal,
 * and exposes the live status to the caller.
 *
 * Centralizes the submit→poll→cleanup pattern so every batch/long-running
 * action UI (storyboard render-all, video render-all, audio render-all,
 * export, LLM polish) is one ``useAsyncTask`` call instead of 80 lines of
 * setInterval bookkeeping.
 *
 * Polling stops automatically on completion, failure, error, or unmount.
 */
export function useAsyncTask(opts: AsyncTaskOpts) {
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [active, setActive] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setActive(false);
  }, []);

  const start = useCallback(async () => {
    if (active) return;
    setActive(true);
    setStatus(null);

    try {
      const initial = await opts.submit();
      const taskId = initial?._task_id;

      if (!taskId) {
        // Backwards-compat: ancient backend returning the result inline.
        // Synthesize a "completed" status so callers can treat it uniformly.
        const synthetic: TaskStatus = {
          task_id: "inline",
          status: "completed",
          progress: 100,
          result: initial,
        };
        setStatus(synthetic);
        await opts.onComplete?.(synthetic);
        setActive(false);
        return;
      }

      let tick = 0;
      const refreshEvery = opts.refreshEvery ?? 3;
      await new Promise<void>((resolve, reject) => {
        intervalRef.current = setInterval(async () => {
          tick += 1;
          try {
            const s: TaskStatus = await api.getTaskStatus(taskId);
            setStatus(s);
            opts.onProgress?.(s);

            if (opts.onPeriodicRefresh && tick % refreshEvery === 0) {
              try { await opts.onPeriodicRefresh(); } catch { /* polling, ignore */ }
            }

            if (s.status === "completed") {
              stop();
              await opts.onComplete?.(s);
              resolve();
            } else if (s.status === "failed") {
              stop();
              const err = new Error(s.error || "task failed");
              opts.onFail?.(err, s);
              reject(err);
            }
          } catch (err) {
            stop();
            opts.onFail?.(err as Error);
            reject(err);
          }
        }, opts.pollInterval ?? 2000);
      });
    } catch (err) {
      stop();
      opts.onFail?.(err as Error);
    }
  }, [active, opts, stop]);

  return { start, stop, active, status };
}
