"""Fail-closed execution service for staff operational read queries."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import get_settings
from src.core.logging import get_logger, log_event
from src.db.session import get_staff_agent_readonly_session_factory
from src.repositories.staff_agent_query import build_staff_query, execute_staff_query
from src.schemas.staff_agent_query import StaffQueryPlan

logger = get_logger(__name__)
STATEMENT_TIMEOUT_MS = 2500

_READONLY_ATTESTATION = text(
    """
    WITH RECURSIVE memberships(role_id) AS (
        SELECT am.roleid FROM pg_auth_members am
        JOIN pg_roles current_role ON current_role.oid = am.member
        WHERE current_role.rolname = current_user
        UNION
        SELECT am.roleid FROM pg_auth_members am
        JOIN memberships m ON m.role_id = am.member
    )
    SELECT
        NOT (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls)
        AND d.datdba <> r.oid
        AND NOT EXISTS (SELECT 1 FROM memberships) AS principal_is_unprivileged,
        NOT has_database_privilege(current_user, current_database(), 'CREATE') AS database_is_read_only,
        NOT EXISTS (
            SELECT 1 FROM pg_namespace n
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
              AND (n.nspowner = r.oid OR has_schema_privilege(current_user, n.oid, 'CREATE'))
        ) AS schemas_are_read_only,
        NOT EXISTS (
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
              AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND (
                  c.relowner = r.oid
                  OR has_table_privilege(current_user, c.oid, 'INSERT')
                  OR has_table_privilege(current_user, c.oid, 'UPDATE')
                  OR has_table_privilege(current_user, c.oid, 'DELETE')
                  OR has_table_privilege(current_user, c.oid, 'TRUNCATE')
                  OR has_table_privilege(current_user, c.oid, 'REFERENCES')
                  OR has_table_privilege(current_user, c.oid, 'TRIGGER')
                  OR has_any_column_privilege(current_user, c.oid, 'INSERT')
                  OR has_any_column_privilege(current_user, c.oid, 'UPDATE')
              )
        ) AS tables_are_read_only,
        NOT EXISTS (
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
              AND c.relkind = 'S'
              AND (
                  c.relowner = r.oid
                  OR has_sequence_privilege(current_user, c.oid, 'USAGE')
                  OR has_sequence_privilege(current_user, c.oid, 'UPDATE')
              )
        ) AS sequences_are_read_only,
        NOT EXISTS (
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
              AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND (has_table_privilege(current_user, c.oid, 'SELECT')
                   OR has_any_column_privilege(current_user, c.oid, 'SELECT'))
              AND NOT (n.nspname = 'public' AND c.relname IN (
                  'v_staff_agent_catalog', 'v_staff_agent_availability',
                  'v_staff_agent_booking_operations', 'v_staff_agent_case_operations'
              ))
        ) AS only_safe_views_readable,
        NOT EXISTS (
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
              AND c.relkind = 'S'
              AND (has_sequence_privilege(current_user, c.oid, 'SELECT')
                   OR has_sequence_privilege(current_user, c.oid, 'USAGE')
                   OR has_sequence_privilege(current_user, c.oid, 'UPDATE'))
        ) AS no_sequence_access,
        has_table_privilege(current_user, 'public.v_staff_agent_catalog', 'SELECT')
        AND has_table_privilege(current_user, 'public.v_staff_agent_availability', 'SELECT')
        AND has_table_privilege(current_user, 'public.v_staff_agent_booking_operations', 'SELECT')
        AND has_table_privilege(current_user, 'public.v_staff_agent_case_operations', 'SELECT')
        AS safe_views_are_readable
    FROM pg_roles r CROSS JOIN pg_database d
    WHERE r.rolname = current_user AND r.rolname = 'staff_agent_readonly'
      AND d.datname = current_database()
    """
)


class StaffAgentQueryService:
    """Execute fixed read plans only through a separately configured read-only login."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory

    async def query(self, staff_id: UUID, facility_ids: list[UUID], plan: StaffQueryPlan) -> dict[str, Any]:
        try:
            build_staff_query(plan, facility_ids, staff_id=staff_id)
        except (ValueError, TypeError):
            return {"available": False, "needs_refinement": True, "message": "Hãy thu hẹp tiêu chí tra cứu."}
        try:
            if self.session_factory is None:
                settings = get_settings()
                readonly_url = settings.staff_agent_readonly_database_url
                if not _separate_readonly_login(readonly_url, settings.database_url):
                    return {"available": False, "message": "Công cụ tra cứu dữ liệu vận hành chưa được cấu hình."}
                factory = get_staff_agent_readonly_session_factory()
            else:
                factory = self.session_factory
            if factory is None:
                return {"available": False, "message": "Công cụ tra cứu dữ liệu vận hành chưa được cấu hình."}
            async with factory() as session:
                if session.bind is None or session.bind.dialect.name != "postgresql":
                    return {"available": False, "message": "Công cụ tra cứu dữ liệu vận hành hiện không khả dụng."}
                async with session.begin():
                    await session.execute(text("SET TRANSACTION READ ONLY"))
                    await session.execute(text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT_MS}ms'"))
                    attestation = (await session.execute(_READONLY_ATTESTATION)).mappings().one_or_none()
                    if not attestation or not all(attestation.values()):
                        log_event(logger, logging.ERROR, "staff_agent.query.readonly_principal_rejected")
                        return {"available": False, "message": "Công cụ tra cứu dữ liệu vận hành hiện không khả dụng."}
                    rows = await execute_staff_query(session, plan, facility_ids, staff_id)
            truncated = len(rows) > plan.limit
            rows = rows[: plan.limit]
            log_event(logger, logging.INFO, "staff_agent.query.completed")
            return {
                "available": True,
                "items": rows,
                "count": len(rows),
                "limit": plan.limit,
                "truncated": truncated,
            }
        except (SQLAlchemyError, ValueError, TypeError):
            log_event(logger, logging.WARNING, "staff_agent.query.unavailable")
            return {"available": False, "message": "Không thể tra cứu dữ liệu vận hành lúc này."}


def _separate_readonly_login(readonly_url: str, application_url: str) -> bool:
    if not readonly_url or not application_url:
        return False
    try:
        readonly = make_url(readonly_url)
        application = make_url(application_url)
    except Exception:
        return False
    return (
        readonly.username == "staff_agent_readonly"
        and readonly.username != application.username
        and bool(readonly.database)
        and readonly.database == application.database
    )
