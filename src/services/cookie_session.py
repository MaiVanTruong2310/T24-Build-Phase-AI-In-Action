from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import allowed_cors_origins, get_settings

ACCESS_COOKIE = 'p124_access'
REFRESH_COOKIE = 'p124_refresh'

def cookie_transport(request: Request) -> bool:
    return request.headers.get('x-auth-transport') == 'cookie' or bool(request.cookies.get(REFRESH_COOKIE) or request.cookies.get(ACCESS_COOKIE))

def request_token(request: Request):
    header = request.headers.get('authorization')
    if header:
        scheme, _, token = header.partition(' ')
        if scheme.lower() != 'bearer' or not token.strip():
            raise HTTPException(401, 'Phiên đăng nhập không hợp lệ.')
        return token.strip()
    return request.cookies.get(ACCESS_COOKIE)

def cookie_options():
    settings = get_settings()
    secure = settings.auth_cookie_secure if settings.auth_cookie_secure is not None else settings.app_env == 'production'
    if settings.auth_cookie_samesite == 'none' and not secure:
        raise RuntimeError('SameSite=None requires AUTH_COOKIE_SECURE=true')
    return {'httponly': True, 'secure': secure, 'samesite': settings.auth_cookie_samesite}

def set_session_cookies(response: Response, tokens):
    options = cookie_options()
    response.set_cookie(ACCESS_COOKIE, tokens.access_token, max_age=tokens.expires_in, path='/api/v1', **options)
    response.set_cookie(REFRESH_COOKIE, tokens.refresh_token, max_age=get_settings().jwt_refresh_token_expire_days*86400, path='/api/v1/auth', **options)
    response.headers['Cache-Control'] = 'no-store'

def clear_session_cookies(response: Response):
    options = cookie_options()
    response.delete_cookie(ACCESS_COOKIE, path='/api/v1', **options)
    response.delete_cookie(REFRESH_COOKIE, path='/api/v1/auth', **options)
    response.headers['Cache-Control'] = 'no-store'

def token_result(request, response, tokens):
    from src.api.response import success_response
    if cookie_transport(request):
        set_session_cookies(response, tokens)
        return success_response({'authenticated': True, 'expires_in': tokens.expires_in})
    return success_response(tokens.model_dump(mode='json'))

class CookieOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method not in ('GET','HEAD','OPTIONS') and cookie_transport(request):
            allowed = allowed_cors_origins()
            origin = request.headers.get('origin')
            if not origin or origin.rstrip('/') not in allowed:
                return JSONResponse({'code':403,'message':'Nguồn yêu cầu không hợp lệ.','data':None},status_code=403)
        response = await call_next(request)
        if request.url.path.startswith('/api/v1/auth') or request.url.path == '/api/v1/users/me':
            response.headers['Cache-Control'] = 'no-store'
        if request.url.path == '/api/v1/auth/logout' and cookie_transport(request):
            clear_session_cookies(response)
        if request.url.path == '/api/v1/auth/refresh-token' and response.status_code in (400,401,403) and cookie_transport(request):
            clear_session_cookies(response)
        return response
