import { useState } from 'react'
import './Process.css'

import { MessageSquare, AlertTriangle, ShieldCheck, FileText } from 'lucide-react'



export function Process() {
  const [activeStep, setActiveStep] = useState(0)

  const steps = [

    {

      num: '01',

      icon: <MessageSquare className="w-6 h-6" />,

      title: 'Tiếp Nhận Triệu Chứng Tự Nhiên',

      desc: 'Người bệnh chia sẻ tình trạng bằng lời nói hoặc tin nhắn. Hệ thống tự động trích xuất các triệu chứng dương tính/âm tính và tiền sử bệnh lý.',

      meta: 'Phản hồi trong 1.5 giây',

      badgeColor: 'border-blue-300 dark:border-cyan-500/30 bg-blue-50 light:bg-app-muted dark:bg-cyan-950/40 text-blue-700 light:text-app-primary dark:text-cyan-300'

    },

    {

      num: '02',

      icon: <AlertTriangle className="w-6 h-6" />,

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

      icon: <ShieldCheck className="w-6 h-6" />,

      title: 'Bác Sĩ Giám Sát Phê Duyệt',

      desc: 'Bác sĩ chuyên khoa trực ban rà soát toàn bộ khuyến nghị của AI, điều chỉnh phác đồ phù hợp và ký số xác thực y khoa trước khi hoàn tất.',

      meta: '100% Bác sĩ duyệt ký',

      badgeColor: 'border-emerald-300 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300'

    },

    {

      num: '04',

      icon: <FileText className="w-6 h-6" />,

      title: 'Toa Thuốc & Lịch Khám Ưu Tiên',

      desc: 'Cấp mã toa thuốc điện tử và ưu tiên chuyển tiếp người bệnh tới phòng khám chuyên khoa trực tiếp mà không cần bốc số chờ đợi lâu.',

      meta: 'Liên thông bệnh viện số',

      badgeColor: 'border-blue-300 dark:border-blue-500/30 bg-blue-50 light:bg-app-muted dark:bg-blue-950/40 text-blue-700 light:text-app-primary dark:text-blue-300'

    }

  ]



  return (
    <section id="quy-trinh" className="bg-slate-50 light:bg-app-page dark:bg-[#070D1E] py-16 sm:py-24 border-b border-slate-200 light:border-app-border dark:border-slate-800/80 relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="care-process-container reveal-item">
          <div className="care-process-palette" aria-label="Quy trình khám gồm 4 bước">
            {steps.map((step, index) => (
              <button
                key={step.num}
                type="button"
                className={`care-process-color ${activeStep === index ? 'is-active' : ''}`}
                aria-expanded={activeStep === index}
                aria-controls={`care-process-detail-${step.num}`}
                onMouseEnter={() => setActiveStep(index)}
                onFocus={() => setActiveStep(index)}
                onClick={() => setActiveStep(index)}
              >
                <span className="care-process-top"><span className="care-process-number">{step.num}</span><span aria-hidden="true">{step.icon}</span></span>
                <span className="care-process-name">{step.title}</span>
                <span id={`care-process-detail-${step.num}`} className="care-process-detail" hidden={activeStep !== index}>
                  <span className="care-process-description">{step.desc}</span>
                  <span className="care-process-meta">{step.meta}</span>
                </span>
              </button>
            ))}
          </div>
          <div className="care-process-stats">
            <h2>4 Bước Khám Chữa Bệnh Thông Minh &amp; An Toàn Tuyệt Đối</h2>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M4 7.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5S5.5 9.83 5.5 9 4.83 7.5 4 7.5zm10 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5S15.5 9.83 15.5 9 14.83 7.5 14 7.5zm-5 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5S10.5 9.83 10.5 9 9.83 7.5 9 7.5z" /></svg>
          </div>
        </div>
      </div>
    </section>
  )
}
