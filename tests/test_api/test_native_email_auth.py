from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
import httpx
from src.services import supabase_auth as gateway
from src.core.exceptions import AppError, AuthenticationError
from src.schemas.auth import LoginRequest, RegisterRequest

@pytest.mark.asyncio
async def test_phone_login_never_calls_provider(monkeypatch):
    remote=AsyncMock()
    monkeypatch.setattr(gateway,'auth_call',remote)
    with pytest.raises(AppError):
        await gateway.login_email(LoginRequest(phone='0900000000',password='example-password'),AsyncMock())
    remote.assert_not_awaited()

@pytest.mark.asyncio
async def test_unconfirmed_email_never_activates_profile(monkeypatch):
    monkeypatch.setattr(gateway,'auth_call',AsyncMock(return_value={'id':str(uuid4()),'email_confirmed_at':None}))
    session=AsyncMock()
    with pytest.raises(AuthenticationError): await gateway.authenticated_profile('test-token',session)
    session.execute.assert_not_awaited()
    session.commit.assert_not_awaited()

@pytest.mark.asyncio
async def test_verified_login_preserves_profile_role_and_id(monkeypatch):
    identity_id=uuid4()
    profile=MagicMock(status='pending_verification',role='patient',id=uuid4())
    session=AsyncMock()
    session.execute.return_value.scalar_one_or_none=MagicMock(return_value=profile)
    monkeypatch.setattr(gateway,'auth_call',AsyncMock(return_value={'id':str(identity_id),'email_confirmed_at':'2026-10-01T00:00:00Z','user_metadata':{'role':'admin'}}))
    actual=await gateway.authenticated_profile('test-token',session)
    assert actual is profile and actual.role=='patient' and actual.status=='active'

@pytest.mark.asyncio
async def test_signup_requires_confirmation_and_no_fake_otp(monkeypatch):
    remote=AsyncMock(return_value={'id':str(uuid4()),'identities':[]})
    monkeypatch.setattr(gateway,'auth_call',remote)
    session=AsyncMock()
    result=await gateway.register_email(RegisterRequest(email='Test@example.com',password='example-password'),session)
    assert result=={'confirmation_required':True,'email':'test@example.com'}
    assert remote.call_args.args[0]=='/signup'
    assert 'phone' not in remote.call_args.args[1]
    session.add.assert_not_called()

@pytest.mark.asyncio
async def test_supabase_unconfirmed_error_is_readable(monkeypatch):
    client=AsyncMock()
    client.request.return_value=httpx.Response(400,json={'error_code':'email_not_confirmed'})
    context=MagicMock()
    context.__aenter__=AsyncMock(return_value=client)
    context.__aexit__=AsyncMock(return_value=False)
    monkeypatch.setattr(gateway.httpx,'AsyncClient',lambda **kwargs:context)
    with pytest.raises(AppError) as err: await gateway.auth_call('/token',{})
    assert 'xác nhận email' in str(err.value)

@pytest.mark.asyncio
async def test_recovery_uses_email_not_mock_otp(monkeypatch):
    from src.api.endpoints import auth
    from src.schemas.auth import ForgotPasswordRequest
    remote=AsyncMock(return_value={})
    monkeypatch.setattr(auth,'native_auth_enabled',lambda:True)
    monkeypatch.setattr(auth,'auth_call',remote)
    service=AsyncMock()
    response=await auth.forgot_password(ForgotPasswordRequest(email='test@example.com'),service)
    assert response.data.otp is None
    assert remote.call_args.args[0]=='/recover'
    service.request_password_reset.assert_not_awaited()
