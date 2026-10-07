export const MAX_APPOINTMENT_DAYS = 90

/**
 * Returns today's date in Vietnam timezone (Asia/Ho_Chi_Minh) as 'YYYY-MM-DD'.
 */
export function vietnamToday(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now)
  const part = (type: string) => parts.find(p => p.type === type)!.value
  return `${part('year')}-${part('month')}-${part('day')}`
}

/**
 * Returns latest allowed appointment date (90 days from today) as 'YYYY-MM-DD'.
 */
export function latestAppointmentDate(today = vietnamToday()): string {
  const date = new Date(`${today}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + MAX_APPOINTMENT_DAYS)
  return date.toISOString().slice(0, 10)
}

/**
 * Formats any date string (ISO, YYYY-MM-DD, Date object) to Vietnamese standard 'dd/mm/yyyy'.
 * Example: '1995-12-25' -> '25/12/1995'
 */
export function formatDateVN(value?: string | Date | null, fallback = ''): string {
  if (!value) return fallback
  if (value instanceof Date) {
    if (isNaN(value.getTime())) return fallback
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Ho_Chi_Minh',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(value)
  }
  const str = String(value).trim()
  if (!str) return fallback
  // Already dd/mm/yyyy
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(str)) return str
  // Standard YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    const [year, month, day] = str.split('-')
    return `${day}/${month}/${year}`
  }
  // ISO string or timestamp
  const parsed = new Date(str)
  if (!isNaN(parsed.getTime())) {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Ho_Chi_Minh',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(parsed)
  }
  return str
}

/**
 * Formats datetime string to 'HH:mm dd/mm/yyyy'.
 * Example: '2026-10-06T09:30:00Z' -> '16:30 06/10/2026' (UTC+7)
 */
export function formatDateTimeVN(value?: string | Date | null, fallback = ''): string {
  if (!value) return fallback
  const parsed = value instanceof Date ? value : new Date(String(value).trim())
  if (isNaN(parsed.getTime())) return fallback
  const dateStr = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Ho_Chi_Minh',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(parsed)
  const timeStr = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(parsed)
  return `${timeStr} ${dateStr}`
}

/**
 * Converts 'dd/mm/yyyy' or 'dd-mm-yyyy' to standard ISO 'YYYY-MM-DD' for API submissions.
 */
export function parseVNToIsoDate(value: string): string {
  const str = value.trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) return str
  if (/^\d{2}[/-]\d{2}[/-]\d{4}$/.test(str)) {
    const [d, m, y] = str.split(/[/-]/)
    return `${y}-${m}-${d}`
  }
  return str
}

/**
 * Calculates current age in years based on date of birth in Vietnam timezone.
 */
export function calculateAge(birthDateStr?: string | null, today = vietnamToday()): number | null {
  if (!birthDateStr) return null
  const iso = parseVNToIsoDate(birthDateStr)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null
  const [by, bm, bd] = iso.split('-').map(Number)
  const [ty, tm, td] = today.split('-').map(Number)
  let age = ty - by
  if (tm < bm || (tm === bm && td < bd)) {
    age -= 1
  }
  return age >= 0 ? age : null
}

/**
 * Validates date of birth field.
 * Returns empty string if valid, or a descriptive error message in Vietnamese.
 */
export function birthDateError(value: string, today = vietnamToday()): string {
  if (!value || !value.trim()) return 'Vui lòng nhập ngày sinh.'
  const iso = parseVNToIsoDate(value)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    return 'Ngày sinh không đúng định dạng ngày/tháng/năm (dd/mm/yyyy).'
  }
  const [year, month, day] = iso.split('-').map(Number)
  const parsed = new Date(`${iso}T00:00:00Z`)
  if (
    Number.isNaN(parsed.getTime()) ||
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() + 1 !== month ||
    parsed.getUTCDate() !== day
  ) {
    return 'Ngày sinh không hợp lệ hoặc không tồn tại trên lịch.'
  }
  if (iso > today) {
    return 'Ngày sinh không được nằm trong tương lai (không vượt quá ngày hôm nay).'
  }
  const age = calculateAge(iso, today)
  if (age !== null && age > 150) {
    return 'Ngày sinh không hợp lệ (tuổi không được vượt quá 150 tuổi).'
  }
  return ''
}

/**
 * Validates Email / Gmail format strictly according to user requirements.
 */
export function emailError(value: string): string {
  const trimmed = (value || '').trim()
  if (!trimmed) return 'Vui lòng nhập email / Gmail để xác thực tài khoản.'
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  if (!emailRegex.test(trimmed)) {
    return 'Email không đúng định dạng (VD: taikhoan@gmail.com).'
  }
  if (trimmed.toLowerCase().endsWith('@gmail.com')) {
    const local = trimmed.split('@')[0]
    if (local.length < 6 || local.length > 30) {
      return 'Địa chỉ Gmail không đúng định dạng (tên tài khoản từ 6 đến 30 ký tự).'
    }
    if (!/^[a-zA-Z0-9.]+$/.test(local) || local.startsWith('.') || local.endsWith('.') || local.includes('..')) {
      return 'Tên Gmail chỉ chứa chữ cái, số và dấu chấm (không ở đầu/cuối hoặc liên tiếp).'
    }
  }
  return ''
}

/**
 * Validates Vietnamese Citizen ID (CCCD - 12 digits).
 */
export function citizenIdError(value: string): string {
  const trimmed = (value || '').trim()
  if (!trimmed) return ''
  if (!/^\d{12}$/.test(trimmed)) {
    return 'Số CCCD phải gồm chính xác 12 chữ số.'
  }
  return ''
}

/**
 * Validates Health Insurance Code (BHYT - 10 to 15 alphanumeric characters).
 */
export function healthInsuranceCodeError(value: string): string {
  const trimmed = (value || '').trim()
  if (!trimmed) return ''
  if (!/^[a-zA-Z0-9]{10,15}$/.test(trimmed)) {
    return 'Mã số BHYT phải gồm từ 10 đến 15 ký tự chữ và số.'
  }
  return ''
}

/**
 * Validates appointment booking date.
 * Must be a real calendar date, not in the past, and within 90 days.
 */
export function appointmentDateError(value: string, today = vietnamToday()): string {
  if (!value || !value.trim()) return 'Vui lòng chọn ngày khám mong muốn.'
  const iso = parseVNToIsoDate(value)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    return 'Ngày khám không đúng định dạng ngày/tháng/năm (dd/mm/yyyy).'
  }
  const [year, month, day] = iso.split('-').map(Number)
  const parsed = new Date(`${iso}T00:00:00Z`)
  if (
    year < 1 ||
    Number.isNaN(parsed.getTime()) ||
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() + 1 !== month ||
    parsed.getUTCDate() !== day
  ) {
    return 'Ngày khám không tồn tại. Vui lòng kiểm tra lại ngày, tháng và năm.'
  }
  if (iso < today) {
    return 'Ngày khám không được nằm trong quá khứ.'
  }
  if (iso > latestAppointmentDate(today)) {
    return 'Chỉ được đặt ngày khám trong vòng 90 ngày tới.'
  }
  return ''
}
