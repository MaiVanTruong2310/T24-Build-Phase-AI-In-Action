import { Receipt, CheckCircle2, Info } from 'lucide-react';

export function Billing() {
  return (
    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
            <Receipt size={16} />
          </div>
          <h2 className="text-base font-bold text-slate-800">Bảng Tính Chi Phí & BHYT</h2>
        </div>
        <div className="text-xs font-bold text-teal-700 bg-teal-50 px-2 py-1 rounded">
          Mức hưởng: 80%
        </div>
      </div>

      <div className="space-y-3 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-600">Phí khám chuyên khoa Tim mạch</span>
          <span className="text-sm font-bold text-slate-900">350.000 VNĐ</span>
        </div>
        <div className="flex justify-between items-center text-teal-600">
          <span className="text-sm font-medium flex items-center gap-1.5">
            <CheckCircle2 size={16} />
            BHYT điện tử khấu trừ (80%)
          </span>
          <span className="text-sm font-bold">-280.000 VNĐ</span>
        </div>
      </div>

      <div className="bg-sky-50 border border-sky-100 rounded-xl p-4 flex justify-between items-center mb-4">
        <span className="text-base font-bold text-slate-800">Tạm tính người bệnh thanh toán:</span>
        <span className="text-xl font-bold text-sky-700">70.000 VNĐ</span>
      </div>

      <div className="flex items-start gap-2 text-xs text-slate-500">
        <Info size={14} className="flex-shrink-0 mt-0.5" />
        <p>Chưa bao gồm các dịch vụ kỹ thuật cận lâm sàng (ECG, Siêu âm tim) sẽ phát sinh theo chỉ định thực tế.</p>
      </div>
    </div>
  );
}
