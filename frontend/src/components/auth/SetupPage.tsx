"use client";

import { useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { auth } from "@/lib/api";
import { useTranslation } from "@/i18n";

interface Props {
  onComplete: () => void;
}

export default function SetupPage({ onComplete }: Props) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError(t("auth.passwordTooShort"));
      return;
    }
    if (password !== confirm) {
      setError(t("auth.passwordMismatch"));
      return;
    }
    setSubmitting(true);
    try {
      await auth.setup(email.trim(), password, displayName.trim());
      onComplete();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail;
      setError(detail?.message ?? t("auth.setupRetry", undefined, "初始化失败，请稍后重试"));
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-amber-500/50 transition-colors";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-950 via-gray-900 to-black px-6">
      <div className="w-full max-w-md glass-panel rounded-2xl p-8 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-xl">
            <ShieldCheck size={22} className="text-amber-400" />
          </div>
          <div>
            <h1 className="text-xl font-display font-bold text-white">{t("auth.setupTitle", undefined, "初始化管理员")}</h1>
            <p className="text-xs text-gray-500 mt-0.5">{t("auth.setupSubtitle")}</p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t("auth.emailLabel")} <span className="text-red-500">*</span></label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("auth.adminEmailPlaceholder", undefined, "admin@example.com")} className={inputClass} autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t("auth.displayNameOptional", undefined, "显示名（可选）")}</label>
            <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder={t("auth.adminDisplayPlaceholder", undefined, "管理员")} className={inputClass} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t("auth.passwordLabel")} <span className="text-red-500">*</span></label>
            <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("auth.passwordMinPlaceholder", undefined, "至少 8 位")} className={inputClass} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t("auth.confirmPasswordLabel", undefined, "确认密码")} <span className="text-red-500">*</span></label>
            <input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} className={inputClass} />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">{error}</div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50"
          >
            {submitting ? <Loader2 size={16} className="animate-spin" /> : null}
            {submitting ? t("auth.setupSubmitting") : t("auth.setupSubmit")}
          </button>
        </form>
      </div>
    </div>
  );
}
