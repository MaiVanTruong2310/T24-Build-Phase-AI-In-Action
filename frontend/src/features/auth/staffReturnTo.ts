const STAFF_DEFAULT = '/staff/coordination'

export function staffReturnTo(value: string | null): string {
  if (!value?.startsWith('/') || value.startsWith('//') || value.includes('\\')) return STAFF_DEFAULT
  try {
    const target = new URL(value, window.location.origin)
    return target.origin === window.location.origin && /^\/staff(?:\/|$)/.test(target.pathname)
      ? `${target.pathname}${target.search}${target.hash}`
      : STAFF_DEFAULT
  } catch {
    return STAFF_DEFAULT
  }
}

// Trang bệnh nhân nhân viên vẫn được xem: hồ sơ bác sĩ (nút "Xem hồ sơ" ở màn quản lý bác sĩ).
const STAFF_VISIBLE_PATIENT_PAGES = /^\/patient\/doctors(?:\/|$)/

/** Nhân viên mở trang chủ/trang bệnh nhân (kể cả khi mở lại tab với phiên cũ) được đưa về bàn điều phối. */
export function staffRedirectFor(role: string | undefined, pathname: string): string | null {
  if (role !== 'staff' || STAFF_VISIBLE_PATIENT_PAGES.test(pathname)) return null
  return STAFF_DEFAULT
}
