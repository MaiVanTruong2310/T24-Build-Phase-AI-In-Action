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

export const AUTH_SESSION_KEY = 'medicare_auth_session';

export function readAccessToken(): string | null {
  return localStorage.getItem('access_token');
}

export function readRefreshToken(): string | null {
  return localStorage.getItem('refresh_token');
}

export function saveTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

export function publishSession(user: SessionUser | null): void {
  const value: StoredSession = { user, changed_at: Date.now() };
  localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(value));
}

export function clearSession(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  publishSession(null);
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
