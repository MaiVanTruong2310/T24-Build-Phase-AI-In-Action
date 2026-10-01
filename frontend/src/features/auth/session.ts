export interface SessionUser {
  id: string;
  email?: string | null;
  phone?: string | null;
  full_name: string;
  role: 'patient' | 'staff';
}

interface StoredSession {
  user: SessionUser | null;
  changed_at: number;
}

export const ACCESS_TOKEN_KEY = 'access_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';
export const AUTH_SESSION_KEY = 'medicare_auth_session';
export const AUTH_TOKENS_UPDATED_EVENT = 'auth:tokens-updated';

export function readAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function readRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function saveTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  window.dispatchEvent(new Event(AUTH_TOKENS_UPDATED_EVENT));
}

export function publishSession(user: SessionUser | null): void {
  const value: StoredSession = { user, changed_at: Date.now() };
  localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(value));
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  publishSession(null);
  window.dispatchEvent(new Event(AUTH_TOKENS_UPDATED_EVENT));
}

export function readPublishedSession(): SessionUser | null {
  const raw = localStorage.getItem(AUTH_SESSION_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as StoredSession;
    return parsed?.user || null;
  } catch {
    return null;
  }
}

export function getUserAvatarUrl(user: SessionUser): string {
  const name = encodeURIComponent(user.full_name || 'User');
  return `https://ui-avatars.com/api/?name=${name}&background=0284c7&color=fff&size=64`;
}
