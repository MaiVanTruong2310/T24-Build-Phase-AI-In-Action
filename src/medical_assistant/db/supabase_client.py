"""
Database and Supabase client provider using high-performance HTTPX client.
Eliminates heavy external dependencies while providing connection pooling,
timeout resilience, and async/sync compatibility for 10,000 CCU load.
"""

from typing import Any

import httpx

from src.medical_assistant.config import get_settings


class SupabaseRestClient:
    """
    Lightweight, fast PostgREST / Supabase client using httpx.Client with connection pooling.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout_seconds: float = 8.0,
        connect_timeout_seconds: float = 3.0,
        max_connections: int = 50,
        max_keepalive_connections: int = 20,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        limits = httpx.Limits(
            max_keepalive_connections=max_keepalive_connections,
            max_connections=max_connections,
            keepalive_expiry=30.0,
        )
        timeout = httpx.Timeout(timeout_seconds, connect=connect_timeout_seconds)
        self.client = httpx.Client(
            base_url=f"{self.base_url}/rest/v1",
            headers=self.headers,
            limits=limits,
            timeout=timeout,
            transport=httpx.HTTPTransport(retries=1),
        )

    def close(self) -> None:
        """Close pooled sockets held by the shared HTTP client."""
        self.client.close()

    def select(self, table: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Execute a SELECT query against Supabase PostgREST table.
        """
        response = self.client.get(f"/{table}", params=params)
        response.raise_for_status()
        return response.json()

    def insert(self, table: str, data: Any) -> list[dict[str, Any]]:
        """
        Execute an INSERT query into Supabase table.
        """
        response = self.client.post(f"/{table}", json=data)
        response.raise_for_status()
        return response.json()

    def insert_minimal(self, table: str, data: Any) -> None:
        """Insert without requesting rows back (works with INSERT-only RLS)."""
        response = self.client.post(
            f"/{table}",
            json=data,
            headers={"Prefer": "return=minimal"},
        )
        response.raise_for_status()

    def update(self, table: str, data: Any, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Execute an UPDATE (PATCH) query into Supabase table with filter params.
        """
        response = self.client.patch(f"/{table}", json=data, params=params)
        response.raise_for_status()
        return response.json()


_supabase_client: SupabaseRestClient | None = None
_supabase_admin_client: SupabaseRestClient | None = None


def get_supabase_client() -> SupabaseRestClient:
    """
    Get or create a cached Supabase client singleton.
    """
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment or .env"
            )
        _supabase_client = SupabaseRestClient(
            base_url=settings.supabase_url,
            api_key=settings.supabase_key,
            timeout_seconds=settings.supabase_timeout_seconds,
            connect_timeout_seconds=settings.supabase_connect_timeout_seconds,
            max_connections=settings.supabase_max_connections,
            max_keepalive_connections=settings.supabase_max_keepalive_connections,
        )
    return _supabase_client


def get_supabase_admin_client() -> SupabaseRestClient:
    """Return a server-only client for privileged writes containing patient PII."""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError(
                "SUPABASE_URL and server-only SUPABASE_SERVICE_ROLE_KEY must be configured"
            )
        _supabase_admin_client = SupabaseRestClient(
            base_url=settings.supabase_url,
            api_key=settings.supabase_service_role_key,
            timeout_seconds=settings.supabase_timeout_seconds,
            connect_timeout_seconds=settings.supabase_connect_timeout_seconds,
            max_connections=settings.supabase_max_connections,
            max_keepalive_connections=settings.supabase_max_keepalive_connections,
        )
    return _supabase_admin_client


def close_supabase_clients() -> None:
    """Close and clear cached clients so shutdown does not leak sockets."""
    global _supabase_client, _supabase_admin_client
    clients = {_supabase_client, _supabase_admin_client}
    for client in clients:
        if client is not None:
            client.close()
    _supabase_client = None
    _supabase_admin_client = None
