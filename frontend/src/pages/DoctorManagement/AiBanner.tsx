import React from 'react';
import { Activity } from 'lucide-react';

export function AiBanner() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 mt-2">
      <div className="flex items-start md:items-center gap-4">
        <div className="w-12 h-12 bg-teal-700 rounded-xl flex items-center justify-center text-white shrink-0 shadow-sm">
          <Activity size={24} />
        </div>
        <div>
          <h4 className="text-base font-bold text-slate-900 flex items-center flex-wrap gap-2">
            VCare+ Cân Bằng Tải Lâm Sàng Tuần Tới
            <span className="px-2 py-0.5 bg-teal-100 text-teal-700 text-[10px] font-bold rounded uppercase">HITL Active</span>
          </h4>
          <p className="text-sm text-slate-600 mt-1 max-w-4xl">
            Thuật toán phát hiện khả năng quá tải +34% tại Khoa Tim Mạch vào sáng Thứ Tư tuần tới. Khuyến nghị điều chuyển 2 bác sĩ dự phòng từ Cơ sở 2 sang Cơ sở 1.
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <button className="px-5 py-2.5 bg-white border border-slate-300 text-slate-700 rounded-lg font-semibold text-sm hover:bg-slate-50 transition-colors">
          Bỏ qua
        </button>
        <button className="px-5 py-2.5 bg-teal-700 text-white rounded-lg font-semibold text-sm hover:bg-teal-800 transition-colors shadow-sm whitespace-nowrap">
          Áp Dụng Điều Chuyển
        </button>
      </div>
    </div>
  );
}
