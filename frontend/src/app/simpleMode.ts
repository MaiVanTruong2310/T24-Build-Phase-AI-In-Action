// Giao diện tối giản: class `ui-simple` trên <html> (CSS ở styles/simple-mode.css), nhớ theo trình duyệt như nút sáng/tối.
const STORAGE_KEY = 'vcare_ui_simple'

export function readSimpleMode(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function applySimpleMode(enabled: boolean) {
  document.documentElement.classList.toggle('ui-simple', enabled)
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0')
  } catch {
    // Trình duyệt chặn lưu trữ: vẫn áp dụng cho phiên hiện tại.
  }
  window.dispatchEvent(new Event('vcare:ui-simple'))
}

// Áp ngay khi tải trang để không nháy giao diện vẽ tay trước khi React chạy.
if (typeof document !== 'undefined') {
  document.documentElement.classList.toggle('ui-simple', readSimpleMode())
}
