import { fetchWithAuth } from '../../app/apiClient';

export interface Specialty {
  id: string;
  code: string;
  name: string;
  description: string;
}

export interface Doctor {
  id: string;
  code: string;
  full_name: string;
  avatar_url: string | null;
  title: string | null;
  rating?: number; // assuming additional UI field
  experience_years?: number; // assuming additional UI field
  price?: number; // assuming additional UI field
}

export interface Schedule {
  id: string;
  starts_at: string;
  ends_at: string;
  capacity: number;
  status: 'available' | 'inactive' | 'blocked' | 'cancelled';
  version: number;
}

export interface CreateBookingPayload {
  schedule_id: string;
  service_id: string;
  specialty_id: string;
  ai_triage_id: string;
  encounter_type: 'in_person' | 'telehealth';
  reason: string;
  patient_note?: string;
}

export async function fetchSpecialties(): Promise<Specialty[]> {
  const res = await fetchWithAuth('/specialties');
  if (!res.ok) throw new Error('Failed to fetch specialties');
  const json = await res.json();
  return json.data || [];
}

export async function fetchDoctors(specialtyId?: string): Promise<Doctor[]> {
  const query = specialtyId ? `?specialty_id=${specialtyId}` : '';
  const res = await fetchWithAuth(`/doctors${query}`);
  if (!res.ok) throw new Error('Failed to fetch doctors');
  const json = await res.json();
  return json.data || [];
}

export async function fetchAvailability(doctorId: string, date: string): Promise<Schedule[]> {
  const res = await fetchWithAuth(`/doctors/${doctorId}/availability?date=${date}`);
  if (!res.ok) throw new Error('Failed to fetch availability');
  const json = await res.json();
  return json.data || [];
}

export async function createBooking(payload: CreateBookingPayload): Promise<unknown> {
  const res = await fetchWithAuth('/bookings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to create booking');
  return res.json();
}
