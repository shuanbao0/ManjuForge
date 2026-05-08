"use client";

import { useState, useEffect, useCallback } from "react";
import EnvConfigDialog from "@/components/project/EnvConfigDialog";
import { api } from "@/lib/api";
import { isAdmin, isAuthenticated, onAuthChange } from "@/lib/auth";

// Probes the instance-wide environment configuration and prompts the admin
// to fill in DASHSCOPE_API_KEY if it is missing. Per-user secrets live on
// /me/credentials and are handled elsewhere — this checker is admin-only
// because GET /config/env is gated by require_admin on the backend.
export default function EnvConfigChecker() {
  const [isEnvDialogOpen, setIsEnvDialogOpen] = useState(false);
  const [envRequired, setEnvRequired] = useState(false);

  const checkEnvConfig = useCallback(async () => {
    if (!isAuthenticated() || !isAdmin()) return;
    try {
      const config = await api.getEnvConfig();
      const dashscopeKey = config.DASHSCOPE_API_KEY?.trim();
      const hasRequired = !!dashscopeKey && dashscopeKey.length > 0;
      if (!hasRequired) {
        setEnvRequired(true);
        setIsEnvDialogOpen(true);
      }
    } catch (error) {
      console.error("Failed to check env config:", error);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    checkEnvConfig();
    return onAuthChange(() => {
      checkEnvConfig();
    });
  }, [checkEnvConfig]);

  return (
    <EnvConfigDialog
      isOpen={isEnvDialogOpen}
      onClose={() => {
        setIsEnvDialogOpen(false);
        setEnvRequired(false);
      }}
      isRequired={envRequired}
    />
  );
}
