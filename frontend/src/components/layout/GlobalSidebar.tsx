"use client";

import { FolderOpen, Library, Settings, ShieldCheck, LogOut } from "lucide-react";
import clsx from "clsx";
import { useEffect, useState } from "react";
import ManjuForgeBranding from "./ManjuForgeBranding";
import { auth as authApi } from "@/lib/api";
import { getCurrentUser, isAdmin, onAuthChange, type CurrentUser } from "@/lib/auth";

export type GlobalTab = "workspace" | "library" | "settings" | "admin";

interface GlobalSidebarProps {
  activeTab: GlobalTab;
  onTabChange: (tab: GlobalTab) => void;
}

const NAV_ITEMS: { id: GlobalTab; label: string; icon: typeof FolderOpen; hash: string }[] = [
  { id: "workspace", label: "工作区", icon: FolderOpen, hash: "#/" },
  { id: "library", label: "主体库", icon: Library, hash: "#/library" },
  { id: "settings", label: "设置", icon: Settings, hash: "#/settings" },
];

export default function GlobalSidebar({ activeTab, onTabChange }: GlobalSidebarProps) {
  const [user, setUser] = useState<CurrentUser | null>(() => getCurrentUser());

  useEffect(() => {
    const off = onAuthChange(() => setUser(getCurrentUser()));
    return off;
  }, []);

  const handleNav = (item: (typeof NAV_ITEMS)[number]) => {
    onTabChange(item.id);
    window.location.hash = item.hash;
  };

  const handleAdmin = () => {
    onTabChange("admin");
    window.location.hash = "#/admin";
  };

  const handleLogout = async () => {
    await authApi.logout();
    if (typeof window !== "undefined") {
      window.location.hash = "";
      window.location.reload();
    }
  };

  return (
    <aside className="w-56 flex-shrink-0 h-full border-r border-glass-border bg-black/40 backdrop-blur-xl flex flex-col">
      {/* Branding */}
      <div className="p-5 border-b border-glass-border">
        <ManjuForgeBranding size="sm" />
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => handleNav(item)}
              className={clsx(
                "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 relative overflow-hidden",
                isActive
                  ? "bg-primary/10 text-white"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              )}
            >
              {isActive && (
                <div className="absolute left-0 w-1 h-full bg-primary rounded-r" />
              )}
              <Icon size={18} className={isActive ? "text-primary" : ""} />
              <span className="text-sm font-medium">{item.label}</span>
            </button>
          );
        })}

        {isAdmin() && (
          <button
            onClick={handleAdmin}
            className={clsx(
              "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 relative overflow-hidden mt-2",
              activeTab === "admin"
                ? "bg-amber-500/10 text-white"
                : "text-amber-300/80 hover:text-amber-200 hover:bg-amber-500/5"
            )}
          >
            {activeTab === "admin" && (
              <div className="absolute left-0 w-1 h-full bg-amber-500 rounded-r" />
            )}
            <ShieldCheck size={18} />
            <span className="text-sm font-medium">管理控制台</span>
          </button>
        )}
      </nav>

      {/* Footer: user + logout */}
      <div className="p-4 border-t border-glass-border space-y-2">
        {user && (
          <div className="px-2 py-1">
            <div className="text-xs font-medium text-gray-300 truncate">{user.display_name || user.email}</div>
            <div className="text-[10px] text-gray-500 truncate">{user.email}</div>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
        >
          <LogOut size={14} />
          退出登录
        </button>
        <span className="text-xs text-gray-600 block px-2">v0.1.0</span>
      </div>
    </aside>
  );
}
