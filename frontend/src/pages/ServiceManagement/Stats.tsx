import React from 'react';
import { Package, CalendarCheck, TrendingUp, Settings } from 'lucide-react';
import { Service } from './api';

interface Props {
  services: Service[];
  loaded: boolean;
}

export function Stats({ services, loaded }: Props) {
  const activeCount = services.filter((service) => service.status === 'active').length;
  const inactiveCount = services.filter((service) => service.status === 'inactive').length;
  const mostUsedService = services
    .filter((service) => service.patient_count != null)
    .sort((left, right) => (right.patient_count ?? 0) - (left.patient_count ?? 0))[0];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden group">
        <div className="flex justify-between items-start mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase">Tổng số dịch vụ</p>
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg"><Package size={20} /></div>
        </div>
        <div className="flex items-baseline gap-2">
          <h3 className="text-4xl font-black text-slate-900 tracking-tight">{loaded ? services.length : '—'}</h3>
          <span className="text-sm font-semibold text-slate-600">dịch vụ</span>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-slate-500">
          <div className="flex items-center gap-1.5 text-teal-600"><div className="w-2 h-2 rounded-full bg-teal-500"></div> {loaded ? activeCount : '—'} đang mở bán</div>
          <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-slate-300"></div> {loaded ? inactiveCount : '—'} tạm ngưng</div>
        </div>
      </div>

      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex justify-between items-start mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase">Lượt đăng ký khám</p>
          <div className="p-2 bg-teal-50 text-teal-600 rounded-lg"><CalendarCheck size={20} /></div>
        </div>
        <div className="flex items-baseline gap-2">
          <h3 className="text-4xl font-black text-sky-600 tracking-tight">—</h3>
          <span className="text-xs font-bold text-slate-600">chưa có dữ liệu</span>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-slate-500">
          <div>Thống kê lượt khám chưa được cung cấp bởi API.</div>
        </div>
      </div>

      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex justify-between items-start mb-4">
          <p className="text-xs font-bold text-slate-500 uppercase">Doanh thu khám</p>
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><TrendingUp size={20} /></div>
        </div>
        <div className="flex items-baseline gap-2">
          <h3 className="text-4xl font-black text-slate-900 tracking-tight">—</h3>
          <span className="text-sm font-semibold text-slate-600">chưa có dữ liệu</span>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between gap-2 text-[10px] font-medium text-slate-500 leading-tight">
          <div className="flex-1">API hiện không cung cấp số liệu doanh thu.</div>
        </div>
      </div>

      <div className="bg-sky-800 p-5 rounded-xl border border-sky-700 shadow-sm text-white">
        <div className="flex justify-between items-start mb-2">
          <p className="text-xs font-bold text-sky-200 uppercase flex items-center gap-1">Gói có nhiều lượt khám</p>
          <div className="p-1.5 bg-sky-700 text-sky-300 rounded-lg"><Settings size={18} /></div>
        </div>
        <h3 className="text-lg font-bold leading-tight mb-3">{mostUsedService?.name || (loaded ? 'Chưa có dữ liệu lượt khám' : 'Đang tải…')}</h3>
        <div className="flex items-center gap-2 mb-4">
          <span className="bg-sky-700 px-2 py-0.5 rounded text-xs font-semibold">{mostUsedService ? `${mostUsedService.patient_count?.toLocaleString('vi-VN')} lượt khám` : '—'}</span>
          <span className="text-xs text-sky-200">{mostUsedService?.satisfaction_rate != null ? `${mostUsedService.satisfaction_rate}% hài lòng` : 'Chưa có đánh giá'}</span>
        </div>
        <div className="pt-3 border-t border-sky-700 flex justify-between items-center text-xs">
          <span className="text-sky-200">Dữ liệu theo danh sách dịch vụ</span>
        </div>
      </div>
    </div>
  );
}
