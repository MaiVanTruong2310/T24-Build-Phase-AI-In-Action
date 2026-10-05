import React from 'react'
import { Stethoscope, ShieldCheck, MapPin } from 'lucide-react'

export function Footer() {
  return (
    <footer className="bg-slate-100 light:bg-app-muted dark:bg-[#070D1E] pt-16 pb-12 border-t border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-700 light:text-app-text dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid md:grid-cols-4 gap-8 lg:gap-12 mb-12">
          
          {/* Brand Info */}
          <div>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-blue-600/10 light:bg-app-primary/10 dark:bg-blue-600/20 border border-blue-500/30 light:border-app-primary/30 text-blue-600 light:text-app-primary dark:text-cyan-400 flex items-center justify-center">
                <Stethoscope className="w-5 h-5" strokeWidth={2.2} />
              </div>
              <div className="leading-tight">
                <span className="text-lg font-bold text-slate-900 light:text-app-text dark:text-slate-100 tracking-tight">VCare+</span>
                <p className="text-[10px] text-blue-700 light:text-app-primary dark:text-cyan-400 font-mono">CLINICAL HEALTH SYSTEM</p>
              </div>
            </div>
            <p className="text-xs text-slate-600 light:text-app-secondary dark:text-slate-400 leading-relaxed mb-6">
              Hệ thống khám chữa bệnh đa tầng tích hợp Trí tuệ nhân tạo và Hội đồng Bác sĩ Chuyên khoa Trực tuyến 24/7.
            </p>
            <div className="bg-white light:bg-app-surface dark:bg-slate-900/80 border border-slate-200 light:border-app-border dark:border-slate-800/80 p-3.5 rounded-xl shadow-xs">
              <p className="text-[10px] font-semibold text-slate-500 light:text-app-secondary dark:text-slate-400 uppercase tracking-wider mb-1">
                TỔNG ĐÀI CẤP CỨU & TƯ VẤN:
              </p>
              <a href="tel:19006868" className="text-xl font-bold text-red-600 dark:text-red-400 hover:text-red-500 transition-colors">
                1900 6868
              </a>
            </div>
          </div>
          
          {/* Hanoi Facilities */}
          <div>
            <h4 className="font-semibold text-slate-900 light:text-app-text dark:text-slate-100 mb-4 flex items-center gap-2 text-sm">
              <MapPin className="w-4 h-4 text-blue-600 light:text-app-primary dark:text-cyan-400" />
              <span>Cơ Sở Hà Nội</span>
            </h4>
            <div className="space-y-2.5 text-xs text-slate-600 light:text-app-secondary dark:text-slate-400 leading-relaxed">
              <p><strong className="text-slate-800 light:text-app-text dark:text-slate-200">Trụ sở chính:</strong> Tòa nhà Y Tế Công Nghệ Cao, Số 18 Hoàng Diệu, Ba Đình, Hà Nội.</p>
              <p><strong className="text-slate-800 light:text-app-text dark:text-slate-200">Cơ sở Cầu Giấy:</strong> 124 Duy Tân, Phường Dịch Vọng Hậu, Cầu Giấy.</p>
              <p className="text-blue-600 light:text-app-primary dark:text-cyan-400 font-mono font-medium">(024) 7300 8899</p>
            </div>
          </div>
          
          {/* HCMC Facilities */}
          <div>
            <h4 className="font-semibold text-slate-900 light:text-app-text dark:text-slate-100 mb-4 flex items-center gap-2 text-sm">
              <MapPin className="w-4 h-4 text-blue-600 light:text-app-primary dark:text-cyan-400" />
              <span>Cơ Sở TP. Hồ Chí Minh</span>
            </h4>
            <div className="space-y-2.5 text-xs text-slate-600 light:text-app-secondary dark:text-slate-400 leading-relaxed">
              <p><strong className="text-slate-800 light:text-app-text dark:text-slate-200">Cơ sở 1:</strong> 45 Phổ Quang, Phường 2, Tân Bình, TP. HCM.</p>
              <p><strong className="text-slate-800 light:text-app-text dark:text-slate-200">Cơ sở 2:</strong> 88 Nguyễn Du, Phường Bến Nghé, Quận 1.</p>
              <p className="text-blue-600 light:text-app-primary dark:text-cyan-400 font-mono font-medium">(028) 7300 9988</p>
            </div>
          </div>
          
          {/* Certifications */}
          <div>
            <h4 className="font-semibold text-slate-900 light:text-app-text dark:text-slate-100 mb-4 text-sm">
              Chứng Nhận & Tiêu Chuẩn
            </h4>
            <ul className="space-y-3 text-xs text-slate-600 light:text-app-secondary dark:text-slate-400">
              <li className="flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <span>Tiêu chuẩn bảo mật Y Tế HIPAA (Mỹ)</span>
              </li>
              <li className="flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <span>An toàn thông tin ISO/IEC 27001</span>
              </li>
              <li className="flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <span>Cấp phép hoạt động bởi Bộ Y Tế</span>
              </li>
            </ul>
          </div>

        </div>
        
        <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-slate-200 light:border-app-border dark:border-slate-800/80 text-xs text-slate-500 light:text-app-secondary dark:text-slate-400 gap-4">
          <p>© 2026 VCare+ Health System. Giấy phép hoạt động khám chữa bệnh số 482/BYT-GPHĐ.</p>
          <div className="flex items-center gap-4 flex-wrap">
            <span className="hover:text-slate-800 light:hover:text-app-text dark:hover:text-slate-200 transition-colors cursor-pointer">Điều khoản sử dụng y tế</span>
            <span className="w-1 h-1 bg-slate-400 dark:bg-slate-600 rounded-full"></span>
            <span className="hover:text-slate-800 light:hover:text-app-text dark:hover:text-slate-200 transition-colors cursor-pointer">Chính sách bảo mật HIPAA</span>
            <span className="w-1 h-1 bg-slate-400 dark:bg-slate-600 rounded-full"></span>
            <span className="hover:text-slate-800 light:hover:text-app-text dark:hover:text-slate-200 transition-colors cursor-pointer">Quy trình Y lệnh Đa tầng</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
