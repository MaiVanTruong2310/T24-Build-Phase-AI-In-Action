import { fetchWithAuth, resolveWebSocketUrl } from '../../app/apiClient'
import { readAccessToken } from '../auth/session'

export interface Case {
  id: string; source: string; session_id: string | null; patient_id: string | null
  patient: Record<string, string | null>; ai_snapshot: Record<string, unknown>; plan: Record<string, string | boolean>
  facility_id: string | null; assigned_to: string | null; status: string; priority: number; control: string; version: number
  due_at: string | null; follow_up_at: string | null; booking_id: string | null; created_at: string
}
export interface CaseDetail extends Case {
  messages: { id: string; sender: string; actor_id: string | null; body: string; created_at: string }[]
  events: { id: string; actor_id: string | null; action: string; note: string; created_at: string }[]
  deposits: { id: string; amount: number; currency: string; status: string; expires_at: string; instructions: string; refund_policy: string; transaction_reference: string | null }[]
}
export interface Member { user_id: string; name: string; email?: string; is_admin: boolean; on_duty: boolean; clinical_qualification: string; facility_ids: string[] }
export interface Policy { hold_minutes: number; response_minutes: number; emergency_response_minutes: number; payment_instructions: string; refund_policy: string }
export interface Catalog {
  doctors: { id: string; name: string }[]; specialties: { id: string; name: string }[]
  services: { id: string; name: string }[]; facilities: { id: string; name: string }[]
  schedules: { id: string; starts_at: string; ends_at: string; facility_id: string; capacity: number }[]
}
export interface Dashboard { counts: Record<string, number>; overdue: number; emergency: number; followups: Case[] }

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetchWithAuth('/staff/workbench' + path, { method, ...(body !== undefined ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) })
  const data = await response.json()
  if (!response.ok) throw new Error(data.message || data.detail || 'Không thể xử lý yêu cầu.')
  return data.data as T
}

export function resolveStaffWorkbenchWebSocketUrl(ticket?: string | null): string {
  const token = ticket ?? readAccessToken()
  const query = token ? `?${new URLSearchParams({ token }).toString()}` : ''
  return resolveWebSocketUrl(`/staff/chat-takeover/ws/staff${query}`)
}

export const statuses: Record<string, string> = {
  new: 'Chưa nhận', observing: 'AI đang hỗ trợ', contacting: 'Đang liên hệ', waiting_patient: 'Chờ bệnh nhân', planned: 'Đã thống nhất phương án', waiting_deposit: 'Chờ cọc', deposit_verified: 'Đã xác minh cọc', deposit_expired: 'Cọc hết hạn', deposit_late: 'Cọc đến muộn', confirmed: 'Đã chốt lịch', completed: 'Hoàn tất', cancelled: 'Đã hủy', emergency_active: 'Đang xử lý khẩn', emergency_transferred: 'Đã bàn giao cấp cứu', contacted: 'Đã liên hệ'
}
export const priorities = ['Cấp cứu', 'Cần hỗ trợ sớm', 'Ưu tiên', 'Thông thường']
export const dateTime = (value?: string | null) => value ? new Date(value).toLocaleString('vi-VN') : '—'

export function canAdminister(member: Member | null): boolean {
  return Boolean(member?.is_admin && !member.facility_ids.length)
}
