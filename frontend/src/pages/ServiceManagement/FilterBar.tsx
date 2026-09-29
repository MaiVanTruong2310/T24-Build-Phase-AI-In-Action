import React from 'react';
import { Search, Filter, X } from 'lucide-react';

export function FilterBar() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-sm flex flex-col lg:flex-row gap-3 items-center justify-between">
      <div className="flex items-center gap-3 w-full lg:w-auto">
        <div className="relative w-full lg:w-[280px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Tìm kiếm mã, tên gói khám..."
            className="w-full pl-9 pr-8 py-2 bg-slate-50 border border-transparent focus:border-sky-300 focus:bg-white rounded-lg text-sm outline-none transition-all"
          />
          <button className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
            <X size={14} />
          </button>
        </div>
        
        <div className="hidden md:flex bg-slate-100 p-1 rounded-lg">
          <button className="px-4 py-1.5 bg-sky-700 text-white rounded-md text-xs font-semibold shadow-sm">Tất cả (16)</button>
          <button className="px-4 py-1.5 text-slate-600 hover:text-slate-900 rounded-md text-xs font-medium">Cá nhân & Gia đình</button>
          <button className="px-4 py-1.5 text-slate-600 hover:text-slate-900 rounded-md text-xs font-medium">Doanh nghiệp (B2B)</button>
          <button className="px-4 py-1.5 text-slate-600 hover:text-slate-900 rounded-md text-xs font-medium">Tầm soát ung thư</button>
        </div>
      </div>
      
      <div className="flex items-center gap-3 w-full lg:w-auto overflow-x-auto pb-1 lg:pb-0">
        <select className="pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:border-sky-500 min-w-[150px]">
          <option>Mức giá: Mọi khoảng giá</option>
          <option>Dưới 1.000.000 VNĐ</option>
          <option>1tr - 3tr VNĐ</option>
          <option>Trên 3.000.000 VNĐ</option>
        </select>
        
        <select className="pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:border-sky-500 min-w-[150px]">
          <option>Trạng thái: Đang áp dụng</option>
          <option>Đang mở bán</option>
          <option>Tạm ngưng</option>
        </select>
        
        <button className="p-2 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50">
          <Filter size={18} />
        </button>
      </div>
    </div>
  );
}
