"""Classify clinical roles and backfill searchable credentials from legacy titles."""

from alembic import op

revision = "0014_doctor_role_backfill"
down_revision = "0013_doctor_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE doctors ADD COLUMN professional_role varchar(40) NOT NULL DEFAULT 'Bác sĩ'")
    op.execute("""
        UPDATE doctors SET professional_role = CASE
          WHEN title ILIKE '%Điều dưỡng%' THEN 'Điều dưỡng'
          WHEN title ILIKE '%Dược sĩ%' THEN 'Dược sĩ'
          WHEN title ILIKE '%Kỹ thuật viên%' THEN 'Kỹ thuật viên'
          WHEN title ILIKE '%Chuyên gia%' THEN 'Chuyên gia'
          ELSE 'Bác sĩ' END
    """)
    op.execute("""
        UPDATE doctors AS d SET
          honors = CASE WHEN cardinality(honors) = 0 THEN ARRAY(
            SELECT btrim(token) FROM unnest(string_to_array(coalesce(d.title, ''), ',')) AS token
            WHERE btrim(token) IN ('Thầy thuốc ưu tú', 'Thầy thuốc nhân dân')
          ) ELSE honors END,
          academic_ranks = CASE WHEN cardinality(academic_ranks) = 0 THEN ARRAY(
            SELECT btrim(token) FROM unnest(string_to_array(coalesce(d.title, ''), ',')) AS token
            WHERE btrim(token) IN ('Giáo sư', 'Phó giáo sư')
          ) ELSE academic_ranks END,
          degrees = CASE WHEN cardinality(degrees) = 0 THEN ARRAY(
            SELECT btrim(token) FROM unnest(string_to_array(coalesce(d.title, ''), ',')) AS token
            WHERE btrim(token) IN ('Thạc sĩ', 'Tiến sĩ', 'Bác sĩ chuyên khoa I',
                                   'Bác sĩ chuyên khoa II', 'Bác sĩ nội trú', 'Cử nhân',
                                   'Dược sĩ chuyên khoa I')
          ) ELSE degrees END
    """)
    op.execute("CREATE INDEX ix_doctors_role_status ON doctors (professional_role, status, booking_enabled)")


def downgrade() -> None:
    op.execute("DROP INDEX ix_doctors_role_status")
    op.execute("ALTER TABLE doctors DROP COLUMN professional_role")
