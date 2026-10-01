import { memo } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Lock,
  PhoneCall,
  Stethoscope,
  UserCheck,
} from 'lucide-react';
import { ChatbotWidget } from '../../layouts/ChatbotWidget';

const CONSULTATION_STEPS = [
  {
    step: '01',
    title: 'Khai báo triệu chứng',
    desc: 'Mô tả vị trí đau, cường độ, thời gian khởi phát và các yếu tố tăng/giảm đau.',
  },
  {
    step: '02',
    title: 'Phân tầng ATS & Chuyên khoa',
    desc: 'Hệ thống đối chiếu thang đo cấp cứu ATS và đề xuất chuyên khoa lâm sàng đích.',
  },
  {
    step: '03',
    title: 'Bác sĩ đối soát & Đặt hẹn',
    desc: 'Bác sĩ trực ban kiểm duyệt thông tin, tư vấn hướng xử trí và phân bổ lịch khám.',
  },
];

export default memo(function PatientConsultationPage() {
  return (
    <div className="space-y-6 pb-12 transition-colors duration-300">
      {/* ─── CLINICAL HERO / HEADER BANNER ─── */}
      <header className="relative overflow-hidden rounded-2xl border border-slate-200/90 dark:border-slate-800/80 bg-white/90 dark:bg-[#0B1329]/90 backdrop-blur-xl p-5 sm:p-7 shadow-sm transition-colors">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600 to-cyan-500 text-white shadow-lg shadow-blue-500/25">
              <Stethoscope className="h-6 w-6" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 dark:bg-blue-950/70 border border-blue-200/60 dark:border-cyan-500/30 px-2.5 py-0.5 text-[10.5px] font-bold uppercase tracking-wider text-blue-700 dark:text-cyan-300">
                  <Activity className="h-3 w-3" /> Medicare AI · Phân Tầng Y Khoa
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800/50 px-2 py-0.5 text-[10.5px] font-semibold text-emerald-700 dark:text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  BS. Trực ban trực tuyến
                </span>
              </div>
              <h1 className="mt-2 text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">
                Trung Tâm Tư Vấn Triệu Chứng & Điều Phối Khám
              </h1>
              <p className="mt-1.5 max-w-3xl text-xs sm:text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                Hệ thống tiếp đón y tế thông minh tích hợp AI Lâm Sàng và Bác sĩ chuyên khoa giám sát theo thời gian thực.
                Hỗ trợ sàng lọc sơ bộ, đánh giá phân tầng cấp cứu ATS và đặt lịch hẹn khám đích xác.
              </p>
            </div>
          </div>

          {/* Quick Metrics / Trust Indicators */}
          <div className="flex items-center gap-3 self-start md:self-center shrink-0">
            <div className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-[#080E1F]/70 px-3.5 py-2 text-center">
              <div className="text-base font-bold text-blue-600 dark:text-cyan-400">100%</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Bác sĩ đối soát</div>
            </div>
            <div className="rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-[#080E1F]/70 px-3.5 py-2 text-center">
              <div className="text-base font-bold text-emerald-600 dark:text-emerald-400">ATS 1-5</div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400">Chuẩn phân tầng</div>
            </div>
          </div>
        </div>
      </header>

      {/* ─── MAIN CLINICAL CONSULTATION WORKSPACE ─── */}
      <div className="grid items-start gap-6 lg:grid-cols-12">
        {/* Left Column: Embedded Medical Chatbot Terminal */}
        <div className="min-w-0 lg:col-span-8 xl:col-span-9">
          <div className="h-[750px] min-h-[640px] rounded-2xl overflow-hidden border border-slate-200/90 dark:border-slate-800/80 shadow-md transition-colors">
            <ChatbotWidget embedded />
          </div>
        </div>

        {/* Right Column: Medical Supervisory & Safety Sidebar */}
        <aside className="space-y-4 lg:col-span-4 xl:col-span-3">
          {/* Supervising Doctor Card */}
          <section className="rounded-2xl border border-blue-200/80 dark:border-blue-900/50 bg-gradient-to-br from-white via-blue-50/30 to-white dark:from-[#0B1329] dark:via-[#0E1E3B] dark:to-[#0B1329] p-5 shadow-sm transition-colors">
            <div className="flex items-center justify-between border-b border-slate-200/70 dark:border-slate-800/80 pb-3">
              <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-700 dark:text-cyan-300">
                <UserCheck className="h-4 w-4 text-blue-600 dark:text-cyan-400" />
                Bác Sĩ Giám Sát Ca Trực
              </h2>
              <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            </div>

            <div className="mt-3.5 flex items-start gap-3">
              <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-700 to-indigo-600 text-white font-bold shadow-md shadow-blue-600/25">
                <span className="text-sm">PL</span>
                <span className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 ring-2 ring-white dark:ring-[#0B1329] text-[9px] text-white">
                  ✓
                </span>
              </div>
              <div>
                <p className="font-bold text-sm text-slate-900 dark:text-white">BS CKII. Nguyễn Phương Linh</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Khoa Cấp Cứu & Điều Phối Lâm Sàng</p>
                <p className="mt-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                  15 năm kinh nghiệm · BV Chợ Rẫy / ĐHYD
                </p>
              </div>
            </div>

            <p className="mt-3 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400 bg-white/80 dark:bg-[#070D1E]/80 rounded-xl p-3 border border-slate-200/60 dark:border-slate-800">
              Bác sĩ trực ban đang giám sát song song phiên hội chẩn. Nếu phát hiện các dấu hiệu nguy kịch (ATS 1-2), bác sĩ sẽ can thiệp tức thì.
            </p>
          </section>

          {/* 3-Step Consultation Guide */}
          <section className="rounded-2xl border border-slate-200/90 dark:border-slate-800/80 bg-white dark:bg-[#0B1329] p-5 shadow-sm transition-colors">
            <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-slate-100">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Quy Trình Tiếp Đón Chuẩn
            </h2>
            <div className="mt-4 space-y-3.5">
              {CONSULTATION_STEPS.map((item) => (
                <div key={item.step} className="flex items-start gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-950/80 border border-blue-200 dark:border-cyan-500/30 text-[11px] font-bold text-blue-700 dark:text-cyan-300 font-mono">
                    {item.step}
                  </span>
                  <div>
                    <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">{item.title}</h3>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Emergency 115 Warning Card */}
          <section className="relative overflow-hidden rounded-2xl border border-red-300 dark:border-red-900/60 bg-gradient-to-br from-red-50/90 via-red-50/50 to-white dark:from-red-950/40 dark:via-[#1A0A0E] dark:to-[#0B1329] p-5 shadow-sm transition-colors">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-red-700 dark:text-red-400">
              <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0" />
              <span>Báo Động Cấp Cứu 115</span>
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-red-900/90 dark:text-red-200/90">
              Nếu bệnh nhân có biểu hiện nguy cấp: <strong>Đau thắt ngực dữ dội, khó thở cấp, lơ mơ, đột quỵ hoặc yếu liệt đột ngột</strong>, hãy gọi cấp cứu hoặc tới bệnh viện gần nhất ngay.
            </p>
            <a
              href="tel:115"
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-700 px-4 py-2.5 text-xs font-bold text-white shadow-md shadow-red-600/30 hover:from-red-500 hover:to-rose-600 transition-all active:scale-[0.99]"
            >
              <PhoneCall className="h-4 w-4" />
              <span>Gọi Cấp Cứu 115 Ngay</span>
            </a>
          </section>

          {/* Privacy & Compliance Assurance */}
          <section className="rounded-2xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-[#0B1329] p-4.5 shadow-sm transition-colors">
            <h2 className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200">
              <Lock className="h-3.5 w-3.5 text-blue-600 dark:text-cyan-400" />
              Bảo Mật Dữ Liệu Y Tế
            </h2>
            <p className="mt-1.5 text-[10.5px] leading-relaxed text-slate-500 dark:text-slate-400">
              Toàn bộ phiên tư vấn được mã hóa đầu-cuối (E2E), tuân thủ tiêu chuẩn an toàn bảo mật thông tin bệnh án điện tử (EMR) và quy định của Bộ Y Tế.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
});
