"""Metadata and API surface tests for the catalog bounded context."""

from src.db.base import Base
from src.main import app


def test_catalog_metadata_contains_required_tables_and_constraints():
    """The ORM metadata includes all Sprint 002 persistence objects."""
    required = {
        "specialties",
        "facilities",
        "services",
        "doctors",
        "doctor_specialties",
        "doctor_facilities",
        "doctor_services",
        "doctor_schedules",
        "catalog_audit_events",
    }

    assert required.issubset(Base.metadata.tables)
    schedule = Base.metadata.tables["doctor_schedules"]
    assert {constraint.name for constraint in schedule.constraints} >= {
        "uq_schedule_external_identity",
        "excl_doctor_schedule_time",
        "ck_schedule_time_order",
        "ck_schedule_capacity_nonnegative",
    }
    assert {"created_by", "updated_by", "cancellation_reason"}.issubset(schedule.c.keys())


def test_catalog_routes_are_mounted_under_api_v1():
    """Only the approved catalog endpoints are exposed in OpenAPI."""
    paths = app.openapi()["paths"]
    expected = {
        ("GET", "/api/v1/specialties"),
        ("GET", "/api/v1/specialties/{specialty_id}"),
        ("POST", "/api/v1/staff/specialties"),
        ("PATCH", "/api/v1/staff/specialties/{specialty_id}"),
        ("GET", "/api/v1/facilities"),
        ("GET", "/api/v1/facilities/{facility_id}"),
        ("POST", "/api/v1/staff/facilities"),
        ("PATCH", "/api/v1/staff/facilities/{facility_id}"),
        ("GET", "/api/v1/staff/services"),
        ("POST", "/api/v1/staff/services"),
        ("PATCH", "/api/v1/staff/services/{service_id}"),
        ("GET", "/api/v1/doctors"),
            ("GET", "/api/v1/doctors/facets"),
        ("GET", "/api/v1/doctors/{doctor_id}"),
        ("GET", "/api/v1/doctors/{doctor_id}/availability"),
        ("GET", "/api/v1/staff/schedules"),
        ("POST", "/api/v1/staff/schedules"),
        ("PUT", "/api/v1/staff/schedules/{schedule_id}"),
        ("POST", "/api/v1/staff/schedules/import"),
        ("DELETE", "/api/v1/staff/schedules/{schedule_id}/cancel"),
        ("POST", "/api/v1/staff/doctors"),
            ("GET", "/api/v1/staff/doctors"),
            ("GET", "/api/v1/staff/doctors/{doctor_id}"),
        ("PATCH", "/api/v1/staff/doctors/{doctor_id}"),
        ("PATCH", "/api/v1/staff/doctors/{doctor_id}/toggle-booking"),
    }
    catalog_prefixes = (
        "/api/v1/specialties",
        "/api/v1/facilities",
        "/api/v1/doctors",
        "/api/v1/staff/specialties",
        "/api/v1/staff/facilities",
        "/api/v1/staff/services",
        "/api/v1/staff/schedules",
        "/api/v1/staff/doctors",
    )
    actual = {
        (method.upper(), path)
        for path, operations in paths.items()
        if path.startswith(catalog_prefixes)
        for method in operations
    }

    assert actual == expected
    assert not any(path.startswith("/api/v1/coordinator/") for path in paths)
