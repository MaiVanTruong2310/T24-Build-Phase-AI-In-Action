"""Fixed SQLAlchemy query compiler for the curated staff read views."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, and_, asc, desc, or_, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.staff_agent_query import StaffQueryOperator, StaffQueryPlan, StaffQuerySubject

_metadata = MetaData()


def _view(name: str, columns: dict[str, Any]) -> Table:
    return Table(name, _metadata, *(Column(key, kind) for key, kind in columns.items()))


_uuid = PG_UUID(as_uuid=True)
_time = DateTime(timezone=True)
_text = String()
_int = Integer()
_views = {
    StaffQuerySubject.CATALOG: _view(
        "v_staff_agent_catalog",
        {
            "doctor_id": _uuid,
            "doctor_name": _text,
            "doctor_title": _text,
            "specialty_id": _uuid,
            "specialty_name": _text,
            "facility_id": _uuid,
            "facility_name": _text,
            "service_id": _uuid,
            "service_name": _text,
            "booking_mode": _text,
        },
    ),
    StaffQuerySubject.AVAILABILITY: _view(
        "v_staff_agent_availability",
        {
            "schedule_id": _uuid,
            "doctor_id": _uuid,
            "doctor_name": _text,
            "specialty_id": _uuid,
            "specialty_name": _text,
            "facility_id": _uuid,
            "facility_name": _text,
            "service_id": _uuid,
            "service_name": _text,
            "starts_at": _time,
            "ends_at": _time,
            "remaining_capacity": _int,
        },
    ),
    StaffQuerySubject.BOOKING_OPERATIONS: _view(
        "v_staff_agent_booking_operations",
        {
            "booking_id": _uuid,
            "booking_status": _text,
            "starts_at": _time,
            "ends_at": _time,
            "created_at": _time,
            "doctor_id": _uuid,
            "doctor_name": _text,
            "specialty_id": _uuid,
            "specialty_name": _text,
            "facility_id": _uuid,
            "facility_name": _text,
            "service_id": _uuid,
            "service_name": _text,
        },
    ),
    StaffQuerySubject.CASE_OPERATIONS: _view(
        "v_staff_agent_case_operations",
        {
            "case_id": _uuid,
            "case_status": _text,
            "priority": _int,
            "facility_id": _uuid,
            "facility_name": _text,
            "assigned_to": _uuid,
            "due_at": _time,
            "created_at": _time,
            "booking_id": _uuid,
        },
    ),
}

_MEANINGFUL_FILTERS = {
    StaffQuerySubject.CATALOG: {"doctor_name", "specialty_name", "facility_name", "service_name"},
    StaffQuerySubject.AVAILABILITY: {"doctor_name", "specialty_name", "facility_name", "service_name"},
    StaffQuerySubject.BOOKING_OPERATIONS: {
        "booking_status",
        "doctor_name",
        "facility_name",
        "service_name",
        "starts_at",
    },
    StaffQuerySubject.CASE_OPERATIONS: {"case_status", "facility_name", "assigned_to", "due_at", "priority"},
}


def _typed_value(field: str, value: Any) -> Any:
    column_type = next(view.c[field].type for view in _views.values() if field in view.c)
    if isinstance(column_type, PG_UUID):
        return UUID(str(value))
    if isinstance(column_type, DateTime):
        if not isinstance(value, str):
            raise ValueError("Timestamp filters must be ISO-8601 strings")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timestamp filters must include a timezone")
        return parsed
    if isinstance(column_type, Integer):
        if isinstance(value, bool):
            raise ValueError("Integer filters must be integers")
        return int(value)
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError("Text filters must be strings of at most 200 characters")
    return value


def _filter_expression(view: Table, item: Any):
    column = view.c[item.field]
    operator = item.operator
    if operator == StaffQueryOperator.CONTAINS:
        value = _typed_value(item.field, item.value)
        if not isinstance(column.type, String):
            raise ValueError("contains is only supported for text fields")
        escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return column.ilike(f"%{escaped}%", escape="\\")
    if operator == StaffQueryOperator.BETWEEN:
        if not isinstance(item.value, list) or len(item.value) != 2:
            raise ValueError("between requires exactly two values")
        lower, upper = (_typed_value(item.field, value) for value in item.value)
        if lower >= upper:
            raise ValueError("between lower bound must be earlier/smaller than upper bound")
        return column.between(lower, upper)
    if operator == StaffQueryOperator.IN:
        if not isinstance(item.value, list) or not 1 <= len(item.value) <= 20:
            raise ValueError("in requires between one and twenty values")
        return column.in_([_typed_value(item.field, value) for value in item.value])
    value = _typed_value(item.field, item.value)
    if operator == StaffQueryOperator.EQUALS:
        return column == value
    if operator == StaffQueryOperator.GTE:
        return column >= value
    if operator == StaffQueryOperator.LTE:
        return column <= value
    raise ValueError("Unsupported query operator")


def build_staff_query(plan: StaffQueryPlan, facility_ids: list[UUID], *, staff_id: UUID):
    """Compile a validated plan to a parameterized SELECT against one fixed view."""
    view = _views[plan.subject]
    allowed = set(view.c.keys())
    selected = set(plan.select)
    if not selected or not selected <= allowed:
        raise ValueError("The selected fields are not available for this query")
    if len(selected) != len(plan.select):
        raise ValueError("Duplicate selected fields are not allowed")
    meaningful = {item.field for item in plan.filters} & _MEANINGFUL_FILTERS[plan.subject]
    if not meaningful:
        raise ValueError("Add a filter that narrows this lookup")
    if any(item.field not in allowed for item in plan.filters):
        raise ValueError("A filter field is not available for this query")
    if any(item.field not in selected for item in plan.sort):
        raise ValueError("Sort fields must also be selected")
    if any(item.field not in allowed for item in plan.sort):
        raise ValueError("A sort field is not available for this query")
    if plan.subject == StaffQuerySubject.AVAILABILITY:
        window = next(
            (
                item
                for item in plan.filters
                if item.field == "starts_at" and item.operator == StaffQueryOperator.BETWEEN
            ),
            None,
        )
        if window is None:
            raise ValueError("Availability queries require a bounded starts_at window")
        start, end = (_typed_value("starts_at", value) for value in window.value)
        now = datetime.now(start.tzinfo)
        if start < now or end - start > timedelta(days=31):
            raise ValueError("Availability window must be future-facing and at most 31 days")

    expressions = []
    for item in plan.filters:
        if (
            plan.subject == StaffQuerySubject.CASE_OPERATIONS
            and item.field == "assigned_to"
            and item.operator == StaffQueryOperator.EQUALS
            and item.value == "me"
        ):
            item = item.model_copy(update={"value": str(staff_id)})
        expressions.append(_filter_expression(view, item))
    if plan.subject == StaffQuerySubject.AVAILABILITY:
        expressions.append(view.c.remaining_capacity > 0)
    if "facility_id" in view.c and facility_ids:
        facility_scope = view.c.facility_id.in_(facility_ids)
        if plan.subject == StaffQuerySubject.CASE_OPERATIONS:
            facility_scope = or_(view.c.facility_id.is_(None), facility_scope)
        expressions.append(facility_scope)
    if not isinstance(staff_id, UUID):
        raise ValueError("Invalid staff principal")

    statement = select(*(view.c[field] for field in plan.select)).where(and_(*expressions))
    ordering = [asc(view.c[item.field]) if item.direction == "asc" else desc(view.c[item.field]) for item in plan.sort]
    if ordering:
        statement = statement.order_by(*ordering)
    return statement.limit(plan.limit + 1)


async def execute_staff_query(session: AsyncSession, plan: StaffQueryPlan, facility_ids: list[UUID], staff_id: UUID):
    statement = build_staff_query(plan, facility_ids, staff_id=staff_id)
    result = await session.execute(statement)
    return [dict(row._mapping) for row in result.fetchall()]
