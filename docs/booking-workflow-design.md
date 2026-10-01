# Booking workflow design

## Understanding

- A doctor schedule is published availability and capacity, not itself a patient booking.
- Patient-created bookings are always `pending_approval`, including bookings attached to a schedule with capacity.
- A pending booking reserves one effective capacity unit. Expiration, rejection, and cancellation release that reservation.
- Staff-created schedules for shared/group services do not create bookings; patients select those schedules and the backend creates the booking.
- Staff-created schedules for doctor visits may create a `confirmed` booking when a registered or guest patient is supplied.
- Frontend displays service/patient names but sends IDs for existing records. Guest forms send contact data for backend patient resolution.
- The temporary `BookingHold` workflow is removed.

## Assumptions

- Existing `services.booking_mode` (`group` or `doctor_visit`) is authoritative.
- Guest patients are represented by a temporary `User` patient record so the existing non-null `bookings.user_id` contract remains intact.
- `doctor_schedules.capacity` remains the configured maximum; effective remaining capacity is derived from `pending_approval` and `confirmed` bookings.
- All schedule/booking transitions use one transaction and row locks to prevent double booking.
- Existing notification and audit behavior remains, except hold-specific notifications and endpoints.

## Decision log

1. **Remove holds.** The approval workflow already reserves capacity through a pending booking and has a cron expiry path; a second temporary hold is redundant.
2. **Use service mode, not a frontend flag.** The request carries `service_id`; the backend loads `booking_mode` from the database to prevent client-side misclassification.
3. **Keep capacity as maximum.** Counting active bookings avoids mutating the configured capacity and makes repeated cron runs idempotent.
4. **Create guest users transactionally.** This preserves ownership, staff patient context, notifications, and existing foreign-key constraints without duplicating PII columns on bookings.

## Acceptance criteria

- No booking or frontend request references `BookingHold`.
- Patient schedule booking returns `pending_approval` and rejects when effective capacity is exhausted.
- Expired, rejected, and cancelled pending bookings no longer consume capacity.
- Group schedule creation returns a schedule without a booking.
- Doctor-visit schedule creation with a patient returns a confirmed booking; guest contact data is resolved to a patient user.
- Existing booking, schedule, notification, and staff review tests remain green or are updated to the new contract.
