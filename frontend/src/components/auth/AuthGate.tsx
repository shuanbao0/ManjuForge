"use client";

import { ReactNode, useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { auth as authApi } from "@/lib/api";
import { isAuthenticated, getCurrentUser, onAuthChange, clearSession } from "@/lib/auth";
import LoginPage from "./LoginPage";
import SetupPage from "./SetupPage";

type Phase = "loading" | "needs-setup" | "needs-login" | "authed";

interface Props {
  children: ReactNode;
}

export default function AuthGate({ children }: Props) {
  const [phase, setPhase] = useState<Phase>("loading");

  const refresh = useCallback(async () => {
    try {
      const status = await authApi.setupStatus();
      if (status.needs_setup) {
        clearSession();
        setPhase("needs-setup");
        return;
      }
    } catch {
      // If setup-status fails (network), assume the app is unreachable. Showing
      // the login screen lets the user retry once the backend is back up.
      setPhase("needs-login");
      return;
    }

    if (!isAuthenticated()) {
      setPhase("needs-login");
      return;
    }

    // Validate the cached token against /auth/me — protects against revoked
    // tokens persisted in localStorage from a previous session.
    try {
      await authApi.me();
      setPhase("authed");
    } catch {
      clearSession();
      setPhase("needs-login");
    }
  }, []);

  useEffect(() => {
    refresh();
    const off = onAuthChange(() => {
      // Token may have been written / cleared in another tab via the
      // storage event, or in *this* tab via login/logout. We re-evaluate
      // unconditionally so the gate flips to /login the moment the token
      // disappears, even if the user was mid-session in this tab.
      if (!isAuthenticated()) {
        setPhase("needs-login");
        return;
      }
      if (getCurrentUser()) {
        setPhase("authed");
      }
    });
    return off;
  }, [refresh]);

  if (phase === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-950 via-gray-900 to-black">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">加载中…</span>
        </div>
      </div>
    );
  }

  if (phase === "needs-setup") {
    return <SetupPage onComplete={() => setPhase("authed")} />;
  }

  if (phase === "needs-login") {
    return <LoginPage onLoggedIn={() => setPhase("authed")} />;
  }

  return <>{children}</>;
}
