import React from 'react'
import { Visible } from '../../features/uiVisibility/Visible'
import { ChevronRight, HeartPulse, PhoneCall, MessageCircleHeart, Activity, BadgeCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import './Hero.css'
import './Sections.css'
import { SosButton } from '../../features/chat/SosButton'

const STEPS = [
  { icon: MessageCircleHeart, title: 'Bạn mô tả triệu chứng', text: 'Nhắn bằng lời của bạn, AI hỏi từng câu ngắn để hiểu rõ tình trạng.' },
  { icon: Activity, title: 'AI sàng lọc & gợi ý', text: 'Phân loại mức độ theo thang ATS 1–5 và gợi ý chuyên khoa. Có dấu hiệu nguy hiểm thì hướng dẫn gọi 115.' },
  { icon: BadgeCheck, title: 'Điều phối viên xác nhận', text: 'Bạn chọn bác sĩ và giờ khám, nhân viên điều phối xem lại và xác nhận lịch.' },
]

export function Hero() {
  return (
    <section className="hero relative py-12 sm:py-20 lg:py-28 border-b border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-900 light:text-app-text dark:text-white overflow-hidden bg-app-page light:bg-app-page dark:bg-app-page transition-colors duration-300">
      {/* Nét nguệch ngoạc rất nhẹ làm điểm nhấn nền */}
      <svg className="hero-doodle" aria-hidden="true" viewBox="0 0 1200 600" preserveAspectRatio="none">
        <path d="M-20 520 C 120 480, 220 560, 380 520 S 640 470, 800 520 S 1060 570, 1220 510" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="7 9" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        <path className="hero-doodle__cross" d="M1090 70h14v14h14v14h-14v14h-14V98h-14V84h14z" />
        <path className="hero-doodle__cross" d="M70 130h10v10h10v10H80v10H70v-10H60v-10h10z" />
      </svg>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-10 lg:gap-14 items-center relative z-10">

        {/* Left Column: Clinical Value Proposition */}
        <div className="lg:col-span-7 reveal-item">
          <p className="hero-kicker">Trợ lý tiếp đón y tế</p>

          <h1 className="text-2xl sm:text-4xl lg:text-5xl font-semibold leading-tight mb-4 sm:mb-6 tracking-tight text-slate-900 light:text-app-text dark:text-slate-100">
            Mô tả triệu chứng, AI giúp bạn đến{' '}
            <span className="hero-circle">
              <span className="clinical-heading-gradient font-bold">đúng chuyên khoa</span>
              <svg className="hero-circle__ink" aria-hidden="true" viewBox="0 0 140 70" preserveAspectRatio="none">
                <path d="M18 40 C 8 18, 52 5, 88 7 C 124 9, 138 28, 124 47 C 108 66, 56 68, 28 56 C 10 48, 8 34, 22 22" />
              </svg>
            </span>
          </h1>

          <p className="text-sm sm:text-base lg:text-lg text-slate-600 light:text-app-secondary dark:text-slate-300 mb-7 sm:mb-8 leading-relaxed max-w-xl font-normal">
            Kể triệu chứng bằng tiếng Việt, AI sàng lọc mức độ khẩn cấp và gợi ý chuyên khoa. Điều phối viên xác nhận lịch khám cho bạn.
          </p>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 sm:gap-4 mb-7">
            <Link to="/patient" className="hero-btn hero-btn--primary">
              <HeartPulse className="w-5 h-5" strokeWidth={2.2} aria-hidden="true" />
              <span>Bắt đầu tư vấn</span>
            </Link>
            <a href="#quy-trinh" className="hero-btn hero-btn--ghost">
              <span>Xem cách hoạt động</span>
              <ChevronRight className="w-4 h-4" strokeWidth={2.4} aria-hidden="true" />
            </a>
          </div>

          <Visible id="landing.hero_emergency" inline>
            <SosButton className="hero-sos">
              <PhoneCall className="w-[18px] h-[18px] shrink-0" strokeWidth={2.2} aria-hidden="true" />
              <span>Đau ngực, khó thở, yếu liệt đột ngột?</span>
              <b>Gọi ngay 115</b>
            </SosButton>
          </Visible>
        </div>

        {/* Right Column: 3 bước nối bằng đường chỉ */}
        <div className="lg:col-span-5 reveal-item">
          <div className="hero-steps">
            <p className="hero-steps__tag">Chỉ 3 bước</p>
            <ol className="hero-steps__list">
              {STEPS.map(({ icon: Icon, title, text }, index) => (
                <li key={title} className="hero-step">
                  <span className="hero-step__num" aria-hidden="true">{index + 1}</span>
                  <div className="hero-step__card">
                    <span className="hero-step__icon" aria-hidden="true"><Icon className="h-5 w-5" strokeWidth={2.2} /></span>
                    <div>
                      <h3 className="hero-step__title">{title}</h3>
                      <p className="hero-step__text">{text}</p>
                    </div>
                    {index === STEPS.length - 1 && <span className="hero-step__stamp" aria-hidden="true">Đã duyệt</span>}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>

      </div>
    </section>
  )
}
