"use client";

import { ReactNode } from "react";
import { Loader2 } from "lucide-react";
import clsx from "clsx";
import type { AsyncAction } from "@/hooks/useAsyncAction";

/**
 * Button paired with an :type:`AsyncAction`.
 *
 * Renders a spinner + disables itself while the action is pending and
 * forwards click → action.run. Visual variants follow the rest of the
 * app's button styles (primary / outline / danger / ghost).
 *
 * Compound Component: callers pass the underlying hook and click
 * arguments declaratively instead of wiring isPending / disabled by
 * hand. Five new features all use this — no per-feature button
 * boilerplate.
 */
type Variant = "primary" | "outline" | "danger" | "ghost";

interface ActionButtonProps<TArgs extends any[], TResult> {
  action: AsyncAction<TArgs, TResult>;
  /** Arguments to forward to ``action.run`` when clicked. */
  args: TArgs;
  children: ReactNode;
  /** Optional icon to render before the label (hidden while pending). */
  icon?: ReactNode;
  variant?: Variant;
  size?: "sm" | "md";
  className?: string;
  /** Extra disable signal beyond ``action.isPending``. */
  disabled?: boolean;
  /** Override the rendered title; defaults to children string when given. */
  title?: string;
}

const VARIANT_STYLES: Record<Variant, string> = {
  primary:
    "bg-primary hover:bg-primary/90 text-white border-transparent",
  outline:
    "bg-transparent hover:bg-white/5 text-white border-white/15",
  danger:
    "bg-red-600 hover:bg-red-700 text-white border-transparent",
  ghost:
    "bg-transparent hover:bg-white/10 text-gray-200 border-transparent",
};

const SIZE_STYLES = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
};

export function ActionButton<TArgs extends any[], TResult>({
  action,
  args,
  children,
  icon,
  variant = "primary",
  size = "md",
  className,
  disabled,
  title,
}: ActionButtonProps<TArgs, TResult>) {
  const isDisabled = disabled || action.isPending;
  return (
    <button
      type="button"
      onClick={() => {
        if (!isDisabled) {
          action.run(...args);
        }
      }}
      disabled={isDisabled}
      title={title}
      className={clsx(
        "inline-flex items-center gap-2 rounded-lg border font-medium transition-colors",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        VARIANT_STYLES[variant],
        SIZE_STYLES[size],
        className,
      )}
    >
      {action.isPending ? (
        <Loader2 className="animate-spin" size={size === "sm" ? 14 : 16} />
      ) : (
        icon
      )}
      <span>{children}</span>
    </button>
  );
}
