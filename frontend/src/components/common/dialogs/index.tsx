"use client";

import { dialogStore } from "./store";
import type { Variant, ConfirmVariant } from "./variants";

export { default as DialogProvider } from "./DialogProvider";

interface ToastOptions {
  title?: string;
  description?: string;
  duration?: number;
}

const DEFAULT_DURATION = 4000;

function buildToast(variant: Variant, message: string, opts?: ToastOptions): string {
  return dialogStore.pushToast({
    variant,
    message,
    title: opts?.title,
    description: opts?.description,
    duration: opts?.duration ?? DEFAULT_DURATION,
  });
}

interface ToastApi {
  (message: string, opts?: ToastOptions): string;
  success: (message: string, opts?: ToastOptions) => string;
  error: (message: string, opts?: ToastOptions) => string;
  warning: (message: string, opts?: ToastOptions) => string;
  info: (message: string, opts?: ToastOptions) => string;
  dismiss: (id: string) => void;
}

const baseToast: ToastApi = ((message: string, opts?: ToastOptions) =>
  buildToast("info", message, opts)) as ToastApi;
baseToast.success = (m, o) => buildToast("success", m, o);
baseToast.error = (m, o) => buildToast("error", m, o);
baseToast.warning = (m, o) => buildToast("warning", m, o);
baseToast.info = (m, o) => buildToast("info", m, o);
baseToast.dismiss = (id) => dialogStore.dismissToast(id);

export const toast = baseToast;

export interface ConfirmOptions {
  title: string;
  message?: string;
  variant?: ConfirmVariant;
  confirmLabel?: string;
  cancelLabel?: string;
}

export function confirmDialog(opts: ConfirmOptions): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    dialogStore.pushConfirm({
      title: opts.title,
      message: opts.message,
      variant: opts.variant ?? "info",
      confirmLabel: opts.confirmLabel,
      cancelLabel: opts.cancelLabel,
      resolve,
    });
  });
}

export interface PromptOptions {
  title: string;
  message?: string;
  variant?: ConfirmVariant;
  placeholder?: string;
  defaultValue?: string;
  inputType?: "text" | "password";
  confirmLabel?: string;
  cancelLabel?: string;
  validate?: (value: string) => string | null;
}

export function promptDialog(opts: PromptOptions): Promise<string | null> {
  return new Promise<string | null>((resolve) => {
    dialogStore.pushPrompt({
      title: opts.title,
      message: opts.message,
      variant: opts.variant ?? "info",
      placeholder: opts.placeholder,
      defaultValue: opts.defaultValue,
      inputType: opts.inputType,
      confirmLabel: opts.confirmLabel,
      cancelLabel: opts.cancelLabel,
      validate: opts.validate,
      resolve,
    });
  });
}

export type { Variant, ConfirmVariant };
