import { CheckCircle2, XCircle, AlertTriangle, Info, type LucideIcon } from "lucide-react";

export type Variant = "success" | "error" | "warning" | "info";

export interface VariantTokens {
  icon: LucideIcon;
  bar: string;
  iconColor: string;
  ring: string;
  orbBg: string;
  progress: string;
  confirmBtn: string;
  confirmShadow: string;
}

export const VARIANT_TOKENS: Record<Variant, VariantTokens> = {
  success: {
    icon: CheckCircle2,
    bar: "bg-emerald-400",
    iconColor: "text-emerald-400",
    ring: "ring-emerald-400/30",
    orbBg: "bg-emerald-500/10",
    progress: "bg-emerald-400/70",
    confirmBtn: "bg-emerald-600 hover:bg-emerald-500",
    confirmShadow: "shadow-emerald-500/25",
  },
  error: {
    icon: XCircle,
    bar: "bg-rose-400",
    iconColor: "text-rose-400",
    ring: "ring-rose-400/30",
    orbBg: "bg-rose-500/10",
    progress: "bg-rose-400/70",
    confirmBtn: "bg-rose-600 hover:bg-rose-500",
    confirmShadow: "shadow-rose-500/25",
  },
  warning: {
    icon: AlertTriangle,
    bar: "bg-amber-400",
    iconColor: "text-amber-400",
    ring: "ring-amber-400/30",
    orbBg: "bg-amber-500/10",
    progress: "bg-amber-400/70",
    confirmBtn: "bg-amber-600 hover:bg-amber-500",
    confirmShadow: "shadow-amber-500/25",
  },
  info: {
    icon: Info,
    bar: "bg-sky-400",
    iconColor: "text-sky-400",
    ring: "ring-sky-400/30",
    orbBg: "bg-sky-500/10",
    progress: "bg-sky-400/70",
    confirmBtn: "bg-sky-600 hover:bg-sky-500",
    confirmShadow: "shadow-sky-500/25",
  },
};

export type ConfirmVariant = "info" | "warning" | "danger";

export const CONFIRM_TOKENS: Record<ConfirmVariant, VariantTokens> = {
  info: VARIANT_TOKENS.info,
  warning: VARIANT_TOKENS.warning,
  danger: VARIANT_TOKENS.error,
};
