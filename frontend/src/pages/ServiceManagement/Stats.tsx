import React from 'react';
import { Package, CalendarCheck, TrendingUp, Settings } from 'lucide-react';

export function Stats() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Stat 1 */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden group">
        <div className="flex justify-between items-start mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase">Tổng số gói phát hành</p>
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
            <Package size={20} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <h3 className="text-4xl font-black text-slate-900 tracking-tight">16</h3>
          <span className="text-sm font-semibold text-slate-600">Gói hoạt động</span>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-slate-500">
          <div className="flex items-center gap-1.5 text-teal-600"><div className="w-2 h-2 rounded-full bg-teal-500"></div> 14 Đang mở bán</div>
          <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-slate-300"></div> 2 Gói bảo trì</div>
        </div>
      </div>

      {/* Stat 2 */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex justify-between items-start mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase">Lượt đăng ký khám (Tháng 5)</p>
          <div className="p-2 bg-teal-50 text-teal-600 rounded-lg">
            <CalendarCheck size={20} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <h3 className="text-4xl font-black text-sky-600 tracking-tight">2.840</h3>
          <span className="text-xs font-bold text-teal-600 bg-teal-50 px-1.5 py-0.5 rounded">↗+14.6%</span>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-slate-500">
          <div>68% Đặt qua Mobile App</div>
          <div>32% Tại viện</div>
        </div>
      </div>

      {/* Stat 3 */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex justify-between items-start mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase">Doanh thu khám định kỳ</p>
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
            <TrendingUp size={20} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <h3 className="text-4xl font-black text-slate-900 tracking-tight">4.2</h3>
          <span className="text-sm font-semibold text-slate-600">Tỷ VNĐ</span>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between gap-2 text-[10px] font-medium text-slate-500 leading-tight">
          <div className="flex-1 border-r border-slate-100">Đạt 108% Kế hoạch quý</div>
          <div className="flex-1">B2B: 1.8 Tỷ</div>
          <div className="flex-1 text-teal-600">Bảo hiểm: 28%</div>
        </div>
      </div>

      {/* Stat 4 */}
      <div className="bg-sky-800 p-5 rounded-xl border border-sky-700 shadow-sm text-white">
        <div className="flex justify-between items-start mb-2">
          <p className="text-xs font-bold text-sky-200 uppercase flex items-center gap-1">⭐ Gói phổ biến nhất</p>
          <div className="p-1.5 bg-sky-700 text-sky-300 rounded-lg">
            <Settings size={18} />
          </div>
        </div>
        <h3 className="text-lg font-bold leading-tight mb-3">Khám Tổng Quát Toàn Diện Platinum</h3>
        <div className="flex items-center gap-2 mb-4">
          <span className="bg-sky-700 px-2 py-0.5 rounded text-xs font-semibold">842 Lượt book</span>
          <span className="text-xs text-sky-200">Đánh giá 4.9/5 ★</span>
        </div>
        <div className="pt-3 border-t border-sky-700 flex justify-between items-center text-xs">
          <span className="text-sky-200">Tỷ lệ hài lòng: 98.4%</span>
          <span className="font-semibold text-white hover:underline cursor-pointer">Xem chi tiết →</span>
        </div>
      </div>
    </div>
  );
}
