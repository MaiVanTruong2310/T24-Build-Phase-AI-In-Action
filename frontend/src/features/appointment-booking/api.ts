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
  category?: string | null;
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
  facilities?: DoctorFacility[];
  facility_ids?: string[];
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

export async function fetchDoctors(
  filters: { specialtyId?: string; facilityId?: string; name?: string } | string = {},
): Promise<Doctor[]> {
  const normalizedFilters = typeof filters === 'string' ? { specialtyId: filters } : filters;
  const query = new URLSearchParams();
  if (normalizedFilters.specialtyId) query.set('specialty_id', normalizedFilters.specialtyId);
  if (normalizedFilters.facilityId) query.set('facility_id', normalizedFilters.facilityId);
  if (normalizedFilters.name) query.set('name', normalizedFilters.name);
  const queryString = query.toString();
  const res = await fetchWithAuth(`/doctors${queryString ? `?${queryString}` : ''}`);
  if (!res.ok) throw new Error('Failed to fetch doctors');
  const json = await res.json();
  return (json.data || []).map((doctor: Record<string, unknown>) => ({
    ...doctor,
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

export async function fetchServices(): Promise<MedicalService[]> {
  const res = await fetchWithAuth('/services');
  if (!res.ok) throw new Error('Failed to fetch services');
  const json = await res.json();
  return json.data || [];
}

export async function fetchAvailability(doctorId: string, date: string, facilityId?: string): Promise<Schedule[]> {
  const query = new URLSearchParams({ date });
  if (facilityId) query.set('facility_id', facilityId);
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

export async function createBooking(payload: CreateBookingPayload): Promise<unknown> {
  const res = await fetchWithAuth('/bookings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to create booking');
  return res.json();
}
