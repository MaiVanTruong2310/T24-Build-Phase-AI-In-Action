import React from 'react';
import { Search, Filter, X } from 'lucide-react';

export interface ServiceFilters {
  search: string;
  category: string;
  priceRange: string;
  status: string;
}

interface Props {
  filters: ServiceFilters;
  categories: string[];
  onChange: (filters: ServiceFilters) => void;
}

export function FilterBar({ filters, categories, onChange }: Props) {
  const update = (values: Partial<ServiceFilters>) => onChange({ ...filters, ...values });

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-sm flex flex-col lg:flex-row gap-3 items-center justify-between">
      <div className="flex items-center gap-3 w-full lg:w-auto">
        <div className="relative w-full lg:w-[280px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={filters.search}
            onChange={(event) => update({ search: event.target.value })}
            placeholder="Tìm kiếm mã, tên gói khám..."
            className="w-full pl-9 pr-8 py-2 bg-slate-50 border border-transparent focus:border-sky-300 focus:bg-white rounded-lg text-sm outline-none transition-all"
          />
          <button type="button" aria-label="Xóa nội dung tìm kiếm" onClick={() => update({ search: '' })} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
            <X size={14} />
          </button>
        </div>

        <div className="hidden md:flex bg-slate-100 p-1 rounded-lg">
          {['', ...categories].map((category) => (
            <button type="button" key={category || 'all'} onClick={() => update({ category })} aria-pressed={filters.category === category} className={`px-4 py-1.5 rounded-md text-xs font-medium ${filters.category === category ? 'bg-sky-700 text-white font-semibold shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
              {category || 'Tất cả'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3 w-full lg:w-auto overflow-x-auto pb-1 lg:pb-0">
        <select aria-label="Lọc theo mức giá" value={filters.priceRange} onChange={(event) => update({ priceRange: event.target.value })} className="pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:border-sky-500 min-w-[150px]">
          <option value="">Mức giá: Mọi khoảng giá</option>
          <option value="under-1m">Dưới 1.000.000 VNĐ</option>
          <option value="1m-3m">1tr - 3tr VNĐ</option>
          <option value="over-3m">Trên 3.000.000 VNĐ</option>
        </select>

        <select aria-label="Lọc theo trạng thái" value={filters.status} onChange={(event) => update({ status: event.target.value })} className="pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:border-sky-500 min-w-[150px]">
          <option value="">Trạng thái: Tất cả</option>
          <option value="active">Đang mở bán</option>
          <option value="inactive">Tạm ngưng</option>
        </select>

        <button type="button" aria-label="Xóa tất cả bộ lọc" onClick={() => onChange({ search: '', category: '', priceRange: '', status: '' })} className="p-2 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50">
          <Filter size={18} />
        </button>
      </div>
    </div>
  );
}
