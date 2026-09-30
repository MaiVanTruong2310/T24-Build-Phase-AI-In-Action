import { fetchWithAuth } from '../../app/apiClient';

export interface Specialty {
  id: string;
  code: string;
  name: string;
  description: string;
}

export interface Facility {
  id: string;
  code: string;
  name: string;
  address?: string | null;
  phone?: string | null;
}

export interface MedicalService {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  duration_minutes?: number | null;
  price?: number | null;
  original_price?: number | null;
  category?: string | null;
  features?: string[] | null;
  booking_mode?: 'group' | 'doctor_visit';
  patient_count?: number | null;
  satisfaction_rate?: number | null;
}

export interface Doctor {
  id: string;
  code: string;
  full_name: string;
  bio?: string | null;
  avatar_url: string | null;
  title: string | null;
  rating?: number; // assuming additional UI field
  experience_years?: number; // assuming additional UI field
  price?: number; // assuming additional UI field
  facilities?: DoctorFacility[];
  facility_ids?: string[];
  service_ids?: string[];
  specialties?: Array<{ specialty_id: string; name: string }>;
  services?: Array<{ service_id: string; name: string }>;
}

export interface DoctorFacility {
  facility_id: string;
  department?: string | null;
  room?: string | null;
  facility?: {
    id: string;
    code: string;
    name: string;
  } | null;
}

export interface Schedule {
  id: string;
  doctor_id: string;
  facility_id: string;
  starts_at: string;
  ends_at: string;
  capacity: number;
  status: 'available' | 'inactive' | 'blocked' | 'cancelled';
  version: number;
  source_system?: string | null;
  external_schedule_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ScheduleAuditEvent {
  id: string;
  actor_id: string | null;
  entity_type: string;
  entity_id: string;
  action: 'created' | 'updated' | 'cancelled' | 'imported' | string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface CreateSchedulePayload {
  doctor_id: string;
  facility_id: string;
  starts_at: string;
  ends_at: string;
  capacity: number;
  status: 'available' | 'inactive' | 'blocked';
  source_system?: string;
  external_schedule_id?: string;
}

export interface UpdateSchedulePayload {
  starts_at: string;
  ends_at: string;
  capacity: number;
  status: 'available' | 'inactive' | 'blocked';
  expected_version: number;
}

export class ScheduleApiError extends Error {
  status: number;
  code?: number;

  constructor(message: string, status: number, code?: number) {
    super(message);
    this.name = 'ScheduleApiError';
    this.status = status;
    this.code = code;
  }
}

export interface CreateBookingPayload {
  hold_id?: string;
  schedule_id?: string;
  doctor_id?: string;
  facility_id?: string;
  starts_at?: string;
  ends_at?: string;
  service_id: string;
  specialty_id: string;
  encounter_type: 'in_person' | 'telehealth';
  reason: string;
  patient_note?: string;
}

export type BookingStatus = 'pending_approval' | 'confirmed' | 'rejected' | 'cancelled';

export interface Booking {
  id: string;
  user_id: string;
  schedule_id: string | null;
  hold_id: string | null;
  service_id: string;
  specialty_id: string;
  doctor_id: string;
  facility_id: string;
  starts_at: string;
  ends_at: string;
  booking_mode: 'group' | 'doctor_visit';
  encounter_type: 'in_person' | 'telehealth';
  reason: string;
  patient_note: string | null;
  status: BookingStatus;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface RescheduleBookingPayload {
  schedule_id: string;
  hold_id: string;
}

export type BookingHoldStatus = 'active' | 'released' | 'expired' | 'consumed';

export interface BookingHold {
  id: string;
  user_id: string;
  schedule_id: string;
  service_id: string;
  specialty_id: string;
  status: BookingHoldStatus;
  expires_at: string;
  released_at: string | null;
  created_at: string;
}

export class BookingApiError extends Error {
  status: number;
  code?: number;

  constructor(message: string, status: number, code?: number) {
    super(message);
    this.name = 'BookingApiError';
    this.status = status;
    this.code = code;
  }
}

export async function fetchSpecialties(): Promise<Specialty[]> {
  const res = await fetchWithAuth('/specialties');
  if (!res.ok) throw new Error('Failed to fetch specialties');
  const json = await res.json();
  return json.data || [];
}

export async function fetchDoctors(
  filters: { specialtyId?: string; facilityId?: string; serviceId?: string; name?: string; bookingEnabled?: boolean } | string = {},
): Promise<Doctor[]> {
  const normalizedFilters = typeof filters === 'string' ? { specialtyId: filters } : filters;
  const query = new URLSearchParams();
  if (normalizedFilters.specialtyId) query.set('specialty_id', normalizedFilters.specialtyId);
  if (normalizedFilters.facilityId) query.set('facility_id', normalizedFilters.facilityId);
  if (normalizedFilters.serviceId) query.set('service_id', normalizedFilters.serviceId);
  if (normalizedFilters.name) query.set('name', normalizedFilters.name);
  if (normalizedFilters.bookingEnabled !== undefined) {
    query.set('booking_enabled', String(normalizedFilters.bookingEnabled));
  }
  const queryString = query.toString();
  const res = await fetchWithAuth(`/doctors${queryString ? `?${queryString}` : ''}`);
  if (!res.ok) throw new Error('Failed to fetch doctors');
  const json = await res.json();
  return (json.data || []).map((doctor: Record<string, unknown>) => ({
    ...doctor,
    service_ids: (doctor.service_ids as string[] | undefined)
      || ((doctor.services as Array<{ service_id: string }> | undefined) || []).map((item) => item.service_id),
    specialties: ((doctor.specialties as Array<{ specialty_id: string; specialty?: { name: string } | null }> | undefined) || []).map((item) => ({
      specialty_id: item.specialty_id,
      name: item.specialty?.name || 'Chưa cập nhật',
    })),
    services: ((doctor.services as Array<{ service_id: string; service?: { name: string } | null }> | undefined) || []).map((item) => ({
      service_id: item.service_id,
      name: item.service?.name || 'Chưa cập nhật',
    })),
  })) as Doctor[];
}

export async function fetchFacilities(): Promise<Facility[]> {
  const res = await fetchWithAuth('/facilities');
  if (!res.ok) throw new Error('Failed to fetch facilities');
  const json = await res.json();
  return json.data || [];
}

export async function fetchServices(filters: { specialtyId?: string; facilityId?: string } = {}): Promise<MedicalService[]> {
  const query = new URLSearchParams();
  if (filters.specialtyId) query.set('specialty_id', filters.specialtyId);
  if (filters.facilityId) query.set('facility_id', filters.facilityId);
  const queryString = query.toString();
  const res = await fetchWithAuth(`/services${queryString ? `?${queryString}` : ''}`);
  if (!res.ok) throw new Error('Failed to fetch services');
  const json = await res.json();
  return json.data || [];
}

export async function fetchAvailability(doctorId: string, date: string, facilityId?: string, serviceId?: string): Promise<Schedule[]> {
  const query = new URLSearchParams({ date });
  if (facilityId) query.set('facility_id', facilityId);
  if (serviceId) query.set('service_id', serviceId);
  const res = await fetchWithAuth(`/doctors/${doctorId}/availability?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch availability');
  const json = await res.json();
  return json.data || [];
}

export async function fetchDoctorSchedules(doctorId: string, from: string, to: string): Promise<Schedule[]> {
  const query = new URLSearchParams({ doctor_id: doctorId, from, to });
  const res = await fetchWithAuth(`/staff/schedules?${query.toString()}`);
  if (!res.ok) {
    throw await toScheduleApiError(res);
  }
  const json = await res.json();
  return json.data || [];
}

export async function fetchScheduleActivity(
  doctorId: string,
  from: string,
  to: string,
): Promise<ScheduleAuditEvent[]> {
  const query = new URLSearchParams({ doctor_id: doctorId, from, to });
  const res = await fetchWithAuth(`/staff/schedule-activity?${query.toString()}`);
  if (!res.ok) {
    throw await toScheduleApiError(res);
  }
  const json = await res.json();
  return json.data || [];
}

export async function createDoctorSchedule(payload: CreateSchedulePayload): Promise<Schedule> {
  const res = await fetchWithAuth('/staff/schedules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw await toScheduleApiError(res);
  }
  const json = await res.json();
  return json.data;
}

export async function updateDoctorSchedule(
  scheduleId: string,
  payload: UpdateSchedulePayload,
): Promise<Schedule> {
  const res = await fetchWithAuth(`/staff/schedules/${scheduleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw await toScheduleApiError(res);
  }
  const json = await res.json();
  return json.data;
}

async function toScheduleApiError(response: Response): Promise<ScheduleApiError> {
  try {
    const json = await response.json();
    return new ScheduleApiError(
      json.message || 'Không thể thực hiện thao tác với lịch khám',
      response.status,
      json.error?.code,
    );
  } catch {
    return new ScheduleApiError('Không thể thực hiện thao tác với lịch khám', response.status);
  }
}

export async function createBooking(payload: CreateBookingPayload, idempotencyKey?: string): Promise<Booking> {
  const res = await fetchWithAuth('/bookings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey || crypto.randomUUID(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await toBookingApiError(res);
  const json = await res.json();
  return json.data as Booking;
}

export async function rescheduleBooking(
  bookingId: string,
  payload: RescheduleBookingPayload,
): Promise<Booking> {
  const res = await fetchWithAuth(`/bookings/${bookingId}/reschedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await toBookingApiError(res);
  const json = await res.json();
  return json.data as Booking;
}

export async function createBookingHold(
  scheduleId: string,
  serviceId: string,
  specialtyId: string,
  holdSeconds = 300,
): Promise<BookingHold> {
  const res = await fetchWithAuth('/bookings/hold', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schedule_id: scheduleId,
      service_id: serviceId,
      specialty_id: specialtyId,
      hold_seconds: holdSeconds,
    }),
  });
  if (!res.ok) throw await toBookingApiError(res);
  const json = await res.json();
  return json.data as BookingHold;
}

export async function releaseBookingHold(holdId: string): Promise<void> {
  const res = await fetchWithAuth(`/bookings/holds/${holdId}`, { method: 'DELETE' });
  if (!res.ok) throw await toBookingApiError(res);
}

export async function fetchBookings(status?: BookingStatus): Promise<Booking[]> {
  const query = new URLSearchParams({ offset: '0', limit: '50' });
  if (status) query.set('status', status);
  const res = await fetchWithAuth(`/bookings?${query.toString()}`);
  if (!res.ok) throw await toBookingApiError(res);
  const json = await res.json();
  return (json.data || []) as Booking[];
}

export async function fetchBooking(bookingId: string): Promise<Booking> {
  const res = await fetchWithAuth(`/bookings/${bookingId}`);
  if (!res.ok) throw await toBookingApiError(res);
  const json = await res.json();
  return json.data as Booking;
}

export async function cancelBooking(bookingId: string, reason?: string): Promise<Booking> {
  const res = await fetchWithAuth(`/bookings/${bookingId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(reason?.trim() ? { reason: reason.trim() } : {}),
  });
  if (!res.ok) throw await toBookingApiError(res);
  const json = await res.json();
  return json.data as Booking;
}

async function toBookingApiError(response: Response): Promise<BookingApiError> {
  try {
    const json = await response.json();
    return new BookingApiError(
      json.message || 'Không thể thực hiện thao tác với lịch hẹn',
      response.status,
      json.error?.code,
    );
  } catch {
    return new BookingApiError('Không thể thực hiện thao tác với lịch hẹn', response.status);
  }
}
