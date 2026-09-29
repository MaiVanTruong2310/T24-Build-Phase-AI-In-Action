import {
  fetchStaffBooking,
  updateBookingStatus,
  type PendingBooking,
} from '../AppointmentApproval/api';

export type Booking = PendingBooking;

export async function fetchBooking(id: string): Promise<Booking> {
  return fetchStaffBooking(id);
}

export async function updateBookingReview(
  id: string,
  status: 'confirmed' | 'rejected',
  note?: string,
): Promise<Booking> {
  return updateBookingStatus(id, status, note);
}
