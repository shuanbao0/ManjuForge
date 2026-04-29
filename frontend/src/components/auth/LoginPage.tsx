"use client";

import { useState } from "react";
import { Loader2, LogIn } from "lucide-react";
import { auth } from "@/lib/api";

interface Props {
  onLoggedIn: () => void;
}

export default function LoginPage({ onLoggedIn }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await auth.login(email.trim(), password);
      onLoggedIn();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: { code?: string; message?: string } } } })?.response?.data?.detail;
      const code = detail?.code;
      if (code === "INVALID_CREDENTIALS") setError("邮箱或密码不正确");
      else if (code === "USER_NOT_ACTIVE") setError("该账户已被禁用");
      else setError(detail?.message ?? "登录失败");
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
            <LogIn size={22} className="text-amber-400" />
          </div>
          <div>
            <h1 className="text-xl font-display font-bold text-white">登录</h1>
            <p className="text-xs text-gray-500 mt-0.5">使用管理员或用户账户登录 ManjuForge</p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">邮箱</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className={inputClass} autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">密码</label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} />
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
            {submitting ? "登录中..." : "登录"}
          </button>
        </form>
      </div>
    </div>
  );
}
