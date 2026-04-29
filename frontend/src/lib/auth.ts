// Browser-side auth state. JWT lives in localStorage and is attached to
// every backend request by the axios interceptor in api.ts.

const TOKEN_KEY = "manju_forge_access_token";
const EXPIRES_KEY = "manju_forge_token_expires_at";
const USER_KEY = "manju_forge_user";

export type Role = "admin" | "user";
export type Status = "active" | "disabled";

export interface CurrentUser {
  id: number;
  email: string;
  role: Role;
  status: Status;
  display_name: string;
  is_active: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: CurrentUser;
}

export interface SetupStatus {
  needs_setup: boolean;
  user_count: number;
}

const isBrowser = () => typeof window !== "undefined";

export function getToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getTokenExpiresAt(): number | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(EXPIRES_KEY);
  if (!raw) return null;
  const t = Date.parse(raw);
  return Number.isFinite(t) ? t : null;
}

export function isTokenExpired(skewMs = 30_000): boolean {
  const exp = getTokenExpiresAt();
  if (exp === null) return true;
  return Date.now() + skewMs >= exp;
}

export function getCurrentUser(): CurrentUser | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CurrentUser;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null && !isTokenExpired();
}

export function isAdmin(): boolean {
  const u = getCurrentUser();
  return !!u && u.role === "admin";
}

export function persistSession(resp: TokenResponse): void {
  if (!isBrowser()) return;
  localStorage.setItem(TOKEN_KEY, resp.access_token);
  localStorage.setItem(EXPIRES_KEY, resp.expires_at);
  localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
  notifyAuthChange();
}

export function persistUser(user: CurrentUser): void {
  if (!isBrowser()) return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  notifyAuthChange();
}

export function clearSession(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EXPIRES_KEY);
  localStorage.removeItem(USER_KEY);
  notifyAuthChange();
}

// ── Auth-state change subscription ────────────────────────────────────────
//
// Components subscribe to know when login / logout happens (within the same
// tab). storage events handle cross-tab; a custom event covers same-tab.

const AUTH_EVENT = "manju-forge-auth-changed";

export function notifyAuthChange(): void {
  if (!isBrowser()) return;
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function onAuthChange(handler: () => void): () => void {
  if (!isBrowser()) return () => {};
  const sameTab = () => handler();
  const crossTab = (e: StorageEvent) => {
    if (e.key === TOKEN_KEY || e.key === USER_KEY) handler();
  };
  window.addEventListener(AUTH_EVENT, sameTab);
  window.addEventListener("storage", crossTab);
  return () => {
    window.removeEventListener(AUTH_EVENT, sameTab);
    window.removeEventListener("storage", crossTab);
  };
}
