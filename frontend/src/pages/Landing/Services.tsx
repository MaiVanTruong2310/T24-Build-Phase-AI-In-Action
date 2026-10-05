import type { CSSProperties } from 'react'
import './Services.css'

import { Stethoscope, CalendarCheck, HeartPulse, FileText, CheckCircle2 } from 'lucide-react'



export function Services() {

  const services = [

    {

      icon: Stethoscope,

      title: 'AI Sàng Lọc Triệu Chứng Chuyên Sâu',

      desc: 'Phân tích ngữ nghĩa ngôn ngữ tự nhiên tiếng Việt y khoa, đối chiếu với ngân hàng phác đồ lâm sàng thế giới để dự báo nguy cơ tức thì.',

      highlights: ['Hiểu ngữ cảnh tiếng Việt tự nhiên', 'Nhận diện tổ hợp bệnh lý đa cơ quan'],

      iconColor: 'text-blue-600 light:text-app-primary dark:text-cyan-400',

      boxColor: 'border-blue-200 light:border-app-border dark:border-cyan-500/30 bg-blue-50 light:bg-app-muted dark:bg-cyan-950/40'

    },

    {

      icon: CalendarCheck,

      title: 'Điều Phối Khám Đúng Chuyên Khoa',

      desc: 'Tự động sắp xếp thứ tự ưu tiên dựa trên mức độ nghiêm trọng và kết nối trực tiếp đến bác sĩ đúng chuyên khoa phù hợp.',

      highlights: ['Tiết kiệm hơn 85% thời gian chờ', 'Đặt khám đúng chuyên gia đầu ngành'],

      iconColor: 'text-sky-600 light:text-app-primary dark:text-blue-400',

      boxColor: 'border-sky-200 light:border-app-border dark:border-blue-500/30 bg-sky-50 light:bg-app-muted dark:bg-blue-950/40'

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

    <section className="py-24 bg-white light:bg-app-surface dark:bg-[#0B1329] border-b border-slate-200 light:border-app-border dark:border-slate-800/80 text-slate-900 light:text-app-text dark:text-white relative z-10 transition-colors duration-300">

      <div className="max-w-7xl mx-auto px-6">

        <div className="text-center mb-16 reveal-item">

<h2 className="text-3xl lg:text-4xl font-semibold text-slate-900 light:text-app-text dark:text-slate-100 mb-4 tracking-tight">

            Giải Pháp Chăm Sóc Sức Khỏe Thông Minh Đạt Chuẩn

          </h2>

          <p className="text-slate-600 light:text-app-secondary dark:text-slate-400 text-sm lg:text-base max-w-2xl mx-auto leading-relaxed">

            Ứng dụng các chuẩn mực lâm sàng tiên tiến nhất nhằm đem lại trải nghiệm chăm sóc y tế chuẩn xác, ân cần và an tâm tuyệt đối cho người bệnh.

          </p>

        </div>



        <div className="health-services-container" aria-label="Các giải pháp chăm sóc sức khỏe">
          {services.map((service, index) => {
            const Icon = service.icon
            return (
              <article
                key={service.title}
                className="health-service-glass"
                style={{ '--service-angle': [-15, -5, 5, 15][index] } as CSSProperties}
                tabIndex={0}
                aria-labelledby={`health-service-title-${index}`}
              >
                <div className="health-service-body">
                  <Icon className="health-service-icon" aria-hidden="true" />
                  <div className="health-service-details">
                    <p>{service.desc}</p>
                    <ul>
                      {service.highlights.map(highlight => (
                        <li key={highlight}><CheckCircle2 aria-hidden="true" /><span>{highlight}</span></li>
                      ))}
                    </ul>
                  </div>
                </div>
                <h3 id={`health-service-title-${index}`} className="health-service-title">{service.title}</h3>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}
