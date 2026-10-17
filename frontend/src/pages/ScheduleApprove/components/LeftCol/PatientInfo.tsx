import { User, ShieldCheck, AlertTriangle, FileWarning, CloudOff } from 'lucide-react';

export function PatientInfo() {
  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-sky-100 flex items-center justify-center text-sky-600">
            <User size={20} />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">
              HỒ SƠ HÀNH CHÍNH & LÂM SÀNG
            </p>
            <h2 className="text-lg font-bold text-slate-800">Thông Tin Người Khám & Khai Báo</h2>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold">
          <ShieldCheck size={14} />
          Đã đồng bộ VNeID
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 bg-white p-4 rounded-xl border border-slate-100">
        <div>
          <p className="text-xs text-slate-500 font-medium mb-1">Họ và tên bệnh nhân</p>
          <p className="font-bold text-slate-900 text-base">Nguyễn Văn An</p>
          <p className="text-xs text-slate-600 mt-1">42 tuổi • Nam</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 font-medium mb-1">Số định danh CCCD</p>
          <p className="font-bold text-slate-900 text-base">001082009842</p>
          <p className="text-xs text-emerald-600 mt-1 flex items-center gap-1">
            <ShieldCheck size={12} />
            Sinh trắc học hợp lệ
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500 font-medium mb-1">Mã thẻ BHYT đăng ký</p>
          <p className="font-bold text-slate-900 text-base tracking-wide">DN 4 01 01 209 8241</p>
          <p className="text-xs text-sky-600 mt-1">Đã xác thực Cổng BHXH VN</p>
        </div>
      </div>

      <div className="mb-6">
        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">
          TIỀN SỬ BỆNH & YẾU TỐ NGUY CƠ GHI NHẬN:
        </p>
        <div className="flex flex-wrap gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-lg text-sm font-semibold border border-amber-100">
            <AlertTriangle size={14} />
            Tăng huyết áp vô căn (Độ I - 3 năm)
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 rounded-lg text-sm font-semibold border border-rose-100">
            <FileWarning size={14} />
            Dị ứng Penicillin & Beta-lactam (Cấp 2)
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg text-sm font-semibold">
            <CloudOff size={14} />
            Không hút thuốc lá chủ động
          </span>
        </div>
      </div>

      <div className="bg-white border border-slate-100 rounded-xl p-4 relative">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sky-700 font-semibold text-sm">
            <User size={16} />
            Triệu chứng bệnh nhân mô tả qua Cổng Bệnh Nhân (Conversational Ingestion):
          </div>
          <span className="text-xs text-slate-400 font-medium">10:14 sáng nay</span>
        </div>
        <p className="text-slate-700 text-sm italic leading-relaxed pl-4 border-l-4 border-slate-200">
          "Tôi bị đau thắt ngực nhẹ sau xương ức, cảm giác khó thở hụt hơi rõ nhất khi leo cầu 
          thang hoặc vận động gắng sức khoảng 3 ngày nay. Nghỉ ngơi khoảng 5 phút thì đỡ dần."
        </p>
      </div>
    </div>
  );
}
