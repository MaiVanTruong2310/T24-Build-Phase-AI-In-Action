import { fetchWithAuth } from '../../app/apiClient'

export interface SessionSummary {
  id: string
  date: string
  period: 'morning' | 'afternoon'
  remaining: number
  capacity: number
  facility_id: string
}

export interface ConsultationRequest {
  id: string
  patient_id: string
  patient_name: string | null
  patient_phone: string | null
  patient_email: string | null
  doctor_name?: string
  facility_name?: string
  service_name?: string
  specialty_name?: string
  session_id: string
  doctor_id: string
  facility_id: string
  date: string
  period: 'morning' | 'afternoon'
  service_id: string
  specialty_id: string
  reason: string
  patient_note: string | null
  status: 'pending' | 'confirmed' | 'rejected' | 'cancelled'
  staff_note: string | null
  slot_id: string | null
  starts_at: string | null
  ends_at: string | null
  created_at: string | null
  slots?: Array<{ id: string; starts_at: string; ends_at: string; available: boolean }>
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithAuth(path, init)
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.message || payload.detail || 'Không thể xử lý yêu cầu.')
  return payload.data as T
}

const json = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const fetchSessions = (doctorId: string, date: string, facilityId: string) =>
  api<SessionSummary[]>(`/coordination/sessions?${new URLSearchParams({ doctor_id: doctorId, date, facility_id: facilityId })}`)
export const createConsultationRequest = (body: Record<string, unknown>) =>
  api<ConsultationRequest>('/coordination/requests', json(body))
export const fetchMyRequests = () => api<ConsultationRequest[]>('/coordination/requests/mine')
export const cancelConsultationRequest = (requestId: string) =>
  api<{ id: string }>(`/coordination/requests/${requestId}/cancel`, json({}))
export const fetchCoordinatorRequests = () => api<ConsultationRequest[]>('/staff/coordination/requests')
export const fetchWeeklyShifts = () => api<Array<{ id: string; doctor_id: string; facility_id: string; weekday: number; period: string; start_time: string; slot_minutes: number; slot_count: number; active: boolean }>>('/staff/coordination/rules')
export const createWeeklyShift = (body: Record<string, string | number>) => api<{ id: string }>('/staff/coordination/rules', json(body))
export const createStandardWeek = (doctor_id: string, facility_id: string, effective_from: string) =>
  api<{ rules_created: number }>('/staff/coordination/rules/standard-week', json({ doctor_id, facility_id, effective_from }))
export const publishSessions = (from_date: string, through_date: string) =>
  api<{ sessions_created: number }>('/staff/coordination/publish', json({ from_date, through_date }))
export const assignConsultation = (requestId: string, slotId: string, note: string) =>
  api<{ id: string; booking_id: string }>(`/staff/coordination/requests/${requestId}/assign`, json({ slot_id: slotId, note }))
export const rejectConsultation = (requestId: string, note: string) =>
  api<{ id: string }>(`/staff/coordination/requests/${requestId}/reject`, json({ note }))
