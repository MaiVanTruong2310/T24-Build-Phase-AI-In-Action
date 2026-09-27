import React from 'react';
import { Stethoscope, Activity, FileText, Star } from 'lucide-react';

export function Stats() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-sm font-medium text-slate-500">Tổng Bác Sĩ Hệ Thống</h3>
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
            <Stethoscope size={18} />
          </div>
        </div>
        <div className="flex items-end gap-3 mb-2">
          <span className="text-4xl font-bold text-slate-900">148</span>
          <span className="text-sm font-medium text-teal-600 mb-1 flex items-center">
             ~+12 tháng này
          </span>
        </div>
        <p className="text-xs text-slate-500">32 PGS/TS · 74 BSCKII/ThS · 42 Bác sĩ Trẻ</p>
      </div>

      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-sm font-medium text-slate-500">Đang Trực Tuyến & Lâm Sàng</h3>
          <div className="p-2 bg-teal-50 text-teal-600 rounded-lg">
            <Activity size={18} />
          </div>
        </div>
        <div className="flex items-end gap-3 mb-2">
          <span className="text-4xl font-bold text-slate-900">42</span>
          <span className="text-xs font-medium bg-teal-100 text-teal-700 px-2 py-0.5 rounded-full mb-1">
            28.4% Lực lượng
          </span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-1.5 mb-2 overflow-hidden">
          <div className="bg-teal-600 h-1.5 rounded-full" style={{ width: '28.4%' }}></div>
        </div>
        <p className="text-xs text-slate-500 text-right">34 khám, 8 cấp cứu</p>
      </div>

      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-sm font-medium text-slate-500">Tải Công Việc Trung Bình</h3>
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
            <FileText size={18} />
          </div>
        </div>
        <div className="flex items-center gap-4 mb-2">
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-bold text-slate-900">78</span>
            <span className="text-xl font-medium text-slate-500">%</span>
          </div>
          <div className="w-8 h-8 rounded-full border-4 border-slate-100 border-t-sky-600 border-r-sky-600 border-b-sky-600 transform rotate-45"></div>
        </div>
        <p className="text-xs text-slate-500 flex justify-between">
          <span>Ngưỡng tối ưu: 65% - 85%</span>
          <span className="text-teal-600 font-medium">An toàn tải</span>
        </p>
      </div>

      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-sm font-medium text-slate-500">Đánh Giá Chuyên Môn</h3>
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
            <Star size={18} />
          </div>
        </div>
        <div className="flex items-baseline gap-1 mb-2">
          <span className="text-4xl font-bold text-slate-900">4.92</span>
          <span className="text-sm text-slate-500 font-medium">/ 5.0</span>
          <span className="text-xs text-teal-600 font-medium ml-2">99.1% Hài lòng</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex text-amber-400 gap-0.5">
            <Star size={14} fill="currentColor" />
            <Star size={14} fill="currentColor" />
            <Star size={14} fill="currentColor" />
            <Star size={14} fill="currentColor" />
            <Star size={14} fill="currentColor" />
          </div>
          <span className="text-xs text-slate-500">18,420 lượt bình chọn</span>
        </div>
      </div>
    </div>
  );
}
