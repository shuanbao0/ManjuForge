"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import zhCN from "./locales/zh-CN";
import enUS from "./locales/en-US";

export type Locale = "zh-CN" | "en-US";

export const SUPPORTED_LOCALES: { code: Locale; label: string; flag: string }[] = [
  { code: "zh-CN", label: "简体中文", flag: "🇨🇳" },
  { code: "en-US", label: "English", flag: "🇺🇸" },
];

const LS_KEY = "manju_forge_locale";
const DEFAULT_LOCALE: Locale = "zh-CN";

type Messages = typeof zhCN;

const BUNDLES: Record<Locale, unknown> = {
  "zh-CN": zhCN,
  "en-US": enUS,
};

function detectInitialLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  try {
    const stored = window.localStorage.getItem(LS_KEY);
    if (stored === "zh-CN" || stored === "en-US") return stored;
  } catch {
    /* ignore */
  }
  // Chinese-first product: default to zh-CN unless the user has explicitly
  // chosen otherwise. Don't auto-switch on navigator.language, which surprises
  // users on English-locale browsers and breaks tests that assert on the
  // default UI copy.
  return DEFAULT_LOCALE;
}

function lookup(bundle: unknown, key: string): string | undefined {
  let cur: unknown = bundle;
  for (const part of key.split(".")) {
    if (cur && typeof cur === "object" && part in (cur as Record<string, unknown>)) {
      cur = (cur as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return typeof cur === "string" ? cur : undefined;
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{\{\s*([\w.-]+)\s*\}\}/g, (m, name) => {
    const v = vars[name];
    return v === undefined || v === null ? m : String(v);
  });
}

export type TFunction = (
  key: string,
  vars?: Record<string, string | number>,
  fallback?: string,
) => string;

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: TFunction;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  // Hydrate from localStorage / navigator after mount to avoid SSR mismatch.
  useEffect(() => {
    const next = detectInitialLocale();
    setLocaleState(next);
  }, []);

  // Reflect locale on <html lang="..."> for accessibility.
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(LS_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const t = useCallback<TFunction>(
    (key, vars, fallback) => {
      const primary = lookup(BUNDLES[locale], key);
      if (primary != null) return interpolate(primary, vars);
      const zh = lookup(BUNDLES[DEFAULT_LOCALE], key);
      if (zh != null) return interpolate(zh, vars);
      return fallback ?? key;
    },
    [locale],
  );

  const value = useMemo<I18nContextValue>(
    () => ({ locale, setLocale, t }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useTranslation(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    // Provider missing — give callers a safe fallback rather than crashing.
    // Returns the default-locale string so screens still render correctly.
    const tFallback: TFunction = (key, vars, fallback) => {
      const zh = lookup(BUNDLES[DEFAULT_LOCALE], key);
      if (zh != null) return interpolate(zh, vars);
      return fallback ?? key;
    };
    return { locale: DEFAULT_LOCALE, setLocale: () => undefined, t: tFallback };
  }
  return ctx;
}

export type { Messages };
