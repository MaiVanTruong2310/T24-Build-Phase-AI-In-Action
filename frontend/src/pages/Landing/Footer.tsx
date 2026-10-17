import { Link } from 'react-router-dom'
import { Phone } from 'lucide-react'
import './Sections.css'
import { SosButton } from '../../features/chat/SosButton'

const LINKS = [
  { label: 'Trang chủ', to: '/' },
  { label: 'Tư vấn AI', to: '/patient' },
  { label: 'Tìm bác sĩ', to: '/patient/doctors' },
  { label: 'Đặt lịch khám', to: '/patient/appointments' },
  { label: 'Chuyên khoa', to: '/patient/departments' },
]

export function Footer() {
  return (
    <footer className="lp-footer">
      <div className="lp-wrap">
        <div className="lp-footer__grid">
          <div>
            <p className="lp-footer__brand">VCare<span>+</span></p>
            <p className="lp-footer__desc">Trợ lý tiếp đón y tế: sàng lọc mức độ khẩn cấp, gợi ý chuyên khoa và hỗ trợ đặt lịch khám, có điều phối viên xác nhận.</p>
          </div>

          <nav aria-label="Liên kết nhanh">
            <p className="lp-footer__head">Liên kết</p>
            <ul>
              {LINKS.map((item) => (
                <li key={item.to}><Link to={item.to}>{item.label}</Link></li>
              ))}
            </ul>
          </nav>

          <div>
            <p className="lp-footer__head">Tài khoản</p>
            <ul>
              <li><Link to="/login">Đăng nhập</Link></li>
              <li><Link to="/register">Đăng ký</Link></li>
            </ul>
          </div>

          <SosButton className="hero-sos lp-footer__sos">
            <Phone className="h-[18px] w-[18px] shrink-0" strokeWidth={2.2} aria-hidden="true" />
            <span>Cấp cứu</span>
            <b>115</b>
          </SosButton>
        </div>

        <div className="lp-footer__bottom">
          <p>© 2026 VCare+ · Bản demo của dự án P-124, AI20K Cohort 4.</p>
          <p>VCare+ không chẩn đoán, không kê đơn và không thay thế bác sĩ. Thông tin bác sĩ tham khảo từ danh mục công khai của Vinmec.</p>
        </div>
      </div>
    </footer>
  )
}
