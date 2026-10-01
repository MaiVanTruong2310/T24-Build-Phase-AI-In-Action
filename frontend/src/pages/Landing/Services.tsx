import React from 'react'
import { Stethoscope, CalendarCheck, HeartPulse, FileText, CheckCircle2, ShieldCheck } from 'lucide-react'

export function Services() {
  const services = [
    {
      icon: Stethoscope,
      title: 'AI Sàng Lọc Triệu Chứng Chuyên Sâu',
      desc: 'Phân tích ngữ nghĩa ngôn ngữ tự nhiên tiếng Việt y khoa, đối chiếu với ngân hàng phác đồ lâm sàng thế giới để dự báo nguy cơ tức thì.',
      highlights: ['Hiểu ngữ cảnh tiếng Việt tự nhiên', 'Nhận diện tổ hợp bệnh lý đa cơ quan'],
      iconColor: 'text-blue-600 dark:text-cyan-400',
      boxColor: 'border-blue-200 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40'
    },
    {
      icon: CalendarCheck,
      title: 'Điều Phối Khám Đúng Chuyên Khoa',
      desc: 'Tự động sắp xếp thứ tự ưu tiên dựa trên mức độ nghiêm trọng và kết nối trực tiếp đến bác sĩ đúng chuyên khoa phù hợp.',
      highlights: ['Tiết kiệm hơn 85% thời gian chờ', 'Đặt khám đúng chuyên gia đầu ngành'],
      iconColor: 'text-sky-600 dark:text-blue-400',
      boxColor: 'border-sky-200 dark:border-blue-500/30 bg-sky-50 dark:bg-blue-950/40'
    },
    {
      icon: HeartPulse,
      title: 'Hỗ Trợ Tiếp Nhận Cấp Cứu Trực Tuyến',
      desc: 'Khi phát hiện dấu hiệu đe dọa tính mạng (nhồi máu cơ tim, đột quỵ, khó thở cấp), hệ thống lập tức mở kênh cấp cứu 115 và chỉ dẫn sơ cứu.',
      highlights: ['Kích hoạt đường dây khẩn cấp 1-chạm', 'Hướng dẫn xử trí tại chỗ an toàn'],
      iconColor: 'text-red-600 dark:text-red-400',
      boxColor: 'border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-950/40'
    },
    {
      icon: FileText,
      title: 'Bệnh Án Điện Tử Chuẩn HL7 / FHIR',
      desc: 'Lưu trữ trọn đời tiền sử bệnh, đơn thuốc và kết quả xét nghiệm theo chuẩn quốc tế HIPAA, bảo mật đa tầng, dễ dàng liên thông bệnh viện.',
      highlights: ['Tra cứu hồ sơ sức khỏe 24/7', 'Mã hóa cấp độ cao AES-256'],
      iconColor: 'text-emerald-600 dark:text-emerald-400',
      boxColor: 'border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40'
    }
  ]

  return (
    <section className="py-24 bg-white dark:bg-[#0B1329] border-b border-slate-200 dark:border-slate-800/80 text-slate-900 dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16 reveal-item">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-700 dark:text-cyan-300 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-3.5 py-1.5 mb-4 rounded-full">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
            <span>HỆ SINH THÁI Y KHOA TOÀN DIỆN</span>
          </div>
          <h2 className="text-3xl lg:text-4xl font-semibold text-slate-900 dark:text-slate-100 mb-4 tracking-tight">
            Giải Pháp Chăm Sóc Sức Khỏe Thông Minh Đạt Chuẩn
          </h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm lg:text-base max-w-2xl mx-auto leading-relaxed">
            Ứng dụng các chuẩn mực lâm sàng tiên tiến nhất nhằm đem lại trải nghiệm chăm sóc y tế chuẩn xác, ân cần và an tâm tuyệt đối cho người bệnh.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {services.map((s, i) => {
            const Icon = s.icon
            return (
              <div
                key={i}
                className="bg-slate-50 dark:bg-slate-900/60 rounded-2xl p-6 border border-slate-200 dark:border-slate-800/80 hover:border-cyan-500/40 hover:-translate-y-1 transition-all duration-300 shadow-xs dark:shadow-none reveal-item flex flex-col justify-between"
              >
                <div>
                  <div className={`w-12 h-12 rounded-xl border flex items-center justify-center mb-6 ${s.boxColor} ${s.iconColor}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <h3 className="font-semibold text-base text-slate-900 dark:text-slate-100 mb-2.5">
                    {s.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mb-6 leading-relaxed">
                    {s.desc}
                  </p>
                </div>

                <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-300 border-t border-slate-200 dark:border-slate-800/60 pt-4">
                  {s.highlights.map((h, j) => (
                    <li key={j} className="flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400 shrink-0" />
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
