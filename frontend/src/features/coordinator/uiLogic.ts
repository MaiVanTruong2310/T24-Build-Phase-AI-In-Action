import type { CaseDetail, Member } from './api'
import type { Schedule } from '../appointment-booking/api'

export function acceptCaseDetail(current: CaseDetail | null, incoming: CaseDetail, selectedId: string | null): CaseDetail | null {
  if (incoming.id !== selectedId) return current
  if (current?.id === incoming.id && current.version > incoming.version) return current
  return incoming
}

export function canCaseAction(case_: CaseDetail | null, member: Member | null, action: string): boolean {
  if (!case_ || !member || case_.assigned_to !== member.user_id) return false
  const closed = ['completed', 'cancelled'].includes(case_.status)
  if (action === 'refund_request') return case_.deposits.some(d => d.status === 'verified')
  if (action === 'refund_confirm') return case_.deposits.some(d => d.status === 'refund_pending')
  if (closed) return false
  if (action === 'complete') return ['confirmed', 'emergency_transferred'].includes(case_.status)
  if (action === 'takeover') return Boolean(case_.session_id) && case_.control !== 'human'
  if (action === 'resume' || action === 'message') return Boolean(case_.session_id) && case_.control === 'human'
  if (action === 'emergency_ack') return case_.priority === 0 && !['emergency_active', 'emergency_transferred'].includes(case_.status)
  if (action === 'emergency_transfer') return case_.priority === 0 && case_.status === 'emergency_active'
  return ['contact', 'cancel', 'handover', 'follow_up'].includes(action)
}

export function shiftError(form: { start_time: string; period: string; slot_minutes: string; slot_count: string; effective_from: string }): string {
  if (!form.effective_from) return 'Chọn ngày bắt đầu có hiệu lực.'
  const [hour, minute] = form.start_time.split(':').map(Number)
  const duration = Number(form.slot_minutes), count = Number(form.slot_count)
  if (!form.start_time || !Number.isInteger(hour) || !Number.isInteger(minute)) return 'Chọn giờ bắt đầu hợp lệ.'
  if (!Number.isInteger(duration) || duration < 5 || duration > 240 || !Number.isInteger(count) || count < 1 || count > 20) return 'Kiểm tra thời lượng và số lượt khám.'
  if ((form.period === 'morning' && hour >= 12) || (form.period === 'afternoon' && hour < 12)) return 'Giờ bắt đầu không thuộc buổi đã chọn.'
  if (hour * 60 + minute + duration * count > (form.period === 'morning' ? 720 : 1440)) return 'Các lượt khám vượt quá phạm vi buổi đã chọn.'
  return ''
}

export function publicationError(from: string, through: string, today: string): string {
  if (!from || !through || from < today || through < from) return 'Chọn khoảng ngày hợp lệ, từ hôm nay trở đi.'
  const days = (Date.parse(through) - Date.parse(from)) / 86400000
  return !Number.isFinite(days) || days > 42 ? 'Khoảng công bố tối đa 42 ngày.' : ''
}

export function scheduleStats(schedules: Schedule[]) {
  return {
    total: schedules.length,
    available: schedules.filter(s => s.status === 'available').length,
    blocked: schedules.filter(s => s.status === 'blocked').length,
    capacity: schedules.filter(s => !['cancelled', 'inactive'].includes(s.status)).reduce((sum, s) => sum + s.capacity, 0),
  }
}

export function schedulesCsv(schedules: Schedule[], doctorName: string): string {
  // Prevent spreadsheet formula execution in free-text cells.
  const cell = (value: unknown) => {
    let text = String(value ?? '')
    if (/^[=+@-]/.test(text)) text = "'" + text
    return '"' + text.replaceAll('"', '""') + '"'
  }
  return [['Bác sĩ', 'Mã cơ sở', 'Bắt đầu', 'Kết thúc', 'Sức chứa', 'Trạng thái'], ...schedules.map(s => [doctorName, s.facility_id, s.starts_at, s.ends_at, s.capacity, s.status])].map(row => row.map(cell).join(',')).join('\r\n')
}
