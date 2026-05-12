"use client";

import { useCallback, useRef, useState } from "react";

/**
 * Template Method hook for one-shot synchronous backend actions.
 *
 * Differs from :func:`useAsyncTask`: that hook submits a request that
 * returns a ``_task_id`` and polls ``/tasks/{id}`` until terminal. The
 * actions wired into ``useAsyncAction`` instead return their result
 * directly (e.g. ``api.autoAssignVoices``,
 * ``api.rewriteToScreenplay``) — we just need ``isPending`` /
 * ``result`` / ``error`` lifecycle without polling overhead.
 *
 * The five huobao-parity feature hooks
 * (``useScreenplayRewrite``/``useEntityExtraction``/``useAutoVoices``/
 * ``useTimelineSlicer``/``useBatchKeyframes``) all stack on top of this
 * so the lifecycle stays uniform — Template Method pattern at the hook
 * level.
 *
 * Cancellation: a stale-result guard discards results from any
 * invocation that was superseded by a newer call or an unmount before
 * resolve. The underlying request still finishes server-side; only the
 * client-side state is fenced.
 */
export interface AsyncAction<TArgs extends any[], TResult> {
  /** Run the action. Returns the result, or ``null`` if the call was
   *  superseded by another invocation before it resolved. */
  run: (...args: TArgs) => Promise<TResult | null>;
  isPending: boolean;
  error: Error | null;
  result: TResult | null;
  /** Forget result + error without changing isPending. */
  reset: () => void;
}

export function useAsyncAction<TArgs extends any[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
): AsyncAction<TArgs, TResult> {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [result, setResult] = useState<TResult | null>(null);

  // Generation counter — every run() bumps this; results from older
  // generations are discarded so React state can never lag behind the
  // user's latest click.
  const generationRef = useRef(0);

  const run = useCallback(
    async (...args: TArgs): Promise<TResult | null> => {
      const myGen = ++generationRef.current;
      setIsPending(true);
      setError(null);
      try {
        const data = await fn(...args);
        if (generationRef.current !== myGen) return null;
        setResult(data);
        return data;
      } catch (e: any) {
        if (generationRef.current !== myGen) return null;
        const err = e instanceof Error ? e : new Error(String(e?.message ?? e));
        setError(err);
        return null;
      } finally {
        if (generationRef.current === myGen) {
          setIsPending(false);
        }
      }
    },
    [fn],
  );

  const reset = useCallback(() => {
    generationRef.current++;
    setResult(null);
    setError(null);
  }, []);

  return { run, isPending, error, result, reset };
}
