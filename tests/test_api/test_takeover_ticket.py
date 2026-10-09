"""Takeover handshake tickets must not be locally signed JWTs.

The staff/patient WebSocket handshake cannot send an Authorization header, so
``GET /staff/chat-takeover/ticket`` issues a credential that travels in the query
string. That credential used to be a JWT signed with the shared ``jwt_secret_key``
and verified locally, which meant anyone knowing the secret could mint a session
for any user. It is now an opaque, server-side ticket.
"""

from uuid import uuid4

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.core.security import create_access_token
from src.main import app
from src.realtime.chat_takeover import TakeoverTicketStore, takeover_tickets


def test_ticket_round_trips_to_the_bound_user():
    """An issued ticket resolves to the user it was minted for."""
    store = TakeoverTicketStore()
    bound = uuid4()
    assert store.redeem(store.issue(bound)) == bound


def test_unknown_ticket_is_rejected():
    """A ticket that was never issued resolves to nothing."""
    assert TakeoverTicketStore().redeem("not-a-real-ticket") is None


def test_expired_ticket_is_rejected():
    """A ticket past its TTL resolves to nothing."""
    store = TakeoverTicketStore(ttl_seconds=0)
    assert store.redeem(store.issue(uuid4())) is None


def test_locally_signed_jwt_is_not_a_valid_ticket():
    """A JWT signed with the local secret is not redeemable as a ticket."""
    token, _ = create_access_token(subject=str(uuid4()), role="staff")
    assert takeover_tickets.redeem(token) is None


def test_socket_closes_when_the_token_is_a_forged_local_jwt():
    """The staff socket refuses a locally signed token instead of trusting its claims.

    ``TestClient`` is deliberately not used as a context manager: the WebSocket route
    never needs the application lifespan, and skipping it keeps the test offline.
    """
    token, _ = create_access_token(subject=str(uuid4()), role="staff")
    test_client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as closed:
        with test_client.websocket_connect(f"/api/v1/staff/chat-takeover/ws/staff?token={token}") as socket:
            socket.receive_text()
    assert closed.value.code == 1008
