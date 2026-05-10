"use client";

import { useEffect, useRef, useState } from "react";
import { Globe, Check, ChevronDown } from "lucide-react";
import clsx from "clsx";
import { useTranslation, SUPPORTED_LOCALES, type Locale } from "@/i18n";

interface LanguageSwitcherProps {
  /** "compact": icon-only button with dropdown — fits sidebars / headers.
   *  "inline": full-width segmented control — fits Settings page. */
  variant?: "compact" | "inline";
  className?: string;
}

export default function LanguageSwitcher({
  variant = "compact",
  className,
}: LanguageSwitcherProps) {
  const { locale, setLocale } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handle = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [open]);

  if (variant === "inline") {
    return (
      <div className={clsx("flex gap-2", className)}>
        {SUPPORTED_LOCALES.map((l) => {
          const isActive = l.code === locale;
          return (
            <button
              key={l.code}
              type="button"
              onClick={() => setLocale(l.code as Locale)}
              className={clsx(
                "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors",
                isActive
                  ? "border-primary/50 bg-primary/10 text-white"
                  : "border-white/10 bg-white/5 text-gray-300 hover:border-white/20 hover:bg-white/10",
              )}
              aria-pressed={isActive}
            >
              <span>{l.flag}</span>
              <span>{l.label}</span>
              {isActive && <Check size={14} className="text-primary" />}
            </button>
          );
        })}
      </div>
    );
  }

  const current = SUPPORTED_LOCALES.find((l) => l.code === locale) ?? SUPPORTED_LOCALES[0];

  return (
    <div ref={ref} className={clsx("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <Globe size={14} />
        <span className="flex-1 text-left">{current.label}</span>
        <ChevronDown size={12} className={clsx("transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div
          role="listbox"
          className="absolute bottom-full left-0 right-0 mb-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden z-30"
        >
          {SUPPORTED_LOCALES.map((l) => {
            const isActive = l.code === locale;
            return (
              <button
                key={l.code}
                type="button"
                role="option"
                aria-selected={isActive}
                onClick={() => {
                  setLocale(l.code as Locale);
                  setOpen(false);
                }}
                className={clsx(
                  "w-full flex items-center gap-2 px-3 py-2 text-xs text-left transition-colors",
                  isActive
                    ? "bg-primary/10 text-white"
                    : "text-gray-300 hover:bg-white/5 hover:text-white",
                )}
              >
                <span>{l.flag}</span>
                <span className="flex-1">{l.label}</span>
                {isActive && <Check size={12} className="text-primary" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
