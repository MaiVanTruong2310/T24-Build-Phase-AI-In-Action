import { clearSession, markCookieSession, readPublishedSession } from '../features/auth/session';
// const LOCAL_API_ORIGIN = 'https://c4-app-t124-dev.duckdns.org';
const LOCAL_API_ORIGIN = 'http://localhost:8000';
function normalizeApiOrigin(value: string): string {
  const trimmed = value.trim().replace(/\/$/, '');
  const scheme = /^(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i.test(trimmed) ? 'http://' : 'https://';
  const origin = !trimmed ? LOCAL_API_ORIGIN : /^https?:\/\//.test(trimmed) ? trimmed : scheme + trimmed;
  return origin.replace(/\/api\/v1$/, '');
}
const RAILWAY_FRONTEND_HOST = 'creative-enjoyment-production-e3d9.up.railway.app';
const API_ORIGIN = typeof window !== 'undefined' && window.location.hostname === RAILWAY_FRONTEND_HOST
  ? window.location.origin
  : normalizeApiOrigin(import.meta.env.VITE_API_BASE_URL || LOCAL_API_ORIGIN);
const API_BASE = `${API_ORIGIN}/api/v1`;
const REVISION_KEY = 'p124_cookie_revision';
let refreshPromise: Promise<boolean> | null = null;

const REFRESH_LOCK_KEY = 'medicare_auth_refresh_lock';
const TAB_ID = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const wait = (milliseconds: number): Promise<void> => new Promise(resolve => window.setTimeout(resolve,milliseconds));
async function acquireFallbackRefreshLock(): Promise<() => void> {
  const owner = `${TAB_ID}-${Date.now()}`;
  const expiresAt = Date.now() + 45_000;

  for (let attempt = 0; attempt < 900; attempt += 1) {
    const raw = localStorage.getItem(REFRESH_LOCK_KEY);
    let lockExpired = true;
    if (raw) {
      try {
        lockExpired = Number((JSON.parse(raw) as { expires_at?: number }).expires_at || 0) <= Date.now();
      } catch {
        lockExpired = true;
      }
    }

    if (!raw || lockExpired) {
      localStorage.setItem(REFRESH_LOCK_KEY, JSON.stringify({ owner, expires_at: expiresAt }));
      let acquiredOwner: string | undefined;
      try {
        acquiredOwner = (JSON.parse(localStorage.getItem(REFRESH_LOCK_KEY) || '{}') as { owner?: string }).owner;
      } catch {
        acquiredOwner = undefined;
      }
      if (acquiredOwner === owner) {
        return () => {
          const current = localStorage.getItem(REFRESH_LOCK_KEY);
          if (current) {
            try {
              if ((JSON.parse(current) as { owner?: string }).owner === owner) {
                localStorage.removeItem(REFRESH_LOCK_KEY);
              }
            } catch {
              localStorage.removeItem(REFRESH_LOCK_KEY);
            }
          }
        };
      }
    }

    await wait(50);
  }

  throw new Error('Unable to acquire refresh lock');
}

let sessionWrite: Promise<unknown> = Promise.resolve();
function withSessionLock<T>(fn: () => Promise<T>): Promise<T> {
  const queued = sessionWrite.then(() => typeof navigator !== 'undefined' && navigator.locks
    ? navigator.locks.request('medicare-auth-refresh', fn) : (async () => {
      const release = await acquireFallbackRefreshLock();
      try { return await fn(); } finally { release(); }
    })());
  sessionWrite = queued.catch(() => undefined);
  return queued;
}

export function resolveApiUrl(url: string): string {
  if (/^https?:\/\//.test(url)) return url;
  if (url.startsWith('/api/')) return `${API_ORIGIN}${url}`;
  return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`;
}

export function resolveWebSocketUrl(path: string): string {
  const url = new URL(resolveApiUrl(path));
  if (url.protocol === 'https:') url.protocol = 'wss:';
  else if (url.protocol === 'http:') url.protocol = 'ws:';
  else throw new TypeError(`Unsupported API protocol for WebSocket: ${url.protocol}`);
  return url.toString();
}

export function fetchPublicApi(url: string, options: RequestInit = {}): Promise<Response> {
  const resolved = resolveApiUrl(url);
  const headers = new Headers(options.headers);
  headers.set('X-Auth-Transport', 'cookie');
  if (readPublishedSession()) headers.set('X-Session-Expected', '1');
  const send = () => fetch(resolved, {...options, headers, credentials: 'include'});
  if (/\/auth\/(login|logout)$/.test(resolved)) return withSessionLock(send);
  return send();
}
function unauthorized(): void {
  clearSession();
  window.dispatchEvent(new Event('auth:unauthorized'));
}
async function performRefresh(): Promise<boolean> {
  const response = await fetchPublicApi('/auth/refresh-token', {method:'POST'});
  if (!response.ok) {
    if ([400,401,403].includes(response.status)) { unauthorized(); return false; }
    throw new Error('Không thể gia hạn phiên lúc này. Vui lòng thử lại.');
  }
  const payload = await response.json();
  if (payload?.data?.authenticated !== true) throw new Error('Phản hồi gia hạn phiên chưa hợp lệ.');
  localStorage.setItem(REVISION_KEY, `${Date.now()}-${Math.random()}`);
  markCookieSession();
  return true;
}
async function refreshCookieSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  const before = localStorage.getItem(REVISION_KEY);
  const run = async () => {
    if (before !== localStorage.getItem(REVISION_KEY)) return true;
    return performRefresh();
  };
  refreshPromise = withSessionLock(run).finally(() => { refreshPromise = null; });
  const refreshed = await refreshPromise;
  if (refreshed) window.dispatchEvent(new Event('auth:refreshed'));
  return refreshed;
}
async function migrateLegacyUnlocked(): Promise<void> {
  const legacyRefresh = localStorage.getItem('refresh_token');
  if (!legacyRefresh) { localStorage.removeItem('access_token'); return; }
  const response = await fetchPublicApi('/auth/refresh-token', {
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:legacyRefresh}),
  });
  if (!response.ok) {
    if ([400,401,403].includes(response.status)) {clearSession();return;}
    throw new Error('Chưa thể chuyển phiên đăng nhập. Vui lòng thử lại.');
  }
  const payload = await response.json();
  if (payload?.data?.authenticated !== true) throw new Error('Chưa thể xác nhận phiên cookie.');
  markCookieSession();
}
export function migrateLegacySession(): Promise<void> {
  if (!localStorage.getItem('refresh_token')) {
    localStorage.removeItem('access_token');
    return Promise.resolve();
  }
  return withSessionLock(migrateLegacyUnlocked);
}
export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  let response = await fetchPublicApi(url,options);
  // Authentication actions have their own error semantics and must never be replayed.
  if (response.status !== 401 || resolveApiUrl(url).startsWith(`${API_BASE}/auth/`)) return response;
  if (!(await refreshCookieSession())) return response;
  response = await fetchPublicApi(url,options);
  if (response.status === 401) unauthorized();
  return response;
}
