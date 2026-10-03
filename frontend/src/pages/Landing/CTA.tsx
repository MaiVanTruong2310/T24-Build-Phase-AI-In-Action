import React from 'react'
import { Phone, HeartPulse } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useSelector } from 'react-redux'
import type { RootState } from '../../app/store'

export function CTA() {
  const theme = useSelector((state: RootState) => state.layout.theme)
  const isDark = theme === 'dark'

  return (
    <section
      className="py-24 relative overflow-hidden border-b border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-900 light:text-app-text dark:text-white bg-[#F8FAFC] light:bg-app-page dark:bg-[#0B1329] transition-colors duration-300"
      style={{
        backgroundImage: isDark
          ? `linear-gradient(rgba(11, 19, 41, 0.94), rgba(11, 19, 41, 0.96)), url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&q=80&w=1920')`
          : `linear-gradient(rgba(248, 250, 252, 0.94), rgba(248, 250, 252, 0.96)), url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&q=80&w=1920')`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      <div className="max-w-4xl mx-auto px-6 text-center relative z-10 reveal-item">
<h2 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-slate-900 light:text-app-text dark:text-slate-100 mb-6 leading-tight tracking-tight">
          Sẵn Sàng Trải Nghiệm Khám Bệnh Đa Tầng Bác Sĩ Giám Sát?
        </h2>

        <p className="text-slate-600 light:text-app-secondary dark:text-slate-300 text-sm sm:text-base mb-10 max-w-2xl mx-auto leading-relaxed">
          Bắt đầu sàng lọc triệu chứng lâm sàng cùng VCare+ và nhận phác đồ được phê duyệt bởi các bác sĩ chuyên khoa ngay hôm nay. Hoàn toàn bảo mật theo chuẩn y tế quốc tế.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
          <Link
            to="/patient"
            className="btn-clinical-primary w-full sm:w-auto px-8 py-3.5 rounded-xl flex items-center justify-center gap-2.5 text-sm sm:text-base"
          >
            <HeartPulse className="w-5 h-5 text-cyan-200 light:text-app-on-primary" />
            <span>Bắt Đầu Tư Vấn Miễn Phí</span>
          </Link>
          <a
            href="tel:19006868"
            className="btn-clinical-ghost w-full sm:w-auto px-8 py-3.5 rounded-xl flex items-center justify-center gap-2.5 text-sm sm:text-base text-slate-700 light:text-app-text dark:text-slate-200"
          >
            <Phone className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Tổng Đài Y Tế: 1900 6868</span>
          </a>
        </div>

        <p className="text-xs text-slate-500 light:text-app-secondary dark:text-slate-400">
          Miễn phí sàng lọc ban đầu • Hỗ trợ kết nối BHYT tại các cơ sở liên kết
        </p>
      </div>
    </section>
  )
}
