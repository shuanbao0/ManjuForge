"use client";

import { useEffect, type ReactNode } from "react";
import ToastViewport from "./ToastViewport";
import ConfirmHost from "./ConfirmHost";
import PromptHost from "./PromptHost";
import { toast } from "./index";

declare global {
  interface Window {
    __nativeAlert?: typeof window.alert;
  }
}

export default function DialogProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!window.__nativeAlert) {
      window.__nativeAlert = window.alert.bind(window);
    }
    window.alert = (msg?: unknown) => {
      const text = msg == null ? "" : String(msg);
      toast.info(text);
    };
    return () => {
      if (window.__nativeAlert) window.alert = window.__nativeAlert;
    };
  }, []);

  return (
    <>
      {children}
      <ToastViewport />
      <ConfirmHost />
      <PromptHost />
    </>
  );
}
