import { Link } from 'react-router-dom'
import './HeaderBrand.css'

export function HeaderBrand({ slogan = 'Hệ Thống Y Tế Bác Sĩ Giám Sát' }: { slogan?: string }) {
  return (
    <Link to="/" className="header-brand" aria-label={`VCare+ · ${slogan} · Trang chủ`}>
      <span className="header-brand__mark">
        <img src="/vcare-logo.png" alt="" />
      </span>
      <span className="header-brand__content">
        <span className="header-brand__wordmark">VCare<span className="header-brand__plus">+</span></span>
        <span className="header-brand__slogan">{slogan}</span>
      </span>
    </Link>
  )
}
