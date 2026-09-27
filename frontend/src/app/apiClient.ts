const API_BASE = '/api/v1';

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const getAccessToken = () => localStorage.getItem('access_token');
  const getRefreshToken = () => localStorage.getItem('refresh_token');
  const setTokens = (access: string, refresh: string) => {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  };
  const clearTokens = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  };

  let token = getAccessToken();

  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Prepend API_BASE if url is relative and doesn't start with http or /api/v1
  const fullUrl = url.startsWith('http') || url.startsWith('/api') ? url : `${API_BASE}${url.startsWith('/') ? url : '/' + url}`;

  let response = await fetch(fullUrl, { ...options, headers });

  if (response.status === 401) {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        const refreshResponse = await fetch(`${API_BASE}/auth/refresh-token`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          const newToken = data.data.access_token;
          const newRefreshToken = data.data.refresh_token; 
          setTokens(newToken, newRefreshToken || refreshToken);
          
          headers.set('Authorization', `Bearer ${newToken}`);
          response = await fetch(fullUrl, { ...options, headers });
        } else {
          clearTokens();
          window.dispatchEvent(new Event('auth:unauthorized'));
        }
      } catch (e) {
        clearTokens();
        window.dispatchEvent(new Event('auth:unauthorized'));
      }
    } else {
      clearTokens();
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
  }

  return response;
}
