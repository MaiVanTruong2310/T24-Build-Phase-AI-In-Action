import React from 'react'
import { CheckCircle2, XCircle, AlertTriangle, FileText, ShieldCheck } from 'lucide-react'

export function Comparison() {
  const comparisonItems = [
    {
      title: 'Thẩm định lâm sàng chuyên môn',
      icon: CheckCircle2,
      rawAI: {
        status: 'Không có bác sĩ thẩm định',
        desc: 'Câu trả lời sinh ra từ xác suất thống kê văn bản, không chịu trách nhiệm y khoa.'
      },
      medicareAI: {
        status: '100% Bác sĩ chuyên khoa ký duyệt',
        desc: 'Bác sĩ trực tiếp rà soát, xác thực phác đồ và chịu trách nhiệm chuyên môn.'
      }
    },
    {
      title: 'Kiểm soát ảo giác y khoa (Hallucination)',
      icon: AlertTriangle,
      rawAI: {
        status: 'Rủi ro sai lệch cao (15% - 25%)',
        desc: 'Có thể bịa đặt phác đồ hoặc liều thuốc nguy hiểm tới tính mạng.'
      },
      medicareAI: {
        status: 'Kiểm soát 0% sai lệch lâm sàng',
        desc: 'Hàng rào an toàn kép (Safety Gates) loại trừ triệt để hiện tượng bịa đặt thông tin.'
      }
    },
    {
      title: 'Xử trí dấu hiệu cấp cứu tối khẩn',
      icon: AlertTriangle,
      rawAI: {
        status: 'Chỉ đưa lời khuyên chung chung',
        desc: 'Không phân loại được cấp độ khẩn cấp, không kết nối cấp cứu thực địa.'
      },
      medicareAI: {
        status: 'Kích hoạt Triage Đỏ & Kênh 115',
        desc: 'Điều phối khẩn cấp phòng cấp cứu và chỉ dẫn sơ cứu tại chỗ theo từng giây.'
      }
    },
    {
      title: 'Tính pháp lý toa thuốc & bệnh án',
      icon: FileText,
      rawAI: {
        status: 'Hoàn toàn không có giá trị pháp lý',
        desc: 'Không thể dùng để mua thuốc tại nhà thuốc hay hưởng quyền lợi BHYT.'
      },
      medicareAI: {
        status: 'Toa thuốc điện tử có mã định danh',
        desc: 'Liên thông hệ thống Đơn thuốc Quốc gia & đồng bộ hồ sơ bệnh án số.'
      }
    }
  ]

  return (
    <section className="bg-white dark:bg-[#0B1329] py-16 sm:py-24 border-b border-slate-200 dark:border-slate-800/80 text-slate-900 dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-12 sm:mb-16 reveal-item">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-700 dark:text-cyan-300 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-3.5 py-1.5 mb-4 rounded-full">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
            <span>ĐỐI CHIẾU TIÊU CHUẨN AN TOÀN Y KHOA</span>
          </div>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-semibold text-slate-900 dark:text-slate-100 mb-3 sm:mb-4 tracking-tight">
            Sự Khác Biệt Giữa AI Đại Trà & MediCare AI (Có Bác Sĩ Giám Sát)
          </h2>
          <p className="text-slate-600 dark:text-slate-400 text-xs sm:text-sm lg:text-base max-w-2xl mx-auto leading-relaxed">
            Tại sao người bệnh không nên tự ý dùng chatbot đại trà để chẩn đoán sức khỏe? Hãy đối chiếu bảng tiêu chuẩn lâm sàng dưới đây.
          </p>
        </div>

        {/* Desktop Table (MD and UP) */}
        <div className="hidden md:block bg-slate-50 dark:bg-slate-900/60 rounded-2xl border border-slate-200 dark:border-slate-800/80 overflow-hidden shadow-xs dark:shadow-xl reveal-item">
          <div className="grid grid-cols-3 text-sm font-semibold bg-slate-100 dark:bg-slate-950/70 border-b border-slate-200 dark:border-slate-800/80">
            <div className="p-5 text-slate-700 dark:text-slate-300">Tiêu Chí Lâm Sàng</div>
            <div className="p-5 text-slate-500 dark:text-slate-400 border-l border-slate-200 dark:border-slate-800/80">AI Đơn Thuần (Chatbot Đại Trà)</div>
            <div className="p-5 text-blue-700 dark:text-cyan-300 bg-blue-50/70 dark:bg-blue-950/30 border-l border-slate-200 dark:border-slate-800/80">
              MediCare AI & Bác Sĩ Giám Sát (HITL)
            </div>
          </div>
          
          <div className="divide-y divide-slate-200 dark:divide-slate-800/60 text-sm">
            {comparisonItems.map((item, idx) => {
              const Icon = item.icon
              return (
                <div key={idx} className="grid grid-cols-3 items-center">
                  <div className="p-5 font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2">
                    <Icon className="w-4 h-4 text-blue-600 dark:text-cyan-400 shrink-0" />
                    <span>{item.title}</span>
                  </div>
                  <div className="p-5 border-l border-slate-200 dark:border-slate-800/60">
                    <div className="font-medium text-red-600 dark:text-red-400 flex items-center gap-1.5 mb-1 text-xs sm:text-sm">
                      <XCircle className="w-4 h-4 shrink-0" /> {item.rawAI.status}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                      {item.rawAI.desc}
                    </div>
                  </div>
                  <div className="p-5 border-l border-slate-200 dark:border-slate-800/60 bg-blue-50/40 dark:bg-blue-950/20">
                    <div className="font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 mb-1 text-xs sm:text-sm">
                      <CheckCircle2 className="w-4 h-4 shrink-0" /> {item.medicareAI.status}
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                      {item.medicareAI.desc}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Mobile Responsive Cards (Below MD) */}
        <div className="md:hidden space-y-4 reveal-item">
          {comparisonItems.map((item, idx) => {
            const Icon = item.icon
            return (
              <div
                key={idx}
                className="bg-slate-50 dark:bg-slate-900/70 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 shadow-xs"
              >
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3 border-b border-slate-200 dark:border-slate-800 pb-2.5">
                  <Icon className="w-4 h-4 text-blue-600 dark:text-cyan-400 shrink-0" />
                  <span>{item.title}</span>
                </div>

                <div className="space-y-3">
                  {/* Raw AI */}
                  <div className="bg-red-50/70 dark:bg-red-950/30 border border-red-200 dark:border-red-500/20 rounded-xl p-3">
                    <div className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                      Chatbot Đại Trà:
                    </div>
                    <div className="text-xs font-semibold text-red-600 dark:text-red-400 flex items-center gap-1 mb-1">
                      <XCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{item.rawAI.status}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                      {item.rawAI.desc}
                    </p>
                  </div>

                  {/* MediCare AI */}
                  <div className="bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-500/30 rounded-xl p-3">
                    <div className="text-[10px] font-semibold text-blue-700 dark:text-cyan-300 uppercase tracking-wider mb-1">
                      MediCare AI (HITL):
                    </div>
                    <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 mb-1">
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                      <span>{item.medicareAI.status}</span>
                    </div>
                    <p className="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed">
                      {item.medicareAI.desc}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

      </div>
    </section>
  )
}
