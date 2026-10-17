import { fetchWithAuth } from '../../app/apiClient';
import type { BookingListStatus, BookingStatus } from '../../features/appointment-booking/api';

export type ApprovalStatus = Extract<BookingStatus, 'pending_approval' | 'confirmed' | 'rejected'>;

export interface StaffBookingAITriage {
  symptoms?: string | null;
  clinical_facts?: Record<string, unknown> | null;
  collected_details?: string[] | null;
  ats_level?: number | null;
  urgency_tier?: string | null;
  is_emergency?: boolean | null;
  emergency_warning?: string | null;
  max_booking_days?: number | null;
  suggested_department_name?: string | null;
  suggested_department_code?: string | null;
  candidate_specialties?: Array<Record<string, unknown>> | null;
  care_pipeline?: {
    is_multi_specialty?: boolean;
    primary_department?: string;
    secondary_departments?: string[];
    pipeline_steps?: Array<{ step_number?: number; department_name?: string; target_symptoms?: string[]; clinical_rationale?: string }>;
    formatted_guidance?: string;
  } | null;
  captured_at?: string | null;
  source?: string | null;
}

export interface PendingBooking {
  id: string;
  booking_code: string;
  patient_name: string;
  patient_age: number | null;
  patient_gender: 'male' | 'female' | 'other' | 'unspecified' | null;
  patient_phone: string | null;
  patient_email: string | null;
  patient_cccd: string | null;
  patient_bhyt: string | null;
  doctor_name: string;
  doctor_title: string | null;
  doctor_avatar: string | null;
  specialty_name: string;
  service_name: string;
  facility_name: string;
  facility_address: string | null;
  room: string | null;
  starts_at: string;
  ends_at: string;
  encounter_type: 'in_person' | 'telehealth';
  reason: string;
  patient_note: string | null;
  status: BookingStatus;
  staff_note: string | null;
  reviewed_at: string | null;
  ai_triage: StaffBookingAITriage | null;
  requested_at: string;
  created_at: string;
}

export interface BookingServiceOption {
  id: string;
  name: string;
}

export interface StaffBookingPage {
  items: PendingBooking[];
  total: number;
  offset: number;
  limit: number;
  status_counts: { all: number; pending_approval: number; confirmed: number; rejected: number };
}

interface StaffBookingResponse {
  id: string;
  user_id: string;
  schedule_id: string | null;
  appointment_schedule_id?: string | null;
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
  staff_note: string | null;
  reviewed_at: string | null;
  patient_name: string | null;
  patient_email: string | null;
  patient_phone: string | null;
  patient_date_of_birth: string | null;
  patient_gender: PendingBooking['patient_gender'];
  patient_citizen_id: string | null;
  patient_health_insurance_code: string | null;
  doctor_name: string | null;
  doctor_title: string | null;
  doctor_avatar: string | null;
  specialty_name: string | null;
  service_name: string | null;
  facility_name: string | null;
  facility_address: string | null;
  room: string | null;
  ai_triage: StaffBookingAITriage | null;
  created_at: string;
}

function calculateAge(dateOfBirth: string | null): number | null {
  if (!dateOfBirth) return null;
  const birthDate = new Date(dateOfBirth);
  if (Number.isNaN(birthDate.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const month = today.getMonth() - birthDate.getMonth();
  if (month < 0 || (month === 0 && today.getDate() < birthDate.getDate())) age -= 1;
  return age;
}

function toPendingBooking(value: StaffBookingResponse): PendingBooking {
  return {
    id: value.id,
    booking_code: `MED-${value.id.slice(0, 8).toUpperCase()}`,
    patient_name: value.patient_name || 'Chưa cập nhật',
    patient_age: calculateAge(value.patient_date_of_birth),
    patient_gender: value.patient_gender,
    patient_phone: value.patient_phone,
    patient_email: value.patient_email,
    patient_cccd: value.patient_citizen_id,
    patient_bhyt: value.patient_health_insurance_code,
    doctor_name: value.doctor_name || 'Chưa phân công',
    doctor_title: value.doctor_title,
    doctor_avatar: value.doctor_avatar,
    specialty_name: value.specialty_name || 'Chưa cập nhật',
    service_name: value.service_name ?? 'Khám riêng',
    facility_name: value.facility_name || 'Chưa cập nhật',
    facility_address: value.facility_address,
    room: value.room,
    starts_at: value.starts_at,
    ends_at: value.ends_at,
    encounter_type: value.encounter_type,
    reason: value.reason,
    patient_note: value.patient_note,
    status: value.status,
    staff_note: value.staff_note,
    reviewed_at: value.reviewed_at,
    ai_triage: value.ai_triage ?? null,
    requested_at: value.created_at,
    created_at: value.created_at,
  };
}

async function readStaffResponse(response: Response): Promise<StaffBookingResponse> {
  const json = await response.json();
  if (!response.ok) throw new Error(json.message || 'Không thể cập nhật lịch hẹn');
  return json.data as StaffBookingResponse;
}

export async function fetchPendingBookings(
  filters: { status?: BookingListStatus; date?: string; q?: string; serviceId?: string; offset?: number; limit?: number; scheduledOnly?: boolean } = {},
): Promise<StaffBookingPage> {
  const query = new URLSearchParams({ offset: String(filters.offset ?? 0), limit: String(filters.limit ?? 20) });
  if (filters?.status) query.set('status', filters.status);
  if (filters?.date) query.set('date', filters.date);
  if (filters.q) query.set('q', filters.q);
  if (filters.serviceId) query.set('service_id', filters.serviceId);
  if (filters.scheduledOnly) query.set('scheduled_only', 'true');

  const res = await fetchWithAuth(`/staff/bookings?${query.toString()}`);
  const json = await res.json();
  if (!res.ok) throw new Error(json.message || 'Không thể tải danh sách lịch hẹn');
  const page = json.data as Omit<StaffBookingPage, 'items'> & { items?: StaffBookingResponse[] };
  return { ...page, items: (page.items || []).map(toPendingBooking) };
}

export async function fetchBookingServiceOptions(): Promise<BookingServiceOption[]> {
  const res = await fetchWithAuth('/api/v1/staff/services');
  const json = await res.json();
  if (!res.ok) throw new Error(json.message || 'Không thể tải danh sách gói khám');
  return ((json.data || []) as BookingServiceOption[]).map(({ id, name }) => ({ id, name }));
}

export async function fetchStaffBooking(id: string): Promise<PendingBooking> {
  const response = await fetchWithAuth(`/staff/bookings/${id}`);
  const value = await readStaffResponse(response);
  return toPendingBooking(value);
}

export async function updateBookingStatus(
  id: string,
  status: Extract<ApprovalStatus, 'confirmed' | 'rejected'>,
  note?: string,
): Promise<PendingBooking> {
  const response = await fetchWithAuth(`/staff/bookings/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, note: note?.trim() || undefined }),
  });
  const value = await readStaffResponse(response);
  return toPendingBooking(value);
}

export async function approveBooking(id: string, note?: string): Promise<PendingBooking> {
  return updateBookingStatus(id, 'confirmed', note);
}

export async function rejectBooking(id: string, reason: string): Promise<PendingBooking> {
  return updateBookingStatus(id, 'rejected', reason);
}

export async function cancelStaffAppointment(id: string, reason: string): Promise<PendingBooking> {
  const response = await fetchWithAuth(`/staff/bookings/${id}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason.trim() }),
  });
  return toPendingBooking(await readStaffResponse(response));
}
