import { useState } from 'react'
import './BrandFlipCard.css'

export function BrandFlipCard({ slogan = 'Hệ Thống Y Tế Bác Sĩ Giám Sát' }: { slogan?: string }) {
  const [flipped, setFlipped] = useState(false)
  return (
    <button
      type="button"
      className="brand-flip-card"
      onClick={() => setFlipped(value => !value)}
      aria-label="Lật thẻ thương hiệu VCare+ để xem tên hoặc logo"
      aria-pressed={flipped}
      title="Rê chuột hoặc chạm để lật thẻ thương hiệu"
    >
      <span className="brand-flip-card__inner" aria-hidden="true">
        <span className="brand-flip-card__front">
          <span className="brand-flip-card__name">VCare+</span>
          <span className="brand-flip-card__slogan">{slogan}</span>
        </span>
        <span className="brand-flip-card__back">
          <img src="/vcare-logo.png" alt="" className="brand-flip-card__logo" />
        </span>
      </span>
    </button>
  )
}
