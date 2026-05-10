"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { X } from "lucide-react";
import { VARIANT_TOKENS } from "./variants";
import { dialogStore, type ToastItem } from "./store";

interface Props {
  toast: ToastItem;
}

export default function Toast({ toast }: Props) {
  const tokens = VARIANT_TOKENS[toast.variant];
  const Icon = tokens.icon;
  const [progress, setProgress] = useState(100);
  const pausedRef = useRef(false);

  useEffect(() => {
    if (toast.duration <= 0) return;
    let raf = 0;
    let lastTick = performance.now();
    let elapsed = 0;

    const tick = (now: number) => {
      const dt = now - lastTick;
      lastTick = now;
      if (!pausedRef.current) elapsed += dt;
      const remaining = Math.max(0, 1 - elapsed / toast.duration);
      setProgress(remaining * 100);
      if (remaining <= 0) {
        dialogStore.dismissToast(toast.id);
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [toast.id, toast.duration]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.95, transition: { duration: 0.18 } }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
      onMouseEnter={() => { pausedRef.current = true; }}
      onMouseLeave={() => { pausedRef.current = false; }}
      className="relative w-[360px] overflow-hidden rounded-xl border border-white/5 bg-gray-900/95 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.45)] pointer-events-auto"
    >
      <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${tokens.bar}`} />
      <div className="flex items-start gap-3 p-3.5 pl-4">
        <div className={`mt-0.5 ${tokens.iconColor} shrink-0`}>
          <Icon size={18} strokeWidth={2.25} />
        </div>
        <div className="min-w-0 flex-1">
          {toast.title && (
            <div className="text-sm font-medium text-white leading-snug">{toast.title}</div>
          )}
          <div
            className={`text-sm leading-snug ${
              toast.title ? "text-gray-400 mt-0.5" : "text-gray-200"
            } break-words`}
          >
            {toast.message}
          </div>
          {toast.description && (
            <div className="text-xs text-gray-500 mt-1 leading-snug break-words">
              {toast.description}
            </div>
          )}
        </div>
        <button
          onClick={() => dialogStore.dismissToast(toast.id)}
          className="shrink-0 -mr-1 -mt-1 p-1 rounded-md text-gray-500 hover:text-gray-200 hover:bg-white/5 transition-colors"
          aria-label="Close"
        >
          <X size={14} />
        </button>
      </div>
      {toast.duration > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/5">
          <div
            className={`h-full ${tokens.progress} transition-[width] duration-100 ease-linear`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </motion.div>
  );
}
