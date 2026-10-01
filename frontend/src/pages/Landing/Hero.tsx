import React from 'react'
import { Stethoscope, ShieldCheck, ChevronRight, Activity, Lock, HeartPulse, CheckCircle2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useSelector } from 'react-redux'
import type { RootState } from '../../app/store'

export function Hero() {
  const theme = useSelector((state: RootState) => state.layout.theme)
  const isDark = theme === 'dark'

  return (
    <section
      className="relative py-12 sm:py-20 lg:py-28 border-b border-slate-200 dark:border-slate-800/80 text-slate-900 dark:text-white overflow-hidden bg-[#F8FAFC] dark:bg-[#0B1329] transition-colors duration-300"
      style={{
        backgroundImage: isDark
          ? `linear-gradient(rgba(11, 19, 41, 0.92), rgba(11, 19, 41, 0.94)), url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&q=80&w=1920')`
          : `linear-gradient(rgba(248, 250, 252, 0.93), rgba(248, 250, 252, 0.95)), url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&q=80&w=1920')`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      {/* Calm Medical Ambient Glow Orbs (Deep Blue & Soft Cyan) */}
      <div className="medical-glow-orb orb-clinical-blue top-[-10%] left-[8%] w-[480px] h-[480px]" />
      <div className="medical-glow-orb orb-clinical-cyan top-[35%] right-[5%] w-[420px] h-[420px]" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-8 lg:gap-14 items-center relative z-10">

        {/* Left Column: Clinical Value Proposition */}
        <div className="lg:col-span-7 reveal-item">


          {/* Heading */}
          <h1 className="text-2xl sm:text-4xl lg:text-5xl font-semibold leading-tight mb-4 sm:mb-6 tracking-tight text-slate-900 dark:text-slate-100">
            Y Tế Thông Minh Với AI Agent &{' '}
            <span className="clinical-heading-gradient font-bold">
              Bác Sĩ Giám Sát 24/7
            </span>
          </h1>

          {/* Subtext */}
          <p className="text-sm sm:text-base lg:text-lg text-slate-600 dark:text-slate-300 mb-6 sm:mb-8 leading-relaxed max-w-2xl font-normal">
            Sàng lọc triệu chứng lâm sàng tức thì theo chuẩn phân loại quốc tế ATS Cấp 1–5, kết hợp cùng sự thẩm định, phê duyệt và ký số phác đồ của đội ngũ bác sĩ chuyên khoa giàu kinh nghiệm.
          </p>

          {/* 2 Rounded-xl Action Buttons (10-12px) */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4 mb-7 sm:mb-9">
            <Link
              to="/patient"
              className="btn-clinical-primary px-6 sm:px-7 py-3 sm:py-3.5 rounded-xl flex items-center justify-center gap-2.5 text-sm sm:text-base"
            >
              <HeartPulse className="w-5 h-5 text-cyan-200" />
              <span>Khám & Tư Vấn Bác Sĩ Ngay</span>
            </Link>

            <a
              href="#quy-trinh"
              className="btn-clinical-ghost px-5 sm:px-6 py-3 sm:py-3.5 rounded-xl flex items-center justify-center gap-2 text-sm sm:text-base"
            >
              <span>Xem Quy Trình Đa Tầng</span>
              <ChevronRight className="w-4 h-4 text-slate-400" />
            </a>
          </div>

          {/* Brand Guarantee Bar with VCare+ Logo */}
          <div className="flex items-center gap-4 border-t border-slate-200 dark:border-slate-800/80 pt-5 sm:pt-6">
            <img
              src="/vcare-logo.png"
              alt="VCare+ Logo"
              className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl object-contain bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-md shrink-0 p-1"
            />
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100">
                <span>VCare+ — Hệ Thống Y Tế Số Đa Tầng</span>
                <span className="font-mono text-[9px] text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded">
                  EST. 2026
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed max-w-xl">
                Sản phẩm công nghệ y tế phục vụ người Việt, kết hợp AI phân luồng lâm sàng và đội ngũ bác sĩ chuyên khoa bảo chứng y lệnh 24/7.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Clinical Live Triage Card */}
        <div className="lg:col-span-5 reveal-item">
          <div className="bg-white/95 dark:bg-slate-900/85 backdrop-blur-xl rounded-2xl border border-slate-200 dark:border-slate-700/70 p-4 sm:p-7 shadow-xl dark:shadow-2xl dark:shadow-blue-950/40 relative transition-colors duration-300">

            {/* Header of Live Triage Card */}
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4 mb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-600/20 border border-blue-200 dark:border-blue-500/30 text-blue-600 dark:text-cyan-400 flex items-center justify-center shrink-0">
                  <Stethoscope className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                    Phân Luồng Lâm Sàng Trực Tiếp
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Quy trình tiếp nhận & xác thực 3 tầng
                  </p>
                </div>
              </div>

              {/* Crimson Alert Badge for Emergency (ATS Level 2) */}
              <div className="border border-red-500/40 bg-red-100 dark:bg-red-950/70 text-red-700 dark:text-red-300 text-xs font-semibold px-2.5 py-1 rounded-lg shrink-0 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 dark:bg-red-400 animate-pulse"></span>
                <span>Triage Đỏ (Cấp cứu)</span>
              </div>
            </div>

            {/* Step Sequence Mockup */}
            <div className="space-y-3.5">
              {/* Step 1: Patient input */}
              <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/70 rounded-xl p-3.5 text-xs sm:text-sm text-slate-800 dark:text-slate-200">
                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1.5">
                  <span className="font-semibold text-blue-700 dark:text-cyan-300">1. Người bệnh mô tả:</span>
                  <span>14:32:10</span>
                </div>
                <p className="italic text-slate-600 dark:text-slate-300">
                  "Tôi bị tức thắt ngực trái hơn 1 giờ nay, cảm giác đè nặng lan lên vai và cánh tay trái, hơi vã mồ hôi..."
                </p>
              </div>

              {/* Step 2: AI Clinical Triage Assessment */}
              <div className="bg-blue-50/50 dark:bg-slate-800/70 rounded-xl p-3.5 border border-blue-200 dark:border-cyan-500/30">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 dark:text-cyan-400">
                    <Activity className="w-3.5 h-3.5" />
                    <span>2. AI Đề xuất phân luồng (ATS Cấp 2)</span>
                  </div>
                  <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-mono">Độ nhạy: 99.4%</span>
                </div>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  Dấu hiệu cảnh báo: <strong className="text-red-600 dark:text-red-400 font-semibold">Hội chứng mạch vành cấp nghi ngờ</strong>. Khuyến nghị đo điện tâm đồ ECG 12 chuyển đạo ngay và chuyển viện cấp cứu.
                </p>
              </div>

              {/* Step 3: Verified Doctor Sign-off */}
              <div className="bg-emerald-50/60 dark:bg-slate-800/80 rounded-xl p-3.5 border border-emerald-200 dark:border-emerald-500/30 flex items-start gap-3">
                <img
                  src="https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&q=80&w=150"
                  alt="Doctor"
                  className="w-10 h-10 rounded-xl object-cover border border-emerald-500/40 shrink-0 mt-0.5"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                      BS. CKII Nguyễn Minh Đức
                    </h4>
                    <span className="border border-emerald-500/40 bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 text-[10px] font-semibold px-2 py-0.5 rounded-md shrink-0">
                      Bác Sĩ Đã Ký Số
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-snug">
                    "Đã xác nhận chẩn đoán sơ bộ. Đang điều phối phòng cấp cứu Tim mạch cơ sở 1 tiếp nhận khẩn cấp."
                  </p>
                </div>
              </div>
            </div>

            {/* Bottom Card Footer */}
            <div className="flex items-center justify-between mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
              <div className="flex items-center gap-1.5 text-[11px]">
                <Lock className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
                <span>Mã hoá bảo mật HIPAA</span>
              </div>
              <Link
                to="/patient"
                className="text-blue-600 dark:text-cyan-400 hover:underline font-medium text-xs flex items-center gap-1 transition-colors"
              >
                <span>Hội chẩn thực tế</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

          </div>
        </div>

      </div>
    </section>
  )
}
