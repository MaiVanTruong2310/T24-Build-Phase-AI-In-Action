import { HeartPulse, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import './Sections.css'
import { SosButton } from '../../features/chat/SosButton'

export function CTA() {
  return (
    <section className="lp-section lp-section--last">
      <div className="lp-wrap">
        <div className="lp-cta reveal-item">
          <h2 className="lp-title">Thử trợ lý tiếp đón VCare+</h2>
          <p className="lp-cta__text">
            Mô tả triệu chứng, nhận gợi ý mức độ khẩn cấp và chuyên khoa, rồi đặt lịch khám ngay trong cuộc trò chuyện.
          </p>
          <div className="lp-cta__actions">
            <Link to="/patient" className="hero-btn hero-btn--primary">
              <HeartPulse className="h-5 w-5" strokeWidth={2.2} aria-hidden="true" />
              <span>Bắt đầu tư vấn</span>
            </Link>
            <Link to="/patient/doctors" className="hero-btn hero-btn--ghost">
              <Search className="h-5 w-5" strokeWidth={2.2} aria-hidden="true" />
              <span>Tìm bác sĩ</span>
            </Link>
          </div>
          <SosButton className="hero-sos">
            <span>Khẩn cấp?</span>
            <b>Gọi 115 ngay, đừng chờ kết quả từ ứng dụng</b>
          </SosButton>
        </div>
      </div>
    </section>
  )
}
