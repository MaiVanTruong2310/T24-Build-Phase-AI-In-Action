"""Create medical catalog, schedules, and durable catalog audit tables."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_medical_catalog"
down_revision = "0002_user_personal_information"
branch_labels = None
depends_on = None


def _uuid(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "specialties",
        _uuid("id"),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        if_not_exists=True,
    )
    op.create_index("ix_specialties_code", "specialties", ["code"], if_not_exists=True)

    op.create_table(
        "facilities",
        _uuid("id"),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        if_not_exists=True,
    )
    op.create_index("ix_facilities_code", "facilities", ["code"], if_not_exists=True)

    op.create_table(
        "services",
        _uuid("id"),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        if_not_exists=True,
    )
    op.create_index("ix_services_code", "services", ["code"], if_not_exists=True)

    op.create_table(
        "doctors",
        _uuid("id"),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("license_number", sa.String(64), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("review_status", sa.String(32), server_default="approved", nullable=False),
        sa.Column("booking_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("license_number"),
        if_not_exists=True,
    )
    op.create_index("ix_doctors_code", "doctors", ["code"], if_not_exists=True)

    op.create_table(
        "doctor_specialties",
        _uuid("id"),
        _uuid("doctor_id"),
        _uuid("specialty_id"),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["specialty_id"], ["specialties.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "specialty_id", name="uq_doctor_specialty"),
        if_not_exists=True,
    )
    op.create_index("ix_doctor_specialties_doctor_id", "doctor_specialties", ["doctor_id"], if_not_exists=True)
    op.create_index("ix_doctor_specialties_specialty_id", "doctor_specialties", ["specialty_id"], if_not_exists=True)

    op.create_table(
        "doctor_facilities",
        _uuid("id"),
        _uuid("doctor_id"),
        _uuid("facility_id"),
        sa.Column("department", sa.String(160), nullable=True),
        sa.Column("room", sa.String(64), nullable=True),
        sa.Column("active_from", sa.Date(), nullable=True),
        sa.Column("active_to", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "facility_id", name="uq_doctor_facility"),
        if_not_exists=True,
    )
    op.create_index("ix_doctor_facilities_doctor_id", "doctor_facilities", ["doctor_id"], if_not_exists=True)
    op.create_index("ix_doctor_facilities_facility_id", "doctor_facilities", ["facility_id"], if_not_exists=True)

    op.create_table(
        "doctor_services",
        _uuid("id"),
        _uuid("doctor_id"),
        _uuid("service_id"),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "service_id", name="uq_doctor_service"),
        if_not_exists=True,
    )
    op.create_index("ix_doctor_services_doctor_id", "doctor_services", ["doctor_id"], if_not_exists=True)
    op.create_index("ix_doctor_services_service_id", "doctor_services", ["service_id"], if_not_exists=True)

    op.create_table(
        "doctor_schedules",
        _uuid("id"),
        _uuid("doctor_id"),
        _uuid("facility_id"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), server_default="available", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_system", sa.String(64), nullable=True),
        sa.Column("external_schedule_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "external_schedule_id", name="uq_schedule_external_identity"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_schedule_time_order"),
        sa.CheckConstraint("capacity >= 0", name="ck_schedule_capacity_nonnegative"),
        if_not_exists=True,
    )
    op.create_index("ix_doctor_schedules_doctor_id", "doctor_schedules", ["doctor_id"], if_not_exists=True)
    op.create_index("ix_doctor_schedules_facility_id", "doctor_schedules", ["facility_id"], if_not_exists=True)
    op.create_index("ix_doctor_schedules_starts_at", "doctor_schedules", ["starts_at"], if_not_exists=True)

    op.create_table(
        "catalog_audit_events",
        _uuid("id"),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        _uuid("entity_id"),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("ix_catalog_audit_events_actor_id", "catalog_audit_events", ["actor_id"], if_not_exists=True)
    op.create_index("ix_catalog_audit_events_entity_type", "catalog_audit_events", ["entity_type"], if_not_exists=True)
    op.create_index("ix_catalog_audit_events_entity_id", "catalog_audit_events", ["entity_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_catalog_audit_events_entity_id", table_name="catalog_audit_events")
    op.drop_index("ix_catalog_audit_events_entity_type", table_name="catalog_audit_events")
    op.drop_index("ix_catalog_audit_events_actor_id", table_name="catalog_audit_events")
    op.drop_table("catalog_audit_events")
    op.drop_index("ix_doctor_schedules_starts_at", table_name="doctor_schedules")
    op.drop_index("ix_doctor_schedules_facility_id", table_name="doctor_schedules")
    op.drop_index("ix_doctor_schedules_doctor_id", table_name="doctor_schedules")
    op.drop_table("doctor_schedules")
    op.drop_index("ix_doctor_services_service_id", table_name="doctor_services")
    op.drop_index("ix_doctor_services_doctor_id", table_name="doctor_services")
    op.drop_table("doctor_services")
    op.drop_index("ix_doctor_facilities_facility_id", table_name="doctor_facilities")
    op.drop_index("ix_doctor_facilities_doctor_id", table_name="doctor_facilities")
    op.drop_table("doctor_facilities")
    op.drop_index("ix_doctor_specialties_specialty_id", table_name="doctor_specialties")
    op.drop_index("ix_doctor_specialties_doctor_id", table_name="doctor_specialties")
    op.drop_table("doctor_specialties")
    op.drop_index("ix_doctors_code", table_name="doctors")
    op.drop_table("doctors")
    op.drop_index("ix_services_code", table_name="services")
    op.drop_table("services")
    op.drop_index("ix_facilities_code", table_name="facilities")
    op.drop_table("facilities")
    op.drop_index("ix_specialties_code", table_name="specialties")
    op.drop_table("specialties")
