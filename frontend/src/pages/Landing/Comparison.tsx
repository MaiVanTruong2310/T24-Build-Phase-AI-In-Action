import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'

export function Comparison() {
  return (
    <div className="bg-slate-50 py-20">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="inline-block bg-indigo-100 text-indigo-800 text-xs font-bold px-3 py-1.5 rounded-full mb-6 uppercase tracking-wider">
            Phân Tích So Sánh
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-4">Sự Khác Biệt Giữa AI Đơn Thuần & MediCare AI (HITL)</h2>
          <p className="text-slate-500 max-w-2xl mx-auto">
            Tại sao không nên tự dùng chatbot đại trà để chẩn đoán bệnh? Hãy xem bảng so sánh tiêu chuẩn y khoa dưới đây.
          </p>
        </div>

        <div className="bg-white rounded-3xl overflow-hidden shadow-sm border border-slate-200">
          <div className="grid grid-cols-3 text-sm font-bold bg-slate-50 border-b border-slate-200">
            <div className="p-6 text-slate-900">Tiêu chí Y tế</div>
            <div className="p-6 text-slate-900 border-l border-slate-200">AI Đơn Thuần (ChatGPT / MXH)</div>
            <div className="p-6 text-sky-800 bg-sky-50 border-l border-slate-200">MediCare AI & Bác Sĩ Đồng Hành</div>
          </div>
          
          <div className="divide-y divide-slate-100 text-sm">
            {/* Row 1 */}
            <div className="grid grid-cols-3 items-center">
              <div className="p-6 font-semibold text-slate-900 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-slate-400" />
                Kiểm chứng lâm sàng
              </div>
              <div className="p-6 border-l border-slate-100">
                <div className="font-semibold text-red-600 flex items-center gap-1.5 mb-1">
                  <XCircle className="w-4 h-4" /> Không có bác sĩ thẩm định
                </div>
                <div className="text-xs text-slate-500 leading-relaxed">Câu trả lời chỉ mang tính chất thống kê từ ngữ.</div>
              </div>
              <div className="p-6 border-l border-slate-100 bg-sky-50/30">
                <div className="font-semibold text-emerald-600 flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-4 h-4" /> 100% Bác sĩ kiểm tra & duyệt
                </div>
                <div className="text-xs text-slate-600 leading-relaxed">Bác sĩ chuyên khoa ký duyệt mọi khuyến nghị y tế.</div>
              </div>
            </div>

            {/* Row 2 */}
            <div className="grid grid-cols-3 items-center">
              <div className="p-6 font-semibold text-slate-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-slate-400" />
                Hiện tượng Ảo giác (Hallucination)
              </div>
              <div className="p-6 border-l border-slate-100">
                <div className="font-semibold text-red-600 flex items-center gap-1.5 mb-1">
                  <AlertTriangle className="w-4 h-4" /> Rủi ro cao (15% - 25%)
                </div>
                <div className="text-xs text-slate-500 leading-relaxed">Dễ bịa đặt tên thuốc, liều dùng gây tử vong.</div>
              </div>
              <div className="p-6 border-l border-slate-100 bg-sky-50/30">
                <div className="font-semibold text-emerald-600 flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-4 h-4" /> Kiểm soát 0% sai lệch
                </div>
                <div className="text-xs text-slate-600 leading-relaxed">Đội ngũ bác sĩ chuyên khoa chặn đứng hoàn toàn ảo giác y khoa.</div>
              </div>
            </div>

            {/* Row 3 */}
            <div className="grid grid-cols-3 items-center">
              <div className="p-6 font-semibold text-slate-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-slate-400" />
                Xử trí cấp cứu (Emergency)
              </div>
              <div className="p-6 border-l border-slate-100">
                <div className="font-semibold text-slate-600 flex items-center gap-1.5 mb-1">
                  <XCircle className="w-4 h-4" /> Chỉ khuyên câu sáo rỗng
                </div>
                <div className="text-xs text-slate-500 leading-relaxed">Không thể phân loại rủi ro tức thời hay liên hệ cứu hộ.</div>
              </div>
              <div className="p-6 border-l border-slate-100 bg-sky-50/30">
                <div className="font-semibold text-emerald-600 flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-4 h-4" /> Kích hoạt Triage Đỏ & 115
                </div>
                <div className="text-xs text-slate-600 leading-relaxed">Điều phối xe cấp cứu và nối máy điều dưỡng trưởng trong 30s.</div>
              </div>
            </div>

            {/* Row 4 */}
            <div className="grid grid-cols-3 items-center">
              <div className="p-6 font-semibold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-slate-400" />
                Pháp lý BHYT & Toa thuốc
              </div>
              <div className="p-6 border-l border-slate-100">
                <div className="font-semibold text-red-600 flex items-center gap-1.5 mb-1">
                  <XCircle className="w-4 h-4" /> Không có giá trị pháp lý
                </div>
                <div className="text-xs text-slate-500 leading-relaxed">Không thể kê đơn hay sử dụng thanh toán bảo hiểm.</div>
              </div>
              <div className="p-6 border-l border-slate-100 bg-sky-50/30">
                <div className="font-semibold text-emerald-600 flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-4 h-4" /> Toa thuốc điện tử hợp pháp
                </div>
                <div className="text-xs text-slate-600 leading-relaxed">Liên thông cổng Dược Quốc Gia & Thanh toán BHYT.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
