import { fetchWithAuth } from '../../app/apiClient';

export interface Booking {
  id: string;
  booking_code: string;
  patient_id: string;
  doctor_id: string;
  facility_id: string;
  specialty_id: string;
  service_id: string;
  schedule_id: string;
  status: 'pending' | 'pending_approval' | 'confirmed' | 'rejected' | 'cancelled' | 'attended';
  reason: string | null;
  patient_note: string | null;
  hold_expires_at: string | null;
  requested_at: string;
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  staff_note: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchBooking(id: string): Promise<Booking> {
  const response = await fetchWithAuth(`/bookings/${id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch booking');
  }
  const data = await response.json();
  return data.data || data;
}

export async function updateBookingStatus(id: string, status: string, note?: string): Promise<Booking> {
  const payload: { status: string; note?: string } = { status };
  if (note) payload.note = note;

  const response = await fetchWithAuth(`/bookings/${id}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error('Failed to update booking status');
  }
  const data = await response.json();
  return data.data || data;
}
