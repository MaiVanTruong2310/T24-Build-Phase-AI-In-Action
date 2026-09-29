import { Brain, Activity, Clock } from 'lucide-react';

export function AITriage() {
  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6 mb-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
            <Brain size={20} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              AI Clinical Triage Engine 
              <span className="bg-indigo-600 text-white text-[10px] uppercase font-bold px-2 py-0.5 rounded-full">
                MedPALM-2 Triage
              </span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Phân tích rủi ro & gợi ý phác đồ cận lâm sàng trước tiếp đón</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-medium text-slate-500 mb-0.5">Độ tin cậy mô hình: <span className="text-indigo-600 font-bold text-sm">98.4%</span></p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="md:col-span-2">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
            CHUYÊN KHOA PHÙ HỢP NHẤT:
          </p>
          <h3 className="text-xl font-bold text-indigo-700 mb-2">
            Tim Mạch Can Thiệp (Interventional Cardiology)
          </h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Nguy cơ hội chứng mạch vành cấp mức độ nghi ngờ trung bình - cao do triệu chứng 
            đau thắt ngực gắng sức ở nam giới 42 tuổi có tiền sử THA.
          </p>
        </div>
        <div className="flex items-center justify-center bg-white border border-slate-100 rounded-xl p-4">
          <div className="relative w-24 h-24 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-slate-100"
                strokeWidth="3"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className="text-teal-500"
                strokeWidth="3"
                strokeDasharray="98, 100"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center text-center">
              <span className="text-2xl font-bold text-slate-800">98%</span>
              <span className="text-[9px] text-slate-500 uppercase font-semibold">Độ khớp</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="text-center mb-6">
          <span className="text-xs font-semibold text-teal-600 bg-teal-50 px-3 py-1 rounded-full border border-teal-100">
            Khuyến nghị khám chuyên sâu
          </span>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Activity size={14} className="text-teal-600" />
            Chỉ định cận lâm sàng khuyến nghị trước khi vào khám với Bác sĩ:
          </p>
          <span className="text-[10px] text-slate-400">Nhấn chọn để đưa vào phiếu hẹn</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label className="flex items-start gap-3 p-3 bg-white border border-sky-200 rounded-xl cursor-pointer hover:border-sky-300 transition-colors">
            <input type="checkbox" defaultChecked className="mt-1 w-4 h-4 text-sky-600 rounded border-slate-300 focus:ring-sky-500" />
            <div>
              <p className="text-sm font-bold text-slate-800">Điện tâm đồ (ECG)</p>
              <p className="text-xs text-slate-500 mb-1">12 chuyển đạo tại giường</p>
              <span className="text-[10px] font-semibold text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded">
                Khuyên làm trước (10 phút)
              </span>
            </div>
          </label>
          <label className="flex items-start gap-3 p-3 bg-white border border-sky-200 rounded-xl cursor-pointer hover:border-sky-300 transition-colors">
            <input type="checkbox" defaultChecked className="mt-1 w-4 h-4 text-sky-600 rounded border-slate-300 focus:ring-sky-500" />
            <div>
              <p className="text-sm font-bold text-slate-800">Siêu âm tim Doppler</p>
              <p className="text-xs text-slate-500 mb-1">Màu tim & van tim 4D</p>
              <span className="text-[10px] font-semibold text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded">
                Đánh giá phân suất tống máu
              </span>
            </div>
          </label>
          <label className="flex items-start gap-3 p-3 bg-white border border-sky-200 rounded-xl cursor-pointer hover:border-sky-300 transition-colors">
            <input type="checkbox" defaultChecked className="mt-1 w-4 h-4 text-sky-600 rounded border-slate-300 focus:ring-sky-500" />
            <div>
              <p className="text-sm font-bold text-slate-800">Xét nghiệm Troponin T</p>
              <p className="text-xs text-slate-500 mb-1">Định lượng hs-Troponin T</p>
              <span className="text-[10px] font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded">
                Loại trừ NMCT cấp
              </span>
            </div>
          </label>
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex gap-3">
        <Clock className="text-amber-500 flex-shrink-0 mt-0.5" size={20} />
        <div>
          <p className="text-sm font-bold text-amber-800 mb-1">Cảnh báo hướng dẫn chuẩn bị lâm sàng:</p>
          <p className="text-sm text-amber-700">
            Bệnh nhân cần được dặn nhịn ăn tối thiểu 04 tiếng trước khung giờ khám nếu cần tiến hành
            xét nghiệm bilan lipid máu toàn phần và đường huyết tĩnh mạch bổ sung.
          </p>
        </div>
      </div>
    </div>
  );
}
