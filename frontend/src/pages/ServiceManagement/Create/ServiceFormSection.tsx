import React from 'react';
import { FileText } from 'lucide-react';
import { ServiceForm } from './index';

interface Props {
  form: ServiceForm;
  errors: Partial<Record<keyof ServiceForm, string>>;
  onChange: (field: keyof ServiceForm, value: string | number) => void;
}

export function ServiceFormSection({ form, errors, onChange }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-100 text-sky-700 rounded-lg">
            <FileText size={20} />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">1. Thông tin dịch vụ</h2>
            <p className="text-xs text-slate-500">Định danh dịch vụ bắt buộc</p>
          </div>
        </div>
        <span className="text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-1 rounded">(*) Bắt buộc</span>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">Tên dịch vụ <span className="text-rose-500">*</span></label>
            <input 
              type="text" 
              value={form.name}
              onChange={(e) => onChange('name', e.target.value)}
              className={`w-full px-3 py-2 bg-slate-50 border ${errors.name ? 'border-rose-300 focus:border-rose-500' : 'border-transparent focus:border-sky-300'} focus:bg-white rounded-lg text-sm outline-none transition-all`}
              placeholder="VD: Khám tổng quát cơ bản"
            />
            {errors.name && <p className="text-rose-500 text-[10px] mt-1">{errors.name}</p>}
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">Mã dịch vụ <span className="text-rose-500">*</span></label>
            <input 
              type="text" 
              value={form.code}
              onChange={(e) => onChange('code', e.target.value)}
              className={`w-full px-3 py-2 bg-slate-50 border ${errors.code ? 'border-rose-300 focus:border-rose-500' : 'border-transparent focus:border-sky-300'} focus:bg-white rounded-lg text-sm outline-none transition-all uppercase`}
              placeholder="VD: PKG-GEN-01"
            />
            {errors.code && <p className="text-rose-500 text-[10px] mt-1">{errors.code}</p>}
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">Thời gian dự kiến (phút) <span className="text-rose-500">*</span></label>
            <input 
              type="number" 
              value={form.duration_minutes}
              onChange={(e) => onChange('duration_minutes', parseInt(e.target.value) || 0)}
              className={`w-full px-3 py-2 bg-slate-50 border ${errors.duration_minutes ? 'border-rose-300 focus:border-rose-500' : 'border-transparent focus:border-sky-300'} focus:bg-white rounded-lg text-sm outline-none transition-all`}
            />
            {errors.duration_minutes && <p className="text-rose-500 text-[10px] mt-1">{errors.duration_minutes}</p>}
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1.5">Mô tả dịch vụ</label>
          <textarea 
            value={form.description}
            onChange={(e) => onChange('description', e.target.value)}
            className="w-full px-3 py-2 bg-slate-50 border border-transparent focus:border-sky-300 focus:bg-white rounded-lg text-sm outline-none transition-all min-h-[120px]"
            placeholder="Nhập mô tả chi tiết cho dịch vụ này..."
          />
        </div>
      </div>
    </div>
  );
}
