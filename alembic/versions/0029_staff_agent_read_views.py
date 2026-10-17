"""Create narrow read-only views for staff agent operational queries."""

from collections.abc import Sequence

from alembic import op

revision: str = "0029_staff_agent_read_views"
down_revision: str | None = "0028_staff_agent_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Expose only operational columns to the separately provisioned reader."""
    op.execute(
        """
        CREATE OR REPLACE VIEW v_staff_agent_catalog AS
        SELECT d.id AS doctor_id, d.full_name AS doctor_name, d.title AS doctor_title,
               sp.id AS specialty_id, sp.name AS specialty_name,
               f.id AS facility_id, f.name AS facility_name,
               s.id AS service_id, s.name AS service_name, s.booking_mode
        FROM doctors d
        LEFT JOIN doctor_specialties ds ON ds.doctor_id = d.id
        LEFT JOIN specialties sp ON sp.id = ds.specialty_id AND sp.status = 'active'
        LEFT JOIN doctor_facilities df ON df.doctor_id = d.id
        LEFT JOIN facilities f ON f.id = df.facility_id AND f.status = 'active'
        LEFT JOIN doctor_services dsv ON dsv.doctor_id = d.id AND dsv.active
        LEFT JOIN services s ON s.id = dsv.service_id AND s.status = 'active'
        WHERE d.status = 'active' AND d.review_status = 'approved' AND d.booking_enabled
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_staff_agent_availability AS
        SELECT ds.id AS schedule_id, d.id AS doctor_id, d.full_name AS doctor_name,
               sp.id AS specialty_id, sp.name AS specialty_name,
               f.id AS facility_id, f.name AS facility_name,
               s.id AS service_id, s.name AS service_name,
               ds.starts_at, ds.ends_at,
               GREATEST(
                   CASE WHEN s.booking_mode = 'doctor_visit' THEN 1 ELSE ds.capacity END
                   - COALESCE((
                       SELECT count(*)
                       FROM bookings b
                       WHERE b.schedule_id = ds.id AND b.status = 'pending_approval'
                         AND b.expired_at > CURRENT_TIMESTAMP
                   ), 0)
                   - COALESCE((
                       SELECT count(*)
                       FROM booking_holds h
                       WHERE h.schedule_id = ds.id AND h.status = 'active'
                         AND h.expires_at > CURRENT_TIMESTAMP
                   ), 0),
                   0
               )::integer AS remaining_capacity
        FROM doctor_schedules ds
        JOIN doctors d ON d.id = ds.doctor_id
        JOIN facilities f ON f.id = ds.facility_id
        LEFT JOIN specialties sp ON sp.id = (
            SELECT dsx.specialty_id FROM doctor_specialties dsx
            JOIN specialties sx ON sx.id = dsx.specialty_id AND sx.status = 'active'
            WHERE dsx.doctor_id = d.id ORDER BY dsx.is_primary DESC, sx.name LIMIT 1
        )
        LEFT JOIN services s ON s.id = ds.service_id
        WHERE ds.status = 'available' AND ds.starts_at > CURRENT_TIMESTAMP
          AND d.status = 'active' AND d.review_status = 'approved' AND d.booking_enabled
          AND f.status = 'active'
          AND (ds.service_id IS NULL OR s.status = 'active')
          AND NOT EXISTS (
              SELECT 1 FROM bookings b
              WHERE b.appointment_schedule_id = ds.id
          )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_staff_agent_booking_operations AS
        SELECT b.id AS booking_id, b.status AS booking_status, b.starts_at, b.ends_at,
               b.created_at, d.id AS doctor_id, d.full_name AS doctor_name,
               sp.id AS specialty_id, sp.name AS specialty_name,
               f.id AS facility_id, f.name AS facility_name,
               s.id AS service_id, s.name AS service_name
        FROM bookings b
        JOIN doctors d ON d.id = b.doctor_id
        JOIN specialties sp ON sp.id = b.specialty_id
        JOIN facilities f ON f.id = b.facility_id
        JOIN services s ON s.id = b.service_id
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_staff_agent_case_operations AS
        SELECT c.id AS case_id, c.status AS case_status, c.priority,
               c.facility_id, f.name AS facility_name, c.assigned_to,
               c.due_at, c.created_at, c.booking_id
        FROM coordination_cases c
        LEFT JOIN facilities f ON f.id = c.facility_id
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'staff_agent_readonly') THEN
                EXECUTE 'GRANT USAGE ON SCHEMA public TO staff_agent_readonly';
                EXECUTE 'GRANT SELECT ON v_staff_agent_catalog, v_staff_agent_availability, '
                        'v_staff_agent_booking_operations, v_staff_agent_case_operations '
                        'TO staff_agent_readonly';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove only the read views introduced by this migration."""
    op.execute("DROP VIEW IF EXISTS v_staff_agent_case_operations")
    op.execute("DROP VIEW IF EXISTS v_staff_agent_booking_operations")
    op.execute("DROP VIEW IF EXISTS v_staff_agent_availability")
    op.execute("DROP VIEW IF EXISTS v_staff_agent_catalog")
