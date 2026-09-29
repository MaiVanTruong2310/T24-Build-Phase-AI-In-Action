import { MessageSquare, AlertTriangle, ShieldCheck, FileText } from 'lucide-react'

export function Process() {
  const steps = [
    {
      num: '01',
      icon: <MessageSquare className="w-5 h-5 text-blue-600" />,
      title: 'Khai Triệu Chứng Tự Nhiên',
      desc: 'Trò chuyện tự do bằng văn bản hoặc giọng nói. AI tự động ghi nhận tiền sử, hoàn cảnh khởi phát và tính chất cơn đau.',
      meta: 'Phản hồi dưới 2 giây',
      color: 'blue'
    },
    {
      num: '02',
      icon: <AlertTriangle className="w-5 h-5 text-emerald-600" />,
      title: 'AI Triage Phân Tầng Rủi Ro',
      desc: <>Phân loại 3 cấp độ: <span className="text-red-600 font-semibold">Đỏ (Cấp cứu)</span>, <span className="text-amber-600 font-semibold">Vàng (Ưu tiên)</span>, <span className="text-emerald-600 font-semibold">Xanh (Theo dõi)</span> theo hướng dẫn của Hội Đồng Y Tế.</>,
      meta: 'Tự động gắn nhãn rủi ro',
      color: 'emerald'
    },
    {
      num: '03',
      icon: <ShieldCheck className="w-5 h-5 text-indigo-600" />,
      title: 'Bác Sĩ Giám Sát Phê Duyệt',
      desc: 'Bác sĩ lâm sàng trực ban kiểm chứng toàn bộ đề xuất của AI, điều chỉnh phác đồ và ký số xác thực y khoa hợp pháp.',
      meta: '100% An Toàn Y Khoa',
      color: 'indigo'
    },
    {
      num: '04',
      icon: <FileText className="w-5 h-5 text-sky-600" />,
      title: 'Toa Thuốc & Khám Ưu Tiên',
      desc: 'Nhận toa thuốc điện tử có mã định danh QR hoặc đặt lịch khám chuyên khoa phòng khám trực tiếp không phải bốc số chờ đợi.',
      meta: 'Đồng bộ Apple & Zalo',
      color: 'sky'
    }
  ]
  return (
    <div className="bg-slate-50 py-20 border-y border-slate-100">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="inline-block bg-blue-100 text-blue-800 text-xs font-bold px-3 py-1.5 rounded-full mb-6">
            TIÊU CHUẨN Y TẾ TƯƠNG LAI
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-4">Quy Trình 4 Bước Khép Kín Chuẩn Y Khoa<br/>Toàn Diện</h2>
          <p className="text-slate-500 max-w-2xl mx-auto">
            Mô hình kết hợp hoàn hảo giữa năng lực tính toán cực nhanh của Trí tuệ Nhân tạo và lương tri, kinh nghiệm vững vàng của Bác sĩ chuyên khoa.
          </p>
        </div>
        
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((s, i) => (
            <div key={i} className="bg-white rounded-3xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 hover:-translate-y-1 transition-transform relative">
              <div className="flex items-center justify-between mb-6">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg bg-${s.color}-50 text-${s.color}-600`}>
                  {s.num}
                </div>
                {s.icon}
              </div>
              <h3 className="font-bold text-slate-900 mb-3">{s.title}</h3>
              <p className="text-sm text-slate-500 mb-6 leading-relaxed">
                {s.desc}
              </p>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <ShieldCheck className="w-4 h-4 text-sky-500" /> {s.meta}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
