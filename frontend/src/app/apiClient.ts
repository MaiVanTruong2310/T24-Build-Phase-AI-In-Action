const API_BASE = '/api/v1';
const REFRESH_PATH = `${API_BASE}/auth/refresh-token`;
const UNAUTHORIZED_EVENT = 'auth:unauthorized';

let refreshPromise: Promise<string | null> | null = null;

function getAccessToken(): string | null {
  return localStorage.getItem('access_token');
}

function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token');
}

function saveTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

function clearTokens(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

function notifyUnauthorized(): void {
  clearTokens();
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));

  // The API client is outside the React Router tree, so use a hard redirect
  // to guarantee that stale Redux auth state is discarded as well.
  if (window.location.pathname !== '/login') {
    window.location.replace('/login');
  }
}

function resolveApiUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/api/')) {
    return url;
  }
  return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`;
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    notifyUnauthorized();
    return null;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(REFRESH_PATH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-store',
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
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const fullUrl = resolveApiUrl(url);
  const headers = new Headers(options.headers || {});
  const accessToken = getAccessToken();

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
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
  retryHeaders.set('Authorization', `Bearer ${newAccessToken}`);
  response = await fetch(fullUrl, { ...options, headers: retryHeaders });

  // If the newly refreshed token is rejected immediately, end the session
  // instead of repeatedly retrying the same request.
  if (response.status === 401) {
    notifyUnauthorized();
  }

  return response;
}
