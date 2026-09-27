import { ShieldCheck, Activity, ChevronRight, Lock } from 'lucide-react'

export function Hero() {
  return (
    <div className="bg-slate-50 py-16">
      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <div className="flex items-center gap-2 text-sky-600 font-semibold text-sm mb-4">
            <div className="w-2 h-2 rounded-full bg-sky-600"></div>
            HỆ THỐNG Y TẾ THÔNG MINH THẾ HỆ MỚI
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 leading-tight mb-6">
            Y Tế Thông Minh Với <span className="text-sky-600">AI Agent</span><br />
            & Bác Sĩ Giám Sát <span className="text-emerald-600">24/7</span><br />
            Chuyên Khoa
          </h1>
          <p className="text-lg text-slate-600 mb-8 leading-relaxed">
            Khám phá tiêu chuẩn chăm sóc sức khỏe mới: AI sàng lọc triệu chứng chính xác trong 30 giây, kết nối đội ngũ bác sĩ chuyên khoa phê duyệt tức thì, an toàn tuyệt đối.
          </p>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-8">
            <button className="w-full sm:w-auto bg-sky-700 hover:bg-sky-800 text-white font-semibold py-3 px-6 rounded-xl flex items-center justify-center gap-2 transition-colors">
              <Activity className="w-5 h-5" />
              Tư Vấn & Khám Bệnh Ngay
            </button>
            <button className="w-full sm:w-auto bg-white hover:bg-slate-50 text-slate-700 font-semibold py-3 px-6 rounded-xl border border-slate-200 flex items-center justify-center gap-2 transition-colors">
              <ChevronRight className="w-5 h-5 text-slate-400" />
              Xem Quy Trình Khám Bệnh Đa Tầng
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-6 text-sm font-medium text-slate-700 mb-6">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              Chuẩn BỘ Y TẾ & HIPAA
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-sky-600" />
              100% Y lệnh <span className="text-slate-500 font-normal">có Bác sĩ duyệt</span>
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="flex text-amber-400 text-lg">
              {'★★★★★'.split('').map((star, i) => <span key={i}>{star}</span>)}
            </div>
            <span className="font-bold text-slate-900">4.9/5</span>
            <span className="text-slate-500">(50.000+ bệnh nhân)</span>
          </div>
        </div>
        
        {/* Right side: Mock UI */}
        <div className="relative mt-8 lg:mt-0">
          <div className="bg-white rounded-3xl shadow-[0_20px_50px_rgb(0,0,0,0.1)] border border-slate-100 p-6 relative z-10">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">MediCare AI Clinical Triage</h3>
                  <p className="text-xs text-slate-500">BS. Nguyễn Phương Linh đang giám sát</p>
                </div>
              </div>
              <div className="bg-red-50 text-red-600 text-xs font-bold px-2 py-1 rounded-md shrink-0">
                Triage Đỏ
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="bg-slate-50 rounded-2xl p-4 text-sm text-slate-700">
                "Tôi bị tức thắt ngực trái 2 giờ nay, lan lên khớp vai và cánh tay trái, hơi vã mồ hôi."
              </div>
              
              <div className="bg-blue-50/50 rounded-2xl p-4 border border-blue-100">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-700">
                    <Activity className="w-4 h-4" />
                    Sàng lọc MedPaLM AI
                  </div>
                  <span className="text-xs text-slate-500">Độ tin cậy: 98.4%</span>
                </div>
                <p className="text-sm text-slate-700">
                  Dấu hiệu cảnh báo: <span className="text-red-600 font-semibold">Hội chứng vành cấp nghi ngờ</span>. Đề nghị điện tâm đồ ECG 12 chuyển đạo ngay.
                </p>
              </div>
              
              <div className="flex items-start gap-3 bg-emerald-50/50 rounded-2xl p-4 border border-emerald-100">
                <img src="https://i.pravatar.cc/150?img=47" alt="Doctor" className="w-10 h-10 rounded-full shrink-0" />
                <div>
                  <div className="flex items-center justify-between mb-1 gap-2">
                    <h4 className="text-sm font-bold text-slate-900">BS. Nguyễn Phương Linh (Trực ban lâm sàng)</h4>
                    <span className="bg-emerald-100 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded shrink-0">Đã Duyệt</span>
                  </div>
                  <p className="text-xs text-slate-600 italic">
                    "Tôi đã kích hoạt tiếp nhận ưu tiên tại Khoa Tim Mạch. Bác sĩ trực sẵn sàng đón tiếp bệnh nhân."
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-100">
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Lock className="w-3.5 h-3.5" />
                Mã hóa end-to-end
              </div>
              <button className="bg-sky-700 hover:bg-sky-800 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1 transition-colors">
                Thử hội chẩn thực tế <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          {/* Badge Demo */}
          <div className="absolute -top-4 -right-4 bg-emerald-600 text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg flex items-center gap-1.5 z-20">
            <div className="w-2 h-2 rounded-full bg-white animate-pulse"></div>
            Demo Mô Phỏng Trực Tiếp
          </div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-sky-200/50 blur-3xl rounded-full -z-10"></div>
        </div>
      </div>
    </div>
  )
}
