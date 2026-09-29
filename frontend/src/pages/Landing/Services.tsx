import { MessageSquare, Calendar, Activity, FileText } from 'lucide-react'

export function Services() {
  return (
    <div className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="inline-block bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1.5 rounded-full mb-6">
            HỆ SINH THÁI TOÀN DIỆN
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-4">Dịch Vụ & Tính Năng Y Tế Thông Minh</h2>
          <p className="text-slate-500 max-w-2xl mx-auto">
            Trang bị các công nghệ lâm sàng tiên tiến nhất nhằm đem lại trải nghiệm chăm sóc y tế toàn vẹn, tiện lợi và chính xác.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Service 1 */}
          <div className="bg-slate-50 rounded-3xl p-6 border border-slate-100 hover:border-sky-100 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center mb-6">
              <MessageSquare className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 mb-3">AI Sàng Lọc Triệu Chứng Chuyên Sâu</h3>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">Sử dụng Natural Language Processing y khoa chuyên biệt, phân tích ngữ nghĩa các mô tả triệu chứng và đối chiếu ngân hàng dữ liệu y văn thế giới.</p>
            <ul className="space-y-2 text-xs text-slate-600 font-medium">
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Tương thích tiếng Việt tự nhiên</li>
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Dự đoán yếu tố nguy cơ tức thì</li>
            </ul>
          </div>
          {/* Service 2 */}
          <div className="bg-slate-50 rounded-3xl p-6 border border-slate-100 hover:border-sky-100 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-6">
              <Calendar className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 mb-3">Đặt Lịch Khám Thông Minh</h3>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">Trực ban lâm sàng liên tục không gián đoạn, tự động xếp lịch ưu tiên theo mức độ nghiêm trọng và phân bổ bác sĩ chuyên môn phù hợp nhất.</p>
            <ul className="space-y-2 text-xs text-slate-600 font-medium">
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Tiết kiệm 90% thời gian chờ</li>
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Đặt khám đúng chuyên gia phụ trách</li>
            </ul>
          </div>
          {/* Service 3 */}
          <div className="bg-slate-50 rounded-3xl p-6 border border-slate-100 hover:border-sky-100 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-red-100 text-red-600 flex items-center justify-center mb-6">
              <Activity className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 mb-3">Tiếp Quản Cấp Cứu Trực Tuyến</h3>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">Khi phát hiện các dấu hiệu sinh tử nguy cấp (nhồi máu cơ tim, đột quỵ, sốc phản vệ), hệ thống lập tức mở kênh liên lạc 115 và bác sĩ cấp cứu.</p>
            <ul className="space-y-2 text-xs text-slate-600 font-medium">
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Kích hoạt Hotline cấp cứu 1 chạm</li>
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Hướng dẫn sơ cứu sơ bộ tức thời</li>
            </ul>
          </div>
          {/* Service 4 */}
          <div className="bg-slate-50 rounded-3xl p-6 border border-slate-100 hover:border-sky-100 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mb-6">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 mb-3">Hồ Sơ Điện Tử Chuẩn HL7/FHIR</h3>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">Lưu trữ lịch sử khám, đơn thuốc và kết quả xét nghiệm trọn đời theo chuẩn y tế quốc tế HIPAA, bảo mật đa tầng, dễ dàng chia sẻ liên viện.</p>
            <ul className="space-y-2 text-xs text-slate-600 font-medium">
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Tra cứu kết quả xét nghiệm 24/7</li>
              <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-sky-500 rounded-full"></div> Mã hóa chuẩn ngân hàng và y tế</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
