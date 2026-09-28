import { Activity, Info } from 'lucide-react';

export function TriageInfo() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <div className="font-bold text-slate-900 flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-500" />
          Chỉ Số Sơ Lược & Khuyến Cáo Trước Khám
        </div>
        <div className="bg-emerald-100 text-emerald-700 text-xs font-bold px-2.5 py-1 rounded-md">
          Triage: Độ 2
        </div>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
            <div className="text-[10px] text-slate-500 font-semibold mb-1">Nhịp tim tự đo</div>
            <div className="text-xl font-bold text-sky-700">88 bpm</div>
            <div className="text-[10px] font-medium text-emerald-600 mt-1">Ổn định</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
            <div className="text-[10px] text-slate-500 font-semibold mb-1">Huyết áp gần nhất</div>
            <div className="text-xl font-bold text-slate-900">135/85</div>
            <div className="text-[10px] font-medium text-amber-600 mt-1">Tiền tăng HA</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
            <div className="text-[10px] text-slate-500 font-semibold mb-1">Điện tâm đồ (ECG AI)</div>
            <div className="text-xl font-bold text-emerald-600">Sinus</div>
            <div className="text-[10px] font-medium text-slate-500 mt-1">Nhịp xoang đều</div>
          </div>
        </div>
        <div className="flex gap-2 text-xs text-slate-600 bg-amber-50 p-3 rounded-lg border border-amber-100">
          <Info className="w-4 h-4 text-amber-500 shrink-0" />
          <span>Vui lòng nhịn ăn trước 4 tiếng nếu có chỉ định xét nghiệm lipid máu đi kèm.</span>
        </div>
      </div>
    </div>
  )
}
