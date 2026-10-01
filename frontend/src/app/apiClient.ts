import {
  clearSession,
  readAccessToken,
  readRefreshToken,
  saveTokens,
} from '../features/auth/session';

// Default matches the local backend started by run.ps1.
// Set VITE_API_BASE_URL in frontend/.env.local to override this when needed.
const LOCAL_API_ORIGIN = 'http://localhost:8000';

function normalizeApiOrigin(value: string): string {
  const trimmedValue = value.trim().replace(/\/$/, '');
  if (!trimmedValue) return LOCAL_API_ORIGIN;
  if (trimmedValue.startsWith('http://') || trimmedValue.startsWith('https://')) {
    return trimmedValue.replace(/\/api\/v1$/, '');
  }
  return `http://${trimmedValue}`.replace(/\/api\/v1$/, '');
}

// API_DOMAIN_PROD/API_DOMAIN_DEV are injected by CI/CD as the backend URL.
const API_ORIGIN = normalizeApiOrigin(import.meta.env.VITE_API_BASE_URL || LOCAL_API_ORIGIN);
const API_BASE = `${API_ORIGIN}/api/v1`;
const REFRESH_PATH = `${API_BASE}/auth/refresh-token`;
const NGROK_SKIP_BROWSER_WARNING_HEADER = 'ngrok-skip-browser-warning';
const UNAUTHORIZED_EVENT = 'auth:unauthorized';
const REFRESH_LOCK_NAME = 'medicare-auth-refresh';
const REFRESH_LOCK_KEY = 'medicare_auth_refresh_lock';
const TAB_ID = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

let refreshPromise: Promise<string | null> | null = null;

const wait = (milliseconds: number): Promise<void> => new Promise((resolve) => {
  window.setTimeout(resolve, milliseconds);
});

async function acquireFallbackRefreshLock(): Promise<() => void> {
  const owner = `${TAB_ID}-${Date.now()}`;
  const expiresAt = Date.now() + 10_000;

  for (let attempt = 0; attempt < 200; attempt += 1) {
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

function notifyUnauthorized(): void {
  clearSession();
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));

  // The API client is outside the React Router tree, so use a hard redirect
  // to guarantee that stale Redux auth state is discarded as well.
  if (window.location.pathname !== '/login') {
    window.location.replace('/login');
  }
}

export function resolveApiUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  if (url.startsWith('/api/')) {
    return `${API_ORIGIN}${url}`;
  }
  return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`;
}

export function fetchPublicApi(url: string, options: RequestInit = {}): Promise<Response> {
  const resolvedUrl = resolveApiUrl(url);
  const headers = new Headers(options.headers);
  if (/\.ngrok(?:-free\.(?:dev|app)|\.io)$/.test(new URL(resolvedUrl).hostname)) {
    headers.set(NGROK_SKIP_BROWSER_WARNING_HEADER, 'true');
  }
  return fetch(resolvedUrl, { ...options, headers });
}

async function performRefresh(refreshToken: string): Promise<string | null> {
  try {
    const response = await fetch(REFRESH_PATH, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
        [NGROK_SKIP_BROWSER_WARNING_HEADER]: 'true',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      notifyUnauthorized();
      return null;
    }

    const payload = await response.json();
    const accessToken = payload?.data?.access_token;
    const rotatedRefreshToken = payload?.data?.refresh_token;

    if (typeof accessToken !== 'string' || typeof rotatedRefreshToken !== 'string') {
      notifyUnauthorized();
      return null;
    }

    saveTokens(accessToken, rotatedRefreshToken);
    return accessToken;
  } catch {
    notifyUnauthorized();
    return null;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = readRefreshToken();
  if (!refreshToken) {
    notifyUnauthorized();
    return null;
  }

  refreshPromise = (async () => {
    try {
      const refreshWithLock = async (release: () => void) => {
        try {
          const latestRefreshToken = readRefreshToken();
          if (!latestRefreshToken) {
            notifyUnauthorized();
            return null;
          }

          // Another tab may have rotated the shared refresh token while this
          // tab was waiting. Reuse the new access token instead of rotating
          // the already-revoked token and triggering reuse detection.
          if (latestRefreshToken !== refreshToken) {
            return readAccessToken();
          }

          return performRefresh(latestRefreshToken);
        } finally {
          release();
        }
      };

      if (typeof navigator !== 'undefined' && navigator.locks) {
        return navigator.locks.request(REFRESH_LOCK_NAME, (lock) => {
          if (!lock) return null;
          return refreshWithLock(() => undefined);
        });
      }

      const release = await acquireFallbackRefreshLock();
      return refreshWithLock(release);
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const fullUrl = resolveApiUrl(url);
  const headers = new Headers(options.headers || {});
  headers.set(NGROK_SKIP_BROWSER_WARNING_HEADER, 'true');

  // An explicitly supplied token must take precedence over a stale token in
  // localStorage, which matters immediately after a successful login.
  if (!headers.has('Authorization')) {
    const accessToken = readAccessToken();
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`);
    }
  }

  let response = await fetch(fullUrl, { ...options, headers });
  const isRefreshRequest = fullUrl === REFRESH_PATH;

  if (response.status !== 401 || isRefreshRequest) {
    return response;
  }

  const newAccessToken = await refreshAccessToken();
  if (!newAccessToken) {
    return response;
  }

  // Rebuild headers from the original options so a stale Authorization
  // header cannot overwrite the newly rotated access token.
  const retryHeaders = new Headers(options.headers || {});
  retryHeaders.set(NGROK_SKIP_BROWSER_WARNING_HEADER, 'true');
  retryHeaders.set('Authorization', `Bearer ${newAccessToken}`);
  response = await fetch(fullUrl, { ...options, headers: retryHeaders });

  // If the newly refreshed token is rejected immediately, end the session
  // instead of repeatedly retrying the same request.
  if (response.status === 401) {
    notifyUnauthorized();
  }

  return response;
}
