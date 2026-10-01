import React from 'react';
import { Service } from './api';
import { Clock, CheckCircle2, Copy, FileEdit, ArrowRight, UserCircle, Star } from 'lucide-react';

interface Props {
  services: Service[];
}

export function ServiceGrid({ services }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {services.map((service) => (
        <div key={service.id} className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm flex flex-col group hover:shadow-md transition-shadow">
          {/* Header Area with Banner */}
          <div className="relative h-40 bg-slate-100">
            {/* Banner Placeholder */}
            <div className="absolute inset-0 bg-gradient-to-br from-sky-900 to-sky-700 opacity-90 mix-blend-multiply"></div>
            <img src={`https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=600&q=80`} alt="Service Background" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-black/40"></div>
            
            {/* Badges */}
            <div className="absolute top-3 left-3 flex gap-2">
              <span className="px-2.5 py-1 bg-sky-600 text-white text-[10px] font-bold rounded uppercase tracking-wider">{service.category || 'Dịch vụ'}</span>
              <span className="px-2.5 py-1 bg-white/20 backdrop-blur-md text-white border border-white/30 text-[10px] font-bold rounded uppercase tracking-wider">Mã: {service.code}</span>
            </div>
            
            <div className="absolute top-3 right-3">
              <span className={`px-2 py-1 flex items-center gap-1.5 rounded-full text-[10px] font-bold ${service.status === 'active' ? 'bg-emerald-500 text-white' : 'bg-slate-500 text-white'}`}>
                <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                {service.status === 'active' ? 'Đang mở bán' : 'Tạm ngưng'}
              </span>
            </div>
            
            {/* Title */}
            <div className="absolute bottom-4 left-4 right-4">
              <h3 className="text-xl font-bold text-white leading-tight drop-shadow-md">{service.name}</h3>
            </div>
          </div>
          
          {/* Body Content */}
          <div className="p-5 flex-1 flex flex-col">
            <div className="flex justify-between items-end mb-4 border-b border-slate-100 pb-4">
              <div>
                <p className="text-xs text-slate-400 line-through decoration-slate-300">{service.original_price ? service.original_price.toLocaleString('vi-VN') : (service.price ? (service.price * 1.2).toLocaleString('vi-VN') : '0')} VNĐ</p>
                <p className="text-2xl font-bold text-sky-700">{service.price ? service.price.toLocaleString('vi-VN') : '0'} <span className="text-sm font-semibold text-slate-500">VNĐ</span></p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500 flex items-center gap-1 justify-end"><Clock size={12} /> Dự kiến: {service.duration_minutes} phút</p>
                {service.features && <p className="text-xs font-semibold text-teal-600 mt-1">{service.features.length} Danh mục kỹ thuật</p>}
              </div>
            </div>
            
            <div className="flex-1 mb-5">
              <p className="text-xs font-bold text-slate-700 uppercase mb-3">Hạng mục khám lâm sàng & Cận lâm sàng:</p>
              <ul className="space-y-2.5">
                {service.features?.map((feature, idx) => (
                  <li key={idx} className="flex gap-2 text-sm text-slate-600 leading-snug">
                    <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              {service.features && service.features.length > 0 && (
                <p className="text-xs font-semibold text-sky-600 mt-3 cursor-pointer hover:underline flex items-center gap-1">
                  Xem thêm <ArrowRight size={12} />
                </p>
              )}
            </div>
            
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg mb-5 text-xs font-semibold">
              <div className="flex items-center gap-1 text-slate-700">
                <UserCircle size={16} className="text-slate-400" />
                Lượt đã khám: <span className="text-slate-900">{service.patient_count?.toLocaleString() ?? 'Chưa cập nhật'}{service.patient_count !== null && ' bệnh nhân'}</span>
              </div>
              <div className="flex items-center gap-1 text-sky-600">
                <Star size={14} className="fill-sky-600" />
                {service.satisfaction_rate !== null ? `${service.satisfaction_rate}% hài lòng` : 'Chưa cập nhật'}
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3 mt-auto">
              <button className="flex items-center justify-center gap-2 px-3 py-2 text-sky-700 bg-sky-50 hover:bg-sky-100 rounded-lg text-sm font-semibold transition-colors">
                <Copy size={16} /> Cấu hình (18)
              </button>
              <button className="flex items-center justify-center gap-2 px-3 py-2 text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-semibold transition-colors">
                <FileEdit size={16} /> Sửa chi tiết
              </button>
            </div>
          </div>
          
          <div className="px-5 py-3 border-t border-slate-100 bg-slate-50 flex justify-between items-center text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" defaultChecked={service.status === 'active'} />
                <div className="w-8 h-4 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-emerald-500"></div>
              </label>
              <span className="font-medium">Hiển thị App/Web</span>
            </div>
            <div className="text-[10px]">Cập nhật: {new Date(service.updated_at).toLocaleDateString('vi-VN')}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
