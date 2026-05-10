"use client";

import { useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence } from "framer-motion";
import Toast from "./Toast";
import { dialogStore } from "./store";

export default function ToastViewport() {
  const { toasts } = useSyncExternalStore(
    dialogStore.subscribe,
    dialogStore.getSnapshot,
    dialogStore.getServerSnapshot,
  );

  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed top-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none">
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <Toast key={t.id} toast={t} />
        ))}
      </AnimatePresence>
    </div>,
    document.body,
  );
}
