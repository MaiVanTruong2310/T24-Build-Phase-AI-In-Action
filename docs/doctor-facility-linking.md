# Doctor–facility linking

Doctors and facilities use a many-to-many relationship through
`doctor_facilities`. A doctor can work at more than one facility, and a
facility can contain many doctors. Do not add a single `facility_id` column to
`doctors`.

## Source and matching rules

`scripts/link_doctors_to_facilities.py` joins operational doctors to the
Vietnamese Vinmec crawl. The `doc-vinmec-NNNN` sequence and doctor name must
both match the crawl record at the same position. The script then reads only
the current `Nơi làm việc` field. It does not infer the current facility from
the biography or historical work experience.

Facility matching is deterministic and distinguishes hospitals from general
clinics. For example, a specialized clinic inside Vinmec Times City still maps
to the Times City hospital, while `Phòng khám Đa khoa quốc tế Vinmec Times
City` maps to the general clinic row.

Unrecognized organization-wide units, research institutes, and records with
no current workplace remain unlinked in the generated review report.

## Runbook

Dry run and generate the review artifacts:

```powershell
python -B scripts/link_doctors_to_facilities.py
```

Outputs:

- `data/generated/doctor_facility_link_plan.json`: counts, source evidence,
  generated links, and unresolved records.
- `scripts/supabase/migrations/20260930010000_link_doctors_to_facilities.sql`:
  idempotent upsert migration with an orphan check.

Apply directly only when `DATABASE_URL` points to the target Supabase
PostgreSQL database:

```powershell
python -B scripts/link_doctors_to_facilities.py --apply
```

The apply path checks the expected unique constraint, performs an upsert on
`(doctor_id, facility_id, room)`, and verifies that no orphan relationship
exists. It never deletes existing relationships.

## Application behavior

`DoctorScheduleService` resolves a facility UUID, code, or canonical name,
intersects `doctor_specialties` with active `doctor_facilities`, and filters
`doctor_schedules` by the same facility. If operational schedules are empty,
the sourced crawl fallback uses the same canonical facility matching rules.

`FacilityService` reads linked doctors from Supabase first and uses the current
workplace field from the crawl only as a fallback.
