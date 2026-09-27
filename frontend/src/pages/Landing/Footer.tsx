import { PlusSquare, ShieldCheck } from 'lucide-react'

export function Footer() {
  return (
    <footer className="bg-slate-50 pt-16 pb-8 border-t border-slate-200">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid md:grid-cols-4 gap-8 lg:gap-12 mb-12">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <div className="bg-sky-600 text-white p-1 rounded">
                <PlusSquare className="w-6 h-6" strokeWidth={2.5} />
              </div>
              <div className="leading-tight">
                <h1 className="text-lg font-bold text-sky-800">MediCare AI</h1>
                <p className="text-[10px] text-slate-500 font-medium">Clinical Intelligence System</p>
              </div>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed mb-6">
              Hệ thống y tế số đa tầng tích hợp Trí tuệ nhân tạo và Đội ngũ Bác sĩ Chuyên khoa Trực tuyến 24/7.
            </p>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">TỔNG ĐÀI CẤP CỨU 24/7:</p>
              <p className="text-xl font-bold text-red-600">1900 6868</p>
            </div>
          </div>
          
          <div>
            <h4 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <span className="w-4 h-4 text-sky-600">📍</span> Cơ Sở Hà Nội
            </h4>
            <div className="space-y-3 text-xs text-slate-600">
              <p><strong className="text-slate-900">Trụ sở chính:</strong> Tòa nhà Y Tế Công Nghệ Cao, Số 18 Hoàng Diệu, Ba Đình, Hà Nội.</p>
              <p><strong className="text-slate-900">Cơ sở Cầu Giấy:</strong> 124 Duy Tân, Phường Dịch Vọng Hậu, Cầu Giấy.</p>
              <p><strong className="text-slate-900">Hotline:</strong> (024) 7300 8899</p>
            </div>
          </div>
          
          <div>
            <h4 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <span className="w-4 h-4 text-sky-600">📍</span> Cơ Sở TP. Hồ Chí Minh
            </h4>
            <div className="space-y-3 text-xs text-slate-600">
              <p><strong className="text-slate-900">Chi nhánh Tân Bình:</strong> 45 Phổ Quang, Phường 2, Tân Bình, TP. HCM.</p>
              <p><strong className="text-slate-900">Chi nhánh Quận 1:</strong> 88 Nguyễn Du, Phường Bến Nghé, Quận 1.</p>
              <p><strong className="text-slate-900">Hotline:</strong> (028) 7300 9988</p>
            </div>
          </div>
          
          <div>
            <h4 className="font-bold text-slate-900 mb-4">Chứng Nhận & Tiêu Chuẩn</h4>
            <ul className="space-y-3 text-xs text-slate-600">
              <li className="flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Chuẩn an toàn thông tin ISO/IEC 27001</span>
              </li>
              <li className="flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Đạt chuẩn bảo mật Y Tế HIPAA (Mỹ)</span>
              </li>
              <li className="flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Cấp phép hoạt động bởi Bộ Y Tế Việt Nam</span>
              </li>
            </ul>
          </div>
        </div>
        
        <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-slate-200 text-xs text-slate-500">
          <p>© 2024 MediCare AI Health System. Mọi quyền được bảo lưu.</p>
          <div className="flex items-center gap-4 mt-4 md:mt-0">
            <a href="#" className="hover:text-slate-800 transition-colors">Điều khoản dịch vụ</a>
            <span className="w-1 h-1 bg-slate-300 rounded-full"></span>
            <a href="#" className="hover:text-slate-800 transition-colors">Chính sách bảo mật HIPAA</a>
            <span className="w-1 h-1 bg-slate-300 rounded-full"></span>
            <a href="#" className="hover:text-slate-800 transition-colors">Quy trình Y lệnh Đa tầng</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
