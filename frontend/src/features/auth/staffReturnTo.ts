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
