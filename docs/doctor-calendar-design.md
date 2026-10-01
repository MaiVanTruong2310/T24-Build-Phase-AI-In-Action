# Doctor Schedule Types and Patient Slot Generation

## Scope

- Keep the existing `doctor_schedules` table.
- Add `type` and `note` fields; do not create a new calendar table.
- Keep the existing availability endpoint and extend its response with schedule type information.
- Generate patient-facing slots from the selected service duration.
- Allow staff to create schedules at any time, including outside the default window.

## Business rules

### Schedule type

`type` is one of:

- `consultation`: a bookable doctor schedule with a facility and capacity.
- `busy`: a doctor-wide or facility-specific blocked period.
- `leave`: a leave period that blocks booking.
- `other`: another operational block such as training or a meeting.

`status` remains the lifecycle state (`available`, `blocked`, `inactive`, `cancelled`).
`note` stores the internal explanation. Patient UI does not expose the note.

### Patient slots

- Default working window: 08:00-18:00 in `Asia/Ho_Chi_Minh`.
- Patient slot length and step equal the selected service duration.
- A staff-created `consultation` schedule is an explicit time window and is rendered using its own start/end values.
- Generated slots are created only in gaps not covered by a consultation schedule or a non-cancelled blocking schedule.
- Busy, leave and other schedules disable overlapping slots.
- A consultation slot remains selectable while `remaining_capacity > 0`.
- If remaining capacity is unavailable, the patient UI displays `Con trong` rather than guessing a number.
- Staff-created consultation schedules outside 08:00-18:00 are still returned and selectable.

## API contract

The existing endpoint remains the source for schedule blocks:

```http
GET /api/v1/doctors/{doctor_id}/availability
    ?date=YYYY-MM-DD
    &facility_id={uuid}
    &service_id={uuid}
```

The response includes `type`, `note`, nullable `facility_id`, `capacity`, and
`remaining_capacity`. Blocking schedules may have a null facility and apply to
all facilities; a facility-specific block applies only to that facility.

The backend still filters inactive doctors/facilities. Consultation schedules
must be available and have positive remaining capacity. Blocking schedules are
returned so the patient page can disable overlapping generated slots.

## Booking validation

The booking transaction rechecks the selected time. It rejects:

- a non-consultation schedule used as `schedule_id`;
- a requested time overlapping a non-cancelled busy/leave/other schedule;
- an overlapping active doctor-visit booking;
- a consultation schedule with no remaining capacity.

For generated requested-time slots, the request contains doctor, facility,
service, start and end timestamps and remains pending staff review.

## Database compatibility

- Existing rows are migrated to `type = 'consultation'`.
- `facility_id` becomes nullable for doctor-wide blocking periods.
- The PostgreSQL overlap exclusion applies only to consultation schedules so a
  blocking schedule can overlap a consultation window and disable it.
- Existing schedule status and booking behavior remain compatible.

## Frontend behavior

Staff schedule create/update forms expose type and note. Service, patient and
capacity fields are relevant only for consultation schedules. The patient page
renders service-duration slots, includes explicit staff schedules outside the
default window, and marks blocked/past/full periods as unavailable.

## Decision log

1. Reuse `doctor_schedules` instead of adding a second table.
2. Use `type` for business meaning and `status` for lifecycle state.
3. Keep the existing availability endpoint; do not add a calendar endpoint.
4. Let patient slot length/step come from service duration.
5. Permit arbitrary staff schedule times; the default 08:00-18:00 window is
   only used for generated patient slots.
