import type { Variant, ConfirmVariant } from "./variants";

export interface ToastItem {
  id: string;
  variant: Variant;
  title?: string;
  description?: string;
  message: string;
  duration: number;
  createdAt: number;
}

export interface ConfirmRequest {
  id: string;
  title: string;
  message?: string;
  variant: ConfirmVariant;
  confirmLabel?: string;
  cancelLabel?: string;
  resolve: (ok: boolean) => void;
}

export interface PromptRequest {
  id: string;
  title: string;
  message?: string;
  variant: ConfirmVariant;
  placeholder?: string;
  defaultValue?: string;
  inputType?: "text" | "password";
  confirmLabel?: string;
  cancelLabel?: string;
  validate?: (value: string) => string | null;
  resolve: (value: string | null) => void;
}

interface State {
  toasts: ToastItem[];
  confirmQueue: ConfirmRequest[];
  promptQueue: PromptRequest[];
}

type Listener = () => void;

const state: State = { toasts: [], confirmQueue: [], promptQueue: [] };
const listeners = new Set<Listener>();

let snapshot: State = state;

function commit() {
  snapshot = {
    toasts: [...state.toasts],
    confirmQueue: [...state.confirmQueue],
    promptQueue: [...state.promptQueue],
  };
  listeners.forEach((l) => l());
}

export const dialogStore = {
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  getSnapshot(): State {
    return snapshot;
  },
  getServerSnapshot(): State {
    return { toasts: [], confirmQueue: [], promptQueue: [] };
  },
  pushToast(t: Omit<ToastItem, "id" | "createdAt">): string {
    const id = `t_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    state.toasts.push({ ...t, id, createdAt: Date.now() });
    commit();
    return id;
  },
  dismissToast(id: string) {
    const i = state.toasts.findIndex((t) => t.id === id);
    if (i >= 0) {
      state.toasts.splice(i, 1);
      commit();
    }
  },
  pushConfirm(req: Omit<ConfirmRequest, "id">): string {
    const id = `c_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    state.confirmQueue.push({ ...req, id });
    commit();
    return id;
  },
  resolveConfirm(id: string, ok: boolean) {
    const i = state.confirmQueue.findIndex((c) => c.id === id);
    if (i >= 0) {
      const [req] = state.confirmQueue.splice(i, 1);
      commit();
      req.resolve(ok);
    }
  },
  pushPrompt(req: Omit<PromptRequest, "id">): string {
    const id = `p_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    state.promptQueue.push({ ...req, id });
    commit();
    return id;
  },
  resolvePrompt(id: string, value: string | null) {
    const i = state.promptQueue.findIndex((p) => p.id === id);
    if (i >= 0) {
      const [req] = state.promptQueue.splice(i, 1);
      commit();
      req.resolve(value);
    }
  },
};
