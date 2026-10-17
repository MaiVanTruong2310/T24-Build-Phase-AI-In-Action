import { memo, useEffect, useState } from 'react'
import { Palette, Type } from 'lucide-react'
import { applySimpleMode, readSimpleMode } from '../app/simpleMode'

/** Nút chuyển giao diện: ghi tên giao diện sẽ chuyển sang ("Đơn giản" ↔ "Mặc định") cho dễ nhận ra. */
export const SimpleModeToggle = memo(function SimpleModeToggle({ className = '' }: { className?: string }) {
  const [enabled, setEnabled] = useState(readSimpleMode)

  // Đồng bộ khi có nhiều nút trên trang (header + menu di động).
  useEffect(() => {
    const sync = () => setEnabled(document.documentElement.classList.contains('ui-simple'))
    window.addEventListener('vcare:ui-simple', sync)
    return () => window.removeEventListener('vcare:ui-simple', sync)
  }, [])

  const Icon = enabled ? Palette : Type
  const text = enabled ? 'Mặc định' : 'Đơn giản'
  const title = enabled
    ? 'Về giao diện mặc định (phông vẽ tay, đầy đủ trang trí)'
    : 'Chuyển sang giao diện đơn giản (chữ dễ đọc, ít chi tiết)'
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={() => applySimpleMode(!enabled)}
      className={`simple-toggle ${className}`}
    >
      <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2.2} aria-hidden="true" />
      <span>{text}</span>
    </button>
  )
})
