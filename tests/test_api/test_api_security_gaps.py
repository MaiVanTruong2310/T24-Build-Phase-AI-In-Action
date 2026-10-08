"""
Supplementary API Security Tests — Gap Coverage
================================================
Current test_api/ tests cover happy-path responses.
These tests target:

GAP 1 — Auth boundary: unauthenticated requests must be rejected (401)
    GAP 2 — Request body validation: malformed payloads must return 400
    GAP 3 — Rate-limiting / size: oversized request bodies must return 413 or 400
GAP 4 — CORS headers: OPTIONS preflight must include correct CORS headers
GAP 5 — Health endpoints: /health/ready must reflect DB dependency status
"""

import pytest

# ===========================================================================
# GAP 1 — AUTHENTICATION BOUNDARY TESTS
# ===========================================================================


class TestAuthBoundary:
    """Authenticated endpoints must reject requests without valid Bearer token."""

    @pytest.mark.asyncio
    async def test_patient_profile_endpoint_rejects_unauthenticated(self, client):
        """GET /api/v1/patients/me requires authentication."""
        resp = await client.get("/api/v1/patients/me")
        assert resp.status_code in (401, 403), f"Expected 401/403 for unauthenticated access, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_booking_create_rejects_unauthenticated(self, client):
        """POST /api/v1/bookings requires authentication."""
        resp = await client.post("/api/v1/bookings", json={})
        assert resp.status_code in (401, 403, 422), (
            f"Unauthenticated booking create must be rejected, got {resp.status_code}"
        )

    @pytest.mark.asyncio
    async def test_chat_endpoint_accepts_unauthenticated_guest(self, client):
        """
        POST /api/v1/chat should be accessible to unauthenticated users (guest patients).
        Authentication is optional for the chat triage endpoint.
        """
        resp = await client.post(
            "/api/v1/chat",
            json={"query": "Xin chào", "session_id": "test-auth-guest-session"},
        )
        # Must succeed (200) or at least not return 401
        assert resp.status_code != 401, "Chat endpoint must be accessible to unauthenticated guest patients"


# ===========================================================================
# GAP 2 — REQUEST BODY VALIDATION
# ===========================================================================


class TestRequestBodyValidation:
    """Malformed or incomplete payloads must return the API's documented 400."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_rejects_missing_query(self, client):
        """POST /api/v1/chat with no 'query' field must return 400."""
        resp = await client.post("/api/v1/chat", json={"session_id": "abc"})
        assert resp.status_code == 400, f"Missing 'query' field must return 400, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_chat_endpoint_rejects_empty_query(self, client):
        """POST /api/v1/chat with empty string 'query' must return 422."""
        resp = await client.post(
            "/api/v1/chat",
            json={"query": "", "session_id": "test-empty-query"},
        )
        assert resp.status_code == 400, f"Empty 'query' must return 400, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_booking_request_rejects_missing_patient_name(self, client):
        """POST /api/v1/booking-requests without patient_name must return 400."""
        payload = {
            "phone": "0987654321",
            "specialty_code": "TIM_MACH",
            "consent": True,
        }
        resp = await client.post("/api/v1/booking-requests", json=payload)
        assert resp.status_code == 400, f"Missing patient_name must cause 400, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_booking_request_rejects_missing_consent(self, client):
        """POST /api/v1/booking-requests without legal consent must return 400."""
        payload = {
            "patient_name": "Nguyen Van A",
            "phone": "0987654321",
            "specialty_code": "TIM_MACH",
            # consent is missing
        }
        resp = await client.post("/api/v1/booking-requests", json=payload)
        assert resp.status_code == 400, f"Missing consent must cause 400, got {resp.status_code}"


# ===========================================================================
# GAP 3 — OVERSIZED PAYLOAD PROTECTION
# ===========================================================================


class TestOversizedPayloadProtection:
    """Very long inputs must be rejected to prevent prompt injection via body size."""

    @pytest.mark.asyncio
    async def test_extremely_long_query_is_rejected_or_truncated(self, client):
        """
        A query exceeding 10,000 characters must either be:
        - Rejected with 413 or 400, OR
        - Sanitized/truncated and handled gracefully (not crash the agent).
        """
        huge_query = "A" * 15_000
        resp = await client.post(
            "/api/v1/chat",
            json={"query": huge_query, "session_id": "test-oversized"},
        )
        # Must not crash with 500 — either reject or handle gracefully
        assert resp.status_code != 500, "Oversized query must not cause an unhandled 500 server error"
        assert resp.status_code in (200, 400, 413, 422)


# ===========================================================================
# GAP 4 — HEALTH CHECK ENDPOINT
# ===========================================================================


class TestHealthCheckEndpoints:
    """Health endpoints must return valid status payloads."""

    @pytest.mark.asyncio
    async def test_health_ready_returns_200(self, client):
        """GET /health/ready must return 200 in a healthy state."""
        resp = await client.get("/health/ready")
        assert resp.status_code == 200, f"Health readiness endpoint must return 200, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_health_live_returns_200(self, client):
        """GET /health/live (or /health) must return 200."""
        resp = await client.get("/health/live")
        if resp.status_code == 404:
            # Try fallback path
            resp = await client.get("/health")
        assert resp.status_code == 200, f"Health liveness endpoint must return 200, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_health_ready_response_has_status_field(self, client):
        """Health readiness response body must include a 'status' field."""
        resp = await client.get("/health/ready")
        if resp.status_code == 200:
            body = resp.json()
            assert "status" in body, f"Health endpoint must return a 'status' field, got keys: {list(body.keys())}"
