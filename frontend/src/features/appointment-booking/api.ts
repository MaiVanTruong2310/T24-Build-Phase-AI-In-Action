import { fetchWithAuth } from '../../app/apiClient';
import { cachedQuery } from '../../app/queryCache';

const CATALOG_TTL_MS = 60_000;

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
  booking_enabled?: boolean;
  professional_role?: string;
  honors?: string[];
  academic_ranks?: string[];
  degrees?: string[];
  languages?: string[];
  position?: string | null;
  experience_years?: number | null;
  education?: string[];
  work_history?: string[];
  awards?: string[];
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
  position?: string | null;
  is_primary?: boolean;
  active_from?: string | null;
  active_to?: string | null;
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

export async function fetchSpecialties(filters: { facilityId?: string } = {}): Promise<Specialty[]> {
  const query = new URLSearchParams({ limit: '150' });
  if (filters.facilityId) query.set('facility_id', filters.facilityId);
  const queryString = query.toString();
  return cachedQuery(`catalog:specialties:${queryString}`, CATALOG_TTL_MS, async () => {
    const res = await fetchWithAuth(`/specialties?${queryString}`);
    if (!res.ok) throw new Error('Failed to fetch specialties');
    const json = await res.json();
    return json.data || [];
  });
}

export async function fetchDoctors(
  filters: { specialtyId?: string; facilityId?: string; serviceId?: string; name?: string; bookingEnabled?: boolean; honor?: string; academicRank?: string; degree?: string; language?: string; professionalRole?: string; onDate?: string; offset?: number; limit?: number } | string = {},
): Promise<Doctor[]> {
  const normalizedFilters = typeof filters === 'string' ? { specialtyId: filters } : filters;
  const query = new URLSearchParams();
  if (normalizedFilters.specialtyId) query.set('specialty_id', normalizedFilters.specialtyId);
  if (normalizedFilters.facilityId) query.set('facility_id', normalizedFilters.facilityId);
  if (normalizedFilters.serviceId) query.set('service_id', normalizedFilters.serviceId);
  if (normalizedFilters.name) query.set('name', normalizedFilters.name);
  if (normalizedFilters.honor) query.set('honor', normalizedFilters.honor);
  if (normalizedFilters.academicRank) query.set('academic_rank', normalizedFilters.academicRank);
  if (normalizedFilters.degree) query.set('degree', normalizedFilters.degree);
  if (normalizedFilters.language) query.set('language', normalizedFilters.language);
  if (normalizedFilters.professionalRole) query.set('professional_role', normalizedFilters.professionalRole);
  if (normalizedFilters.onDate) query.set('on_date', normalizedFilters.onDate);
  if (normalizedFilters.offset) query.set('offset', String(normalizedFilters.offset));
  if (normalizedFilters.limit) query.set('limit', String(normalizedFilters.limit));
  if (normalizedFilters.bookingEnabled !== undefined) {
    query.set('booking_enabled', String(normalizedFilters.bookingEnabled));
  }
  const queryString = query.toString();
  return cachedQuery(`catalog:doctors:${queryString}`, CATALOG_TTL_MS, async () => {
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
  });
}

export async function fetchDoctorDetail(doctorId: string): Promise<Doctor> {
  return cachedQuery(`catalog:doctor:${doctorId}`, CATALOG_TTL_MS, async () => {
    const response = await fetchWithAuth(`/doctors/${doctorId}`)
    if (!response.ok) throw new Error('Không thể tải hồ sơ bác sĩ')
    const json = await response.json()
    const doctor = json.data as Record<string, unknown>
    const rawSpecialties = (doctor.specialties as Array<{ specialty_id: string; specialty?: { name: string } | null; name?: string }> | undefined) || []
    const rawServices = (doctor.services as Array<{ service_id: string; service?: { name: string } | null; name?: string }> | undefined) || []
    return {
      ...doctor,
      specialties: rawSpecialties.map(item => ({
        specialty_id: item.specialty_id,
        name: item.specialty?.name || item.name || 'Chưa cập nhật',
      })),
      services: rawServices.map(item => ({
        service_id: item.service_id,
        name: item.service?.name || item.name || 'Thông tin dịch vụ đang cập nhật',
      })),
    } as Doctor
  })
}

export async function fetchDoctorFacets(): Promise<{ honors: string[]; academic_ranks: string[]; degrees: string[]; languages: string[]; professional_roles: string[] }> {
  return cachedQuery('catalog:doctor-facets', CATALOG_TTL_MS, async () => {
    const response = await fetchWithAuth('/doctors/facets')
    if (!response.ok) throw new Error('Không thể tải bộ lọc bác sĩ')
    const json = await response.json()
    return json.data
  })
}

export async function fetchFacilities(filters: { specialtyId?: string } = {}): Promise<Facility[]> {
  const query = new URLSearchParams({ limit: '50' });
  if (filters.specialtyId) query.set('specialty_id', filters.specialtyId);
  const queryString = query.toString();
  return cachedQuery(`catalog:facilities:${queryString}`, CATALOG_TTL_MS, async () => {
    const res = await fetchWithAuth(`/facilities?${queryString}`);
    if (!res.ok) throw new Error('Failed to fetch facilities');
    const json = await res.json();
    return json.data || [];
  });
}

export interface PackageRequest {
  id: string;
  service_id: string;
  service_name?: string | null;
  service_price?: number | null;
  facility_id: string;
  facility_name?: string | null;
  preferred_date: string;
  preferred_period: 'morning' | 'afternoon';
  status: 'pending' | 'contacted' | 'confirmed' | 'cancelled' | 'completed';
  note?: string | null;
  staff_note?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_phone?: string | null;
  patient_email?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  created_at?: string;
}

export interface CreatePackageRequestPayload {
  consent_to_contact?: boolean;
  guardian_name?: string;
  guardian_phone?: string;
  service_id: string;
  facility_id: string;
  preferred_date: string;
  preferred_period: 'morning' | 'afternoon';
  note?: string;
  patient_name?: string;
  patient_phone?: string;
  patient_email?: string;
  gender?: string;
  date_of_birth?: string;
}

export async function fetchServices(filters: { specialtyId?: string; facilityId?: string; category?: string; name?: string; limit?: number } = {}): Promise<MedicalService[]> {
  const query = new URLSearchParams();
  if (filters.specialtyId) query.set('specialty_id', filters.specialtyId);
  if (filters.facilityId) query.set('facility_id', filters.facilityId);
  if (filters.category) query.set('category', filters.category);
  if (filters.name) query.set('name', filters.name);
  if (filters.limit) query.set('limit', String(filters.limit));
  const queryString = query.toString();
  return cachedQuery(`catalog:services:${queryString}`, CATALOG_TTL_MS, async () => {
    const res = await fetchWithAuth(`/services${queryString ? `?${queryString}` : ''}`);
    if (!res.ok) throw new Error('Failed to fetch services');
    const json = await res.json();
    return json.data || [];
  });
}

export async function fetchServiceCategories(): Promise<string[]> {
  return cachedQuery('catalog:service-categories', CATALOG_TTL_MS, async () => {
    const res = await fetchWithAuth('/services/categories');
    if (!res.ok) throw new Error('Failed to fetch service categories');
    const json = await res.json();
    return json.data || [];
  });
}

export async function fetchDoctorConsultationService(): Promise<MedicalService | null> {
  const services = await fetchServices({ limit: 100 });
  const found = services.find((s) => s.code === 'DV-KHAN-CHUYEN-KHOA' || s.name.includes('Khám Chuyên khoa'));
  return found || services[0] || null;
}

export async function createPackageRequest(payload: CreatePackageRequestPayload): Promise<PackageRequest> {
  const res = await fetchWithAuth('/packages/requests', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json.message || 'Không thể gửi yêu cầu đăng ký gói khám');
  }
  const json = await res.json();
  return json.data;
}

export async function fetchMyPackageRequests(): Promise<PackageRequest[]> {
  const res = await fetchWithAuth('/packages/requests/mine');
  if (!res.ok) throw new Error('Failed to fetch my package requests');
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
