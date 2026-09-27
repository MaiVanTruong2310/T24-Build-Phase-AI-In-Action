import { MessageSquare, Phone } from 'lucide-react'

export function CTA() {
  return (
    <div className="bg-sky-700 py-24 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-sky-600/30 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-sky-800/30 rounded-full blur-3xl translate-y-1/2 -translate-x-1/3"></div>
      
      <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
        <h2 className="text-4xl md:text-5xl font-bold text-white mb-6 leading-tight">
          Sẵn Sàng Trải Nghiệm Chăm Sóc Sức Khỏe Thông Minh?
        </h2>
        <p className="text-sky-100 text-lg mb-10 max-w-2xl mx-auto leading-relaxed">
          Bắt đầu phác đồ chẩn đoán lâm sàng cùng MediCare AI và đội ngũ Bác sĩ chuyên khoa ngay bây giờ. Hoàn toàn miễn phí sàng lọc ban đầu và bảo mật tuyệt đối.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button className="w-full sm:w-auto bg-white text-sky-700 hover:bg-sky-50 font-bold py-4 px-8 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-lg shadow-sky-900/20">
            <MessageSquare className="w-5 h-5" />
            Bắt Đầu Hội Chẩn Miễn Phí
          </button>
          <button className="w-full sm:w-auto bg-transparent hover:bg-sky-600 border border-sky-400 text-white font-bold py-4 px-8 rounded-xl transition-colors flex items-center justify-center gap-2">
            <Phone className="w-5 h-5" />
            Tổng Đài Cấp Cứu 1900 6868
          </button>
        </div>
      </div>
    </div>
  )
}
