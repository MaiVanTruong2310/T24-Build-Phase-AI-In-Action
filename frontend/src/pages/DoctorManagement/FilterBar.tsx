import React from 'react';
import { Search, ChevronDown, Filter, X } from 'lucide-react';

export function FilterBar() {
  return (
    <div className="p-4 border-b border-slate-200">
      <div className="flex flex-col md:flex-row gap-4 mb-4">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Tìm theo tên bác sĩ, mã BS, số CCHN..." 
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
          />
        </div>
        
        <div className="relative w-full md:w-64">
          <select className="w-full appearance-none pl-4 pr-10 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500">
            <option>Tất cả chuyên khoa</option>
            <option>Tim Mạch Can Thiệp</option>
            <option>Thần Kinh & Cột Sống</option>
            <option>Cấp Cứu & Đa Khoa</option>
            <option>Tiêu Hóa & Gan Mật</option>
            <option>Nhi Sơ Sinh</option>
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>

        <div className="relative w-full md:w-64">
          <select className="w-full appearance-none pl-4 pr-10 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:border-sky-500">
            <option>Tất cả cơ sở bệnh viện</option>
            <option>Cơ sở 1 - Q.10</option>
            <option>Cơ sở 2 - Thủ Đức</option>
            <option>Cơ sở 3 - Đống Đa</option>
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>

        <button className="flex items-center justify-between px-4 py-2 bg-slate-50 border border-slate-200 text-slate-700 rounded-lg font-medium text-sm hover:bg-slate-100 md:min-w-[160px]">
          Tất cả trạng thái <Filter size={16} className="text-slate-400" />
        </button>
      </div>

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-500">Bộ lọc đang áp dụng:</span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-sky-50 border border-sky-100 text-sky-700 text-sm rounded-full">
            Cơ sở: Toàn hệ thống
            <X size={14} className="cursor-pointer text-sky-400 hover:text-sky-600" />
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-teal-50 border border-teal-100 text-teal-700 text-sm rounded-full">
            Đang làm việc & Trực
            <X size={14} className="cursor-pointer text-teal-500 hover:text-teal-700" />
          </span>
          <button className="text-sm text-sky-600 hover:text-sky-700 font-medium">Xóa tất cả</button>
        </div>
        <div className="text-sm text-slate-500">
          Hiển thị <span className="font-semibold text-slate-900">10</span> trên tổng số <span className="font-semibold text-slate-900">148</span> kết quả
        </div>
      </div>
    </div>
  );
}
