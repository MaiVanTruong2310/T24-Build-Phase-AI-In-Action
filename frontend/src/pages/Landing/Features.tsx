import { ShieldAlert, Activity, CalendarCheck, UsersRound, Ban } from 'lucide-react'
import './Sections.css'

// Nội dung bám theo README/ARCHITECTURE của dự án: chỉ nêu những gì hệ thống thật sự làm.
const FEATURES = [
  {
    icon: ShieldAlert,
    tag: 'ATS 1–2',
    title: 'Cấp cứu đi trước',
    text: 'Khi mô tả có dấu hiệu nguy hiểm như đau ngực, khó thở hay yếu liệt đột ngột, hệ thống dừng hỏi và hướng dẫn gọi 115. Bước này kiểm tra bằng quy tắc cố định, trước khi gọi mô hình AI.',
    danger: true,
  },
  {
    icon: Activity,
    tag: 'ATS 1–5',
    title: 'Phân tầng và gợi ý chuyên khoa',
    text: 'AI đánh giá mức độ khẩn cấp theo thang ATS và gợi ý chuyên khoa phù hợp. Mỗi lượt chỉ hỏi một câu ngắn, bạn không phải điền biểu mẫu dài.',
  },
  {
    icon: CalendarCheck,
    tag: 'Đặt lịch',
    title: 'Tìm bác sĩ, đặt lịch',
    text: 'Xem bác sĩ, khung giờ còn trống và giữ chỗ ngay trong cuộc trò chuyện hoặc bằng form đặt lịch. Tiến trình điều trị và hồ sơ bệnh án nằm trong tài khoản của bạn.',
  },
  {
    icon: UsersRound,
    tag: 'Có người duyệt',
    title: 'Điều phối viên trong vòng lặp',
    text: 'Nhân viên điều phối xác nhận lịch khám, theo dõi phiên chat và có thể tiếp quản khi AI không chắc chắn hoặc ca phức tạp.',
  },
]

const LIMITS = ['Chẩn đoán xác định', 'Kê đơn hay liều thuốc', 'Thay thế bác sĩ']

export function Features() {
  return (
    <section id="tinh-nang" className="lp-section" aria-labelledby="features-title">
      <div className="lp-wrap">
        <div className="reveal-item mb-12 max-w-2xl">
          <p className="lp-kicker">VCare+ làm được gì</p>
          <h2 id="features-title" className="lp-title">Một trợ lý tiếp đón, bốn việc cụ thể</h2>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {FEATURES.map(({ icon: Icon, tag, title, text, danger }) => (
            <article key={title} className={`lp-card reveal-item${danger ? ' lp-card--danger' : ''}`}>
              <div className="mb-4 flex items-center justify-between gap-3">
                <span className="lp-icon lp-icon--lg" aria-hidden="true"><Icon className="h-6 w-6" strokeWidth={2.1} /></span>
                <span className="lp-tag">{tag}</span>
              </div>
              <h3 className="lp-card-title">{title}</h3>
              <p className="lp-card-text">{text}</p>
            </article>
          ))}
        </div>

        <div className="lp-limits reveal-item">
          <p className="lp-limits__label"><Ban className="h-5 w-5 shrink-0" strokeWidth={2.2} aria-hidden="true" /> VCare+ không làm:</p>
          <ul>
            {LIMITS.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <p className="lp-limits__note">Mọi quyết định y khoa vẫn thuộc về bác sĩ.</p>
        </div>
      </div>
    </section>
  )
}
