import React from 'react'
import { Activity, ShieldAlert, Stethoscope, Lock, ShieldCheck } from 'lucide-react'

export function BentoFeatures() {
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    e.currentTarget.style.setProperty('--mouse-x', `${x}px`)
    e.currentTarget.style.setProperty('--mouse-y', `${y}px`)
  }

  const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.setProperty('--mouse-x', '-500px')
    e.currentTarget.style.setProperty('--mouse-y', '-500px')
  }

  return (
    <section id="tinh-nang" className="py-24 bg-[#F8FAFC] dark:bg-[#0B1329] text-slate-900 dark:text-white relative z-10 border-b border-slate-200 dark:border-slate-800/80 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <div className="reveal-item mb-16 max-w-3xl">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-700 dark:text-cyan-300 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-3.5 py-1.5 mb-4 rounded-full">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
            <span>NỀN TẢNG Y TẾ SỐ ĐA TẦNG • CLINICAL BENTO</span>
          </div>
          <h2 className="text-3xl lg:text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 mb-4">
            Đột Phá Y Khoa Với Sự Kết Hợp Kép Giữa AI & Bác Sĩ
          </h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm lg:text-base leading-relaxed">
            Hệ sinh thái khám bệnh kết hợp hoàn hảo giữa năng lực tính toán phân luồng siêu tốc của AI y khoa và trách nhiệm chuyên môn tối cao của các bác sĩ chuyên khoa đầu ngành.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          
          {/* Card 1: Span 8 - Triage ATS Quốc Tế */}
          <div
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="clinical-bento-card md:col-span-8 p-7 lg:p-9 flex flex-col justify-between reveal-item"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="w-11 h-11 rounded-xl border border-cyan-500/30 bg-cyan-50 dark:bg-cyan-950/40 text-blue-600 dark:text-cyan-400 flex items-center justify-center">
                  <Activity className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-medium text-blue-700 dark:text-cyan-300 border border-blue-300 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-2.5 py-1 rounded-lg">
                  TIÊU CHUẨN ATS CẤP 1–5
                </span>
              </div>
              <h3 className="text-xl lg:text-2xl font-semibold text-slate-900 dark:text-slate-100 mb-3 tracking-tight">
                Phân Loại Mức Độ Khẩn Cấp Theo Thời Gian Thực
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-6 max-w-2xl">
                Tự động đánh giá nguy cơ lâm sàng ngay khi người bệnh vừa nhập triệu chứng. Hệ thống phân chia theo 5 cấp độ khẩn cấp (Hồi sức, Khẩn cấp, Cấp cứu, Bán khẩn, Không khẩn) để ưu tiên nguồn lực y tế đúng lúc.
              </p>
            </div>

            {/* Live Clinical Telemetry Preview */}
            <div className="text-xs text-slate-800 dark:text-slate-300 bg-slate-100/90 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-700/70 p-4 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-xs">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse"></span>
                <span className="text-slate-500 dark:text-slate-400">Trạng thái phân tầng:</span>
                <span className="font-semibold text-blue-700 dark:text-cyan-300">ATS Cấp 2 (Emergent)</span>
              </div>
              <div className="text-slate-500 dark:text-slate-400">
                Thời gian xử lý: <span className="text-slate-800 dark:text-slate-200 font-medium">1.2 giây</span>
              </div>
              <div className="text-slate-500 dark:text-slate-400">
                Khoa điều phối: <span className="text-blue-600 dark:text-blue-400 font-medium">Trung tâm Tim Mạch</span>
              </div>
            </div>
          </div>

          {/* Card 2: Span 4 - Red Flags Engine */}
          <div
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="clinical-bento-card md:col-span-4 p-7 lg:p-9 flex flex-col justify-between reveal-item"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="w-11 h-11 rounded-xl border border-red-500/30 bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 flex items-center justify-center">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                {/* Crimson Red Badge strictly reserved for Emergency Triage */}
                <span className="text-[11px] font-semibold text-red-700 dark:text-red-300 border border-red-500/40 bg-red-100 dark:bg-red-950/70 px-2.5 py-1 rounded-lg">
                  TẦNG CẢNH BÁO ĐỎ
                </span>
              </div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-3 tracking-tight">
                Cảnh Báo Cờ Đỏ Lâm Sàng
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Tự động rà soát các dấu hiệu sinh tồn tối khẩn (Đột quỵ FAST, Nhồi máu cơ tim ACS, Suy hô hấp) bằng thuật toán phủ định lâm sàng chuyên sâu, loại trừ 100% rủi ro bỏ sót ca nguy kịch.
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 text-xs text-red-700 dark:text-red-300 flex items-center justify-between">
              <span>Độ trễ phát hiện dấu hiệu đỏ:</span>
              <span className="font-semibold text-red-600 dark:text-red-400">&lt; 0.5 giây</span>
            </div>
          </div>

          {/* Card 3: Span 6 - Human In The Loop Doctor Supervision */}
          <div
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="clinical-bento-card md:col-span-6 p-7 lg:p-9 flex flex-col justify-between reveal-item"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="w-11 h-11 rounded-xl border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                  <Stethoscope className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-medium text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 px-2.5 py-1 rounded-lg">
                  BÁC SĨ GIÁM SÁT SONG HÀNH
                </span>
              </div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-3 tracking-tight">
                100% Khuyến Nghị Y Lệnh Có Bác Sĩ Ký Số
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Mô hình AI đóng vai trò trợ lý lâm sàng đắc lực. Mọi kết luận tư vấn, hướng dẫn xử trí và lịch chỉ định khám chuyên khoa đều được thẩm định và xác thực bởi bác sĩ có chứng chỉ hành nghề hợp pháp.
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 text-xs text-emerald-700 dark:text-emerald-300 flex items-center justify-between">
              <span>Cam kết an toàn:</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">Trách nhiệm chuyên môn 100%</span>
            </div>
          </div>

          {/* Card 4: Span 6 - HIPAA & PII Privacy First */}
          <div
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="clinical-bento-card md:col-span-6 p-7 lg:p-9 flex flex-col justify-between reveal-item"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="w-11 h-11 rounded-xl border border-blue-500/30 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                  <Lock className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-medium text-blue-700 dark:text-blue-300 border border-blue-500/30 bg-blue-50 dark:bg-blue-950/40 px-2.5 py-1 rounded-lg">
                  BẢO VỆ DỮ LIỆU NGƯỜI BỆNH
                </span>
              </div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-3 tracking-tight">
                Bảo Mật Bệnh Án Chuẩn Y Tế Quốc Tế
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Tự động khử nhận dạng thông tin cá nhân (PII de-identification) ngay tại cổng tiếp nhận. Dữ liệu bệnh sử được mã hóa theo chuẩn HIPAA và ISO 27001, tuyệt đối bảo vệ quyền riêng tư người bệnh.
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 text-xs text-blue-700 dark:text-blue-300 flex items-center justify-between">
              <span>Chuẩn an toàn thông tin:</span>
              <span className="font-semibold text-blue-600 dark:text-cyan-300">HIPAA Compliant • ISO 27001</span>
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}
