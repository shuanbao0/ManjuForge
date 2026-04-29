"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2,
  Users,
  ShieldCheck,
  Trash2,
  RefreshCw,
  PlusCircle,
  Lock,
  UserPlus,
  Activity,
  Settings as SettingsIcon,
  LogOut,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  admin,
  type AdminSettings,
  type AdminStats,
  type AuditLogEntry,
} from "@/lib/api";
import { type CurrentUser, getCurrentUser } from "@/lib/auth";

type Tab = "users" | "stats" | "audit" | "settings";

export default function AdminPanel() {
  const me = getCurrentUser();
  const [tab, setTab] = useState<Tab>("users");

  return (
    <div className="container mx-auto px-6 py-8 max-w-6xl space-y-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-lg">
            <ShieldCheck size={20} className="text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-display font-bold text-white">管理员控制台</h1>
            <p className="text-xs text-gray-500">登录身份：{me?.email ?? "—"}</p>
          </div>
        </div>
      </header>

      <nav className="flex gap-2 border-b border-white/10">
        {([
          { key: "users", label: "用户", icon: Users },
          { key: "stats", label: "统计", icon: Activity },
          { key: "audit", label: "审计日志", icon: Lock },
          { key: "settings", label: "实例设置", icon: SettingsIcon },
        ] as const).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? "border-amber-500 text-amber-300"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </nav>

      {tab === "users" && <UsersTab />}
      {tab === "stats" && <StatsTab />}
      {tab === "audit" && <AuditTab />}
      {tab === "settings" && <SettingsTab />}
    </div>
  );
}

// ── Users tab ──────────────────────────────────────────────────────────────

function UsersTab() {
  const me = getCurrentUser();
  const [users, setUsers] = useState<CurrentUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setUsers(await admin.listUsers());
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail;
      setError(detail?.message ?? "加载用户失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const sorted = useMemo(() => [...users].sort((a, b) => a.id - b.id), [users]);

  return (
    <section className="glass-panel rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Users size={16} />
          用户列表
          <span className="text-xs text-gray-500 font-normal">{sorted.length} 名</span>
        </h2>
        <div className="flex gap-2">
          <button
            onClick={reload}
            disabled={loading}
            className="px-3 py-1.5 text-xs rounded-lg border border-white/10 hover:border-white/20 text-gray-300 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            刷新
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="px-3 py-1.5 text-xs rounded-lg bg-amber-600/80 hover:bg-amber-500 text-white transition-colors flex items-center gap-1.5"
          >
            <UserPlus size={12} />
            新建用户
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">{error}</div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-gray-500 border-b border-white/10">
            <tr>
              <th className="text-left py-2 px-2 font-medium">ID</th>
              <th className="text-left py-2 px-2 font-medium">邮箱</th>
              <th className="text-left py-2 px-2 font-medium">显示名</th>
              <th className="text-left py-2 px-2 font-medium">角色</th>
              <th className="text-left py-2 px-2 font-medium">状态</th>
              <th className="text-left py-2 px-2 font-medium">最近登录</th>
              <th className="text-right py-2 px-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="text-gray-200">
            {sorted.map((u) => (
              <UserRow
                key={u.id}
                user={u}
                isMe={me?.id === u.id}
                onChanged={reload}
              />
            ))}
            {!loading && sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center py-6 text-gray-500 text-sm">暂无用户</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} onCreated={reload} />}
    </section>
  );
}

function UserRow({
  user,
  isMe,
  onChanged,
}: {
  user: CurrentUser;
  isMe: boolean;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);

  const flipStatus = async () => {
    setBusy(true);
    try {
      await admin.updateUser(user.id, {
        status: user.status === "active" ? "disabled" : "active",
      });
      onChanged();
    } catch (e: unknown) {
      alert((e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message ?? "操作失败");
    } finally {
      setBusy(false);
    }
  };

  const flipRole = async () => {
    setBusy(true);
    try {
      await admin.updateUser(user.id, {
        role: user.role === "admin" ? "user" : "admin",
      });
      onChanged();
    } catch (e: unknown) {
      alert((e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message ?? "操作失败");
    } finally {
      setBusy(false);
    }
  };

  const resetPwd = async () => {
    const pw = window.prompt(`为 ${user.email} 设置新密码（≥ 8 位）`);
    if (!pw) return;
    if (pw.length < 8) {
      alert("密码至少 8 位");
      return;
    }
    setBusy(true);
    try {
      await admin.updateUser(user.id, { new_password: pw });
      alert("密码已重置");
    } catch (e: unknown) {
      alert((e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message ?? "操作失败");
    } finally {
      setBusy(false);
    }
  };

  const forceLogout = async () => {
    if (!window.confirm(`将 ${user.email} 的所有 token 失效？`)) return;
    setBusy(true);
    try {
      await admin.forceLogout(user.id);
      onChanged();
    } catch (e: unknown) {
      alert((e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message ?? "操作失败");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`删除用户 ${user.email}？此操作不可撤销。`)) return;
    setBusy(true);
    try {
      await admin.deleteUser(user.id);
      onChanged();
    } catch (e: unknown) {
      alert((e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message ?? "操作失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <tr className="border-b border-white/5 hover:bg-white/[0.02]">
      <td className="py-2 px-2 text-gray-500">{user.id}</td>
      <td className="py-2 px-2">{user.email}{isMe && <span className="text-[10px] text-amber-400 ml-1">（你）</span>}</td>
      <td className="py-2 px-2 text-gray-400">{user.display_name || "—"}</td>
      <td className="py-2 px-2">
        <span className={`text-xs px-2 py-0.5 rounded ${user.role === "admin" ? "bg-amber-500/15 text-amber-300" : "bg-white/5 text-gray-400"}`}>
          {user.role}
        </span>
      </td>
      <td className="py-2 px-2">
        {user.status === "active" ? (
          <span className="text-xs flex items-center gap-1 text-green-400"><CheckCircle2 size={12} /> active</span>
        ) : (
          <span className="text-xs flex items-center gap-1 text-gray-500"><XCircle size={12} /> disabled</span>
        )}
      </td>
      <td className="py-2 px-2 text-xs text-gray-500">{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "—"}</td>
      <td className="py-2 px-2 text-right space-x-1">
        <button onClick={flipStatus} disabled={busy || isMe} className="text-xs px-2 py-1 rounded border border-white/10 hover:border-white/30 disabled:opacity-30 transition-colors">
          {user.status === "active" ? "禁用" : "启用"}
        </button>
        <button onClick={flipRole} disabled={busy || isMe} className="text-xs px-2 py-1 rounded border border-white/10 hover:border-white/30 disabled:opacity-30 transition-colors">
          {user.role === "admin" ? "降为用户" : "升为管理员"}
        </button>
        <button onClick={resetPwd} disabled={busy} className="text-xs px-2 py-1 rounded border border-white/10 hover:border-white/30 disabled:opacity-30 transition-colors">
          改密
        </button>
        <button onClick={forceLogout} disabled={busy || isMe} className="text-xs px-2 py-1 rounded border border-white/10 hover:border-white/30 disabled:opacity-30 transition-colors flex items-center gap-1 inline-flex">
          <LogOut size={10} />
          强制下线
        </button>
        <button onClick={remove} disabled={busy || isMe} className="text-xs px-2 py-1 rounded border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-30 transition-colors flex items-center gap-1 inline-flex">
          <Trash2 size={10} />
          删除
        </button>
      </td>
    </tr>
  );
}

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<"admin" | "user">("user");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    setSubmitting(true);
    try {
      await admin.createUser({ email: email.trim(), password, role, display_name: displayName.trim() });
      onCreated();
      onClose();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: { code?: string; message?: string } } } })?.response?.data?.detail;
      if (detail?.code === "EMAIL_EXISTS") setError("该邮箱已被使用");
      else setError(detail?.message ?? "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass = "w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-amber-500/50 transition-colors text-sm";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <form onSubmit={submit} className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-4">
        <h3 className="text-lg font-display font-bold text-white flex items-center gap-2"><PlusCircle size={18} className="text-amber-400" />新建用户</h3>
        <div>
          <label className="block text-xs text-gray-400 mb-1">邮箱</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} autoFocus />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">显示名（可选）</label>
          <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">初始密码（≥ 8 位）</label>
          <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">角色</label>
          <div className="flex gap-2">
            {(["user", "admin"] as const).map((r) => (
              <button key={r} type="button" onClick={() => setRole(r)} className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${role === r ? "border-amber-500/60 bg-amber-500/15 text-amber-200" : "border-white/10 bg-white/5 text-gray-400"}`}>
                {r}
              </button>
            ))}
          </div>
        </div>
        {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-xs text-red-300">{error}</div>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-xs rounded-lg border border-white/10 hover:border-white/30 text-gray-300">取消</button>
          <button type="submit" disabled={submitting} className="px-3 py-1.5 text-xs rounded-lg bg-amber-600 hover:bg-amber-500 text-white disabled:opacity-50 flex items-center gap-1.5">
            {submitting ? <Loader2 size={12} className="animate-spin" /> : null}
            创建
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Stats ──────────────────────────────────────────────────────────────────

function StatsTab() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    admin.stats().then((s) => setStats(s)).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="glass-panel rounded-xl p-5 text-sm text-gray-400">加载中…</div>;
  if (!stats) return <div className="glass-panel rounded-xl p-5 text-sm text-red-300">加载失败</div>;

  const Card = ({ label, value }: { label: string; value: string | number | null }) => (
    <div className="glass-panel rounded-xl p-5">
      <div className="text-xs text-gray-500 mb-2">{label}</div>
      <div className="text-2xl font-display font-bold text-white">{value ?? "—"}</div>
    </div>
  );

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card label="总用户数" value={stats.user_count} />
      <Card label="活跃用户" value={stats.active_user_count} />
      <Card label="管理员" value={stats.admin_count} />
      <Card label="禁用用户" value={stats.disabled_user_count} />
      <div className="col-span-2 lg:col-span-4">
        <Card label="最近登录" value={stats.last_login_at ? new Date(stats.last_login_at).toLocaleString() : "—"} />
      </div>
    </div>
  );
}

// ── Audit ──────────────────────────────────────────────────────────────────

function AuditTab() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    admin.auditLogs(200, 0).then(setEntries).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return (
    <section className="glass-panel rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-white">最近活动</h2>
        <button onClick={reload} disabled={loading} className="px-3 py-1.5 text-xs rounded-lg border border-white/10 hover:border-white/20 text-gray-300 flex items-center gap-1.5 disabled:opacity-50">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          刷新
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-gray-500 border-b border-white/10">
            <tr>
              <th className="text-left py-2 px-2 font-medium">时间</th>
              <th className="text-left py-2 px-2 font-medium">操作</th>
              <th className="text-left py-2 px-2 font-medium">操作者</th>
              <th className="text-left py-2 px-2 font-medium">目标</th>
              <th className="text-left py-2 px-2 font-medium">详情</th>
              <th className="text-left py-2 px-2 font-medium">IP</th>
            </tr>
          </thead>
          <tbody className="text-gray-200">
            {entries.map((e) => (
              <tr key={e.id} className="border-b border-white/5">
                <td className="py-2 px-2 text-xs text-gray-400">{new Date(e.created_at).toLocaleString()}</td>
                <td className="py-2 px-2"><code className="text-xs text-amber-300">{e.action}</code></td>
                <td className="py-2 px-2 text-xs">{e.actor_email || <span className="text-gray-500">—</span>}</td>
                <td className="py-2 px-2 text-xs">{e.target_email || <span className="text-gray-500">—</span>}</td>
                <td className="py-2 px-2 text-xs text-gray-400">{e.detail || "—"}</td>
                <td className="py-2 px-2 text-xs text-gray-500">{e.ip || "—"}</td>
              </tr>
            ))}
            {!loading && entries.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-gray-500 text-sm">暂无记录</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ── Settings ───────────────────────────────────────────────────────────────

function SettingsTab() {
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    admin.getSettings().then(setSettings).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  const update = async (patch: Partial<AdminSettings>) => {
    setSaving(true);
    try {
      const updated = await admin.updateSettings(patch);
      setSettings(updated);
    } catch (e: unknown) {
      alert((e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message ?? "保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) return <div className="glass-panel rounded-xl p-5 text-sm text-gray-400">加载中…</div>;

  const Toggle = ({ label, hint, value, onChange }: { label: string; hint: string; value: boolean; onChange: (v: boolean) => void }) => (
    <div className="flex items-start justify-between p-4 rounded-lg bg-white/5 border border-white/10">
      <div>
        <div className="text-sm font-medium text-white">{label}</div>
        <div className="text-xs text-gray-500 mt-0.5">{hint}</div>
      </div>
      <button
        onClick={() => onChange(!value)}
        disabled={saving}
        className={`relative w-11 h-6 rounded-full transition-colors disabled:opacity-50 ${value ? "bg-amber-500" : "bg-white/10"}`}
        aria-pressed={value}
      >
        <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${value ? "translate-x-5" : ""}`} />
      </button>
    </div>
  );

  return (
    <section className="glass-panel rounded-xl p-5 space-y-3">
      <h2 className="text-base font-bold text-white mb-2">实例设置</h2>
      <Toggle
        label="开放公开注册"
        hint="（目前 P1 阶段不会启用注册路由，开关仅作为后续阶段的预留）"
        value={settings.registration_enabled}
        onChange={(v) => update({ registration_enabled: v })}
      />
      <Toggle
        label="注册需要邀请码"
        hint="后续阶段会启用，注册时必须提供有效邀请码"
        value={settings.invitation_required}
        onChange={(v) => update({ invitation_required: v })}
      />
    </section>
  );
}
