import React from 'react';
import { Eye, Clock } from 'lucide-react';
import { ServiceForm } from './index';

interface Props {
  form: ServiceForm;
}

export function PreviewSidebar({ form }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-6">
      <div className="bg-sky-700 p-3 flex items-center justify-between">
        <span className="text-xs font-semibold text-white flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400"></div>
          Xem trước hiển thị App
        </span>
        <button className="text-white/80 hover:text-white"><Eye size={16} /></button>
      </div>

      <div className="relative h-24 bg-slate-100">
        <div className="absolute inset-0 bg-gradient-to-br from-sky-900 to-sky-700 opacity-90 mix-blend-multiply"></div>
        <img src={`https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=600&q=80`} alt="Service Background" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-black/40"></div>
        
        <div className="absolute top-2 left-2 flex gap-1.5">
          <span className="px-2 py-0.5 bg-sky-600 text-white text-[9px] font-bold rounded uppercase tracking-wider">Tiêu Chuẩn</span>
          <span className="px-2 py-0.5 bg-white/20 backdrop-blur-md text-white border border-white/30 text-[9px] font-bold rounded uppercase tracking-wider">
            Mã: {form.code || 'CODE'}
          </span>
        </div>
      </div>

      <div className="p-4 border-b border-slate-100">
        <h3 className="text-base font-bold text-slate-900 mb-2 leading-tight">{form.name || 'Tên dịch vụ hiển thị ở đây'}</h3>
        
        <div className="flex justify-between items-end mt-3">
          <div>
            <p className="text-lg font-bold text-sky-700">Giá tham khảo</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-slate-500 flex items-center gap-1 justify-end"><Clock size={10} /> Dự kiến</p>
            <p className="text-xs font-semibold text-teal-600 mt-0.5">{form.duration_minutes || 0} phút</p>
          </div>
        </div>
      </div>

      <div className="p-4 bg-slate-50 text-xs text-slate-600 leading-relaxed min-h-[100px]">
        {form.description || 'Mô tả dịch vụ sẽ được hiển thị tại đây khi khách hàng xem chi tiết...'}
      </div>
    </div>
  );
}
