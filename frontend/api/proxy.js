/* global process, fetch, Headers, Response, URL */
// Proxy /api/* -> backend, để frontend trên Vercel gọi API cùng domain.
// Cookie đăng nhập (SameSite=none) đặt bởi domain backend khác bị trình duyệt chặn như cookie bên thứ ba;
// đi qua proxy thì cookie thuộc domain Vercel nên không bị chặn.
// Chỉ hoạt động khi project Vercel đặt BACKEND_ORIGIN (vd https://xxx.up.railway.app);
// project không đặt biến này vẫn gọi backend trực tiếp qua VITE_API_BASE_URL như cũ.

export const config = { maxDuration: 300 };

const HOP_BY_HOP = ['host', 'connection', 'content-length', 'transfer-encoding', 'accept-encoding'];

async function proxy(request) {
  const backend = (process.env.BACKEND_ORIGIN || '').replace(/\/$/, '');
  if (!backend) {
    return new Response(JSON.stringify({ message: 'BACKEND_ORIGIN chưa được cấu hình.' }), {
      status: 502,
      headers: { 'content-type': 'application/json' },
    });
  }
  // vercel.json rewrite: /api/:path* -> /api/proxy?__path=:path* (giữ nguyên query gốc).
  const url = new URL(request.url);
  const path = url.searchParams.get('__path') || '';
  url.searchParams.delete('__path');
  url.pathname = `/api/${path}`;
  const headers = new Headers(request.headers);
  for (const name of HOP_BY_HOP) headers.delete(name);
  headers.set('x-forwarded-host', url.host);
  headers.set('x-forwarded-proto', 'https');

  const hasBody = !['GET', 'HEAD'].includes(request.method);
  const upstream = await fetch(`${backend}${url.pathname}${url.search}`, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    redirect: 'manual',
  });

  // fetch đã giải nén body nên bỏ content-encoding/length; giữ nguyên các Set-Cookie.
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete('content-encoding');
  responseHeaders.delete('content-length');
  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;
