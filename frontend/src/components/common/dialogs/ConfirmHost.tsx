"use client";

import { useEffect, useRef, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { CONFIRM_TOKENS } from "./variants";
import { dialogStore, type ConfirmRequest } from "./store";
import { useTranslation } from "@/i18n";

export default function ConfirmHost() {
  const { confirmQueue } = useSyncExternalStore(
    dialogStore.subscribe,
    dialogStore.getSnapshot,
    dialogStore.getServerSnapshot,
  );
  const current = confirmQueue[0];

  if (typeof document === "undefined") return null;

  return createPortal(
    <AnimatePresence>{current && <ConfirmModal req={current} />}</AnimatePresence>,
    document.body,
  );
}

function ConfirmModal({ req }: { req: ConfirmRequest }) {
  const { t } = useTranslation();
  const tokens = CONFIRM_TOKENS[req.variant];
  const Icon = tokens.icon;
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    confirmRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        dialogStore.resolveConfirm(req.id, false);
      } else if (e.key === "Enter") {
        e.preventDefault();
        dialogStore.resolveConfirm(req.id, true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [req.id]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      className="fixed inset-0 z-[110] flex items-center justify-center bg-black/70 backdrop-blur-md p-4"
      onClick={() => dialogStore.resolveConfirm(req.id, false)}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 4, transition: { duration: 0.15 } }}
        transition={{ type: "spring", stiffness: 380, damping: 30 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-white/10 bg-gradient-to-b from-gray-900 to-gray-950 shadow-2xl"
      >
        <div className="p-6">
          <div className="flex items-start gap-4">
            <div
              className={`shrink-0 w-12 h-12 rounded-full flex items-center justify-center ${tokens.orbBg} ring-1 ${tokens.ring}`}
            >
              <Icon size={22} className={tokens.iconColor} strokeWidth={2.25} />
            </div>
            <div className="min-w-0 flex-1 pt-0.5">
              <h3 className="text-base font-semibold text-white leading-snug">{req.title}</h3>
              {req.message && (
                <p className="mt-2 text-sm text-gray-400 leading-relaxed whitespace-pre-line break-words">
                  {req.message}
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-6 pb-6">
          <button
            onClick={() => dialogStore.resolveConfirm(req.id, false)}
            className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
          >
            {req.cancelLabel ?? t("dialogs.cancel", undefined, "取消")}
          </button>
          <button
            ref={confirmRef}
            onClick={() => dialogStore.resolveConfirm(req.id, true)}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white shadow-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-white/30 ${tokens.confirmBtn} ${tokens.confirmShadow}`}
          >
            {req.confirmLabel ?? t("dialogs.confirm", undefined, "确认")}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
