import React from 'react'
import { Heart, Quote } from 'lucide-react'

export function Testimonials() {
  const reviews = [
    {
      text: 'Tôi bị đau thắt lồng ngực lúc nửa đêm, khai báo qua hệ thống chỉ sau 1 phút là AI kích hoạt cảnh báo nguy cơ mạch vành và bác sĩ trực ban gọi điện xử lý ngay. Tôi kịp thời đến viện can thiệp đặt stent đúng trong khung giờ vàng!',
      name: 'Vũ Thành Long',
      desc: '54 tuổi, Hà Nội',
      condition: 'Can thiệp Mạch Vành Cấp',
      img: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=150'
    },
    {
      text: 'Trước đây mỗi lần đi khám phải mất cả buổi sáng xếp hàng lấy số. Nay có MediCare AI, tôi chia sẻ triệu chứng trước, đến bệnh viện là vào thẳng phòng bác sĩ chuyên khoa đúng giờ hẹn, toa thuốc gửi thẳng về điện thoại.',
      name: 'Phạm Thu Hương',
      desc: '38 tuổi, TP. Hồ Chí Minh',
      condition: 'Khám Nội Tim Mạch & Huyết Áp',
      img: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=150'
    },
    {
      text: 'Gia đình có con nhỏ hay bị sốt cao ban đêm. Tính năng tư vấn AI có bác sĩ trực ban kiểm chứng và duyệt ký khiến vợ chồng tôi hoàn toàn yên tâm, không còn cảm giác hoang mang trước các thông tin trôi nổi trên mạng.',
      name: 'Lê Minh Khoa',
      desc: '42 tuổi, Đà Nẵng',
      condition: 'Theo dõi Nhi Khoa Đa Tầng',
      img: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&q=80&w=150'
    }
  ]

  return (
    <section className="bg-white dark:bg-[#0B1329] py-24 border-b border-slate-200 dark:border-slate-800/80 text-slate-900 dark:text-white relative z-10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16 reveal-item">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-700 dark:text-cyan-300 border border-blue-500/30 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-3.5 py-1.5 mb-4 rounded-full">
            <Heart className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
            <span>ĐÁNH GIÁ TỪ NGƯỜI BỆNH & THÂN NHÂN</span>
          </div>
          <h2 className="text-3xl lg:text-4xl font-semibold text-slate-900 dark:text-slate-100 mb-4 tracking-tight">
            Sự An Tâm Tuyệt Đối Trong Từng Khoảnh Khắc Lâm Sàng
          </h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm lg:text-base max-w-2xl mx-auto leading-relaxed">
            Sự an toàn và phục hồi của người bệnh là minh chứng rõ ràng nhất cho giá trị kết hợp giữa công nghệ AI hiện đại và y đức bác sĩ.
          </p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-6">
          {reviews.map((r, i) => (
            <div
              key={i}
              className="bg-slate-50 dark:bg-slate-900/60 rounded-2xl p-6 sm:p-7 border border-slate-200 dark:border-slate-800/80 flex flex-col justify-between hover:border-cyan-500/40 shadow-xs dark:shadow-none transition-all duration-300 reveal-item"
            >
              <div>
                <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-600/10 border border-blue-200 dark:border-blue-500/20 text-blue-600 dark:text-cyan-400 flex items-center justify-center mb-4">
                  <Quote className="w-4 h-4" />
                </div>
                <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed mb-6 italic">
                  "{r.text}"
                </p>
              </div>

              <div className="pt-4 border-t border-slate-200 dark:border-slate-800/80 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <img
                    src={r.img}
                    alt={r.name}
                    className="w-10 h-10 rounded-xl object-cover border border-slate-300 dark:border-slate-700/80"
                  />
                  <div>
                    <h4 className="font-semibold text-slate-900 dark:text-slate-100 text-xs sm:text-sm">
                      {r.name}
                    </h4>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">{r.desc}</p>
                  </div>
                </div>
                <span className="text-[10px] font-medium text-blue-700 dark:text-cyan-300 border border-blue-200 dark:border-cyan-500/30 bg-blue-50 dark:bg-cyan-950/40 px-2 py-0.5 rounded-md hidden sm:inline-block">
                  {r.condition}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
