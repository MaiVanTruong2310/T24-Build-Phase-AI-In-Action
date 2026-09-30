import React from 'react'
import { MessageSquare, AlertTriangle, ShieldCheck, FileText, CheckCircle2 } from 'lucide-react'

export function Process() {
  const steps = [
    {
      num: '01',
      icon: <MessageSquare className="w-5 h-5 text-blue-600 dark:text-cyan-400" />,
      title: 'Tiếp Nhận Triệu Chứng Tự Nhiên',
      desc: 'Người bệnh chia sẻ tình trạng bằng lời nói hoặc tin nhắn. Hệ thống tự động trích xuất các triệu chứng dương tính/âm tính và tiền sử bệnh lý.',
      meta: 'Phản hồi trong 1.5 giây',
      badgeColor: 'border-blue-300 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 text-blue-700 dark:text-cyan-300'
    },
    {
      num: '02',
      icon: <AlertTriangle className="w-5 h-5 text-amber-500 dark:text-amber-400" />,
      title: 'AI Triage Phân Tầng Lâm Sàng',
      desc: (
        <>
          Đánh giá mức độ khẩn cấp: <span className="text-red-600 dark:text-red-400 font-semibold">Triage Đỏ (Cấp cứu)</span>, <span className="text-amber-600 dark:text-amber-400 font-semibold">Vàng (Ưu tiên)</span>, <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Xanh (Theo dõi)</span> theo chuẩn ATS/ESI.
        </>
      ),
      meta: 'Sàng lọc cờ đỏ khẩn cấp',
      badgeColor: 'border-amber-300 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300'
    },
    {
      num: '03',
      icon: <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />,
      title: 'Bác Sĩ Giám Sát Phê Duyệt',
      desc: 'Bác sĩ chuyên khoa trực ban rà soát toàn bộ khuyến nghị của AI, điều chỉnh phác đồ phù hợp và ký số xác thực y khoa trước khi hoàn tất.',
      meta: '100% Bác sĩ duyệt ký',
      badgeColor: 'border-emerald-300 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300'
    },
    {
      num: '04',
      icon: <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />,
      title: 'Toa Thuốc & Lịch Khám Ưu Tiên',
      desc: 'Cấp mã toa thuốc điện tử và ưu tiên chuyển tiếp người bệnh tới phòng khám chuyên khoa trực tiếp mà không cần bốc số chờ đợi lâu.',
      meta: 'Liên thông bệnh viện số',
      badgeColor: 'border-blue-300 dark:border-blue-500/30 bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300'
    }
  ]

  return (
    <section id="quy-trinh" className="bg-slate-50 dark:bg-[#070D1E] py-24 border-b border-slate-200 dark:border-slate-800/80 text-slate-900 dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16 reveal-item">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-700 dark:text-cyan-300 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-3.5 py-1.5 mb-4 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
            <span>QUY TRÌNH TIÊU CHUẨN Y KHOA KHÉP KÍN</span>
          </div>
          <h2 className="text-3xl lg:text-4xl font-semibold text-slate-900 dark:text-slate-100 mb-4 tracking-tight">
            4 Bước Khám Chữa Bệnh Thông Minh & An Toàn Tuyệt Đối
          </h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm lg:text-base max-w-2xl mx-auto leading-relaxed">
            Mô hình kết hợp hoàn hảo giữa tốc độ phân loại ban đầu của AI và kinh nghiệm vững vàng, trách nhiệm chuyên môn của Bác sĩ chuyên khoa.
          </p>
        </div>
        
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((s, i) => (
            <div
              key={i}
              className="bg-white dark:bg-slate-900/60 rounded-2xl p-6 border border-slate-200 dark:border-slate-800/80 shadow-xs dark:shadow-none transition-all duration-300 hover:border-cyan-500/40 hover:-translate-y-1 reveal-item flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-5">
                  <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-lg border ${s.badgeColor}`}>
                    BƯỚC {s.num}
                  </span>
                  <div className="w-9 h-9 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 flex items-center justify-center">
                    {s.icon}
                  </div>
                </div>
                <h3 className="font-semibold text-base text-slate-900 dark:text-slate-100 mb-2.5">
                  {s.title}
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mb-6 leading-relaxed">
                  {s.desc}
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400 pt-4 border-t border-slate-100 dark:border-slate-800/60">
                <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span>{s.meta}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
