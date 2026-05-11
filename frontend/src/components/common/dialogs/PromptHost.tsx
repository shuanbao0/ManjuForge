"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff } from "lucide-react";
import { CONFIRM_TOKENS } from "./variants";
import { dialogStore, type PromptRequest } from "./store";
import { useTranslation } from "@/i18n";

export default function PromptHost() {
  const { promptQueue } = useSyncExternalStore(
    dialogStore.subscribe,
    dialogStore.getSnapshot,
    dialogStore.getServerSnapshot,
  );
  const current = promptQueue[0];
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>{current && <PromptModal req={current} />}</AnimatePresence>,
    document.body,
  );
}

function PromptModal({ req }: { req: PromptRequest }) {
  const { t } = useTranslation();
  const tokens = CONFIRM_TOKENS[req.variant];
  const Icon = tokens.icon;
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState(req.defaultValue ?? "");
  const [error, setError] = useState<string | null>(null);
  const [reveal, setReveal] = useState(false);
  const isPassword = req.inputType === "password";

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = () => {
    if (req.validate) {
      const err = req.validate(value);
      if (err) {
        setError(err);
        return;
      }
    }
    dialogStore.resolvePrompt(req.id, value);
  };
  const cancel = () => dialogStore.resolvePrompt(req.id, null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        cancel();
      } else if (e.key === "Enter") {
        e.preventDefault();
        submit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      className="fixed inset-0 z-[110] flex items-center justify-center bg-black/70 backdrop-blur-md p-4"
      onClick={cancel}
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
          <div className="mt-5 relative">
            <input
              ref={inputRef}
              type={isPassword && !reveal ? "password" : "text"}
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                if (error) setError(null);
              }}
              placeholder={req.placeholder}
              className="w-full rounded-lg bg-white/5 border border-white/10 px-3.5 py-2.5 pr-10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-colors"
            />
            {isPassword && (
              <button
                type="button"
                onClick={() => setReveal((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-gray-500 hover:text-gray-300 transition-colors"
                aria-label={reveal ? "Hide" : "Show"}
              >
                {reveal ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            )}
          </div>
          {error && (
            <p className="mt-2 text-xs text-rose-400 leading-snug">{error}</p>
          )}
        </div>
        <div className="flex justify-end gap-2 px-6 pb-6">
          <button
            onClick={cancel}
            className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
          >
            {req.cancelLabel ?? t("dialogs.cancel", undefined, "取消")}
          </button>
          <button
            onClick={submit}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white shadow-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-white/30 ${tokens.confirmBtn} ${tokens.confirmShadow}`}
          >
            {req.confirmLabel ?? t("dialogs.confirm", undefined, "确认")}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
