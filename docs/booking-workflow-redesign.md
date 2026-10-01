# Booking Workflow Redesign

## Understanding summary

- `DoctorSchedule` represents a doctor's available working window and capacity.
- Patient bookings always start as `pending_approval`, including bookings against a schedule with remaining capacity.
- A pending booking reserves logical capacity until it is confirmed, rejected, cancelled, or expired.
- Staff-created schedules behave differently based on the selected service's `booking_mode`.
- Group services, such as general health checks, create a schedule only; patients later select the schedule and create bookings.
- Doctor-visit services may create a confirmed booking when staff supplies a patient.
- The temporary `BookingHold` workflow is removed.

## Functional design

### Patient booking

1. Patient selects a public schedule and sends `schedule_id`, `service_id`, `specialty_id`, and booking details.
2. Backend loads the service and validates its doctor, facility, specialty, and capacity under a row lock.
3. Backend creates a `pending_approval` booking with the schedule relationship.
4. Capacity is represented as `schedule.capacity - active booking reservations`; the persisted `capacity` remains the configured maximum.
5. Staff confirmation changes the booking to `confirmed` without creating a duplicate schedule.
6. Rejection, cancellation, or expiry removes the booking from the active reservation set.

### Staff schedule creation

The schedule form sends `service_id` and optionally a registered `patient_id` or guest contact data.

- `group`: create only the schedule. No booking is created.
- `doctor_visit` with a patient: create the schedule and a `confirmed` booking in one transaction.
- `doctor_visit` without a patient: create only the schedule.

For a guest, the backend creates or resolves a temporary patient `User` using name, email, and phone, then stores the resulting `user_id` on the booking.

### Expiration and cleanup

The periodic worker scans only `pending_approval` bookings whose approval deadline has passed, marks them `expired`, and relies on active-booking filtering to release capacity. The operation must be idempotent. Rejected and cancelled bookings release capacity immediately through the same active-status rules.

## API and frontend changes

- Remove `hold_id` from booking creation and rescheduling contracts.
- Remove hold endpoints and all hold-specific response types and UI calls.
- Add `service_id` to staff schedule creation.
- Add optional `patient_id` and guest contact fields to the staff schedule form/request.
- Keep IDs in request payloads; expose service and patient names in response projections for display.
- Backend derives behavior from the persisted service `booking_mode`, never from an unchecked frontend mode value.

## Data and migration impact

- Remove the `booking_holds` table and related model/repository/service/schema code.
- Remove booking hold foreign keys and columns after existing data is migrated or retired.
- Preserve `schedule.capacity` as maximum capacity; calculate remaining capacity from active bookings.
- Add any required guest-user marker/status without weakening existing unique email/phone constraints.
- Preserve audit and notification behavior for booking confirmation, rejection, cancellation, and expiry.

## Non-functional requirements

- Use row-level locking for capacity decisions and one transaction for staff schedule plus confirmed booking creation.
- Keep patient and guest contact data protected by existing staff authorization and PHI/PII handling rules.
- Make expiry safe to retry and safe to run concurrently.
- Maintain current pagination, idempotency, audit logging, and notification guarantees.

## Acceptance criteria

1. No booking request requires or creates a hold.
2. A group schedule created by staff has no booking until a patient submits one.
3. A patient booking against available capacity is `pending_approval` and reduces effective availability.
4. Confirming that booking does not create a duplicate schedule.
5. Staff-created doctor-visit schedule with a patient creates exactly one `confirmed` booking.
6. Guest contact data resolves to exactly one patient user for the transaction.
7. Expired, rejected, and cancelled pending bookings no longer consume effective capacity.
8. Concurrent requests cannot exceed schedule capacity.

## Decision log

| Decision | Alternatives considered | Reason |
| --- | --- | --- |
| Remove `BookingHold` | Keep short-lived holds alongside approval bookings | Hold duplicates the pending-approval reservation state and complicates expiry. |
| Keep patient bookings pending approval | Confirm immediately when capacity exists | Staff approval is required by the business workflow. |
| Use service `booking_mode` as the authority | Trust a frontend mode field | Prevents client-side routing errors and tampering. |
| Group schedule creation creates no booking | Preserve automatic booking creation | Group schedules are shared availability for patients to choose later. |
| Guest becomes a temporary `User` | Add nullable guest columns to bookings | Preserves the existing booking ownership, staff projections, notifications, and patient lookup model. |
| Keep configured capacity and derive remaining capacity | Mutate capacity on every booking/expiry | Avoids double counting and makes cron retries idempotent. |

