export const MAX_APPOINTMENT_DAYS = 90

export function latestAppointmentDate(today = vietnamToday()): string {
  const date = new Date(`${today}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + MAX_APPOINTMENT_DAYS)
  return date.toISOString().slice(0, 10)
}

export function vietnamToday(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now)
  const part = (type: string) => parts.find(p => p.type === type)!.value
  return `${part('year')}-${part('month')}-${part('day')}`
}

export function appointmentDateError(value: string, today = vietnamToday()): string {
  if (!value) return 'Vui lòng nhập đầy đủ ngày khám hợp lệ.'
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Ngày khám không hợp lệ.'
  const [year, month, day] = value.split('-').map(Number)
  const parsed = new Date(`${value}T00:00:00Z`)
  if (year < 1 || Number.isNaN(parsed.getTime()) || parsed.getUTCFullYear() !== year ||
      parsed.getUTCMonth() + 1 !== month || parsed.getUTCDate() !== day) {
    return 'Ngày khám không tồn tại. Vui lòng kiểm tra ngày, tháng và năm.'
  }
  if (value < today) return 'Ngày khám không được nằm trong quá khứ.'
  if (value > latestAppointmentDate(today)) return 'Chỉ được đặt ngày khám trong 90 ngày tới.'
  return ''
}
